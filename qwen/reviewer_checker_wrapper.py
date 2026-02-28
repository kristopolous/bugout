#!/usr/bin/env python3
"""
reviewer_checker_wrapper.py - Step 5: Check reviewer competence using Yutori API
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
import requests
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# ANSI Colors
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_WHITE = "\033[97m"

SYMBOLS = {"check": "✅", "star": "★", "user": "👤"}

YUTORI_API_KEY = os.environ.get("YUTORI_KEY")
YUTORI_BASE_URL = "https://api.yutori.com/v1"


def create_scout_for_user(github_username: str, repo: str) -> Optional[Dict]:
    """
    Create a Yutori scout to research a GitHub user's competence.
    """
    if not YUTORI_API_KEY:
        print(f"Error: YUTORI_API_KEY not set", file=sys.stderr)
        return None

    query = f"""
    Research GitHub user {github_username} on repository {repo}.
    Analyze their:
    1. Contribution history to this repository
    2. Code review activity and quality
    3. Technical expertise in relevant areas
    4. Reputation and trustworthiness in the community

    Determine if they are competent enough to review code changes.
    """

    headers = {
        "X-API-Key": YUTORI_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "query": query,
        "display_name": f"reviewer-check-{github_username}",
        "output_interval": 3600
    }

    try:
        response = requests.post(
            f"{YUTORI_BASE_URL}/scouting/tasks",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error creating scout for {github_username}: {e}", file=sys.stderr)
        return None


def get_scout_status(scout_id: str) -> Optional[Dict]:
    """Get the status of a Yutori scout."""
    if not YUTORI_API_KEY:
        return None

    headers = {"X-API-Key": YUTORI_API_KEY}

    try:
        response = requests.get(
            f"{YUTORI_BASE_URL}/scouting/tasks/{scout_id}",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error getting scout status: {e}", file=sys.stderr)
        return None


def get_scout_results(scout_id: str) -> Optional[Dict]:
    """Get the research results from a completed scout."""
    if not YUTORI_API_KEY:
        return None

    headers = {"X-API-Key": YUTORI_API_KEY}

    try:
        response = requests.get(
            f"{YUTORI_BASE_URL}/scouting/tasks/{scout_id}/results",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error getting scout results: {e}", file=sys.stderr)
        return None


def check_reviewer_competence(github_username: str, repo: str, wait: bool = False) -> Dict:
    """
    Check if a GitHub user is competent to review code.
    
    Args:
        github_username: GitHub username to check
        repo: Repository in format "owner/repo"
        wait: If True, wait for scout to complete (with timeout)
        
    Returns:
        Dict with competence assessment
    """
    print(f"Checking competence of {github_username} for {repo}...", file=sys.stderr)

    scout = create_scout_for_user(github_username, repo)
    if not scout:
        return {
            "username": github_username,
            "competent": False,
            "error": "Failed to create scout",
            "reason": "Could not initiate competence check"
        }

    scout_id = scout.get("id")
    
    if wait:
        # Wait for scout to complete (with timeout)
        print(f"  Waiting for scout {scout_id} to complete...", file=sys.stderr)
        max_wait = 60  # seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            status = get_scout_status(scout_id)
            if status and status.get("status") == "completed":
                results = get_scout_results(scout_id)
                return {
                    "username": github_username,
                    "scout_id": scout_id,
                    "status": "completed",
                    "competent": results.get("competent", True) if results else True,
                    "results": results
                }
            time.sleep(5)
        
        return {
            "username": github_username,
            "scout_id": scout_id,
            "status": "timeout",
            "competent": None,
            "reason": "Scout did not complete within timeout"
        }

    return {
        "username": github_username,
        "scout_id": scout_id,
        "status": "pending",
        "competent": None,
        "scout_data": scout
    }


def extract_commenters_from_issue(comments_file: Path) -> List[str]:
    """
    Extract unique commenter usernames from an issue JSON file.
    
    Args:
        comments_file: Path to issue comments JSON
        
    Returns:
        List of unique usernames
    """
    with open(comments_file, 'r') as f:
        issue_data = json.load(f)
    
    usernames = set()
    
    # Add issue author
    author = issue_data.get('author', {}).get('login')
    if author:
        usernames.add(author)
    
    # Add commenters
    for comment in issue_data.get('comments', []):
        commenter = comment.get('author', {}).get('login')
        if commenter:
            usernames.add(commenter)
    
    return sorted(list(usernames))


def check_reviewers_bulk(usernames: List[str], repo: str, wait: bool = False) -> List[Dict]:
    """
    Check competence for multiple reviewers.
    """
    results = []
    for username in usernames:
        result = check_reviewer_competence(username, repo, wait)
        results.append(result)
    return results


def get_best_reviewer(results: List[Dict]) -> Optional[str]:
    """
    From competence check results, return the best reviewer username.
    """
    # First, look for completed and competent reviewers
    for result in results:
        if result.get("competent") is True:
            return result["username"]
    
    # Then, look for any reviewer with a successful scout
    for result in results:
        if result.get("scout_id"):
            return result["username"]
    
    # Fallback to first username
    if results:
        return results[0]["username"]
    
    return None


def save_reviewers_json(results: List[Dict], best_reviewer: Optional[str], output_file: Path) -> Path:
    """
    Save reviewer information to reviewer.json.
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "reviewers": results,
        "best_reviewer": best_reviewer,
        "total_checked": len(results)
    }
    
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    return output_file


def check_reviewers_for_issue(
    comments_file: Path,
    repo: str,
    output_dir: Path,
    wait: bool = False
) -> tuple:
    """
    Main function to check all commenters on an issue for reviewer competence.
    
    Args:
        comments_file: Path to issue comments JSON
        repo: Repository in format "owner/repo"
        output_dir: Directory to save reviewer.json
        wait: If True, wait for scouts to complete
        
    Returns:
        Tuple of (reviewer.json path, best reviewer username)
    """
    # Extract commenters
    usernames = extract_commenters_from_issue(comments_file)
    print(f"\n{Colors.BRIGHT_CYAN}{SYMBOLS['star']} Step 5: Reviewer Check{Colors.RESET}", file=sys.stderr)
    print(f"  {Colors.CYAN}Found {len(usernames)} unique commenters: {Colors.WHITE}{usernames}{Colors.RESET}", file=sys.stderr)

    if not usernames:
        print(f"  {Colors.BRIGHT_RED}✗ No commenters found!{Colors.RESET}", file=sys.stderr)
        return None, None

    # Check competence
    results = check_reviewers_bulk(usernames, repo, wait)

    # Find best reviewer
    best_reviewer = get_best_reviewer(results)
    print(f"  {Colors.BRIGHT_GREEN}{SYMBOLS['check']} Best reviewer: {Colors.BRIGHT_CYAN}@{best_reviewer}{Colors.RESET}", file=sys.stderr)

    # Save reviewer.json
    output_file = output_dir / "reviewer.json"
    save_reviewers_json(results, best_reviewer, output_file)
    
    print(f"{Colors.BRIGHT_GREEN}{SYMBOLS['check']} Step 5 complete: Checked {Colors.BRIGHT_CYAN}{len(results)}{Colors.RESET} reviewers", file=sys.stderr)
    return output_file, best_reviewer


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python reviewer_checker_wrapper.py <comments.json> <repo> [output_dir] [wait]", file=sys.stderr)
        sys.exit(1)
    
    comments_file = Path(sys.argv[1])
    repo = sys.argv[2]
    output_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("./bugout_data")
    wait = len(sys.argv) > 4 and sys.argv[4].lower() == "true"
    
    result_path, best_reviewer = check_reviewers_for_issue(comments_file, repo, output_dir, wait)
    if result_path:
        print(f"Saved to: {result_path}")
        print(f"Best reviewer: {best_reviewer}")
    else:
        sys.exit(1)
