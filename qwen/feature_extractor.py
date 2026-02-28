#!/usr/bin/env python3
"""
feature_extractor.py - Step 2: Feature extraction from bug comments
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Optional
import uuid

# ANSI Colors
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_CYAN = "\033[96m"

SYMBOLS = {"check": "✅", "gear": "⚙️", "arrow": "→"}


def extract_features_from_text(text: str, api_key: str) -> Optional[Dict]:
    """
    Extract features from a single text using the FastINO API.
    
    Args:
        text: The text to analyze
        api_key: FastINO API key
        
    Returns:
        Dict with extracted features or None if failed
    """
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
                        "content": "You are an inference engine that processes text and outputs strict json with the following labels to the dict object: software version, platform, bug behaviour, crash, user frustration, technical description, input data, expected behaviour. You are not conversational."
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                "temperature": 0,
                "max_tokens": 256
            }
        )
        
        obj = response.json()
        completion = obj.get('completion', '{}')
        features = json.loads(completion)
        return features
    except Exception as e:
        print(f"Error extracting features: {e}", file=sys.stderr)
        return None


def process_comments(comments_file: Path, api_key: str, output_file: Path) -> Optional[Path]:
    """
    Process all comments from an issue and extract features.
    
    Args:
        comments_file: Path to the JSON file with issue comments
        api_key: FastINO API key
        output_file: Path to save the features JSON
        
    Returns:
        Path to the output file, or None if failed
    """
    # Load the issue data
    with open(comments_file, 'r') as f:
        issue_data = json.load(f)
    
    # Collect all text content (body + comments)
    texts_to_process = []
    
    # Add issue body
    if issue_data.get('body'):
        texts_to_process.append({
            "source": "issue_body",
            "author": issue_data.get('author', {}).get('login', 'unknown'),
            "created_at": issue_data.get('createdAt'),
            "text": issue_data['body']
        })
    
    # Add all comments
    for comment in issue_data.get('comments', []):
        if comment.get('body'):
            texts_to_process.append({
                "source": "comment",
                "author": comment.get('author', {}).get('login', 'unknown'),
                "created_at": comment.get('createdAt'),
                "text": comment['body']
            })
    
    print(f"{Colors.BRIGHT_CYAN}{SYMBOLS['gear']}{Colors.RESET} {Colors.CYAN}Processing {len(texts_to_process)} text entries...{Colors.RESET}", file=sys.stderr)

    # Extract features for each text
    bugs_with_features = []
    for i, item in enumerate(texts_to_process):
        print(f"  {Colors.DIM}{SYMBOLS['arrow']}{Colors.RESET} {Colors.DIM}Processing {i+1}/{len(texts_to_process)}...{Colors.RESET}", file=sys.stderr)
        
        features = extract_features_from_text(item['text'], api_key)
        
        if features:
            entry = {
                "uuid": str(uuid.uuid4()),
                "source": item['source'],
                "author": item['author'],
                "created_at": item['created_at'],
                "original_text": item['text'][:500],  # Truncate for storage
                **features
            }
            bugs_with_features.append(entry)
    
    # Save results
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump({
            "issue_number": issue_data.get('number'),
            "issue_title": issue_data.get('title'),
            "total_entries": len(bugs_with_features),
            "bugs_with_features": bugs_with_features
        }, f, indent=2)
    
    print(f"{Colors.BRIGHT_GREEN}{SYMBOLS['check']}{Colors.RESET} {Colors.GREEN}Step 2 complete:{Colors.RESET} Extracted features from {Colors.BRIGHT_CYAN}{len(bugs_with_features)}{Colors.RESET} entries", file=sys.stderr)
    return output_file


if __name__ == "__main__":
    from dotenv import load_dotenv
    
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
    
    if len(sys.argv) < 2:
        print("Usage: python feature_extractor.py <comments_json> [output_file]", file=sys.stderr)
        sys.exit(1)
    
    comments_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("./bugout_data/bugs_with_features.json")
    
    api_key = os.environ.get("FASTINO_KEY")
    if not api_key:
        print("Error: FASTINO_KEY not set in environment", file=sys.stderr)
        sys.exit(1)
    
    result = process_comments(comments_file, api_key, output_file)
    if result:
        print(f"Saved to: {result}")
    else:
        sys.exit(1)
