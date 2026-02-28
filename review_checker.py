#!/usr/bin/env python3
"""
review_checker.py - Check if GitHub users are competent to review using Yutori API
"""

import os
import sys
import json
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

YUTORI_API_KEY = os.environ.get("YUTORI_API_KEY")
YUTORI_BASE_URL = "https://api.yutori.com/v1"


def create_scout_for_user(github_username: str, repo: str) -> Optional[Dict]:
    """
    Create a Yutori scout to research a GitHub user's competence.
    Returns the scout data or None if failed.
    """
    if not YUTORI_API_KEY:
        print(f"Error: YUTORI_API_KEY not set in environment", file=sys.stderr)
        return None
    
    # Create a research query about the user's competence
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
        "output_interval": 3600  # Check every hour
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
    """
    Get the status of a Yutori scout.
    """
    if not YUTORI_API_KEY:
        return None
    
    headers = {
        "X-API-Key": YUTORI_API_KEY
    }
    
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
    """
    Get the research results from a completed scout.
    """
    if not YUTORI_API_KEY:
        return None
    
    headers = {
        "X-API-Key": YUTORI_API_KEY
    }
    
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


def check_reviewer_competence(github_username: str, repo: str) -> Dict:
    """
    Check if a GitHub user is competent to review code for a specific repo.
    Returns a dict with competence assessment.
    """
    print(f"Checking competence of {github_username} for {repo}...", file=sys.stderr)
    
    # Create scout
    scout = create_scout_for_user(github_username, repo)
    if not scout:
        return {
            "username": github_username,
            "competent": False,
            "error": "Failed to create scout",
            "reason": "Could not initiate competence check"
        }
    
    scout_id = scout.get("id")
    
    # In a real implementation, we'd wait for the scout to complete
    # For now, return the scout info so it can be checked later
    return {
        "username": github_username,
        "scout_id": scout_id,
        "status": "pending",
        "competent": None,  # Will be determined when scout completes
        "scout_data": scout
    }


def check_reviewers_bulk(usernames: List[str], repo: str) -> List[Dict]:
    """
    Check competence for multiple reviewers.
    """
    results = []
    for username in usernames:
        result = check_reviewer_competence(username, repo)
        results.append(result)
    return results


def get_best_reviewer(results: List[Dict]) -> Optional[str]:
    """
    From competence check results, return the best reviewer username.
    For now, returns the first valid username.
    """
    for result in results:
        if result.get("scout_id"):  # If scout was created successfully
            return result["username"]
    return None


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python review_checker.py <repo> <username1> [username2] ...", file=sys.stderr)
        sys.exit(1)
    
    repo = sys.argv[1]
    usernames = sys.argv[2:]
    
    results = check_reviewers_bulk(usernames, repo)
    print(json.dumps(results, indent=2))
