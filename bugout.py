#!/usr/bin/env python3
"""
bugout.py - Automated bug analysis and patch preparation tool

Usage: python bugout.py <repo> <bug_number>

This tool:
1. Fetches all comments for a GitHub issue using gh CLI
2. Extracts features from comments using parser.py
3. Analyzes bug nature and generates PRD
4. Attempts to fix the bug
5. Finds competent reviewers using Yutori API
6. Prepares a patch folder with all necessary files
"""

import os
import sys
import json
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
from collections import Counter

from review_checker import check_reviewers_bulk, get_best_reviewer

# Load environment variables
OPENAI_HOST = os.environ.get("OPENAI_HOST")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


def summarize_bug_nature(reports: list, issue_title: str = "") -> str:
    """
    Use OpenAI API to summarize the nature of the bug based on all reports.
    Returns a comprehensive summary of the bug's nature, impact, and root causes.
    """
    if not OPENAI_HOST or not OPENAI_MODEL:
        print("  ⚠ OPENAI_HOST or OPENAI_MODEL not set, skipping LLM summary")
        return "No LLM summary available (missing OPENAI_HOST or OPENAI_MODEL)"
    
    # Prepare context from reports
    contexts = []
    for r in reports[:20]:  # Limit to first 20 reports to avoid token limits
        text = r.get("text", "")
        if text:
            contexts.append(text[:500])  # Truncate each to avoid overflow
    
    if not contexts:
        return "No text content available for summarization"
    
    # Build prompt
    prompt = f"""Analyze the following bug reports and provide a comprehensive summary of:
1. The nature and root cause of the bug
2. The impact on users
3. Technical details about what's going wrong
4. Any patterns or commonalities across reports
5. Suggested approach to fixing the issue

Issue Title: {issue_title}

Bug Reports:
"""
    
    for i, ctx in enumerate(contexts, 1):
        prompt += f"\n--- Report {i} ---\n{ctx}\n"
    
    try:
        import requests
        
        headers = {
            "Content-Type": "application/json"
        }
        
        if OPENAI_API_KEY:
            headers["Authorization"] = f"Bearer {OPENAI_API_KEY}"
        
        payload = {
            "model": OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": "You are a technical analyst specializing in bug report analysis. Provide clear, actionable summaries of software issues."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1500
        }
        
        response = requests.post(
            f"{OPENAI_HOST}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        
        result = response.json()
        summary = result["choices"][0]["message"]["content"]
        return summary
        
    except Exception as e:
        print(f"  ⚠ Error generating LLM summary: {e}", file=sys.stderr)
        return f"Error generating summary: {str(e)}"


def run_command(cmd: List[str], cwd: Optional[str] = None, capture_output: bool = True) -> tuple:
    """Run a shell command and return (stdout, stderr, returncode)."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            shell=False
        )
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1


def fetch_issue_comments(repo: str, issue_number: str, output_dir: Path) -> Path:
    """
    Step 1: Fetch all comments for a GitHub issue using gh CLI.
    Saves the output as JSON.
    """
    print(f"Step 1: Fetching comments for {repo}#{issue_number}...")
    
    output_file = output_dir / "issue_comments.json"
    
    # Use gh CLI to fetch issue with comments
    cmd = [
        "gh", "issue", "view", issue_number,
        "--repo", repo,
        "--json", "number,title,state,labels,body,author,createdAt,comments"
    ]
    
    stdout, stderr, rc = run_command(cmd)
    
    if rc != 0:
        print(f"Error fetching issue: {stderr}", file=sys.stderr)
        raise Exception(f"Failed to fetch issue: {stderr}")
    
    # Parse the JSON and reformat for our parser
    issue_data = json.loads(stdout)
    
    # Flatten into rows like comment1.sh does
    rows = []
    
    # Add issue body as first row
    rows.append({
        "issue_number": issue_data["number"],
        "issue_title": issue_data["title"],
        "state": issue_data["state"],
        "labels": ";".join([l["name"] for l in issue_data.get("labels", [])]),
        "author": issue_data["author"]["login"],
        "created_at": issue_data["createdAt"],
        "type": "issue",
        "text": issue_data["body"]
    })
    
    # Add each comment
    for comment in issue_data.get("comments", []):
        rows.append({
            "issue_number": issue_data["number"],
            "issue_title": issue_data["title"],
            "state": issue_data["state"],
            "labels": ";".join([l["name"] for l in issue_data.get("labels", [])]),
            "author": comment["author"]["login"],
            "created_at": comment["createdAt"],
            "type": "comment",
            "text": comment["body"]
        })
    
    # Save to JSON file
    with open(output_file, "w") as f:
        json.dump(rows, f, indent=2)
    
    print(f"  ✓ Saved {len(rows)} entries to {output_file}")
    return output_file


def extract_features(comments_file: Path, output_dir: Path) -> Path:
    """
    Step 2: Use parser.py to extract features from comments.
    Requires FASTINO_KEY environment variable.
    """
    print("Step 2: Extracting features from comments...")
    
    output_file = output_dir / "bugs_with_features.jsonl"
    
    # Run parser.py
    cmd = ["python3", "parser.py", str(comments_file)]
    
    stdout, stderr, rc = run_command(cmd)
    
    if rc != 0:
        print(f"Error extracting features: {stderr}", file=sys.stderr)
        raise Exception(f"Failed to extract features: {stderr}")
    
    # Save output
    with open(output_file, "w") as f:
        f.write(stdout)
    
    # Count lines
    line_count = len(stdout.strip().split("\n")) if stdout.strip() else 0
    print(f"  ✓ Extracted features for {line_count} entries to {output_file}")
    
    return output_file


# Core analysis logic from mcp.py

def compute_frequency(values: list) -> list:
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


def analyze_issue(issue_id: str, reports: list) -> dict:
    """
    Build:
      - frequency distributions for categorical fields
      - aggregated text summaries for freeform fields
      - a PRD-ready summary block
    """
    frequency_dist = {}

    for field in CATEGORICAL_FIELDS:
        values = [r.get(field) for r in reports if field in r]
        frequency_dist[field] = compute_frequency(values)

    # Collect unique text entries for freeform fields
    text_aggregates = {}
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
    top_frustration = max(frustration_dist.items(), key=lambda x: x[1])[0] if frustration_dist else "unknown"

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


def analyze_with_mcp(features_file: Path, issue_id: str, comments_file: Path) -> Dict:
    """
    Step 3: Analyze bug reports and generate PRD summary.
    """
    print("Step 3: Analyzing bug reports...")
    
    # Load features
    reports = []
    with open(features_file) as f:
        for line in f:
            line = line.strip()
            if line:
                reports.append(json.loads(line))
    
    # Get issue title from comments file
    issue_title = ""
    try:
        with open(comments_file) as f:
            rows = json.load(f)
            if rows:
                issue_title = rows[0].get("issue_title", "")
    except:
        pass
    
    result = analyze_issue(issue_id, reports)
    
    # Generate LLM summary of bug nature
    print("  Generating bug nature summary...")
    bug_nature_summary = summarize_bug_nature(reports, issue_title)
    result["bug_nature_summary"] = bug_nature_summary
    
    print(f"  ✓ Generated PRD summary")
    print(f"    - Total reports: {result['prd_summary']['total_reports']}")
    print(f"    - Crash rate: {result['prd_summary']['crash_rate_pct']}%")
    print(f"    - Dominant frustration: {result['prd_summary']['dominant_frustration_level']}")
    
    return result


def generate_prd(mcp_result: Dict, output_dir: Path) -> Path:
    """
    Generate a PRD document from analysis results.
    """
    print("Step 4: Generating PRD...")
    
    prd_file = output_dir / "prd.md"
    
    bug_nature = mcp_result.get('bug_nature_summary', '')
    
    prd = f"""# Product Requirements Document (PRD)

## Bug Analysis Report

**Issue ID:** {mcp_result['prd_summary']['issue_id']}  
**Generated:** {datetime.now().isoformat()}

### Bug Nature Summary

{bug_nature}

### Summary

- **Total Reports:** {mcp_result['prd_summary']['total_reports']}
- **Crash Rate:** {mcp_result['prd_summary']['crash_rate_pct']}%
- **Dominant Frustration Level:** {mcp_result['prd_summary']['dominant_frustration_level']}
- **Top Affected Platform:** {mcp_result['prd_summary']['top_affected_platform']}
- **Top Affected Version:** {mcp_result['prd_summary']['top_affected_version']}
- **Primary Bug Behaviour:** {mcp_result['prd_summary']['primary_bug_behaviour']}

### Frequency Distributions

"""
    
    for field, dist in mcp_result['frequency_distributions'].items():
        prd += f"\n#### {field.replace('_', ' ').title()}\n"
        for value, count in dist:
            prd += f"- {value}: {count}\n"
    
    prd += "\n### Technical Descriptions\n\n"
    for desc in mcp_result['text_aggregates'].get('technical_description', []):
        prd += f"- {desc}\n"
    
    prd += "\n### Expected Behaviour\n\n"
    for exp in mcp_result['text_aggregates'].get('expected_behaviour', []):
        prd += f"- {exp}\n"
    
    prd += "\n### Input Data\n\n"
    for inp in mcp_result['text_aggregates'].get('input_data', []):
        prd += f"- {inp}\n"
    
    prd += """
## Fix Requirements

Based on the analysis above, the fix should address:

1. The primary bug behaviour reported across platforms
2. The crash issues if applicable
3. User frustration points
4. Technical root causes identified

## Implementation Notes

- Consider platform-specific issues
- Test with the input data scenarios described above
- Ensure the fix handles all reported versions
- Verify expected behaviour is met
"""
    
    with open(prd_file, "w") as f:
        f.write(prd)
    
    print(f"  ✓ Generated PRD at {prd_file}")
    return prd_file


def find_commenters(comments_file: Path) -> List[str]:
    """
    Extract unique author usernames from comments.
    """
    with open(comments_file) as f:
        rows = json.load(f)
    
    authors = set()
    for row in rows:
        author = row.get("author")
        if author:
            authors.add(author)
    
    return list(authors)


def find_competent_reviewers(repo: str, authors: List[str]) -> tuple:
    """
    Step 5: Check if comment authors are competent reviewers using Yutori API.
    Returns (best_reviewer, all_results).
    """
    print(f"Step 5: Checking {len(authors)} potential reviewers...")
    
    if not os.environ.get("YUTORI_API_KEY"):
        print("  ⚠ YUTORI_API_KEY not set, skipping reviewer competence check")
        return None, []
    
    results = check_reviewers_bulk(authors, repo)
    
    # Get the best reviewer
    best = get_best_reviewer(results)
    
    print(f"  ✓ Found {len([r for r in results if r.get('scout_id')])} potential reviewers")
    if best:
        print(f"    Best reviewer: {best}")
    
    return best, results


def prepare_patch_folder(
    repo: str,
    issue_number: str,
    prd_file: Path,
    reviewer: Optional[str],
    reviewer_results: List[Dict],
    output_dir: Path
) -> Path:
    """
    Step 6: Prepare patch folder with reviewer.json, patch, prd, and relevant work.
    """
    print("Step 6: Preparing patch folder...")
    
    patch_dir = output_dir / "patch"
    patch_dir.mkdir(exist_ok=True)
    
    # Create reviewer.json
    reviewer_data = {
        "repo": repo,
        "issue_number": issue_number,
        "selected_reviewer": reviewer,
        "all_potential_reviewers": reviewer_results,
        "timestamp": datetime.now().isoformat()
    }
    
    reviewer_file = patch_dir / "reviewer.json"
    with open(reviewer_file, "w") as f:
        json.dump(reviewer_data, f, indent=2)
    
    # Copy PRD
    shutil.copy(prd_file, patch_dir / "prd.md")
    
    # Create placeholder patch file (actual fix would go here)
    patch_file = patch_dir / "fix.patch"
    with open(patch_file, "w") as f:
        f.write("""# Placeholder Patch
# This is where the actual code fix would be applied.
# The fix should be generated based on the PRD analysis.

# To generate the actual fix:
# 1. Clone the repository
# 2. Analyze the PRD to understand the bug
# 3. Make code changes to fix the issue
# 4. Create a git diff
# 5. Save it to this file

# The fix should address:
# - Primary bug behaviour
# - Platform-specific issues
# - Technical root causes
""")
    
    # Copy all relevant work files
    for file in output_dir.iterdir():
        if file.is_file():
            shutil.copy(file, patch_dir / file.name)
    
    print(f"  ✓ Prepared patch folder at {patch_dir}")
    print(f"    - reviewer.json: {reviewer_file}")
    print(f"    - prd.md: {patch_dir / 'prd.md'}")
    print(f"    - fix.patch: {patch_file}")
    print(f"    - All analysis files copied")
    
    return patch_dir


def main():
    if len(sys.argv) < 3:
        print("Usage: python bugout.py <repo> <bug_number>")
        print("Example: python bugout.py microsoft/vscode 12345")
        sys.exit(1)
    
    repo = sys.argv[1]
    issue_number = sys.argv[2]
    
    # Create output directory
    output_dir = Path("bugout_output") / repo.replace("/", "_") / issue_number
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"Bugout Analysis: {repo}#{issue_number}")
    print(f"{'='*60}\n")
    
    try:
        # Step 1: Fetch comments
        comments_file = fetch_issue_comments(repo, issue_number, output_dir)
        
        # Step 2: Extract features
        features_file = extract_features(comments_file, output_dir)
        
        # Step 3: Analyze with MCP
        mcp_result = analyze_with_mcp(features_file, issue_number, comments_file)
        
        # Step 4: Generate PRD
        prd_file = generate_prd(mcp_result, output_dir)
        
        # Step 5: Find competent reviewers
        authors = find_commenters(comments_file)
        reviewer, reviewer_results = find_competent_reviewers(repo, authors)
        
        # Step 6: Prepare patch folder
        patch_dir = prepare_patch_folder(
            repo, issue_number, prd_file, reviewer, reviewer_results, output_dir
        )
        
        print(f"\n{'='*60}")
        print("Bugout Complete!")
        print(f"{'='*60}")
        print(f"\nOutput directory: {output_dir}")
        print(f"Patch folder: {patch_dir}")
        
        if reviewer:
            print(f"\nRecommended reviewer: @{reviewer}")
        
        print(f"\nNext steps:")
        print(f"  1. Review the PRD at {prd_file}")
        print(f"  2. Implement the fix in {patch_dir / 'fix.patch'}")
        print(f"  3. Submit PR with @{reviewer or 'a suitable reviewer'} as reviewer")
        
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
