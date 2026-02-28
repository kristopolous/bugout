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
import tempfile
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
from collections import Counter

from review_checker import check_reviewers_bulk, get_best_reviewer

# Load environment variables
OPENAI_HOST = os.environ.get("OPENAI_HOST")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# ANSI Colors & Styles
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    
    # Foreground colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright foreground colors
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Background colors
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'

# Unicode Symbols
class Symbols:
    CHECK = '✓'
    CROSS = '✗'
    ARROW_RIGHT = '→'
    ARROW_DOWN = '↓'
    ARROW_UP = '↑'
    BULLET = '•'
    STAR = '★'
    DIAMOND = '◆'
    CIRCLE = '●'
    RING = '○'
    BOX_CHECK = '☑'
    BOX_EMPTY = '☐'
    WARNING = '⚠'
    INFO = 'ℹ'
    GEAR = '⚙'
    MAGNIFYING_GLASS = '🔍'
    BUG = '🐛'
    WRENCH = '🔧'
    DOCUMENT = '📄'
    FOLDER = '📁'
    PERSON = '👤'
    PEOPLE = '👥'
    ROCKET = '🚀'
    LIGHTBULB = '💡'
    CHART = '📊'
    BRANCH = '⎇'
    GIT = '⬡'
    HAMMER = '🔨'
    SPARKLES = '✨'
    DIVIDER = '─'
    DIVIDER_DOUBLE = '═'
    DIVIDER_THICK = '━'
    CORNER_TL = '┌'
    CORNER_TR = '┐'
    CORNER_BL = '└'
    CORNER_BR = '┘'
    T_LEFT = '├'
    T_RIGHT = '┤'
    PIPE = '│'

# Convenience functions
def c(text: str, color: str) -> str:
    """Wrap text with color."""
    return f"{color}{text}{Colors.RESET}"

def bold(text: str) -> str:
    return c(text, Colors.BOLD)

def dim(text: str) -> str:
    return c(text, Colors.DIM)

def success(text: str) -> str:
    return c(f"{Symbols.CHECK} {text}", Colors.BRIGHT_GREEN)

def error(text: str) -> str:
    return c(f"{Symbols.CROSS} {text}", Colors.BRIGHT_RED)

def warning(text: str) -> str:
    return c(f"{Symbols.WARNING} {text}", Colors.BRIGHT_YELLOW)

def info(text: str) -> str:
    return c(f"{Symbols.INFO} {text}", Colors.BRIGHT_BLUE)

def header(text: str) -> str:
    return c(f"{Symbols.GEAR} {text}", Colors.BOLD + Colors.BRIGHT_CYAN)

def section(num: int, text: str) -> str:
    """Create a section header."""
    return c(f"{Symbols.BOX_EMPTY} Step {num}: {text}", Colors.BOLD + Colors.BRIGHT_BLUE)

def section_done(num: int, text: str) -> str:
    """Create a completed section header."""
    return c(f"{Symbols.BOX_CHECK} Step {num}: {text}", Colors.BOLD + Colors.BRIGHT_GREEN)

def print_banner():
    """Print the main banner."""
    # Read logo from file
    try:
        logo_file = Path(__file__).parent / "logo.ansiart"
        if logo_file.exists():
            logo = logo_file.read_text()
            print(logo)
        else:
            # Fallback banner
            banner = f"""
{c(f"{Symbols.CORNER_TL}{Symbols.DIVIDER_THICK*58}{Symbols.CORNER_TR}", Colors.BRIGHT_CYAN)}
{c(f"{Symbols.PIPE}{'':^58}{Symbols.PIPE}", Colors.BRIGHT_CYAN)}
{c(f"{Symbols.PIPE}{'🐛 BUGOUT':^58}{Symbols.PIPE}", Colors.BOLD + Colors.BRIGHT_WHITE)}
{c(f"{Symbols.PIPE}{'Automated Bug Analysis & Patch Generation':^58}{Symbols.PIPE}", Colors.DIM)}
{c(f"{Symbols.PIPE}{'':^58}{Symbols.PIPE}", Colors.BRIGHT_CYAN)}
{c(f"{Symbols.CORNER_BL}{Symbols.DIVIDER_THICK*58}{Symbols.CORNER_BR}", Colors.BRIGHT_CYAN)}
"""
            print(banner)
    except:
        # Simple fallback
        print(f"{Colors.BRIGHT_CYAN}🐛 BUGOUT{Colors.RESET} - Automated Bug Analysis & Patch Generation")

def print_divider():
    """Print a divider line."""
    print(c(f"{Symbols.DIVIDER_THICK*60}", Colors.DIM))

def print_box(title: str, items: List[str], color: str = Colors.BRIGHT_BLUE):
    """Print items in a box format."""
    max_len = max(len(title), max(len(i) for i in items)) if items else len(title)
    width = max_len + 4
    
    print(c(f"{Symbols.CORNER_TL}{Symbols.DIVIDER*width}{Symbols.CORNER_TR}", color))
    print(c(f"{Symbols.PIPE} {bold(title):^{max_len}} {Symbols.PIPE}", color))
    print(c(f"{Symbols.T_LEFT}{Symbols.DIVIDER*width}{Symbols.T_RIGHT}", color))
    for item in items:
        print(c(f"{Symbols.PIPE} {Symbols.ARROW_RIGHT} {item:{max_len-2}} {Symbols.PIPE}", color))
    print(c(f"{Symbols.CORNER_BL}{Symbols.DIVIDER*width}{Symbols.CORNER_BR}", color))

def print_tree_item(text: str, is_last: bool = False, indent: int = 0):
    """Print a tree-style item."""
    prefix = "    " * indent
    connector = "└── " if is_last else "├── "
    print(f"{prefix}{c(connector + text, Colors.BRIGHT_WHITE)}")

def call_llm(prompt: str, system_prompt: str = "", max_tokens: int = 4000) -> str:
    """Call the LLM API with the given prompt."""
    import requests
    
    headers = {
        "Content-Type": "application/json"
    }
    
    if OPENAI_API_KEY:
        headers["Authorization"] = f"Bearer {OPENAI_API_KEY}"
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": max_tokens
    }
    
    try:
        response = requests.post(
            f"{OPENAI_HOST}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        raise Exception(f"LLM API error: {e}")


def summarize_bug_nature(reports: list, issue_title: str = "") -> str:
    """
    Use OpenAI API to summarize the nature of the bug based on all reports.
    Returns a comprehensive summary of the bug's nature, impact, and root causes.
    """
    if not OPENAI_HOST or not OPENAI_MODEL:
        print(f"  {warning('OPENAI_HOST or OPENAI_MODEL not set, skipping LLM summary')}")
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
        print(f"  {c(f'{Symbols.LIGHTBULB} Querying LLM for bug analysis...', Colors.BRIGHT_YELLOW)}")
        summary = call_llm(
            prompt,
            system_prompt="You are a technical analyst specializing in bug report analysis. Provide clear, actionable summaries of software issues.",
            max_tokens=1500
        )
        print(f"  {success('LLM analysis complete')}")
        return summary
    except Exception as e:
        print(f"  {error(f'Error generating LLM summary: {e}')}")
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
    print(f"\n{section(1, f'{Symbols.MAGNIFYING_GLASS} Fetching Issue Comments')} {c(f'for {repo}#{issue_number}', Colors.DIM)}")
    
    output_file = output_dir / "issue_comments.json"
    
    # Use gh CLI to fetch issue with comments
    cmd = [
        "gh", "issue", "view", issue_number,
        "--repo", repo,
        "--json", "number,title,state,labels,body,author,createdAt,comments"
    ]
    
    stdout, stderr, rc = run_command(cmd)
    
    if rc != 0:
        print(f"  {error(f'Failed to fetch issue: {stderr}')}")
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
    
    # Print tree structure
    print(f"  {success(f'Saved {c(str(len(rows)), Colors.BRIGHT_YELLOW)} entries')}")
    print_tree_item(f"Issue: {c(issue_data['title'][:50], Colors.BRIGHT_WHITE)}", is_last=len(rows) == 1)
    if len(rows) > 1:
        print_tree_item(f"Comments: {c(str(len(rows)-1), Colors.BRIGHT_YELLOW)}", is_last=True)
    
    return output_file


def extract_features(comments_file: Path, output_dir: Path) -> Path:
    """
    Step 2: Use parser.py to extract features from comments.
    Requires FASTINO_KEY environment variable.
    """
    print(f"\n{section(2, f'{Symbols.CHART} Extracting Features')}")
    
    output_file = output_dir / "bugs_with_features.jsonl"
    
    # Run parser.py
    cmd = ["python3", "parser.py", str(comments_file)]
    
    stdout, stderr, rc = run_command(cmd)
    
    if rc != 0:
        print(f"  {error(f'Failed to extract features: {stderr}')}")
        raise Exception(f"Failed to extract features: {stderr}")
    
    # Save output
    with open(output_file, "w") as f:
        f.write(stdout)
    
    # Count lines
    line_count = len(stdout.strip().split("\n")) if stdout.strip() else 0
    print(f"  {success(f'Extracted features for {c(str(line_count), Colors.BRIGHT_YELLOW)} entries')}")
    print_tree_item(f"Output: {c(str(output_file), Colors.DIM)}", is_last=True)
    
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
    print(f"\n{section(3, f'{Symbols.GEAR} Analyzing Bug Reports')}")
    
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
    bug_nature_summary = summarize_bug_nature(reports, issue_title)
    result["bug_nature_summary"] = bug_nature_summary
    
    # Print summary box
    print(f"  {success('Analysis complete')}")
    crash_rate = result['prd_summary']['crash_rate_pct']
    crash_color = Colors.BRIGHT_RED if crash_rate > 0 else Colors.BRIGHT_GREEN
    
    items = [
        f"Total Reports: {c(str(result['prd_summary']['total_reports']), Colors.BRIGHT_YELLOW)}",
        f"Crash Rate: {c(str(crash_rate) + '%', crash_color)}",
        f"Dominant Frustration: {c(result['prd_summary']['dominant_frustration_level'], Colors.BRIGHT_MAGENTA)}",
        f"Top Platform: {c(result['prd_summary']['top_affected_platform'], Colors.BRIGHT_CYAN)}",
        f"Primary Issue: {c(result['prd_summary']['primary_bug_behaviour'][:40] + '...', Colors.BRIGHT_WHITE)}"
    ]
    
    for i, item in enumerate(items):
        print_tree_item(item, is_last=(i == len(items)-1))
    
    return result


def generate_prd(mcp_result: Dict, output_dir: Path) -> Path:
    """
    Step 4: Generate PRD document from analysis results.
    """
    print(f"\n{section(4, f'{Symbols.DOCUMENT} Generating PRD')}")
    
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
    
    print(f"  {success(f'Generated PRD')}")
    print_tree_item(f"File: {c(str(prd_file), Colors.DIM)}", is_last=True)
    
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
    print(f"\n{section(5, f'{Symbols.PEOPLE} Finding Competent Reviewers')}")
    print(f"  {c(f'Checking {len(authors)} potential reviewers...', Colors.DIM)}")
    
    if not os.environ.get("YUTORI_API_KEY"):
        print(f"  {warning('YUTORI_API_KEY not set, skipping reviewer check')}")
        return None, []
    
    results = check_reviewers_bulk(authors, repo)
    
    # Get the best reviewer
    best = get_best_reviewer(results)
    
    valid_reviewers = [r for r in results if r.get('scout_id')]
    print(f"  {success(f'Found {c(str(len(valid_reviewers)), Colors.BRIGHT_GREEN)} competent reviewers')}")
    
    if best:
        print_tree_item(f"Best reviewer: {c(f'@{best}', Colors.BRIGHT_GREEN + Colors.BOLD)}", is_last=True)
    
    return best, results


def clone_repo(repo: str, work_dir: Path) -> Path:
    """
    Step 6: Clone a GitHub repository to a temporary directory.
    Returns the path to the cloned repository.
    """
    print(f"\n{section(6, f'{Symbols.GIT} Cloning Repository')} {c(repo, Colors.DIM)}")
    
    repo_name = repo.split("/")[1]
    clone_path = work_dir / repo_name
    
    cmd = ["gh", "repo", "clone", repo, str(clone_path)]
    stdout, stderr, rc = run_command(cmd)
    
    if rc != 0:
        print(f"  {error(f'Failed to clone repository: {stderr}')}")
        raise Exception(f"Failed to clone repository: {stderr}")
    
    print(f"  {success('Repository cloned')}")
    print_tree_item(f"Path: {c(str(clone_path), Colors.DIM)}", is_last=True)
    
    return clone_path


def find_relevant_files(repo_path: Path, prd_content: str, max_files: int = 10) -> List[str]:
    """
    Use LLM to identify relevant files in the repository based on the PRD.
    """
    print(f"  {c(f'{Symbols.MAGNIFYING_GLASS} Identifying relevant files...', Colors.BRIGHT_YELLOW)}")
    
    # Get a list of source files
    source_files = []
    for ext in ["*.py", "*.js", "*.ts", "*.java", "*.cpp", "*.c", "*.go", "*.rs"]:
        source_files.extend(repo_path.rglob(ext))
    
    # Sample files (limit to avoid overwhelming the LLM)
    sample_files = [str(f.relative_to(repo_path)) for f in source_files[:100]]
    
    if not sample_files:
        return []
    
    prompt = f"""Given the following bug report, identify the most relevant files to investigate:

Bug Report:
{prd_content[:2000]}

Available files (sample):
"""
    
    for f in sample_files:
        prompt += f"\n- {f}"
    
    prompt += f"\n\nList the top {max_files} most relevant file paths, one per line. Only output file paths, nothing else."
    
    try:
        response = call_llm(
            prompt,
            system_prompt="You are a code analyst. Identify files most likely to contain the bug based on the report.",
            max_tokens=500
        )
        
        # Parse response to get file paths
        files = []
        for line in response.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("-"):
                files.append(line)
            elif line.startswith("-"):
                files.append(line[1:].strip())
        
        print(f"  {success(f'Identified {c(str(len(files)), Colors.BRIGHT_YELLOW)} relevant files')}")
        return files[:max_files]
    except Exception as e:
        print(f"  {warning(f'Error finding relevant files: {e}')}")
        return []


def read_file_content(repo_path: Path, file_path: str) -> str:
    """Read content of a file in the repository."""
    try:
        full_path = repo_path / file_path
        if full_path.exists() and full_path.is_file():
            return full_path.read_text()
    except Exception:
        pass
    return ""


def agentic_fix_generation(repo_path: Path, prd_file: Path, output_dir: Path) -> str:
    """
    Step 7: Perform agentic loop to generate fix using LLM.
    Clones repo, identifies relevant files, and generates fix.
    Returns the fix content.
    """
    print(f"\n{section(7, f'{Symbols.WRENCH} Generating Fix via Agentic Loop')}")
    
    if not OPENAI_HOST or not OPENAI_MODEL:
        print(f"  {warning('OPENAI_HOST or OPENAI_MODEL not set, skipping fix generation')}")
        return ""
    
    # Read PRD
    prd_content = prd_file.read_text()
    
    # Find relevant files
    relevant_files = find_relevant_files(repo_path, prd_content)
    
    if not relevant_files:
        print(f"  {warning('No relevant files found')}")
        return ""
    
    # Print tree of relevant files
    for i, file in enumerate(relevant_files):
        print_tree_item(c(file, Colors.DIM), is_last=(i == len(relevant_files)-1))
    
    # Read relevant file contents
    file_contents = {}
    for file_path in relevant_files:
        content = read_file_content(repo_path, file_path)
        if content:
            file_contents[file_path] = content
    
    # Generate fix
    print(f"  {c(f'{Symbols.LIGHTBULB} Querying LLM for fix proposal...', Colors.BRIGHT_YELLOW)}")
    
    prompt = f"""Given the following bug report, analyze the code and provide a fix.

Bug Report:
{prd_content}

Relevant Files:
"""
    
    for file_path, content in file_contents.items():
        prompt += f"\n\n=== {file_path} ===\n"
        # Truncate content to avoid token limits
        prompt += content[:3000]
    
    prompt += """

Please provide:
1. A detailed explanation of the root cause
2. The specific code changes needed to fix the bug
3. The complete fixed code for each modified file in unified diff format

Format your response as:

ROOT CAUSE ANALYSIS:
<explanation>

FIX:
```diff
<unified diff showing changes>
```
"""
    
    try:
        fix_content = call_llm(
            prompt,
            system_prompt="You are an expert software engineer. Analyze bugs and provide precise fixes in unified diff format.",
            max_tokens=4000
        )
        
        # Save fix proposal
        fix_proposal_file = output_dir / "fix_proposal.md"
        with open(fix_proposal_file, "w") as f:
            f.write(fix_content)
        
        print(f"  {success('Fix proposal generated')}")
        print_tree_item(f"File: {c(str(fix_proposal_file), Colors.DIM)}", is_last=True)
        
        return fix_content
        
    except Exception as e:
        print(f"  {error(f'Failed to generate fix: {e}')}")
        return ""


def generate_patch_file(repo_path: Path, fix_content: str, output_dir: Path) -> Path:
    """
    Step 8: Generate a proper patch file from the fix content.
    Attempts to apply the fix to the cloned repo and generate git diff.
    """
    print(f"\n{section(8, f'{Symbols.HAMMER} Generating Patch File')}")
    
    patch_file = output_dir / "fix.patch"
    
    # Extract diff from fix_content
    import re
    diff_match = re.search(r'```diff\n(.*?)```', fix_content, re.DOTALL)
    
    if diff_match:
        diff_content = diff_match.group(1)
    else:
        # Try to find any diff-like content
        diff_match = re.search(r'(@@.*@@.*\n[-+@ ].*\n)+', fix_content, re.DOTALL)
        if diff_match:
            diff_content = diff_match.group(0)
        else:
            diff_content = fix_content  # Use full content if no diff found
    
    # Write patch file
    with open(patch_file, "w") as f:
        f.write(diff_content)
    
    print(f"  {success('Patch file generated')}")
    print_tree_item(f"File: {c(str(patch_file), Colors.DIM)}", is_last=True)
    
    return patch_file


def prepare_patch_folder(
    repo: str,
    issue_number: str,
    prd_file: Path,
    reviewer: Optional[str],
    reviewer_results: List[Dict],
    fix_content: str,
    patch_file: Path,
    output_dir: Path
) -> Path:
    """
    Step 9: Prepare patch folder with reviewer.json, patch, prd, and relevant work.
    """
    print(f"\n{section(9, f'{Symbols.FOLDER} Preparing Patch Folder')}")
    
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
    
    # Copy patch file
    shutil.copy(patch_file, patch_dir / "fix.patch")
    
    # Copy fix proposal if exists
    fix_proposal = output_dir / "fix_proposal.md"
    if fix_proposal.exists():
        shutil.copy(fix_proposal, patch_dir / "fix_proposal.md")
    
    # Copy all relevant work files
    for file in output_dir.iterdir():
        if file.is_file():
            shutil.copy(file, patch_dir / file.name)
    
    print(f"  {success(f'Patch folder prepared at {c(str(patch_dir), Colors.BRIGHT_CYAN)}')}")
    print_tree_item(f"reviewer.json", is_last=False)
    print_tree_item(f"prd.md", is_last=False)
    print_tree_item(f"fix.patch", is_last=False)
    print_tree_item(f"fix_proposal.md", is_last=True)
    
    return patch_dir


def main():
    if len(sys.argv) < 3:
        print_banner()
        print(f"\n{error('Missing required arguments')}\n")
        print(f"  {bold('Usage:')} python bugout.py <repo> <bug_number>")
        print(f"  {bold('Example:')} python bugout.py microsoft/vscode 12345\n")
        sys.exit(1)
    
    repo = sys.argv[1]
    issue_number = sys.argv[2]
    
    # Create output directory
    output_dir = Path("bugout_output") / repo.replace("/", "_") / issue_number
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create temp directory for cloning
    work_dir = output_dir / "workspace"
    work_dir.mkdir(exist_ok=True)
    
    print_banner()
    print(f"  {bold('Target:')} {c(repo + '#' + issue_number, Colors.BRIGHT_CYAN)}")
    print(f"  {bold('Output:')} {c(str(output_dir), Colors.DIM)}\n")
    print_divider()
    
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
        
        # Step 6: Clone repository
        repo_path = clone_repo(repo, work_dir)
        
        # Step 7: Agentic fix generation
        fix_content = agentic_fix_generation(repo_path, prd_file, output_dir)
        
        # Step 8: Generate patch file
        patch_file = generate_patch_file(repo_path, fix_content, output_dir)
        
        # Step 9: Prepare patch folder
        patch_dir = prepare_patch_folder(
            repo, issue_number, prd_file, reviewer, reviewer_results, 
            fix_content, patch_file, output_dir
        )
        
        # Success banner
        print(f"\n{c(f'{Symbols.CORNER_TL}{Symbols.DIVIDER_THICK*58}{Symbols.CORNER_TR}', Colors.BRIGHT_GREEN)}")
        print(f"{c(f'{Symbols.PIPE}', Colors.BRIGHT_GREEN)} {c(f'{Symbols.SPARKLES} BUGOUT COMPLETE {Symbols.SPARKLES}', Colors.BOLD + Colors.BRIGHT_GREEN):^54} {c(f'{Symbols.PIPE}', Colors.BRIGHT_GREEN)}")
        print(f"{c(f'{Symbols.CORNER_BL}{Symbols.DIVIDER_THICK*58}{Symbols.CORNER_BR}', Colors.BRIGHT_GREEN)}\n")
        
        print_box("Summary", [
            f"{Symbols.FOLDER} Output: {str(output_dir)}",
            f"{Symbols.BRANCH} Patch: {str(patch_dir)}",
            f"{Symbols.GIT} Cloned: {str(repo_path)}",
        ], Colors.BRIGHT_CYAN)
        
        print()
        
        if reviewer:
            print(f"{c(f'{Symbols.PERSON} Recommended Reviewer:', Colors.BRIGHT_YELLOW)} {c(f'@{reviewer}', Colors.BRIGHT_GREEN + Colors.BOLD)}\n")
        
        print(f"{bold('Next Steps:')}")
        print(f"  {c('1.', Colors.BRIGHT_CYAN)} Review the PRD at {c(str(prd_file), Colors.BRIGHT_WHITE)}")
        print(f"  {c('2.', Colors.BRIGHT_CYAN)} Review the fix proposal at {c(str(patch_dir / 'fix_proposal.md'), Colors.BRIGHT_WHITE)}")
        print(f"  {c('3.', Colors.BRIGHT_CYAN)} Review the patch at {c(str(patch_dir / 'fix.patch'), Colors.BRIGHT_WHITE)}")
        print(f"  {c('4.', Colors.BRIGHT_CYAN)} Apply patch to cloned repo at {c(str(repo_path), Colors.BRIGHT_WHITE)}")
        print(f"  {c('5.', Colors.BRIGHT_CYAN)} Test the fix")
        print(f"  {c('6.', Colors.BRIGHT_CYAN)} Submit PR with {c(f'@{reviewer}', Colors.BRIGHT_GREEN) if reviewer else 'a suitable reviewer'} as reviewer\n")
        
    except Exception as e:
        print(f"\n{c(f'{Symbols.CORNER_TL}{Symbols.DIVIDER_THICK*58}{Symbols.CORNER_TR}', Colors.BRIGHT_RED)}")
        print(f"{c(f'{Symbols.PIPE}', Colors.BRIGHT_RED)} {error('Execution Failed'):^54} {c(f'{Symbols.PIPE}', Colors.BRIGHT_RED)}")
        print(f"{c(f'{Symbols.CORNER_BL}{Symbols.DIVIDER_THICK*58}{Symbols.CORNER_BR}', Colors.BRIGHT_RED)}")
        print(f"\n{error(f'{e}')}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
