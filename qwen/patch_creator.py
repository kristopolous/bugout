#!/usr/bin/env python3
"""
patch_creator.py - Step 8: Generate actual patch file
"""

import json
import os
import subprocess
import sys
import shutil
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime

# ANSI Colors
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"
    YELLOW = "\033[33m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_YELLOW = "\033[93m"

SYMBOLS = {"check": "✅", "sparkle": "✨", "patch": "📝", "file": "📄"}


def create_unified_diff(
    old_content: str,
    new_content: str,
    old_path: str,
    new_path: str
) -> str:
    """
    Create a unified diff between two strings.
    
    Args:
        old_content: Original file content
        new_content: New file content
        old_path: Path for the "a" side
        new_path: Path for the "b" side
        
    Returns:
        Unified diff string
    """
    import difflib
    
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{old_path}",
        tofile=f"b/{new_path}",
        lineterm="\n"
    )
    
    return "".join(diff)


def apply_change_to_file(
    clone_path: Path,
    file_path: str,
    old_code: str,
    new_code: str
) -> Tuple[bool, str, str]:
    """
    Apply a code change to a file in the cloned repository.
    
    Args:
        clone_path: Path to cloned repository
        file_path: Relative path to the file
        old_code: Code to replace
        new_code: Replacement code
        
    Returns:
        Tuple of (success, old_content, new_content)
    """
    full_path = clone_path / file_path.lstrip('/')
    
    if not full_path.exists():
        print(f"    File not found: {file_path}", file=sys.stderr)
        return False, "", ""
    
    try:
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            original_content = f.read()
        
        # Try to find and replace the old code
        if old_code in original_content:
            new_content = original_content.replace(old_code, new_code, 1)
        else:
            # Try fuzzy matching - find similar block
            print(f"    Exact match not found, trying line-based replacement...", file=sys.stderr)
            old_lines = old_code.strip().split('\n')
            original_lines = original_content.split('\n')
            
            # Find the best matching block
            best_match_start = -1
            best_match_score = 0
            
            for i in range(len(original_lines) - len(old_lines) + 1):
                block = original_lines[i:i + len(old_lines)]
                matches = sum(1 for a, b in zip(block, old_lines) if a.strip() == b.strip())
                score = matches / len(old_lines)
                
                if score > best_match_score:
                    best_match_score = score
                    best_match_start = i
            
            if best_match_score > 0.5:
                # Replace the matched block
                new_lines = original_lines[:best_match_start] + new_code.split('\n') + original_lines[best_match_start + len(old_lines):]
                new_content = '\n'.join(new_lines)
            else:
                print(f"    Could not find matching code block (best score: {best_match_score:.2f})", file=sys.stderr)
                return False, original_content, original_content
        
        # Write the new content
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True, original_content, new_content
        
    except Exception as e:
        print(f"    Error modifying file: {e}", file=sys.stderr)
        return False, "", ""


def generate_patch_from_agent(
    clone_path: Path,
    agent_response: Dict,
    output_dir: Path
) -> Tuple[Optional[Path], List[Dict]]:
    """
    Generate a patch file from the agent response.
    
    Args:
        clone_path: Path to cloned repository
        agent_response: Agent response JSON
        output_dir: Output directory
        
    Returns:
        Tuple of (patch_file_path, applied_changes)
    """
    changes = agent_response.get("changes", [])
    applied_changes = []
    patch_parts = []

    print(f"\n{Colors.BRIGHT_MAGENTA}{SYMBOLS['sparkle']} Step 8: Generating Patch{Colors.RESET}", file=sys.stderr)
    print(f"  {Colors.CYAN}Applying {len(changes)} changes...{Colors.RESET}", file=sys.stderr)

    for i, change in enumerate(changes, 1):
        file_path = change.get("file", "")
        old_code = change.get("old_code", "")
        new_code = change.get("new_code", "")
        action = change.get("action", "modify")
        explanation = change.get("explanation", "")

        print(f"    {Colors.DIM}Change {i}/{len(changes)}: {Colors.WHITE}{file_path}{Colors.RESET} {Colors.DIM}({action}){Colors.RESET}", file=sys.stderr)
        
        if action == "create":
            # Create new file
            full_path = clone_path / file_path.lstrip('/')
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(new_code)
            applied_changes.append({
                "file": file_path,
                "action": "create",
                "status": "success"
            })
            patch_parts.append(f"diff --git a/{file_path} b/{file_path}\n")
            patch_parts.append(f"new file mode 100644\n")
            patch_parts.append(f"--- /dev/null\n")
            patch_parts.append(f"+++ b/{file_path}\n")
            patch_parts.append(f"+{new_code}\n")
            
        elif action == "delete":
            # Delete file
            full_path = clone_path / file_path.lstrip('/')
            if full_path.exists():
                os.remove(full_path)
            applied_changes.append({
                "file": file_path,
                "action": "delete",
                "status": "success"
            })
            
        elif action == "modify":
            # Modify existing file
            success, old_content, new_content = apply_change_to_file(
                clone_path, file_path, old_code, new_code
            )
            
            if success:
                applied_changes.append({
                    "file": file_path,
                    "action": "modify",
                    "status": "success",
                    "explanation": explanation
                })
                
                # Generate diff for this change
                diff = create_unified_diff(old_content, new_content, file_path, file_path)
                if diff:
                    patch_parts.append(diff)
            else:
                applied_changes.append({
                    "file": file_path,
                    "action": "modify",
                    "status": "failed",
                    "reason": "Could not apply change"
                })
    
    # Create the patch file
    patch_content = f"""# Bug Fix Patch
# Generated: {datetime.now().isoformat()}
# Issue: See PRD for details

"""
    patch_content += "".join(patch_parts)
    
    patch_file = output_dir / "generated.patch"
    with open(patch_file, 'w') as f:
        f.write(patch_content)
    
    # Also create a git-style patch if git is available
    try:
        git_patch = output_dir / "git.patch"
        result = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd=clone_path,
            capture_output=True,
            text=True
        )
        if result.stdout:
            with open(git_patch, 'w') as f:
                f.write(result.stdout)
            print(f"  Git patch saved to: {git_patch}", file=sys.stderr)
    except Exception as e:
        print(f"  Could not create git patch: {e}", file=sys.stderr)
    
    # Save applied changes log
    changes_log = output_dir / "applied_changes.json"
    with open(changes_log, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_changes": len(changes),
            "successful": len([c for c in applied_changes if c.get("status") == "success"]),
            "failed": len([c for c in applied_changes if c.get("status") == "failed"]),
            "changes": applied_changes,
            "analysis": agent_response.get("analysis", {}),
            "testing": agent_response.get("testing", {}),
            "confidence": agent_response.get("confidence", 0)
        }, f, indent=2)
    
    print(f"  {Colors.BRIGHT_GREEN}{SYMBOLS['check']} Patch saved to: {Colors.DIM}{patch_file}{Colors.RESET}", file=sys.stderr)
    print(f"  {Colors.BRIGHT_GREEN}{SYMBOLS['check']} Changes log saved to: {Colors.DIM}{changes_log}{Colors.RESET}", file=sys.stderr)
    
    return patch_file, applied_changes


def update_patch_folder(
    output_dir: Path,
    generated_patch: Path,
    clone_path: Path
) -> Path:
    """
    Update the patch folder with the newly generated patch.
    
    Args:
        output_dir: Output directory
        generated_patch: Path to generated.patch
        clone_path: Path to cloned repository
        
    Returns:
        Path to updated patch folder
    """
    patch_folder = output_dir / "patch"
    patch_folder.mkdir(parents=True, exist_ok=True)
    
    # Copy generated patch to patch folder
    shutil.copy2(generated_patch, patch_folder / "generated.patch")
    
    # Copy git patch if available
    git_patch = output_dir / "git.patch"
    if git_patch.exists():
        shutil.copy2(git_patch, patch_folder / "git.patch")
    
    # Copy applied changes log
    changes_log = output_dir / "applied_changes.json"
    if changes_log.exists():
        shutil.copy2(changes_log, patch_folder / "applied_changes.json")
    
    # Copy agent response
    agent_response = output_dir / "agent_response.json"
    if agent_response.exists():
        shutil.copy2(agent_response, patch_folder / "agent_response.json")
    
    # Create a copy of the modified repo snapshot
    repo_snapshot = output_dir / "repo_snapshot"
    if clone_path.exists() and not repo_snapshot.exists():
        shutil.copytree(clone_path, repo_snapshot, ignore=shutil.ignore_patterns('.git'))
        print(f"  {Colors.BRIGHT_GREEN}{SYMBOLS['check']} Repository snapshot saved to: {Colors.DIM}{repo_snapshot}{Colors.RESET}", file=sys.stderr)
    
    # Update manifest
    manifest_file = patch_folder / "patch_manifest.json"
    if manifest_file.exists():
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)
    else:
        manifest = {"artifacts": []}
    
    manifest["generated_patch"] = "generated.patch"
    manifest["git_patch"] = "git.patch"
    manifest["applied_changes"] = "applied_changes.json"
    manifest["agent_response"] = "agent_response.json"
    manifest["status"] = "ready_for_review"
    manifest["timestamp"] = datetime.now().isoformat()
    
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"{Colors.BRIGHT_GREEN}{SYMBOLS['check']} Step 8 complete: Patch folder updated{Colors.RESET}", file=sys.stderr)
    return patch_folder


def create_patch(
    clone_path: Path,
    agent_response: Dict,
    output_dir: Path
) -> Tuple[Optional[Path], Path]:
    """
    Main function to create patch and update directory.
    
    Args:
        clone_path: Path to cloned repository
        agent_response: Agent response JSON
        output_dir: Output directory
        
    Returns:
        Tuple of (generated_patch, patch_folder)
    """
    # Generate patch from agent response
    generated_patch, applied_changes = generate_patch_from_agent(
        clone_path, agent_response, output_dir
    )
    
    if not generated_patch:
        print("Failed to generate patch", file=sys.stderr)
        return None, None
    
    # Update patch folder
    patch_folder = update_patch_folder(output_dir, generated_patch, clone_path)
    
    return generated_patch, patch_folder


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(
            "Usage: python patch_creator.py <clone_path> <agent_response.json> <output_dir>",
            file=sys.stderr
        )
        sys.exit(1)
    
    clone_path = Path(sys.argv[1])
    agent_response_file = Path(sys.argv[2])
    output_dir = Path(sys.argv[3])
    
    with open(agent_response_file, 'r') as f:
        agent_response = json.load(f)
    
    generated_patch, patch_folder = create_patch(clone_path, agent_response, output_dir)
    
    if generated_patch and patch_folder:
        successful = len([c for c in agent_response.get("changes", [])])
        print(f"{Colors.BRIGHT_GREEN}{SYMBOLS['check']} Patch generated: {Colors.DIM}{generated_patch}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}{SYMBOLS['check']} Patch folder: {Colors.DIM}{patch_folder}{Colors.RESET}")
        print(f"{Colors.BRIGHT_CYAN}{SYMBOLS['sparkle']} Changes applied: {Colors.BOLD}{successful}{Colors.RESET}")
    else:
        sys.exit(1)
