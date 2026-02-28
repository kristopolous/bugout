#!/usr/bin/env python3
"""
bugout.py - Main BugOut Orchestrator

🐛 BugOut: From bug report to patch in 8 automated steps
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

# ═══════════════════════════════════════════════════════════════════════════════
# ANSI Color codes
# ═══════════════════════════════════════════════════════════════════════════════

class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    
    # Foreground colors
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright foreground
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    
    # Background colors
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_RED = "\033[41m"

# ═══════════════════════════════════════════════════════════════════════════════
# Unicode symbols
# ═══════════════════════════════════════════════════════════════════════════════

SYMBOLS = {
    "success": "✓",
    "error": "✗",
    "warning": "⚠",
    "info": "ℹ",
    "arrow": "→",
    "star": "★",
    "bug": "🐛",
    "rocket": "🚀",
    "check": "✅",
    "folder": "📁",
    "file": "📄",
    "gear": "⚙️",
    "sparkle": "✨",
    "link": "🔗",
    "target": "🎯",
}

# ═══════════════════════════════════════════════════════════════════════════════
# Print functions
# ═══════════════════════════════════════════════════════════════════════════════

def print_banner():
    """Print the BugOut banner."""
    # Load logo from parent directory
    logo_path = Path(__file__).parent.parent / "logo.ansiart"
    logo = ""
    if logo_path.exists():
        with open(logo_path, 'r') as f:
            logo = f.read()
    
    banner = f"""
{Colors.BRIGHT_CYAN}{logo}{Colors.RESET}
{Colors.BRIGHT_MAGENTA}╔══════════════════════════════════════════════════════════════╗{Colors.RESET}
{Colors.BRIGHT_MAGENTA}║{Colors.RESET}     {Colors.BOLD}{Colors.BRIGHT_CYAN}🐛 BugOut - Automated Bug Fix Workflow{Colors.RESET}{Colors.BRIGHT_MAGENTA}              {Colors.RESET}║{Colors.RESET}
{Colors.BRIGHT_MAGENTA}╠══════════════════════════════════════════════════════════════╣{Colors.RESET}
{Colors.BRIGHT_MAGENTA}║{Colors.RESET}  {Colors.DIM}From bug report to production-ready patch{Colors.RESET}                    {Colors.BRIGHT_MAGENTA}║{Colors.RESET}
{Colors.BRIGHT_MAGENTA}╚══════════════════════════════════════════════════════════════╝{Colors.RESET}
"""
    print(banner, file=sys.stderr)


def print_step_header(step_num: int, total_steps: int, title: str):
    """Print a formatted step header."""
    progress = f"{Colors.DIM}[{step_num}/{total_steps}]{Colors.RESET}"
    icon = f"{Colors.BRIGHT_CYAN}●{Colors.RESET}"
    print(f"\n{Colors.BOLD}{Colors.BRIGHT_BLUE}━{Colors.RESET} {icon} {progress} {Colors.BOLD}{title}{Colors.RESET}", file=sys.stderr)


def print_step_success(message: str):
    """Print success message."""
    print(f"  {Colors.BRIGHT_GREEN}{SYMBOLS['check']}{Colors.RESET} {Colors.GREEN}{message}{Colors.RESET}", file=sys.stderr)


def print_step_error(message: str):
    """Print error message."""
    print(f"  {Colors.BRIGHT_RED}{SYMBOLS['error']}{Colors.RESET} {Colors.RED}{message}{Colors.RESET}", file=sys.stderr)


def print_step_info(message: str):
    """Print info message."""
    print(f"  {Colors.BRIGHT_CYAN}{SYMBOLS['info']}{Colors.RESET} {Colors.CYAN}{message}{Colors.RESET}", file=sys.stderr)


def print_step_warning(message: str):
    """Print warning message."""
    print(f"  {Colors.BRIGHT_YELLOW}{SYMBOLS['warning']}{Colors.RESET} {Colors.YELLOW}{message}{Colors.RESET}", file=sys.stderr)


def print_sub_step(message: str, value: str = ""):
    """Print a sub-step with formatted output."""
    if value:
        print(f"    {Colors.DIM}{SYMBOLS['arrow']}{Colors.RESET} {Colors.WHITE}{message}{Colors.RESET}: {Colors.BRIGHT_WHITE}{value}{Colors.RESET}", file=sys.stderr)
    else:
        print(f"    {Colors.DIM}{SYMBOLS['arrow']}{Colors.RESET} {Colors.WHITE}{message}{Colors.RESET}", file=sys.stderr)


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
        print(f"\n{Colors.BG_MAGENTA}{Colors.BOLD} Environment Validation Failed {Colors.RESET}", file=sys.stderr)
        for error in errors:
            print(f"  {Colors.BRIGHT_RED}{SYMBOLS['error']}{Colors.RESET} {Colors.RED}{error}{Colors.RESET}", file=sys.stderr)
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
    # Print banner
    print_banner()
    
    # Setup output directory
    if output_dir is None:
        repo_name = repo.replace("/", "_")
        output_dir = Path(f"./bugout_data/{repo_name}/{issue_number}")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Print header
    print(f"{Colors.BG_BLUE}{Colors.BOLD} Configuration {Colors.RESET}", file=sys.stderr)
    print_sub_step("Repository", f"{Colors.BRIGHT_CYAN}{repo}{Colors.RESET}")
    print_sub_step("Issue", f"{Colors.BRIGHT_YELLOW}#{issue_number}{Colors.RESET}")
    print_sub_step("Output", f"{Colors.DIM}{output_dir}{Colors.RESET}")
    print(f"{Colors.DIM}{'─' * 60}{Colors.RESET}", file=sys.stderr)

    total_steps = 8
    best_reviewer = None
    patch_folder = None

    # ═══════════════════════════════════════════════════════════════════════════
    # Step 1: Fetch issue comments
    # ═══════════════════════════════════════════════════════════════════════════
    print_step_header(1, total_steps, f"{SYMBOLS['link']} Fetching issue comments")
    comments_file = fetch_issue_comments(repo, issue_number, output_dir)
    if not comments_file:
        print_step_error("Could not fetch issue comments")
        return False, None
    print_step_success(f"Saved: {Colors.DIM}{comments_file}{Colors.RESET}")

    # ═══════════════════════════════════════════════════════════════════════════
    # Step 2: Extract features
    # ═══════════════════════════════════════════════════════════════════════════
    print_step_header(2, total_steps, f"{SYMBOLS['gear']} Extracting features from comments")
    features_file = output_dir / "bugs_with_features.json"
    api_key = os.environ.get("FASTINO_KEY")
    features_result = process_comments(comments_file, api_key, features_file)
    if not features_result:
        print_step_error("Could not extract features")
        return False, None
    print_step_success(f"Saved: {Colors.DIM}{features_result}{Colors.RESET}")

    # ═══════════════════════════════════════════════════════════════════════════
    # Step 3: Generate PRD
    # ═══════════════════════════════════════════════════════════════════════════
    print_step_header(3, total_steps, f"{SYMBOLS['target']} Generating PRD")
    prd_file = output_dir / "prd.md"
    prd_result = generate_prd_from_file(features_file, prd_file)
    if not prd_result:
        print_step_error("Could not generate PRD")
        return False, None
    print_step_success(f"Saved: {Colors.DIM}{prd_result}{Colors.RESET}")

    # ═══════════════════════════════════════════════════════════════════════════
    # Step 4: Generate bug fix
    # ═══════════════════════════════════════════════════════════════════════════
    print_step_header(4, total_steps, f"{SYMBOLS['bug']} Generating bug fix")
    bug_fix_result = generate_fix(prd_file, features_file, output_dir, api_key)
    if not bug_fix_result:
        print_step_error("Could not generate bug fix")
        return False, None
    print_step_success(f"Saved: {Colors.DIM}{bug_fix_result}{Colors.RESET}")

    # ═══════════════════════════════════════════════════════════════════════════
    # Step 5: Check reviewer competence
    # ═══════════════════════════════════════════════════════════════════════════
    print_step_header(5, total_steps, f"{SYMBOLS['star']} Checking reviewer competence")
    reviewer_result, best_reviewer = check_reviewers_for_issue(
        comments_file, repo, output_dir, wait=False
    )
    if not reviewer_result:
        print_step_error("Could not check reviewers")
        return False, None
    print_step_success(f"Saved: {Colors.DIM}{reviewer_result}{Colors.RESET}")
    if best_reviewer:
        print_sub_step("Best reviewer", f"{Colors.BRIGHT_CYAN}@{best_reviewer}{Colors.RESET}")

    # ═══════════════════════════════════════════════════════════════════════════
    # Step 6: Prepare initial patch folder
    # ═══════════════════════════════════════════════════════════════════════════
    print_step_header(6, total_steps, f"{SYMBOLS['folder']} Preparing initial patch folder")
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
    print_step_success(f"Created: {Colors.DIM}{patch_folder}{Colors.RESET}")

    # ═══════════════════════════════════════════════════════════════════════════
    # Step 7: Clone repo and run agentic loop
    # ═══════════════════════════════════════════════════════════════════════════
    print_step_header(7, total_steps, f"{SYMBOLS['rocket']} Running agentic loop with OpenAI")
    bug_fix_json_path = output_dir / "bug_fix.json"
    clone_path, agent_response = run_agentic_loop(
        repo, prd_file,
        bug_fix_json_path if bug_fix_json_path.exists() else bug_fix_result,
        output_dir
    )
    if not clone_path or not agent_response:
        print_step_warning("Agentic loop did not produce results (continuing...)")
    else:
        print_step_success(f"Clone: {Colors.DIM}{clone_path}{Colors.RESET}")
        print_sub_step("Agent response", f"{Colors.DIM}{output_dir / 'agent_response.json'}{Colors.RESET}")

        # ═══════════════════════════════════════════════════════════════════════
        # Step 8: Generate actual patch and update directory
        # ═══════════════════════════════════════════════════════════════════════
        print_step_header(8, total_steps, f"{SYMBOLS['sparkle']} Generating actual patch file")
        generated_patch, updated_patch_folder = create_patch(
            clone_path, agent_response, output_dir
        )
        if generated_patch and updated_patch_folder:
            print_step_success(f"Generated: {Colors.DIM}{generated_patch}{Colors.RESET}")
            print_step_success(f"Updated: {Colors.DIM}{updated_patch_folder}{Colors.RESET}")
            patch_folder = updated_patch_folder
        else:
            print_step_error("Could not generate patch")

    # ═══════════════════════════════════════════════════════════════════════════
    # Final Summary
    # ═══════════════════════════════════════════════════════════════════════════
    print(f"\n{Colors.BRIGHT_MAGENTA}{'═' * 62}{Colors.RESET}", file=sys.stderr)
    print(f"{Colors.BG_MAGENTA}{Colors.BOLD}  {SYMBOLS['rocket']} BugOut Complete! {Colors.RESET}", file=sys.stderr)
    print(f"{Colors.BRIGHT_MAGENTA}{'═' * 62}{Colors.RESET}", file=sys.stderr)
    
    print_summary(patch_folder, best_reviewer, issue_number, repo)

    return True, patch_folder


def print_summary(patch_folder: Path, best_reviewer: str, issue_number: str, repo: str):
    """Print a summary of the generated artifacts."""
    summary = f"""
{Colors.BRIGHT_CYAN}╔══════════════════════════════════════════════════════════════╗{Colors.RESET}
{Colors.BRIGHT_CYAN}║{Colors.RESET}              {Colors.BOLD}BugOut Summary{Colors.RESET}                                {Colors.BRIGHT_CYAN}║{Colors.RESET}
{Colors.BRIGHT_CYAN}╠══════════════════════════════════════════════════════════════╣{Colors.RESET}
{Colors.BRIGHT_CYAN}║{Colors.RESET}  {Colors.DIM}Repository:{Colors.RESET} {Colors.WHITE}{repo:<44}{Colors.RESET}  {Colors.BRIGHT_CYAN}║{Colors.RESET}
{Colors.BRIGHT_CYAN}║{Colors.RESET}  {Colors.DIM}Issue:{Colors.RESET}      {Colors.BRIGHT_YELLOW}#{issue_number:<46}{Colors.RESET}  {Colors.BRIGHT_CYAN}║{Colors.RESET}
{Colors.BRIGHT_CYAN}║{Colors.RESET}  {Colors.DIM}Patch Folder:{Colors.RESET} {Colors.DIM}{str(patch_folder)[:44]:<44}{Colors.RESET}  {Colors.BRIGHT_CYAN}║{Colors.RESET}
{Colors.BRIGHT_CYAN}║{Colors.RESET}  {Colors.DIM}Best Reviewer:{Colors.RESET} {Colors.BRIGHT_GREEN}@{best_reviewer:<43}{Colors.RESET}  {Colors.BRIGHT_CYAN}║{Colors.RESET}
{Colors.BRIGHT_CYAN}╠══════════════════════════════════════════════════════════════╣{Colors.RESET}
{Colors.BRIGHT_CYAN}║{Colors.RESET}  {Colors.BOLD}Generated Artifacts:{Colors.RESET}                                      {Colors.BRIGHT_CYAN}║{Colors.RESET}
{Colors.BRIGHT_CYAN}║{Colors.RESET}    {Colors.WHITE}• prd.md{Colors.RESET}                  {Colors.DIM}(Product Requirements Doc){Colors.RESET}    {Colors.BRIGHT_CYAN}║{Colors.RESET}
{Colors.BRIGHT_CYAN}║{Colors.RESET}    {Colors.WHITE}• bug_fix.patch{Colors.RESET}           {Colors.DIM}(Initial Proposed Fix){Colors.RESET}       {Colors.BRIGHT_CYAN}║{Colors.RESET}
{Colors.BRIGHT_CYAN}║{Colors.RESET}    {Colors.WHITE}• generated.patch{Colors.RESET}         {Colors.DIM}(AI-Generated Patch){Colors.RESET}        {Colors.BRIGHT_CYAN}║{Colors.RESET}
{Colors.BRIGHT_CYAN}║{Colors.RESET}    {Colors.WHITE}• git.patch{Colors.RESET}               {Colors.DIM}(Git Diff Patch){Colors.RESET}            {Colors.BRIGHT_CYAN}║{Colors.RESET}
{Colors.BRIGHT_CYAN}║{Colors.RESET}    {Colors.WHITE}• reviewer.json{Colors.RESET}           {Colors.DIM}(Reviewer Analysis){Colors.RESET}         {Colors.BRIGHT_CYAN}║{Colors.RESET}
{Colors.BRIGHT_CYAN}║{Colors.RESET}    {Colors.WHITE}• agent_response.json{Colors.RESET}     {Colors.DIM}(Agentic Loop Output){Colors.RESET}       {Colors.BRIGHT_CYAN}║{Colors.RESET}
{Colors.BRIGHT_CYAN}║{Colors.RESET}    {Colors.WHITE}• applied_changes.json{Colors.RESET}    {Colors.DIM}(Applied Changes Log){Colors.RESET}       {Colors.BRIGHT_CYAN}║{Colors.RESET}
{Colors.BRIGHT_CYAN}╠══════════════════════════════════════════════════════════════╣{Colors.RESET}
{Colors.BRIGHT_CYAN}║{Colors.RESET}  {Colors.BOLD}Next Steps:{Colors.RESET}                                                {Colors.BRIGHT_CYAN}║{Colors.RESET}
{Colors.BRIGHT_CYAN}║{Colors.RESET}    {Colors.DIM}1.{Colors.RESET} Review PRD:        {Colors.WHITE}cat {patch_folder}/prd.md{Colors.RESET}              {Colors.BRIGHT_CYAN}║{Colors.RESET}
{Colors.BRIGHT_CYAN}║{Colors.RESET}    {Colors.DIM}2.{Colors.RESET} Review patch:      {Colors.WHITE}cat {patch_folder}/generated.patch{Colors.RESET}   {Colors.BRIGHT_CYAN}║{Colors.RESET}
{Colors.BRIGHT_CYAN}║{Colors.RESET}    {Colors.DIM}3.{Colors.RESET} Contact reviewer:  {Colors.BRIGHT_GREEN}@{best_reviewer}{Colors.RESET}                       {Colors.BRIGHT_CYAN}║{Colors.RESET}
{Colors.BRIGHT_CYAN}║{Colors.RESET}    {Colors.DIM}4.{Colors.RESET} Create PR with the generated patch                     {Colors.BRIGHT_CYAN}║{Colors.RESET}
{Colors.BRIGHT_CYAN}╚══════════════════════════════════════════════════════════════╝{Colors.RESET}
"""
    print(summary, file=sys.stderr)


def main():
    if len(sys.argv) < 3:
        # Load logo for usage message
        logo_path = Path(__file__).parent.parent / "logo.ansiart"
        logo = ""
        if logo_path.exists():
            with open(logo_path, 'r') as f:
                logo = f.read()
        
        print(f"""
{Colors.BRIGHT_CYAN}{logo}{Colors.RESET}
{Colors.BRIGHT_MAGENTA}╔══════════════════════════════════════════════════════════════╗{Colors.RESET}
{Colors.BRIGHT_MAGENTA}║{Colors.RESET}     {Colors.BOLD}{Colors.BRIGHT_CYAN}🐛 BugOut - Automated Bug Fix Workflow{Colors.RESET}{Colors.BRIGHT_MAGENTA}              {Colors.RESET}║{Colors.RESET}
{Colors.BRIGHT_MAGENTA}╠══════════════════════════════════════════════════════════════╣{Colors.RESET}
{Colors.BRIGHT_MAGENTA}║{Colors.RESET}  {Colors.DIM}Usage:{Colors.RESET}                                                       {Colors.BRIGHT_MAGENTA}║{Colors.RESET}
{Colors.BRIGHT_MAGENTA}║{Colors.RESET}    {Colors.WHITE}python bugout.py <repo> <issue_number> [output_dir]{Colors.RESET}          {Colors.BRIGHT_MAGENTA}║{Colors.RESET}
{Colors.BRIGHT_MAGENTA}║{Colors.RESET}                                                          {Colors.BRIGHT_MAGENTA}║{Colors.RESET}
{Colors.BRIGHT_MAGENTA}║{Colors.RESET}  {Colors.DIM}Example:{Colors.RESET}                                                     {Colors.BRIGHT_MAGENTA}║{Colors.RESET}
{Colors.BRIGHT_MAGENTA}║{Colors.RESET}    {Colors.WHITE}python bugout.py microsoft/vscode 12345{Colors.RESET}                      {Colors.BRIGHT_MAGENTA}║{Colors.RESET}
{Colors.BRIGHT_MAGENTA}╚══════════════════════════════════════════════════════════════╝{Colors.RESET}
""", file=sys.stderr)
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
        print(f"\n{Colors.BG_RED}{Colors.BOLD} BugOut Failed {Colors.RESET}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
