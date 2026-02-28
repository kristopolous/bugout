#!/usr/bin/env python3
"""
bugout.py - Main BugOut Orchestrator

BugOut: Automated bug fix workflow
1. Fetch issue comments via gh CLI
2. Extract features from comments using AI
3. Generate PRD using MCP-style analysis
4. Generate bug fix using AI
5. Check reviewer competence using Yutori
6. Prepare patch folder with all artifacts
7. Clone repo and run agentic loop with OpenAI
8. Generate actual patch file and update directory

Usage:
    python bugout.py <repo> <issue_number> [output_dir]
    
Example:
    python bugout.py microsoft/vscode 12345 ./bugout_data
"""

import json
import sys
import os
from pathlib import Path
from typing import Optional, Tuple
from dotenv import load_dotenv

# Import all steps
from comment_fetcher import fetch_issue_comments
from feature_extractor import process_comments
from prd_generator import generate_prd_from_file
from bug_fixer import generate_fix
from reviewer_checker_wrapper import check_reviewers_for_issue
from patch_generator import prepare_patch_folder
from repo_cloner import run_agentic_loop
from patch_creator import create_patch

# Load .env from parent directory
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")


def validate_environment() -> bool:
    """Validate that required environment variables and tools are available."""
    errors = []

    # Check for gh CLI
    import subprocess
    try:
        subprocess.run(["gh", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        errors.append("gh CLI not found. Please install GitHub CLI: https://cli.github.com/")

    # Check for FASTINO_KEY
    if not os.environ.get("FASTINO_KEY"):
        errors.append("FASTINO_KEY environment variable not set")

    # Check for YUTORI_KEY
    if not os.environ.get("YUTORI_KEY"):
        errors.append("YUTORI_KEY environment variable not set")

    # Check for OpenAI configuration (for step 7)
    if not os.environ.get("OPENAI_HOST"):
        errors.append("OPENAI_HOST environment variable not set")
    if not os.environ.get("OPENAI_MODEL"):
        errors.append("OPENAI_MODEL environment variable not set")

    if errors:
        print("Environment validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return False

    return True


def run_bugout(
    repo: str,
    issue_number: str,
    output_dir: Optional[Path] = None
) -> Tuple[bool, Optional[Path]]:
    """
    Run the complete BugOut workflow.
    
    Args:
        repo: Repository in format "owner/repo"
        issue_number: Issue number
        output_dir: Output directory (default: ./bugout_data/<repo>/<issue_number>)
        
    Returns:
        Tuple of (success: bool, patch_folder_path: Optional[Path])
    """
    # Setup output directory
    if output_dir is None:
        repo_name = repo.replace("/", "_")
        output_dir = Path(f"./bugout_data/{repo_name}/{issue_number}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"=" * 60, file=sys.stderr)
    print(f"BugOut: Processing {repo}#{issue_number}", file=sys.stderr)
    print(f"Output directory: {output_dir}", file=sys.stderr)
    print(f"=" * 60, file=sys.stderr)
    
    # Step 1: Fetch issue comments
    print(f"\n[Step 1/8] Fetching issue comments...", file=sys.stderr)
    comments_file = fetch_issue_comments(repo, issue_number, output_dir)
    if not comments_file:
        print("Step 1 failed: Could not fetch issue comments", file=sys.stderr)
        return False, None
    print(f"  Saved to: {comments_file}", file=sys.stderr)

    # Step 2: Extract features
    print(f"\n[Step 2/8] Extracting features from comments...", file=sys.stderr)
    features_file = output_dir / "bugs_with_features.json"
    api_key = os.environ.get("FASTINO_KEY")
    features_result = process_comments(comments_file, api_key, features_file)
    if not features_result:
        print("Step 2 failed: Could not extract features", file=sys.stderr)
        return False, None
    print(f"  Saved to: {features_result}", file=sys.stderr)

    # Step 3: Generate PRD
    print(f"\n[Step 3/8] Generating PRD...", file=sys.stderr)
    prd_file = output_dir / "prd.md"
    prd_result = generate_prd_from_file(features_file, prd_file)
    if not prd_result:
        print("Step 3 failed: Could not generate PRD", file=sys.stderr)
        return False, None
    print(f"  Saved to: {prd_result}", file=sys.stderr)

    # Step 4: Generate bug fix
    print(f"\n[Step 4/8] Generating bug fix...", file=sys.stderr)
    bug_fix_result = generate_fix(prd_file, features_file, output_dir, api_key)
    if not bug_fix_result:
        print("Step 4 failed: Could not generate bug fix", file=sys.stderr)
        return False, None
    print(f"  Saved to: {bug_fix_result}", file=sys.stderr)

    # Step 5: Check reviewer competence
    print(f"\n[Step 5/8] Checking reviewer competence...", file=sys.stderr)
    reviewer_result, best_reviewer = check_reviewers_for_issue(
        comments_file, repo, output_dir, wait=False
    )
    if not reviewer_result:
        print("Step 5 failed: Could not check reviewers", file=sys.stderr)
        return False, None
    print(f"  Saved to: {reviewer_result}", file=sys.stderr)
    print(f"  Best reviewer: {best_reviewer}", file=sys.stderr)

    # Step 6: Prepare initial patch folder
    print(f"\n[Step 6/8] Preparing initial patch folder...", file=sys.stderr)
    analysis_file = output_dir / "prd.analysis.json"
    bug_fix_json = output_dir / "bug_fix.json"

    patch_folder = prepare_patch_folder(
        output_dir,
        prd_file,
        bug_fix_result,
        reviewer_result,
        comments_file,
        features_file,
        analysis_file if analysis_file.exists() else None,
        bug_fix_json if bug_fix_json.exists() else None
    )
    print(f"  Initial patch folder: {patch_folder}", file=sys.stderr)

    # Step 7: Clone repo and run agentic loop
    print(f"\n[Step 7/8] Running agentic loop with OpenAI...", file=sys.stderr)
    bug_fix_json_path = output_dir / "bug_fix.json"
    clone_path, agent_response = run_agentic_loop(
        repo, prd_file,
        bug_fix_json_path if bug_fix_json_path.exists() else bug_fix_result,
        output_dir
    )
    if not clone_path or not agent_response:
        print("Step 7 failed: Agentic loop did not produce results", file=sys.stderr)
        # Continue anyway - we still have the initial patch
    else:
        print(f"  Clone path: {clone_path}", file=sys.stderr)
        print(f"  Agent response: {output_dir / 'agent_response.json'}", file=sys.stderr)

        # Step 8: Generate actual patch and update directory
        print(f"\n[Step 8/8] Generating actual patch file...", file=sys.stderr)
        generated_patch, updated_patch_folder = create_patch(
            clone_path, agent_response, output_dir
        )
        if generated_patch and updated_patch_folder:
            print(f"  Generated patch: {generated_patch}", file=sys.stderr)
            print(f"  Updated patch folder: {updated_patch_folder}", file=sys.stderr)
            patch_folder = updated_patch_folder
        else:
            print("Step 8 failed: Could not generate patch", file=sys.stderr)
    
    print(f"\n" + "=" * 60, file=sys.stderr)
    print(f"BugOut Complete!", file=sys.stderr)
    print(f"Patch folder: {patch_folder}", file=sys.stderr)
    print(f"Best reviewer: {best_reviewer}", file=sys.stderr)
    print(f"=" * 60, file=sys.stderr)
    
    # Print summary
    print_summary(patch_folder, best_reviewer, issue_number)
    
    return True, patch_folder


def print_summary(patch_folder: Path, best_reviewer: str, issue_number: str):
    """Print a summary of the generated artifacts."""
    print(f"""
╔══════════════════════════════════════════════════════════╗
║                    BugOut Summary                        ║
╠══════════════════════════════════════════════════════════╣
║ Issue:           #{issue_number}
║ Patch Folder:    {patch_folder}
║ Best Reviewer:   @{best_reviewer}
╠══════════════════════════════════════════════════════════╣
║ Generated Artifacts:                                     ║
║   - prd.md                  (Product Requirements Doc)   ║
║   - bug_fix.patch           (Initial Proposed Fix)      ║
║   - generated.patch         (AI-Generated Patch)        ║
║   - git.patch               (Git Diff Patch)            ║
║   - reviewer.json           (Reviewer Analysis)         ║
║   - issue_comments.json     (Raw Issue Data)            ║
║   - bugs_with_features.json (Feature Extraction)        ║
║   - agent_response.json     (Agentic Loop Output)       ║
║   - applied_changes.json    (Applied Changes Log)       ║
╚══════════════════════════════════════════════════════════╝

Next Steps:
1. Review the PRD: cat {patch_folder}/prd.md
2. Review the generated patch: cat {patch_folder}/generated.patch
3. Review applied changes: cat {patch_folder}/applied_changes.json
4. Contact reviewer: @{best_reviewer}
5. Create PR with the generated patch
""", file=sys.stderr)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print("Usage: python bugout.py <repo> <issue_number> [output_dir]", file=sys.stderr)
        sys.exit(1)
    
    repo = sys.argv[1]
    issue_number = sys.argv[2]
    output_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    
    # Validate environment
    if not validate_environment():
        sys.exit(1)
    
    # Run BugOut
    success, patch_folder = run_bugout(repo, issue_number, output_dir)
    
    if not success:
        print("\nBugOut failed. Check error messages above.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
