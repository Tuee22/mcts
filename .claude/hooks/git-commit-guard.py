#!/usr/bin/env python3
"""
Enhanced Git Commit Guard Script

Blocks git commit and git push commands until quality checks pass
and user provides explicit confirmation.

Features:
- Comprehensive pattern matching for various git commit syntaxes
- Debug logging to track hook execution
- Better error handling and reporting
- Supports complex command patterns like heredocs and command substitution

Reads tool call data from stdin as primary source (Claude CLI provides
this on stdin for PreToolUse hooks), falls back to environment variable.
"""

import json
import os
import re
import sys
import datetime
from typing import List, Tuple, Optional


def debug_log(message: str) -> None:
    """Log debug messages with timestamp if debug mode enabled."""
    if os.environ.get("MCTS_GIT_GUARD_DEBUG") == "1":
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        debug_file = "/Users/matthewnowak/mcts/.claude/logs/git-guard-debug.log"
        os.makedirs(os.path.dirname(debug_file), exist_ok=True)
        
        with open(debug_file, "a") as f:
            f.write(f"[{timestamp}] {message}\n")


def read_tool_call_from_stdin() -> Optional[dict]:
    """Try to read tool call data from stdin."""
    try:
        debug_log("Attempting to read from stdin...")
        if not sys.stdin.isatty():
            input_data = sys.stdin.read().strip()
            debug_log(f"Stdin data length: {len(input_data) if input_data else 0}")
            if input_data:
                data = json.loads(input_data)
                debug_log(f"Successfully parsed stdin JSON")
                return data
            else:
                debug_log("Stdin is empty")
        else:
            debug_log("Stdin is a tty - no data available")
    except Exception as e:
        debug_log(f"Error reading stdin: {e}")
    return None


def read_tool_call_from_env() -> dict:
    """Fall back to reading from environment variable."""
    try:
        debug_log("Attempting to read from TOOL_CALL env var...")
        tool_call_json = os.environ.get("TOOL_CALL", "{}")
        debug_log(f"TOOL_CALL env var exists: {bool(tool_call_json)}")
        data = json.loads(tool_call_json)
        debug_log(f"Successfully parsed environment JSON")
        return data
    except Exception as e:
        debug_log(f"Error reading env var: {e}")
        return {}


def get_git_patterns() -> Tuple[List[str], List[str]]:
    """Get comprehensive patterns for git commit and push detection."""
    
    # Enhanced git commit patterns to catch various syntaxes
    git_commit_patterns = [
        # Basic patterns - only match when commit is the actual subcommand
        r"^git\s+commit\b",                     # git commit (at start of command)
        r"\bgit\s+commit\s+",                   # git commit with args
        
        # Message flag variations  
        r"git\s+commit\s+.*-m",                 # git commit -m
        r"git\s+commit\s+.*--message",          # git commit --message
        r"git\s+commit\s+.*-am",                # git commit -am
        
        # Complex command patterns that can bypass simple regex
        r"git\s+commit\s+.*\$\(",               # Command substitution: git commit -m "$(..."
        r"git\s+commit\s+.*<<",                 # Heredoc: git commit -m "$(cat <<"
        r"git\s+commit\s+.*cat\s+<<",           # Specific heredoc with cat
        r"git\s+commit\s+.*`",                  # Backtick command substitution
        r"git\s+commit\s+.*printf",             # Printf command substitution
        r"git\s+commit\s+.*echo",               # Echo command substitution
        
        # Multi-line and complex quoting
        r"git\s+commit\s+.*\$'",                # $'...' quoting
        r"git\s+commit\s+.*\\n",                # Newline escapes in messages
        
        # Different git commit forms
        r"git-commit\b",                        # git-commit (hyphenated form)
        
        # Command chains with git commit (but not in quoted strings)
        r"[;&|]\s*git\s+commit\b",              # git commit after command separator
        r"&&\s*git\s+commit\b",                 # git commit after &&
        
        # Catch git commit but avoid false positives with git show commit-hash
        # This pattern is more restrictive - only matches when commit is followed by typical commit flags
        r"git\s+commit\s+(-[a-zA-Z]|--[a-zA-Z])", # git commit followed by flags
    ]
    
    # Enhanced git push patterns
    git_push_patterns = [
        r"\bgit\s+push\b",                      # Basic git push
        r"\bgit\s+push\s+",                     # git push with args
        r"git\s+push\s+.*origin",               # git push origin
        r"git\s+push\s+.*--force",              # git push --force
        r"git\s+push\s+.*-f\b",                 # git push -f
        r"git\s+push\s+.*-u\b",                 # git push -u
        r"git-push\b",                          # git-push (hyphenated form)
    ]
    
    return git_commit_patterns, git_push_patterns


def is_command_in_quotes(command: str, match_start: int) -> bool:
    """
    Check if a git command match is inside quoted strings.
    This helps avoid false positives for echo "git commit" etc.
    """
    try:
        # Get the text before the match to count quotes
        before_match = command[:match_start]
        
        # Count unescaped quotes of different types
        double_quotes = before_match.count('"') - before_match.count('\\"')
        single_quotes = before_match.count("'") - before_match.count("\\'")
        
        # If odd number of quotes, we're inside a quoted string
        inside_double_quotes = (double_quotes % 2) == 1
        inside_single_quotes = (single_quotes % 2) == 1
        
        return inside_double_quotes or inside_single_quotes
    except:
        # If we can't determine, err on the side of caution (don't block)
        return True


def check_git_patterns(command: str) -> Tuple[bool, str, str]:
    """
    Check if command matches any git commit or push patterns.
    
    Returns:
        (is_blocked, block_reason, matched_pattern)
    """
    if not command:
        debug_log("No command to check")
        return False, "", ""
    
    debug_log(f"Checking command: '{command[:100]}{'...' if len(command) > 100 else ''}'")
    
    commit_patterns, push_patterns = get_git_patterns()
    
    # Check git commit patterns
    for pattern in commit_patterns:
        try:
            match = re.search(pattern, command, re.IGNORECASE | re.MULTILINE)
            if match:
                # Check if the match is inside quoted strings (false positive)
                if is_command_in_quotes(command, match.start()):
                    debug_log(f"Pattern '{pattern}' matched but inside quotes - ignoring")
                    continue
                
                debug_log(f"MATCH: Commit pattern '{pattern}' matched")
                return True, "git commit", pattern
        except Exception as e:
            debug_log(f"Error checking pattern '{pattern}': {e}")
    
    # Check git push patterns  
    for pattern in push_patterns:
        try:
            match = re.search(pattern, command, re.IGNORECASE | re.MULTILINE)
            if match:
                # Check if the match is inside quoted strings (false positive)
                if is_command_in_quotes(command, match.start()):
                    debug_log(f"Pattern '{pattern}' matched but inside quotes - ignoring")
                    continue
                    
                debug_log(f"MATCH: Push pattern '{pattern}' matched")
                return True, "git push", pattern
        except Exception as e:
            debug_log(f"Error checking pattern '{pattern}': {e}")
    
    debug_log("No git patterns matched")
    return False, "", ""


def main() -> int:
    """Check if command is a git commit/push and block if so."""
    debug_log("=== ENHANCED GIT COMMIT GUARD START ===")
    
    try:
        # Try stdin first (preferred for Claude CLI hooks)
        tool_call = read_tool_call_from_stdin()

        # Fall back to environment if stdin empty
        if not tool_call:
            debug_log("No stdin data, falling back to environment")
            tool_call = read_tool_call_from_env()

        # Extract command from tool call
        command = tool_call.get("parameters", {}).get("command", "")
        debug_log(f"Extracted command length: {len(command)}")
        
        if not command:
            debug_log("No command found in tool call - allowing")
            return 0

        # Allow bypass with environment variable
        bypass = os.environ.get("MCTS_ALLOW_COMMIT") == "1"
        debug_log(f"Bypass mode enabled: {bypass}")
        if bypass:
            debug_log("Bypassing due to MCTS_ALLOW_COMMIT=1")
            return 0

        # Check for git commit/push patterns
        is_blocked, block_reason, matched_pattern = check_git_patterns(command)
        
        if is_blocked:
            debug_log(f"BLOCKING: {block_reason} detected (pattern: {matched_pattern})")
            
            if "commit" in block_reason:
                print("❌ Git commits are blocked by @no-git-commits policy", file=sys.stderr)
                print("🔧 Quality checks run automatically on Stop hook", file=sys.stderr)
                print("💡 User must explicitly request commits", file=sys.stderr)
                print("🔄 To override: export MCTS_ALLOW_COMMIT=1", file=sys.stderr)
                print(f"🔍 Matched pattern: {matched_pattern}", file=sys.stderr)
            else:
                print("⚠️  Git push blocked - commits must be made with user confirmation", file=sys.stderr)
                print("💡 Ensure quality checks pass and get user approval first", file=sys.stderr)
                print("🔄 To override: export MCTS_ALLOW_COMMIT=1", file=sys.stderr)
                print(f"🔍 Matched pattern: {matched_pattern}", file=sys.stderr)
            
            return 1

        debug_log("ALLOWING: No blocking patterns matched")
        return 0

    except Exception as e:
        debug_log(f"Exception in git guard: {e}")
        # Don't block on errors - fail open but log the error
        print(f"⚠️  Git guard error (failing open): {e}", file=sys.stderr)
        return 0

    finally:
        debug_log("=== ENHANCED GIT COMMIT GUARD END ===")


if __name__ == "__main__":
    sys.exit(main())
