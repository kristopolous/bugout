# BugOut

Automated bug fix workflow that fetches GitHub issues, extracts features, generates PRDs, creates fixes, finds reviewers, and prepares patch folders.

## Overview

BugOut performs 6 automated steps:

1. **Fetch Comments** - Uses `gh` CLI to get all issue comments and saves as JSON
2. **Feature Extraction** - Uses AI (parser.py style) to extract structured features from comments
3. **PRD Generation** - Analyzes features and generates a Product Requirements Document
4. **Bug Fix Generation** - Uses AI to propose a fix based on the PRD
5. **Reviewer Check** - Uses Yutori API to find competent reviewers from issue commenters
6. **Patch Folder** - Prepares a complete patch folder with all artifacts

## Requirements

- Python 3.8+
- GitHub CLI (`gh`)
- Environment variables:
  - `FASTINO_KEY` - For AI inference
  - `YUTORI_API_KEY` - For reviewer competence checking

## Installation

```bash
# Install dependencies
pip install requests python-dotenv

# Ensure gh CLI is installed
gh --version

# Set environment variables
export FASTINO_KEY="your-key"
export YUTORI_API_KEY="your-key"
```

## Usage

### Full Workflow

Run the complete BugOut workflow:

```bash
cd qwen
python bugout.py <repo> <issue_number> [output_dir]
```

**Examples:**

```bash
# Basic usage
python bugout.py microsoft/vscode 12345

# With custom output directory
python bugout.py facebook/react 67890 ./my_output
```

### Individual Steps

You can also run each step individually:

**Step 1: Fetch Comments**
```bash
python comment_fetcher.py <repo> <issue_number> [output_dir]
```

**Step 2: Extract Features**
```bash
python feature_extractor.py <comments.json> [output_file]
```

**Step 3: Generate PRD**
```bash
python prd_generator.py <bugs_with_features.json> [output_prd.md]
```

**Step 4: Generate Bug Fix**
```bash
python bug_fixer.py <prd.md> <bugs_with_features.json> [output_dir]
```

**Step 5: Check Reviewers**
```bash
python reviewer_checker_wrapper.py <comments.json> <repo> [output_dir] [wait]
```

**Step 6: Prepare Patch Folder**
```bash
python patch_generator.py <output_dir> <prd.md> <bug_fix.patch> <reviewer.json> <comments.json> <bugs_with_features.json>
```

## Output Structure

```
bugout_data/
└── <repo>_<issue>/
    ├── issue_<number>_comments.json    # Raw issue data from GitHub
    ├── bugs_with_features.json         # Extracted features
    ├── prd.md                          # Product Requirements Document
    ├── prd.analysis.json               # Feature analysis JSON
    ├── bug_fix.patch                   # Proposed fix
    ├── bug_fix.json                    # Fix details JSON
    ├── reviewer.json                   # Reviewer analysis
    └── patch/                          # Complete patch folder
        ├── prd.md
        ├── bug_fix.patch
        ├── reviewer.json
        ├── issue_comments.json
        ├── bugs_with_features.json
        ├── analysis.json
        ├── bug_fix.json
        └── patch_manifest.json
```

## Generated Artifacts

### prd.md
Product Requirements Document containing:
- Executive summary
- Frequency analysis of bug characteristics
- Technical details from user reports
- Functional and non-functional requirements
- Success criteria

### bug_fix.patch
Proposed fix containing:
- Root cause analysis
- Fix description
- Code changes
- Testing instructions

### reviewer.json
Reviewer analysis containing:
- List of all commenters
- Competence assessment for each
- Best reviewer recommendation

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `FASTINO_KEY` | API key for AI inference | Yes |
| `YUTORI_API_KEY` | API key for Yutori reviewer check | Yes |

## Example Output

```
============================================================
BugOut: Processing microsoft/vscode#12345
Output directory: ./bugout_data/microsoft_vscode/12345
============================================================

[Step 1/6] Fetching issue comments...
  Saved to: bugout_data/microsoft_vscode/12345/issue_12345_comments.json

[Step 2/6] Extracting features from comments...
  Saved to: bugout_data/microsoft_vscode/12345/bugs_with_features.json

[Step 3/6] Generating PRD...
  Saved to: bugout_data/microsoft_vscode/12345/prd.md

[Step 4/6] Generating bug fix...
  Saved to: bugout_data/microsoft_vscode/12345/bug_fix.patch

[Step 5/6] Checking reviewer competence...
  Saved to: bugout_data/microsoft_vscode/12345/reviewer.json
  Best reviewer: somecontributor

[Step 6/6] Preparing patch folder...
  Saved to: bugout_data/microsoft_vscode/12345/patch

============================================================
BugOut Complete!
Patch folder: bugout_data/microsoft_vscode/12345/patch
Best reviewer: @somecontributor
============================================================
```

## License

MIT
