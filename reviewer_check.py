#!/usr/bin/env python3
"""
Check if a GitHub user is capable of reviewing a PR.
Uses Yutori Research API to investigate user expertise.
"""

import curlify
import os
import sys
import json
import time
import argparse
import requests
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
YUTORI_API_KEY = os.environ.get("YUTORI_KEY")
YUTORI_BASE_URL = "https://api.yutori.com"

def get_id(id = None):
    id="fa5c6038-10e0-4c88-a3d7-e21abdedae13"
    response = requests.get( f"{YUTORI_BASE_URL}/v1/research/tasks/{id}",
        headers={"X-API-Key": YUTORI_API_KEY, "Content-Type": "application/json"},
    )
    print(json.dumps(response.json(), indent=2, sort_keys=True))



def create_research_task(query: str,gh_user) -> str:
    """Create a Yutori research task and return task_id."""
    response = requests.post(
        #f"{YUTORI_BASE_URL}/v1/research/tasks",
        f"{YUTORI_BASE_URL}/v1/browsing/tasks",
        headers={"X-API-Key": YUTORI_API_KEY, "Content-Type": "application/json"},
        json={
            "start_url": f"https://github.com/{gh_user}",
            "max_steps": 5,
            "task": query,
            "output_schema": {
                "type": "object",
                "properties": {
                    "can_review": {"type": "boolean"},
                    "competence": {"type": "number"},
                    "reasoning": {"type": "string"},
                    "relevant_experience": {"type": "array", "items": {"type": "string"}},
                    "recommendations": {"type": "array", "items": {"type": "string"}}
                }
            }
        }
    )
    response.raise_for_status()
    return response.json()["task_id"]


def get_task_result(task_id: str, timeout: int = 12000) -> dict:
    """Poll for task completion and return result."""
    start = time.time()
    while time.time() - start < timeout:
        response = requests.get(
            f"{YUTORI_BASE_URL}/v1/research/tasks/{task_id}",
            headers={"X-API-Key": YUTORI_API_KEY}
        )
        response.raise_for_status()
        data = response.json()
        
        if data["status"] == "succeeded":
            return data
        elif data["status"] == "failed":
            raise RuntimeError(f"Task failed: {data.get('error', 'Unknown error')}")
        
        time.sleep(5)
    
    raise TimeoutError("Task did not complete in time")


def check_reviewer_capability(github_user: str, pr_summary: str) -> dict:
    """Check if a GitHub user can review the given PR."""
    query = f"""Research GitHub user "{github_user}" on github.com to determine if they are capable of reviewing and vouching for a pull request.

PR Summary: {pr_summary}

Visit https://github.com/{github_user} and analyze one or more of the following:
1. Their public repositories and primary languages
2. Their contribution history and activity
3. Their bio, company, and public profile information
4. Recent commits and pull requests they've made
5. Topics and technologies they work with

Based on this research, Quickly determine if they have relevant expertise to review the PR described above. If you have competence in your answer, stop immediately and return.


IMPORTANT: Always return a competence value between 0.0 and 1.0 representing your certainty:
- 0.0-0.3: Low competence (insufficient data or no relevant experience)
- 0.4-0.6: Medium competence (some relevant experience but not clear expert)
- 0.7-1.0: High competence (clear expertise in relevant technologies)

Return your assessment in the required JSON format."""

#IMPORTANT: Do this with shallow depth, minimal toolcalls, and as few cycles as possible
    task_id = create_research_task(query, github_user)
    print(f"Researching {github_user}... (task: {task_id})")
    
    result = get_task_result(task_id)
    return result


def main():
    #get_id()
    #sys.exit(0)
    parser = argparse.ArgumentParser(description="Check if a GitHub user can review a PR")
    parser.add_argument("github_user", help="GitHub username to check")
    parser.add_argument("pr_summary", help="PR description/summary")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout in seconds")
    args = parser.parse_args()

    if not YUTORI_API_KEY:
        print("Error: YUTORI_KEY not found in environment", file=sys.stderr)
        sys.exit(1)

    try:
        result = check_reviewer_capability(args.github_user, args.pr_summary)
        print(result)
        output = result.get("output", {})
        if isinstance(output, str):
            output = json.loads(output)
        
        print(f"[DEBUG] Output: {json.dumps(output, indent=2)}")
        
        print(output)

        sys.exit(0)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
