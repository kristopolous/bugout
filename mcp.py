#!/usr/bin/env python3
"""
MCP Server: Bug Report Analyzer
Analyzes bug comments for an issue # and produces frequency distributions
to help generate better PRDs.
"""

import json
import sys
from collections import Counter
from typing import Any

# MCP server uses stdio transport
# pip install mcp

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

app = Server("bug-analyzer")

# ---------------------------------------------------------------------------
# In-memory store: issue_id -> list of bug report dicts
# In production, swap this for a DB / Jira / GitHub API call
# ---------------------------------------------------------------------------
BUG_DATABASE: dict[str, list[dict]] = {
    "1234": [
        {
            "software_version": "2.1.0",
            "platform": "macOS",
            "bug_behaviour": "App crashes on launch",
            "crash": True,
            "user_frustration": "high",
            "technical_description": "NullPointerException in startup module",
            "input_data": "No special input, fresh install",
            "expected_behaviour": "App should open to home screen",
        },
        {
            "software_version": "2.1.0",
            "platform": "Windows",
            "bug_behaviour": "App crashes on launch",
            "crash": True,
            "user_frustration": "high",
            "technical_description": "Missing DLL on Windows 10",
            "input_data": "No special input",
            "expected_behaviour": "App should open to home screen",
        },
        {
            "software_version": "2.0.5",
            "platform": "macOS",
            "bug_behaviour": "Slow performance",
            "crash": False,
            "user_frustration": "medium",
            "technical_description": "Memory leak in rendering loop",
            "input_data": "Large dataset > 10k rows",
            "expected_behaviour": "Smooth rendering under 100ms",
        },
        {
            "software_version": "2.1.0",
            "platform": "Linux",
            "bug_behaviour": "App crashes on launch",
            "crash": True,
            "user_frustration": "high",
            "technical_description": "Segfault on glibc 2.31",
            "input_data": "Ubuntu 20.04",
            "expected_behaviour": "App should open to home screen",
        },
    ]
}


# ---------------------------------------------------------------------------
# Core analysis logic
# ---------------------------------------------------------------------------

def compute_frequency(values: list) -> list[list]:
    """Return [[value, count], ...] sorted by count descending."""
    counter = Counter(str(v) for v in values)
    return [[v, c] for v, c in counter.most_common()]


CATEGORICAL_FIELDS = [
    "software_version",
    "platform",
    "bug_behaviour",
    "crash",
    "user_frustration",
]

TEXT_FIELDS = [
    "technical_description",
    "input_data",
    "expected_behaviour",
]


def analyze_issue(issue_id: str, reports: list[dict]) -> dict:
    """
    Build:
      - frequency distributions for categorical fields
      - aggregated text summaries for freeform fields
      - a PRD-ready summary block
    """
    frequency_dist: dict[str, list] = {}

    for field in CATEGORICAL_FIELDS:
        values = [r.get(field) for r in reports if field in r]
        frequency_dist[field] = compute_frequency(values)

    # Collect unique text entries for freeform fields
    text_aggregates: dict[str, list[str]] = {}
    for field in TEXT_FIELDS:
        seen = []
        for r in reports:
            v = r.get(field, "").strip()
            if v and v not in seen:
                seen.append(v)
        text_aggregates[field] = seen

    # Derive crash rate
    crash_flags = [r.get("crash", False) for r in reports]
    crash_rate = round(sum(1 for c in crash_flags if c) / len(crash_flags) * 100, 1) if crash_flags else 0

    # Most common frustration level
    frustration_dist = dict(frequency_dist.get("user_frustration", []))
    top_frustration = max(frustration_dist, key=frustration_dist.get) if frustration_dist else "unknown"

    prd_summary = {
        "issue_id": issue_id,
        "total_reports": len(reports),
        "crash_rate_pct": crash_rate,
        "dominant_frustration_level": top_frustration,
        "top_affected_platform": frequency_dist["platform"][0][0] if frequency_dist.get("platform") else "unknown",
        "top_affected_version": frequency_dist["software_version"][0][0] if frequency_dist.get("software_version") else "unknown",
        "primary_bug_behaviour": frequency_dist["bug_behaviour"][0][0] if frequency_dist.get("bug_behaviour") else "unknown",
    }

    return {
        "frequency_distributions": frequency_dist,
        "text_aggregates": text_aggregates,
        "prd_summary": prd_summary,
    }


# ---------------------------------------------------------------------------
# MCP Tool definitions
# ---------------------------------------------------------------------------

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="analyze_bug_reports",
            description=(
                "Given a bug issue number and a list of bug report objects, "
                "returns frequency distributions across key fields "
                "(software_version, platform, bug_behaviour, crash, user_frustration) "
                "plus aggregated text entries and a PRD-ready summary block."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_id": {
                        "type": "string",
                        "description": "The bug/issue ticket number (e.g. '1234')",
                    },
                    "reports": {
                        "type": "array",
                        "description": (
                            "List of bug report objects. Each object may contain: "
                            "software_version, platform, bug_behaviour, crash (bool), "
                            "user_frustration, technical_description, input_data, expected_behaviour."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "software_version": {"type": "string"},
                                "platform": {"type": "string"},
                                "bug_behaviour": {"type": "string"},
                                "crash": {"type": "boolean"},
                                "user_frustration": {"type": "string"},
                                "technical_description": {"type": "string"},
                                "input_data": {"type": "string"},
                                "expected_behaviour": {"type": "string"},
                            },
                        },
                    },
                },
                "required": ["issue_id", "reports"],
            },
        ),
        Tool(
            name="fetch_and_analyze_issue",
            description=(
                "Fetch bug reports for a known issue_id from the internal database "
                "and return the same frequency distribution + PRD summary. "
                "Use this when you already have the issue stored server-side."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_id": {
                        "type": "string",
                        "description": "The bug/issue ticket number",
                    }
                },
                "required": ["issue_id"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    if name == "analyze_bug_reports":
        issue_id = arguments["issue_id"]
        reports = arguments["reports"]
        result = analyze_issue(issue_id, reports)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "fetch_and_analyze_issue":
        issue_id = arguments["issue_id"]
        reports = BUG_DATABASE.get(issue_id)
        if reports is None:
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Issue '{issue_id}' not found in database."})
            )]
        result = analyze_issue(issue_id, reports)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    else:
        return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
