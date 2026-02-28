# Reviewer Checker

A CLI tool that uses the Yutori Research API to check if a GitHub user has the expertise to review a pull request.

## What it does

Given a GitHub username and a PR summary, the tool researches the user's background to determine if they have relevant experience to review the proposed changes. It returns a structured assessment with:

- **Can Review**: Yes/No decision
- **Confidence Score**: Percentage indicating certainty
- **Reasoning**: Explanation of why they can or cannot review
- **Relevant Experience**: List of their relevant expertise and background
- **Recommendations**: Suggested next steps or alternative reviewers

## How it works

1. **Creates a Yutori Research Task**: Sends the GitHub user and PR information to Yutori's research API
2. **Polls for completion**: Waits for the research task to complete (default timeout: 120 seconds)
3. **Returns structured output**: Displays a formatted assessment with exit codes (0 = can review, 1 = cannot review)

## Installation

```bash
# Clone and install dependencies
pip install -r requirements.txt

# Set up your Yutori API key
echo "YUTORI_KEY=your_api_key_here" > .env
```

## Usage

```bash
python reviewer_check.py <github_username> "<pr_summary>"
```

### Examples

```bash
# Check if a user can review a React PR
python reviewer_check.js facebook "Fix memory leak in React hooks"

# Check with custom timeout
python reviewer_check.py torvalds "Update Linux kernel scheduler" --timeout 180
```

### Output

```
Researching facebook... (task: abc-123-def)

============================================================
REVIEWER CAPABILITY ASSESSMENT
============================================================

GitHub User: facebook
PR Summary: Fix memory leak in React hooks...

✓ Can Review: YES
✓ Confidence: 87%

Reasoning:
Facebook has extensive experience with React as the creators and
maintainers of the framework. They have deep expertise in hooks,
component lifecycle, and memory management within React applications.

Relevant Experience:
  • Creator and maintainer of React
  • Deep expertise in JavaScript and React internals
  • Experience with performance optimization and memory management

Recommendations:
  • User is highly qualified to review this PR
  • Consider them as a primary reviewer

============================================================
```

## Exit Codes

- `0` - User is capable of reviewing the PR
- `1` - User cannot review the PR or an error occurred

## Environment Variables

- `YUTORI_KEY` - Your Yutori API key (required, starts with `yt-`)

## API

Uses the Yutori Research API (`/v1/research/tasks`) with structured output schema for consistent results.

## Requirements

- Python 3.7+
- `requests` library
- `python-dotenv` library
- Yutori API key (free credits available at platform.yutori.com)
# bugout
