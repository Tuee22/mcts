#!/usr/bin/env python3
"""
Git Commit Guard Script

Blocks git commit and git push commands until quality checks pass
and user provides explicit confirmation.
"""

import json
import os
import re
import sys


def main():
    """Check if command is a git commit/push and block if so."""
    try:
        # Get the command from environment variable
        tool_call_json = os.environ.get('TOOL_CALL', '{}')
        tool_call = json.loads(tool_call_json)
        
        command = tool_call.get('parameters', {}).get('command', '')
        
        # Check for git commit patterns
        git_commit_pattern = r'\bgit\s+commit\b'
        git_push_pattern = r'\bgit\s+push\b'
        
        if re.search(git_commit_pattern, command, re.IGNORECASE):
            print("❌ Git commits are blocked until quality checks pass and user confirms.")
            print("🔧 Run quality checks first: format → type check → build → tests")
            print("💡 Then ask user for explicit commit confirmation.")
            print("🔄 Use quality-gate.py to run all checks")
            return 1
        
        if re.search(git_push_pattern, command, re.IGNORECASE):
            print("⚠️  Git push blocked - commits must be made manually after quality verification.")
            print("💡 Run quality checks and get user confirmation first")
            return 1
            
        return 0
        
    except Exception as e:
        print(f"Git guard error: {e}", file=sys.stderr)
        return 0  # Don't block on errors


if __name__ == "__main__":
    sys.exit(main())