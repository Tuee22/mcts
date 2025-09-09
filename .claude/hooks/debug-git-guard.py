#!/usr/bin/env python3
"""
Debug version of git-commit-guard to understand why it didn't catch the bypass.
This will help us understand if the issue is in pattern matching or hook execution.
"""

import json
import os
import re
import sys
import datetime


def debug_log(message):
    """Log debug messages with timestamp."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    debug_file = "/Users/matthewnowak/mcts/.claude/logs/git-guard-debug.log"
    os.makedirs(os.path.dirname(debug_file), exist_ok=True)

    with open(debug_file, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

    # Also print to stderr for immediate visibility
    print(f"DEBUG: {message}", file=sys.stderr)


def read_tool_call_from_stdin():
    """Try to read tool call data from stdin."""
    try:
        debug_log("Attempting to read from stdin...")
        if not sys.stdin.isatty():
            input_data = sys.stdin.read().strip()
            debug_log(f"Stdin data length: {len(input_data) if input_data else 0}")
            if input_data:
                data = json.loads(input_data)
                debug_log(f"Parsed stdin JSON: {json.dumps(data, indent=2)}")
                return data
            else:
                debug_log("Stdin is empty")
        else:
            debug_log("Stdin is a tty - no data")
    except Exception as e:
        debug_log(f"Error reading stdin: {e}")
    return None


def read_tool_call_from_env():
    """Fall back to reading from environment variable."""
    try:
        debug_log("Attempting to read from TOOL_CALL env var...")
        tool_call_json = os.environ.get("TOOL_CALL", "{}")
        debug_log(f"TOOL_CALL env var: {tool_call_json}")
        data = json.loads(tool_call_json)
        debug_log(f"Parsed env JSON: {json.dumps(data, indent=2)}")
        return data
    except Exception as e:
        debug_log(f"Error reading env var: {e}")
        return {}


def main():
    """Debug version of git commit guard."""
    debug_log("=== GIT COMMIT GUARD DEBUG START ===")

    try:
        # Try stdin first (preferred for Claude CLI hooks)
        tool_call = read_tool_call_from_stdin()

        # Fall back to environment if stdin empty
        if not tool_call:
            debug_log("No stdin data, falling back to environment")
            tool_call = read_tool_call_from_env()

        # Extract command from tool call
        command = tool_call.get("parameters", {}).get("command", "")
        debug_log(f"Extracted command: '{command}'")

        if not command:
            debug_log("No command found in tool call")
            return 0

        # Allow bypass with environment variable
        bypass = os.environ.get("MCTS_ALLOW_COMMIT") == "1"
        debug_log(f"Bypass enabled: {bypass}")
        if bypass:
            debug_log("Bypassing due to MCTS_ALLOW_COMMIT=1")
            return 0

        # Check for git commit patterns
        git_commit_pattern = r"\bgit\s+commit\b"
        git_push_pattern = r"\bgit\s+push\b"

        debug_log(f"Testing against commit pattern: {git_commit_pattern}")
        commit_match = re.search(git_commit_pattern, command, re.IGNORECASE)
        debug_log(f"Commit pattern match: {commit_match is not None}")
        if commit_match:
            debug_log(
                f"Match found at: {commit_match.span()}, text: '{commit_match.group()}'"
            )

        debug_log(f"Testing against push pattern: {git_push_pattern}")
        push_match = re.search(git_push_pattern, command, re.IGNORECASE)
        debug_log(f"Push pattern match: {push_match is not None}")
        if push_match:
            debug_log(
                f"Match found at: {push_match.span()}, text: '{push_match.group()}'"
            )

        if commit_match:
            debug_log("BLOCKING: Git commit detected")
            print(
                "❌ Git commits are blocked by @no-git-commits policy", file=sys.stderr
            )
            print("🔧 Quality checks run automatically on Stop hook", file=sys.stderr)
            print("💡 User must explicitly request commits", file=sys.stderr)
            print("🔄 To override: export MCTS_ALLOW_COMMIT=1", file=sys.stderr)
            return 1

        if push_match:
            debug_log("BLOCKING: Git push detected")
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

        debug_log("ALLOWING: No git commit/push patterns matched")
        return 0

    except Exception as e:
        debug_log(f"Exception in git guard: {e}")
        # Don't block on errors - fail open
        print(f"Git guard error: {e}", file=sys.stderr)
        return 0

    finally:
        debug_log("=== GIT COMMIT GUARD DEBUG END ===")


if __name__ == "__main__":
    sys.exit(main())
