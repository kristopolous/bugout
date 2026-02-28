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
- `wxPython` - For GUI (optional, see GUI section)

## Installation

### CLI Installation

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

### GUI Installation (Optional)

```bash
# Install all dependencies including wxPython
pip install -r requirements.txt

# Or install wxPython separately:

# Linux (Ubuntu/Debian)
sudo apt-get install python3-wxgtk4.0

# macOS
pip install wxPython

# Windows
pip install wxPython
```

## Usage

### Full Workflow (CLI)

Run the complete BugOut workflow from command line:

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

# Show help
python bugout.py --help
```

### Graphical Interface (GUI)

Launch the BugOut graphical interface:

```bash
python bugout.py --gui
```

**GUI Features:**

| Component | Description |
|-----------|-------------|
| 📝 **Config Panel** | Input fields for repo, issue number, output directory |
| 📊 **Status Panel** | Progress bar, step counter (0/8), Run ID display |
| 📋 **Log Panel** | Color-coded live output (success/error/warning/info) |
| 🖱️ **Control Buttons** | Run, Stop, Clear Log |
| 📁 **Directory Browser** | Browse button for selecting output location |
| 🎯 **Visual Indicators** | Step-by-step progress with Unicode symbols |

**GUI Workflow:**
1. Enter repository (e.g., `microsoft/vscode`)
2. Enter issue number (e.g., `12345`)
3. Optionally select output directory
4. Click "🚀 Run BugOut"
5. Watch real-time progress in the log panel
6. View completion summary with patch folder location

**GUI Screenshots:**

```
╔══════════════════════════════════════════════════════════════╗
║     🐛 BugOut - Automated Bug Fix Workflow              ║
╠══════════════════════════════════════════════════════════════╣
║  From bug report to production-ready patch                    ║
╚══════════════════════════════════════════════════════════════╝

Repository:    [microsoft/vscode________________]
Issue Number:  [12345___________________________]
Output Dir:    [./bugout_data___________________] [Browse...]

Status: Running
Progress: [████████████████░░░░░░░░] 62%  Step: 5/8
Run ID: a3f5b2c1

Output Log:
  ✓ Step 1 complete: Fetched 15 comments for issue #12345
  ✓ Step 2 complete: Extracted features from 16 entries
  ✓ Step 3 complete: Generated PRD with 16 reports analyzed
  ✓ Step 4 complete: Generated bug fix
  ✓ Step 5 complete: Checked 8 reviewers
  → Best reviewer: @somecontributor
  ...

[🚀 Run BugOut]  [⏹ Stop]  [🗑 Clear Log]
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

Each run gets a unique 8-character UUID as its directory name for easy tracking and organization.

```
bugout_data/
└── a3f5b2c1/                 # ← Unique run ID (UUID)
    ├── run_metadata.json     # Run info: UUID, repo, issue, timestamp
    ├── issue_comments.json   # Raw issue data from GitHub
    ├── bugs_with_features.json  # Extracted features
    ├── prd.md                # Product Requirements Document
    ├── prd.analysis.json     # Feature analysis JSON
    ├── bug_fix.patch         # Initial proposed fix
    ├── bug_fix.json          # Fix details JSON
    ├── reviewer.json         # Reviewer analysis
    ├── agent_response.json   # Agentic loop output (Step 7)
    ├── generated.patch       # AI-generated unified diff (Step 8)
    ├── git.patch             # Git diff patch (Step 8)
    ├── applied_changes.json  # Applied changes log (Step 8)
    ├── temp/                 # Temp directory with repo clone
    │   └── microsoft_vscode_clone/  # Cloned repository
    ├── repo_snapshot/        # Snapshot of modified repo
    └── patch/                # Complete patch folder
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
        └── patch_manifest.json  # Includes run_id reference
```

### Run Metadata

Each run creates a `run_metadata.json` file:

```json
{
  "run_id": "a3f5b2c1",
  "repo": "microsoft/vscode",
  "issue_number": "12345",
  "timestamp": "2026-02-27T10:30:00.000000",
  "output_dir": "./bugout_data/a3f5b2c1"
}
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
     l         __                       __
  .   .       / /  __ _____ ____  __ __/ /_
   \ /       / _ \/ // / _ `/ _ \/ // / __/
 `/ ! \`    /_.__/\_,_/\_, /\___/\_,_/\__/
 | o:o |              /___/
~| o:o |~
/ \_:_/ \

╔══════════════════════════════════════════════════════════════╗
║     🐛 BugOut - Automated Bug Fix Workflow              ║
╠══════════════════════════════════════════════════════════════╣
║  From bug report to production-ready patch                    ║
╚══════════════════════════════════════════════════════════════╝

Configuration 
  Run ID:      a3f5b2c1
  Repository:  microsoft/vscode
  Issue:       #12345
  Output:      ./bugout_data/a3f5b2c1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

● [1/8] 🔗 Fetching issue comments
  ✅ Step 1 complete: Fetched 15 comments for issue #12345

● [2/8] ⚙️  Extracting features from comments
  ⚙️ Processing 16 text entries...
  ✅ Step 2 complete: Extracted features from 16 entries

● [3/8] 🎯 Generating PRD
  ✅ Step 3 complete: Generated PRD with 16 reports analyzed

● [4/8] 🐛 Generating bug fix
  ✅ Step 4 complete: Generated bug fix

● [5/8] ★ Checking reviewer competence
  ✅ Step 5 complete: Checked 8 reviewers
  ✅ Best reviewer: @somecontributor

● [6/8] 📁 Preparing initial patch folder
  ✅ Created: ./bugout_data/a3f5b2c1/patch

● [7/8] 🚀 Running agentic loop with OpenAI
  🔀 Cloning microsoft/vscode...
  ✅ Clone: ./bugout_data/a3f5b2c1/temp/microsoft_vscode_clone
  → Agent response: ./bugout_data/a3f5b2c1/agent_response.json

● [8/8] ✨ Generating actual patch file
  Applying 3 changes...
  ✅ Generated: ./bugout_data/a3f5b2c1/generated.patch
  ✅ Updated: ./bugout_data/a3f5b2c1/patch

══════════════════════════════════════════════════════════════
  🚀 BugOut Complete! 
══════════════════════════════════════════════════════════════

╔══════════════════════════════════════════════════════════════╗
║              BugOut Summary                                ║
╠══════════════════════════════════════════════════════════════╣
║  Run ID:     a3f5b2c1                                      ║
║  Repository: microsoft/vscode                              ║
║  Issue:      #12345                                        ║
║  Patch Folder: ./bugout_data/a3f5b2c1/patch                ║
║  Best Reviewer: @somecontributor                           ║
╠══════════════════════════════════════════════════════════════╣
║  Generated Artifacts:                                      ║
║    • prd.md                  (Product Requirements Doc)    ║
║    • bug_fix.patch           (Initial Proposed Fix)        ║
║    • generated.patch         (AI-Generated Patch)          ║
║    • git.patch               (Git Diff Patch)              ║
║    • reviewer.json           (Reviewer Analysis)           ║
║    • agent_response.json     (Agentic Loop Output)         ║
║    • applied_changes.json    (Applied Changes Log)         ║
╠══════════════════════════════════════════════════════════════╣
║  Next Steps:                                               ║
║    1. Review PRD:        cat ./bugout_data/a3f5b2c1/prd.md ║
║    2. Review patch:      cat ./bugout_data/a3f5b2c1/patch/ ║
║                          generated.patch                   ║
║    3. Contact reviewer:  @somecontributor                  ║
║    4. Create PR with the generated patch                   ║
╚══════════════════════════════════════════════════════════════╝
```

## Project Structure

```
qwen/
├── bugout.py                 # Main CLI orchestrator (8 steps)
├── bugout_gui.py             # wxPython graphical interface
├── comment_fetcher.py        # Step 1: Fetch issue comments
├── feature_extractor.py      # Step 2: AI feature extraction
├── prd_generator.py          # Step 3: Generate PRD
├── bug_fixer.py              # Step 4: Initial bug fix
├── reviewer_checker_wrapper.py # Step 5: Yutori reviewer check
├── patch_generator.py        # Step 6: Initial patch folder
├── repo_cloner.py            # Step 7: Clone repo + agentic loop
├── patch_creator.py          # Step 8: Generate unified diff
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## License

MIT
