#!/usr/bin/env python3
"""
bug_fixer.py - Step 4: Attempt to fix the bug
Uses AI to analyze the bug and generate a fix.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, List


def get_repo_structure(repo_path: str = ".") -> str:
    """Get a summary of the repository structure."""
    try:
        result = subprocess.run(
            ["find", repo_path, "-type", "f", "-name", "*.py", "-o", "-name", "*.js", "-o", "-name", "*.ts", "-o", "-name", "*.tsx", "-o", "-name", "*.rs", "-o", "-name", "*.go"],
            capture_output=True,
            text=True,
            timeout=30
        )
        files = result.stdout.strip().split('\n')[:50]  # Limit to 50 files
        return '\n'.join(files)
    except Exception as e:
        return f"Error getting structure: {e}"


def generate_fix_prompt(prd_file: Path, features_file: Path) -> str:
    """Generate a prompt for the AI to create a fix."""
    with open(prd_file, 'r') as f:
        prd = f.read()
    
    with open(features_file, 'r') as f:
        features = json.load(f)
    
    bugs = features.get("bugs_with_features", [])
    
    # Collect technical descriptions
    tech_descs = [b.get("technical_description", "") for b in bugs if b.get("technical_description")]
    expected_behaviours = [b.get("expected_behaviour", "") for b in bugs if b.get("expected_behaviour")]
    
    prompt = f"""You are an expert software engineer tasked with fixing a bug.

## PRD (Product Requirements Document)
{prd}

## Bug Reports Summary
Total reports: {len(bugs)}

### Technical Descriptions from Users:
"""
    
    for i, desc in enumerate(tech_descs[:5], 1):
        prompt += f"{i}. {desc}\n"
    
    prompt += "\n### Expected Behaviour:\n"
    for i, exp in enumerate(expected_behaviours[:5], 1):
        prompt += f"{i}. {exp}\n"
    
    prompt += """
## Your Task
1. Analyze the bug reports and PRD
2. Identify the root cause
3. Propose a fix with code changes
4. Provide a clear explanation

## Output Format
Respond with a JSON object:
{
    "root_cause": "Description of the root cause",
    "fix_description": "Description of the fix",
    "code_changes": [
        {
            "file": "path/to/file.py",
            "action": "modify|create|delete",
            "old_code": "...",
            "new_code": "..."
        }
    ],
    "testing_instructions": "How to test the fix"
}
"""
    
    return prompt


def generate_fix_with_ai(prompt: str, api_key: str) -> Optional[Dict]:
    """Use AI to generate a fix."""
    import requests
    
    try:
        response = requests.post(
            "https://api.pioneer.ai/inference",
            headers={
                "Content-Type": "application/json",
                "X-API-Key": api_key
            },
            json={
                "model_id": "839c367a-bfa3-4b78-8f3e-85c44f619106",
                "task": "generate",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert software engineer. You output strict JSON with code fixes. You are not conversational."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.2,
                "max_tokens": 2048
            }
        )
        
        obj = response.json()
        completion = obj.get('completion', '{}')
        fix_data = json.loads(completion)
        return fix_data
    except Exception as e:
        print(f"Error generating fix: {e}", file=sys.stderr)
        return None


def create_patch_file(fix_data: Dict, output_file: Path) -> Optional[Path]:
    """Create a patch file from the fix data."""
    patch_content = f"""# Bug Fix Patch
## Root Cause
{fix_data.get('root_cause', 'Unknown')}

## Fix Description
{fix_data.get('fix_description', 'Unknown')}

## Testing Instructions
{fix_data.get('testing_instructions', 'Unknown')}

## Code Changes
"""
    
    for change in fix_data.get("code_changes", []):
        patch_content += f"\n### File: {change.get('file', 'unknown')}\n"
        patch_content += f"Action: {change.get('action', 'unknown')}\n\n"
        
        if change.get('old_code'):
            patch_content += "```diff\n"
            patch_content += f"- {change['old_code']}\n"
            patch_content += f"+ {change.get('new_code', '')}\n"
            patch_content += "```\n"
        else:
            patch_content += "```code\n"
            patch_content += f"{change.get('new_code', '')}\n"
            patch_content += "```\n"
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        f.write(patch_content)
    
    return output_file


def generate_fix(prd_file: Path, features_file: Path, output_dir: Path, api_key: str) -> Optional[Path]:
    """
    Generate a bug fix based on the PRD and features.
    
    Args:
        prd_file: Path to prd.md
        features_file: Path to bugs_with_features.json
        output_dir: Directory to save fix files
        api_key: API key for AI inference
        
    Returns:
        Path to the patch file, or None if failed
    """
    print("Generating fix prompt...", file=sys.stderr)
    prompt = generate_fix_prompt(prd_file, features_file)
    
    print("Requesting AI-generated fix...", file=sys.stderr)
    fix_data = generate_fix_with_ai(prompt, api_key)
    
    if not fix_data:
        print("Failed to generate fix", file=sys.stderr)
        return None
    
    # Save the raw fix data
    fix_json_file = output_dir / "bug_fix.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(fix_json_file, 'w') as f:
        json.dump(fix_data, f, indent=2)
    
    # Create patch file
    patch_file = output_dir / "bug_fix.patch"
    create_patch_file(fix_data, patch_file)
    
    print(f"Step 4 complete: Generated bug fix", file=sys.stderr)
    return patch_file


if __name__ == "__main__":
    from dotenv import load_dotenv
    
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
    
    if len(sys.argv) < 3:
        print("Usage: python bug_fixer.py <prd.md> <bugs_with_features.json> [output_dir]", file=sys.stderr)
        sys.exit(1)
    
    prd_file = Path(sys.argv[1])
    features_file = Path(sys.argv[2])
    output_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("./bugout_data")
    
    api_key = os.environ.get("FASTINO_KEY")
    if not api_key:
        print("Error: FASTINO_KEY not set in environment", file=sys.stderr)
        sys.exit(1)
    
    result = generate_fix(prd_file, features_file, output_dir, api_key)
    if result:
        print(f"Saved to: {result}")
    else:
        sys.exit(1)
