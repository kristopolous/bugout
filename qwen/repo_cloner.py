#!/usr/bin/env python3
"""
repo_cloner.py - Step 7: Clone repo and run agentic loop
"""

import json
import os
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# ANSI Colors
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_RED = "\033[91m"

SYMBOLS = {"check": "✅", "rocket": "🚀", "clone": "🔀", "sparkle": "✨"}

OPENAI_HOST = os.environ.get("OPENAI_HOST", "api.openai.com")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


def clone_repository(repo: str, temp_dir: Path) -> Path:
    """
    Clone a GitHub repository to a temporary directory.
    
    Args:
        repo: Repository in format "owner/repo"
        temp_dir: Base temp directory
        
    Returns:
        Path to the cloned repository
    """
    repo_name = repo.replace("/", "_")
    clone_path = temp_dir / f"{repo_name}_clone"
    
    github_url = f"https://github.com/{repo}.git"
    
    print(f"Cloning {repo} to {clone_path}...", file=sys.stderr)
    
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", github_url, str(clone_path)],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"  Cloned successfully", file=sys.stderr)
        return clone_path
    except subprocess.CalledProcessError as e:
        print(f"  Error cloning: {e.stderr}", file=sys.stderr)
        return None


def get_repo_structure(repo_path: Path, max_files: int = 100) -> str:
    """
    Get a summary of the repository structure.
    
    Args:
        repo_path: Path to cloned repository
        max_files: Maximum number of files to list
        
    Returns:
        String describing the structure
    """
    structure = []
    
    # Get file types and counts
    file_types = {}
    all_files = []
    
    for ext in ["*.py", "*.js", "*.ts", "*.tsx", "*.rs", "*.go", "*.java", "*.c", "*.cpp", "*.h", "*.hpp"]:
        try:
            result = subprocess.run(
                ["find", str(repo_path), "-name", ext, "-type", "f"],
                capture_output=True,
                text=True,
                timeout=30
            )
            files = [f for f in result.stdout.strip().split('\n') if f]
            for f in files[:20]:
                all_files.append(f)
            file_types[ext] = len(files)
        except Exception:
            pass
    
    structure.append("File counts by type:")
    for ext, count in file_types.items():
        structure.append(f"  {ext}: {count}")
    
    structure.append("\nSample files (first 20):")
    for f in all_files[:max_files]:
        rel_path = str(f).replace(str(repo_path), "")
        structure.append(f"  {rel_path}")
    
    return "\n".join(structure)


def read_relevant_files(repo_path: Path, prd_file: Path) -> List[Dict]:
    """
    Read files that might be relevant to the bug based on PRD analysis.
    
    Args:
        repo_path: Path to cloned repository
        prd_file: Path to PRD file
        
    Returns:
        List of dicts with file path and content
    """
    # Parse PRD for keywords
    with open(prd_file, 'r') as f:
        prd = f.read().lower()
    
    # Extract potential file patterns from PRD
    keywords = []
    for line in prd.split('\n'):
        if 'file' in line or 'module' in line or 'component' in line:
            # Extract potential file names
            words = line.split()
            for word in words:
                if '.' in word and len(word) > 3:
                    keywords.append(word)
    
    relevant_files = []
    
    # Search for relevant files
    for ext in ["*.py", "*.js", "*.ts", "*.tsx", "*.rs", "*.go"]:
        try:
            result = subprocess.run(
                ["find", str(repo_path), "-name", ext, "-type", "f"],
                capture_output=True,
                text=True,
                timeout=30
            )
            files = [f for f in result.stdout.strip().split('\n') if f]
            
            for filepath in files[:50]:  # Limit files to read
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Only include files with meaningful content
                    if len(content) > 100 and len(content) < 50000:
                        rel_path = str(filepath).replace(str(repo_path), "")
                        relevant_files.append({
                            "path": rel_path,
                            "content": content[:10000]  # Truncate for context
                        })
                except Exception:
                    pass
        except Exception:
            pass
    
    return relevant_files[:20]  # Limit to 20 files


def create_agentic_prompt(
    prd_file: Path,
    bug_fix_file: Path,
    repo_structure: str,
    relevant_files: List[Dict]
) -> str:
    """
    Create a prompt for the agentic loop.
    
    Args:
        prd_file: Path to PRD
        bug_fix_file: Path to bug_fix.json or bug_fix.patch
        repo_structure: Repository structure summary
        relevant_files: List of relevant file contents
        
    Returns:
        Prompt string for the AI agent
    """
    with open(prd_file, 'r') as f:
        prd = f.read()
    
    # Try to load bug fix JSON, fallback to patch
    bug_context = ""
    if bug_fix_file.exists():
        if bug_fix_file.suffix == '.json':
            with open(bug_fix_file, 'r') as f:
                bug_data = json.load(f)
                bug_context = f"""
Root Cause: {bug_data.get('root_cause', 'Unknown')}
Fix Description: {bug_data.get('fix_description', 'Unknown')}
Testing Instructions: {bug_data.get('testing_instructions', 'Unknown')}
"""
        else:
            with open(bug_fix_file, 'r') as f:
                bug_context = f.read()[:5000]
    
    files_context = ""
    for i, file_info in enumerate(relevant_files[:10], 1):
        files_context += f"\n### File {i}: {file_info['path']}\n```{file_info['path'].split('.')[-1]}\n{file_info['content'][:3000]}\n```\n"
    
    prompt = f"""You are an expert software engineer agent. Your task is to analyze a bug and generate a precise code fix.

## Context

### Product Requirements Document (PRD)
{prd}

### Previous Bug Fix Analysis
{bug_context}

### Repository Structure
{repo_structure}

### Relevant Source Files
{files_context}

## Your Task

Analyze the bug reports, PRD, and source code to:

1. **Identify the Root Cause**: Pinpoint the exact location and nature of the bug in the codebase
2. **Design a Fix**: Create a minimal, targeted fix that addresses the root cause
3. **Generate the Patch**: Output the exact code changes needed

## Output Format

Respond with a JSON object containing:

```json
{{
    "analysis": {{
        "root_cause": "Detailed explanation of the root cause",
        "affected_files": ["list", "of", "affected", "files"],
        "fix_strategy": "Description of the fix approach"
    }},
    "changes": [
        {{
            "file": "path/to/file.py",
            "action": "modify",
            "line_start": 42,
            "line_end": 55,
            "old_code": "original code here",
            "new_code": "fixed code here",
            "explanation": "Why this change fixes the bug"
        }}
    ],
    "testing": {{
        "unit_tests": "Description of unit tests to add/modify",
        "integration_tests": "Description of integration tests",
        "manual_verification": "Steps to manually verify the fix"
    }},
    "confidence": 0.95
}}
```

## Guidelines

1. Be precise with line numbers and code changes
2. Minimize the scope of changes - only fix what's necessary
3. Preserve existing code style and conventions
4. Include error handling where appropriate
5. Consider edge cases

Begin your analysis now.
"""
    
    return prompt


def call_openai_agent(prompt: str) -> Optional[Dict]:
    """
    Call OpenAI API (or compatible) with the agent prompt.
    
    Args:
        prompt: The prompt to send
        
    Returns:
        Parsed JSON response or None
    """
    import requests
    
    api_key = OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY", "dummy")
    
    # Determine the API endpoint
    if OPENAI_HOST == "api.openai.com":
        base_url = "https://api.openai.com/v1"
    else:
        base_url = f"https://{OPENAI_HOST}/v1"
    
    endpoint = f"{base_url}/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are an expert software engineer agent. You output strict JSON with code fixes. You are not conversational. Always respond with valid JSON only."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1,
        "max_tokens": 4096
    }
    
    try:
        print(f"  Calling {OPENAI_HOST} with model {OPENAI_MODEL}...", file=sys.stderr)
        
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        
        result = response.json()
        completion = result["choices"][0]["message"]["content"]
        
        # Parse JSON from response
        # Handle potential markdown code blocks
        if "```json" in completion:
            completion = completion.split("```json")[1].split("```")[0]
        elif "```" in completion:
            completion = completion.split("```")[1].split("```")[0]
        
        agent_response = json.loads(completion.strip())
        return agent_response
        
    except requests.RequestException as e:
        print(f"  API error: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"  JSON parse error: {e}", file=sys.stderr)
        print(f"  Raw response: {completion[:500]}...", file=sys.stderr)
        return None


def run_agentic_loop(
    repo: str,
    prd_file: Path,
    bug_fix_file: Path,
    output_dir: Path
) -> Tuple[Optional[Path], Optional[Dict]]:
    """
    Run the complete agentic loop.
    
    Args:
        repo: Repository in format "owner/repo"
        prd_file: Path to PRD
        bug_fix_file: Path to bug fix file
        output_dir: Output directory
        
    Returns:
        Tuple of (clone_path, agent_response)
    """
    # Create temp directory
    temp_dir = output_dir / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{Colors.BRIGHT_MAGENTA}{SYMBOLS['rocket']} Step 7: Agentic Loop{Colors.RESET}", file=sys.stderr)
    print(f"  {Colors.DIM}Temp directory: {temp_dir}{Colors.RESET}", file=sys.stderr)

    # Clone repository
    clone_path = clone_repository(repo, temp_dir)
    if not clone_path:
        print(f"  {Colors.BRIGHT_RED}✗ Failed to clone repository{Colors.RESET}", file=sys.stderr)
        return None, None

    # Get repository structure
    print(f"  {Colors.CYAN}Analyzing repository structure...{Colors.RESET}", file=sys.stderr)
    repo_structure = get_repo_structure(clone_path)

    # Read relevant files
    print(f"  {Colors.CYAN}Reading relevant source files...{Colors.RESET}", file=sys.stderr)
    relevant_files = read_relevant_files(clone_path, prd_file)
    print(f"  {Colors.GREEN}Found {len(relevant_files)} relevant files{Colors.RESET}", file=sys.stderr)

    # Create agentic prompt
    print(f"  {Colors.CYAN}Creating agentic prompt...{Colors.RESET}", file=sys.stderr)
    prompt = create_agentic_prompt(prd_file, bug_fix_file, repo_structure, relevant_files)

    # Call AI agent
    print(f"  {Colors.MAGENTA}Running AI agent...{Colors.RESET}", file=sys.stderr)
    agent_response = call_openai_agent(prompt)

    if not agent_response:
        print(f"  {Colors.BRIGHT_RED}✗ Agent failed to generate response{Colors.RESET}", file=sys.stderr)
        return clone_path, None

    # Save agent response
    agent_file = output_dir / "agent_response.json"
    with open(agent_file, 'w') as f:
        json.dump(agent_response, f, indent=2)

    print(f"  {Colors.GREEN}{SYMBOLS['check']} Agent response saved to: {agent_file}{Colors.RESET}", file=sys.stderr)
    print(f"{Colors.BRIGHT_GREEN}{SYMBOLS['check']} Step 7 complete: Agentic loop finished{Colors.RESET}", file=sys.stderr)
    
    return clone_path, agent_response


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(
            "Usage: python repo_cloner.py <repo> <prd.md> <bug_fix.json|bug_fix.patch> [output_dir]",
            file=sys.stderr
        )
        sys.exit(1)
    
    repo = sys.argv[1]
    prd_file = Path(sys.argv[2])
    bug_fix_file = Path(sys.argv[3])
    output_dir = Path(sys.argv[4]) if len(sys.argv) > 4 else Path("./bugout_data")
    
    clone_path, agent_response = run_agentic_loop(repo, prd_file, bug_fix_file, output_dir)
    
    if clone_path:
        print(f"Clone path: {clone_path}")
    if agent_response:
        print(f"Agent generated {len(agent_response.get('changes', []))} code changes")
    else:
        sys.exit(1)
