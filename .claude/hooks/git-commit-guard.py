#!/usr/bin/env python3
"""
Git Commit Guard Script

Blocks git commit and git push commands until quality checks pass
and user provides explicit confirmation.

Reads tool call data from stdin as primary source (Claude CLI provides
this on stdin for PreToolUse hooks), falls back to environment variable.
"""

import json
import os
import re
import sys


def read_tool_call_from_stdin():
    """Try to read tool call data from stdin."""
    try:
        # Check if stdin has data
        if not sys.stdin.isatty():
            input_data = sys.stdin.read().strip()
            if input_data:
                return json.loads(input_data)
    except:
        pass
    return None


def read_tool_call_from_env():
    """Fall back to reading from environment variable."""
    try:
        tool_call_json = os.environ.get("TOOL_CALL", "{}")
        return json.loads(tool_call_json)
    except:
        return {}


def main():
    """Check if command is a git commit/push and block if so."""
    try:
        # Try stdin first (preferred for Claude CLI hooks)
        tool_call = read_tool_call_from_stdin()

        # Fall back to environment if stdin empty
        if not tool_call:
            tool_call = read_tool_call_from_env()

        # Extract command from tool call
        command = tool_call.get("parameters", {}).get("command", "")

        # Allow bypass with environment variable
        if os.environ.get("MCTS_ALLOW_COMMIT") == "1":
            return 0

        # Check for git commit patterns
        git_commit_pattern = r"\bgit\s+commit\b"
        git_push_pattern = r"\bgit\s+push\b"

        if re.search(git_commit_pattern, command, re.IGNORECASE):
            print(
                "❌ Git commits are blocked by @no-git-commits policy", file=sys.stderr
            )
            print("🔧 Quality checks run automatically on Stop hook", file=sys.stderr)
            print("💡 User must explicitly request commits", file=sys.stderr)
            print("🔄 To override: export MCTS_ALLOW_COMMIT=1", file=sys.stderr)
            return 1

        if re.search(git_push_pattern, command, re.IGNORECASE):
            print(
                "⚠️  Git push blocked - commits must be made with user confirmation",
                file=sys.stderr,
            )
            print(
                "💡 Ensure quality checks pass and get user approval first",
                file=sys.stderr,
            )
            print("🔄 To override: export MCTS_ALLOW_COMMIT=1", file=sys.stderr)
            return 1

        return 0

    except Exception as e:
        # Don't block on errors - fail open
        print(f"Git guard error: {e}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
