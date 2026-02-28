#!/usr/bin/env python3
"""
comment_fetcher.py - Step 1: Fetch issue comments via gh CLI
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

# ANSI Colors
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_CYAN = "\033[96m"

SYMBOLS = {"check": "✅", "arrow": "→", "bug": "🐛"}


def fetch_issue_comments(repo: str, issue_number: str, output_dir: Path) -> Optional[Path]:
    """
    Fetch all comments for a GitHub issue using gh CLI.
    
    Args:
        repo: Repository in format "owner/repo"
        issue_number: Issue number
        output_dir: Directory to save the JSON file
        
    Returns:
        Path to the saved JSON file, or None if failed
    """
    output_file = output_dir / f"issue_{issue_number}_comments.json"
    
    # Use gh issue view to get the issue with comments
    cmd = [
        "gh", "issue", "view", issue_number,
        "--repo", repo,
        "--json", "number,title,body,author,createdAt,comments,labels,state"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        issue_data = json.loads(result.stdout)
        
        # Save to file
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(issue_data, f, indent=2)

        num_comments = len(issue_data.get('comments', []))
        print(f"{Colors.BRIGHT_GREEN}{SYMBOLS['check']}{Colors.RESET} {Colors.GREEN}Step 1 complete:{Colors.RESET} Fetched {Colors.BRIGHT_CYAN}{num_comments}{Colors.RESET} comments for issue {Colors.BRIGHT_CYAN}#{issue_number}{Colors.RESET}", file=sys.stderr)
        return output_file
        
    except subprocess.CalledProcessError as e:
        print(f"Error fetching issue: {e.stderr}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}", file=sys.stderr)
        return None


def fetch_issue_list(repo: str, limit: int = 100) -> list:
    """
    Fetch a list of issues from a repository.
    
    Args:
        repo: Repository in format "owner/repo"
        limit: Maximum number of issues to fetch
        
    Returns:
        List of issue summaries
    """
    cmd = [
        "gh", "issue", "list",
        "--repo", repo,
        "--limit", str(limit),
        "--json", "number,title,state,labels,author,createdAt,comments"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error fetching issue list: {e.stderr}", file=sys.stderr)
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}", file=sys.stderr)
        return []


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python comment_fetcher.py <repo> <issue_number> [output_dir]", file=sys.stderr)
        sys.exit(1)
    
    repo = sys.argv[1]
    issue_number = sys.argv[2]
    output_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("./bugout_data")
    
    result = fetch_issue_comments(repo, issue_number, output_dir)
    if result:
        print(f"Saved to: {result}")
    else:
        sys.exit(1)
