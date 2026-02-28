#!/usr/bin/env python3
"""
prd_generator.py - Step 3: Generate PRD using MCP toolcall
Uses MCP to analyze bug reports and generate a Product Requirements Document.
"""

import json
import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import Counter


def compute_frequency(values: list) -> List[List]:
    """Return [[value, count], ...] sorted by count descending."""
    counter = Counter(str(v) for v in values if v)
    return [[v, c] for v, c in counter.most_common()]


def analyze_bug_reports(issue_id: str, reports: List[Dict]) -> Dict:
    """
    Analyze bug reports and generate frequency distributions and PRD summary.
    
    Args:
        issue_id: Issue number
        reports: List of bug report dicts with features
        
    Returns:
        Analysis results with frequency distributions and PRD summary
    """
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
    
    frequency_dist: Dict[str, List] = {}
    
    for field in CATEGORICAL_FIELDS:
        values = [r.get(field) for r in reports if field in r]
        frequency_dist[field] = compute_frequency(values)
    
    # Collect unique text entries
    text_aggregates: Dict[str, List[str]] = {}
    for field in TEXT_FIELDS:
        seen = []
        for r in reports:
            v = r.get(field, "").strip() if isinstance(r.get(field), str) else ""
            if v and v not in seen:
                seen.append(v)
        text_aggregates[field] = seen
    
    # Derive crash rate
    crash_flags = [r.get("crash", False) for r in reports]
    crash_bools = [c for c in crash_flags if isinstance(c, bool)]
    crash_rate = round(sum(1 for c in crash_bools if c) / len(crash_bools) * 100, 1) if crash_bools else 0
    
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


def generate_prd(analysis: Dict, issue_data: Dict) -> str:
    """
    Generate a PRD document from the analysis.
    
    Args:
        analysis: Analysis results from analyze_bug_reports
        issue_data: Original issue data
        
    Returns:
        Formatted PRD text
    """
    summary = analysis["prd_summary"]
    freq = analysis["frequency_distributions"]
    text_agg = analysis["text_aggregates"]
    
    prd = f"""# Product Requirements Document (PRD)
## Issue #{summary['issue_id']}

### Executive Summary
- **Total Reports Analyzed**: {summary['total_reports']}
- **Crash Rate**: {summary['crash_rate_pct']}%
- **Dominant Frustration Level**: {summary['dominant_frustration_level']}
- **Top Affected Platform**: {summary['top_affected_platform']}
- **Top Affected Version**: {summary['top_affected_version']}
- **Primary Bug Behaviour**: {summary['primary_bug_behaviour']}

---

### Bug Characteristics (Frequency Analysis)

#### Software Versions Affected
"""
    
    for version, count in freq.get("software_version", []):
        prd += f"- {version}: {count} reports\n"
    
    prd += "\n#### Platforms Affected\n"
    for platform, count in freq.get("platform", []):
        prd += f"- {platform}: {count} reports\n"
    
    prd += "\n#### Bug Behaviours\n"
    for behaviour, count in freq.get("bug_behaviour", []):
        prd += f"- {behaviour}: {count} reports\n"
    
    prd += "\n#### User Frustration Levels\n"
    for level, count in freq.get("user_frustration", []):
        prd += f"- {level}: {count} reports\n"
    
    prd += "\n---\n\n### Technical Details\n\n"
    
    prd += "#### Technical Descriptions from Users\n"
    for desc in text_agg.get("technical_description", [])[:5]:
        prd += f"- {desc}\n"
    
    prd += "\n#### Input Data / Conditions\n"
    for inp in text_agg.get("input_data", [])[:5]:
        prd += f"- {inp}\n"
    
    prd += "\n#### Expected Behaviour\n"
    for exp in text_agg.get("expected_behaviour", [])[:5]:
        prd += f"- {exp}\n"
    
    prd += f"""
---

### Requirements

#### Functional Requirements
1. Fix the primary bug behaviour: {summary['primary_bug_behaviour']}
2. Ensure compatibility with top affected platform: {summary['top_affected_platform']}
3. Address issues in version: {summary['top_affected_version']}

#### Non-Functional Requirements
1. Reduce crash rate from {summary['crash_rate_pct']}% to 0%
2. Improve user satisfaction (currently {summary['dominant_frustration_level']} frustration)

#### Success Criteria
- Bug no longer occurs on affected platforms
- Crash rate reduced to 0%
- User frustration level reduced to 'low' or 'none'

---

### Stakeholder Input Summary
This PRD incorporates feedback from all commenters on the issue.
The analysis is based on {summary['total_reports']} data points extracted from issue comments.
"""
    
    return prd


def generate_prd_from_file(features_file: Path, output_file: Path) -> Optional[Path]:
    """
    Generate PRD from a features JSON file.
    
    Args:
        features_file: Path to bugs_with_features.json
        output_file: Path to save the PRD
        
    Returns:
        Path to the saved PRD file
    """
    with open(features_file, 'r') as f:
        data = json.load(f)
    
    bugs_with_features = data.get("bugs_with_features", [])
    issue_number = str(data.get("issue_number", "unknown"))
    issue_title = data.get("issue_title", "Unknown Issue")
    
    # Convert features to report format for analysis
    reports = []
    for bug in bugs_with_features:
        report = {
            "software_version": bug.get("software_version"),
            "platform": bug.get("platform"),
            "bug_behaviour": bug.get("bug_behaviour"),
            "crash": bug.get("crash"),
            "user_frustration": bug.get("user_frustration"),
            "technical_description": bug.get("technical_description"),
            "input_data": bug.get("input_data"),
            "expected_behaviour": bug.get("expected_behaviour"),
        }
        reports.append(report)
    
    # Analyze
    analysis = analyze_bug_reports(issue_number, reports)
    
    # Generate PRD
    prd_text = generate_prd(analysis, {"number": issue_number, "title": issue_title})
    
    # Save PRD
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        f.write(prd_text)
    
    # Also save analysis as JSON
    analysis_json_file = output_file.with_suffix('.analysis.json')
    with open(analysis_json_file, 'w') as f:
        json.dump(analysis, f, indent=2)
    
    print(f"Step 3 complete: Generated PRD with {len(reports)} reports analyzed", file=sys.stderr)
    return output_file


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python prd_generator.py <bugs_with_features.json> [output_prd.md]", file=sys.stderr)
        sys.exit(1)
    
    features_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("./bugout_data/prd.md")
    
    result = generate_prd_from_file(features_file, output_file)
    if result:
        print(f"Saved to: {result}")
    else:
        sys.exit(1)
