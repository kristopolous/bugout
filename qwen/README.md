# BugOut

Automated bug fix workflow that fetches GitHub issues, extracts features, generates PRDs, creates fixes, finds reviewers, and prepares patch folders.

## Overview

BugOut performs 8 automated steps:

1. **Fetch Comments** - Uses `gh` CLI to get all issue comments and saves as JSON
2. **Feature Extraction** - Uses AI (parser.py style) to extract structured features from comments
3. **PRD Generation** - Analyzes features and generates a Product Requirements Document
4. **Bug Fix Generation** - Uses AI to propose a fix based on the PRD
5. **Reviewer Check** - Uses Yutori API to find competent reviewers from issue commenters
6. **Patch Folder** - Prepares a complete patch folder with all artifacts
7. **Repo Clone & Agentic Loop** - Clones the repo and uses OpenAI to analyze and generate precise code changes
8. **Patch Creation** - Generates actual unified diff patch files and updates the directory

## Requirements

- Python 3.8+
- GitHub CLI (`gh`)
- `.env` file in project root with:
  - `FASTINO_KEY` - For AI inference
  - `YUTORI_KEY` - For reviewer competence checking
  - `OPENAI_HOST` - OpenAI API host (e.g., `api.openai.com`)
  - `OPENAI_MODEL` - OpenAI model to use (e.g., `gpt-4o`)
  - `OPENAI_API_KEY` - OpenAI API key (optional for some endpoints)

## Installation

```bash
# Install dependencies
pip install requests python-dotenv

# Ensure gh CLI is installed
gh --version

# Create .env file in project root (parent of qwen/)
cat > ../.env << EOF
FASTINO_KEY=your-key
YUTORI_KEY=your-key
OPENAI_HOST=api.openai.com
OPENAI_MODEL=gpt-4o
OPENAI_API_KEY=your-openai-key
EOF
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

**Step 7: Clone Repo & Agentic Loop**
```bash
python repo_cloner.py <repo> <prd.md> <bug_fix.json|bug_fix.patch> [output_dir]
```

**Step 8: Create Patch File**
```bash
python patch_creator.py <clone_path> <agent_response.json> <output_dir>
```

## Output Structure

```
bugout_data/
└── <repo>_<issue>/
    ├── issue_<number>_comments.json    # Raw issue data from GitHub
    ├── bugs_with_features.json         # Extracted features
    ├── prd.md                          # Product Requirements Document
    ├── prd.analysis.json               # Feature analysis JSON
    ├── bug_fix.patch                   # Initial proposed fix
    ├── bug_fix.json                    # Fix details JSON
    ├── reviewer.json                   # Reviewer analysis
    ├── agent_response.json             # Agentic loop output (Step 7)
    ├── generated.patch                 # AI-generated unified diff (Step 8)
    ├── git.patch                       # Git diff patch (Step 8)
    ├── applied_changes.json            # Applied changes log (Step 8)
    ├── temp/                           # Temp directory with repo clone
    │   └── <repo>_clone/               # Cloned repository
    ├── repo_snapshot/                  # Snapshot of modified repo
    └── patch/                          # Complete patch folder
        ├── prd.md
        ├── bug_fix.patch
        ├── reviewer.json
        ├── issue_comments.json
        ├── bugs_with_features.json
        ├── analysis.json
        ├── bug_fix.json
        ├── agent_response.json
        ├── generated.patch
        ├── git.patch
        ├── applied_changes.json
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

### agent_response.json (Step 7)
Output from the agentic loop containing:
- Root cause analysis
- Affected files list
- Fix strategy
- Detailed code changes with line numbers
- Testing recommendations
- Confidence score

### generated.patch (Step 8)
Unified diff patch file containing:
- All code changes from the agentic loop
- Proper diff format for easy review
- Can be applied with `git apply` or `patch`

### git.patch (Step 8)
Git-formatted patch from the actual repository changes:
- Generated from `git diff HEAD`
- Ready for `git am` or PR creation

### applied_changes.json (Step 8)
Log of all applied changes containing:
- List of changes with success/failure status
- Analysis summary from the agent
- Testing instructions
- Confidence score

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `FASTINO_KEY` | API key for AI inference | Yes |
| `YUTORI_KEY` | API key for Yutori reviewer check | Yes |
| `OPENAI_HOST` | OpenAI API host (e.g., `api.openai.com`) | Yes |
| `OPENAI_MODEL` | OpenAI model to use (e.g., `gpt-4o`) | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Optional |

The `.env` file should be in the parent directory (project root).

## Example Output

```
============================================================
BugOut: Processing microsoft/vscode#12345
Output directory: ./bugout_data/microsoft_vscode/12345
============================================================

[Step 1/8] Fetching issue comments...
  Saved to: bugout_data/microsoft_vscode/12345/issue_12345_comments.json

[Step 2/8] Extracting features from comments...
  Saved to: bugout_data/microsoft_vscode/12345/bugs_with_features.json

[Step 3/8] Generating PRD...
  Saved to: bugout_data/microsoft_vscode/12345/prd.md

[Step 4/8] Generating bug fix...
  Saved to: bugout_data/microsoft_vscode/12345/bug_fix.patch

[Step 5/8] Checking reviewer competence...
  Saved to: bugout_data/microsoft_vscode/12345/reviewer.json
  Best reviewer: somecontributor

[Step 6/8] Preparing initial patch folder...
  Saved to: bugout_data/microsoft_vscode/12345/patch

[Step 7/8] Running agentic loop with OpenAI...
  Cloning microsoft/vscode...
  Clone path: bugout_data/microsoft_vscode/12345/temp/microsoft_vscode_clone
  Agent response: bugout_data/microsoft_vscode/12345/agent_response.json

[Step 8/8] Generating actual patch file...
  Applying 3 changes...
  Generated patch: bugout_data/microsoft_vscode/12345/generated.patch
  Updated patch folder: bugout_data/microsoft_vscode/12345/patch

============================================================
BugOut Complete!
Patch folder: bugout_data/microsoft_vscode/12345/patch
Best reviewer: @somecontributor
============================================================
```

## License

MIT
