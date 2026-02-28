#!/usr/bin/env python3
"""
patch_generator.py - Step 6: Prepare patch folder with all artifacts
Creates a complete patch folder with reviewer.json, patch, PRD, and all relevant work.
"""

import json
import shutil
import sys
from pathlib import Path
from typing import Optional, Dict


def prepare_patch_folder(
    output_dir: Path,
    prd_file: Path,
    patch_file: Path,
    reviewer_file: Path,
    comments_file: Path,
    features_file: Path,
    analysis_file: Optional[Path] = None,
    bug_fix_json: Optional[Path] = None,
    run_id: Optional[str] = None
) -> Path:
    """
    Prepare a complete patch folder with all artifacts.
    
    Args:
        output_dir: Base output directory
        prd_file: Path to prd.md
        patch_file: Path to bug_fix.patch
        reviewer_file: Path to reviewer.json
        comments_file: Path to issue comments JSON
        features_file: Path to bugs_with_features.json
        analysis_file: Optional path to analysis JSON
        bug_fix_json: Optional path to bug_fix.json
        
    Returns:
        Path to the patch folder
    """
    patch_folder = output_dir / "patch"
    patch_folder.mkdir(parents=True, exist_ok=True)
    
    # Copy all artifacts to patch folder
    artifacts = [
        (prd_file, "prd.md"),
        (patch_file, "bug_fix.patch"),
        (reviewer_file, "reviewer.json"),
        (comments_file, "issue_comments.json"),
        (features_file, "bugs_with_features.json"),
    ]
    
    if analysis_file and analysis_file.exists():
        artifacts.append((analysis_file, "analysis.json"))
    
    if bug_fix_json and bug_fix_json.exists():
        artifacts.append((bug_fix_json, "bug_fix.json"))
    
    for src, dest_name in artifacts:
        if src and src.exists():
            dest = patch_folder / dest_name
            shutil.copy2(src, dest)
    
    # Create patch_manifest.json
    manifest = {
        "patch_folder": str(patch_folder),
        "run_id": run_id,
        "artifacts": [dest_name for _, dest_name in artifacts],
        "status": "ready_for_review"
    }
    
    with open(patch_folder / "patch_manifest.json", 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"Step 6 complete: Prepared patch folder at {patch_folder}", file=sys.stderr)
    return patch_folder


def create_pr_description(
    prd_file: Path,
    patch_file: Path,
    reviewer_file: Path,
    issue_number: str
) -> str:
    """
    Create a PR description from the artifacts.
    """
    with open(prd_file, 'r') as f:
        prd = f.read()
    
    with open(reviewer_file, 'r') as f:
        reviewers = json.load(f)
    
    best_reviewer = reviewers.get("best_reviewer", "TBD")
    
    pr_description = f"""# Fix for Issue #{issue_number}

## Summary
This PR addresses the bug described in issue #{issue_number}.

## Proposed Reviewer
@{best_reviewer}

## Changes
See attached patch for detailed changes.

## PRD Reference
A full Product Requirements Document has been generated based on analysis of all issue comments.

---

{prd}
"""
    
    return pr_description


if __name__ == "__main__":
    if len(sys.argv) < 6:
        print(
            "Usage: python patch_generator.py <output_dir> <prd.md> <bug_fix.patch> "
            "<reviewer.json> <comments.json> <bugs_with_features.json>",
            file=sys.stderr
        )
        sys.exit(1)
    
    output_dir = Path(sys.argv[1])
    prd_file = Path(sys.argv[2])
    patch_file = Path(sys.argv[3])
    reviewer_file = Path(sys.argv[4])
    comments_file = Path(sys.argv[5])
    features_file = Path(sys.argv[6])
    
    analysis_file = output_dir / "prd.analysis.json"
    bug_fix_json = output_dir / "bug_fix.json"
    
    result = prepare_patch_folder(
        output_dir,
        prd_file,
        patch_file,
        reviewer_file,
        comments_file,
        features_file,
        analysis_file,
        bug_fix_json
    )
    
    print(f"Patch folder ready at: {result}")
