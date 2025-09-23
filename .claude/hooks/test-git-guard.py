#!/usr/bin/env python
"""
Test script for git-commit-guard to understand bypass scenarios
"""

import json
import re
import sys
from typing import List, Tuple


def test_command_against_current_guard(command: str) -> Tuple[bool, str]:
    """Test a command against the current git-commit-guard logic."""
    # Current patterns from the guard
    git_commit_pattern = r"\bgit\s+commit\b"
    git_push_pattern = r"\bgit\s+push\b"

    if re.search(git_commit_pattern, command, re.IGNORECASE):
        return True, "BLOCKED by git commit pattern"

    if re.search(git_push_pattern, command, re.IGNORECASE):
        return True, "BLOCKED by git push pattern"

    return False, "ALLOWED - no patterns matched"


def main():
    """Test various git commands against current guard logic."""

    # The original bypassing command
    original_bypassing_command = '''git commit -m "$(cat <<'EOF'
Fix cross-architecture .so file handling and container crashes

- Add 'file' package to Dockerfile for architecture detection
- Enhance entrypoint.sh with validation of .so file architectures  
- Remove contaminated architecture-specific files with wrong architectures
- Fix symlink creation to work from correct directory with -L flag
- Prevent silent failures when 'file' command unavailable

Fixes import errors when switching between ARM64 and x86_64 platforms.
Tests now pass on both macOS ARM64 and Ubuntu x86_64 environments.

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"'''

    # Test commands that should be blocked
    commands_should_be_blocked = [
        'git commit -m "simple message"',
        'git commit --message="message"',
        'git commit -am "all files"',
        "git push origin main",
        "git push --force",
        original_bypassing_command,
        'git commit -m "$(echo test)"',
        "git commit -m `echo test`",
    ]

    # Test commands that should be allowed
    commands_should_be_allowed = [
        "git status",
        "git add file.txt",
        "git diff",
        "git log --oneline",
        "git show commit-hash",
        'echo "git commit test"',
        'grep "commit" file.txt',
        "docker compose up",
        "poetry run pytest",
    ]

    print("🔍 TESTING CURRENT GIT-COMMIT-GUARD LOGIC")
    print("=" * 60)

    print("\n📌 COMMANDS THAT SHOULD BE BLOCKED:")
    print("-" * 40)
    for cmd in commands_should_be_blocked:
        blocked, reason = test_command_against_current_guard(cmd)
        status = "✅ BLOCKED" if blocked else "❌ BYPASSED"
        # Truncate long commands for display
        display_cmd = cmd[:50] + "..." if len(cmd) > 50 else cmd
        print(f"{status} | {display_cmd}")
        if not blocked and "$(cat <<'EOF'" in cmd:
            print(f"   ⚠️  BYPASS DETECTED: {reason}")

    print("\n📌 COMMANDS THAT SHOULD BE ALLOWED:")
    print("-" * 40)
    for cmd in commands_should_be_allowed:
        blocked, reason = test_command_against_current_guard(cmd)
        status = "❌ BLOCKED" if blocked else "✅ ALLOWED"
        print(f"{status} | {cmd}")
        if blocked:
            print(f"   ⚠️  FALSE POSITIVE: {reason}")

    print(f"\n🎯 ORIGINAL BYPASSING COMMAND ANALYSIS:")
    print("-" * 40)
    blocked, reason = test_command_against_current_guard(original_bypassing_command)
    print(f"Command: git commit -m \"$(cat <<'EOF'...")
    print(f"Status: {'BLOCKED' if blocked else 'BYPASSED'}")
    print(f"Reason: {reason}")

    if not blocked:
        print("\n🔧 WHY IT BYPASSED:")
        print(f"- Pattern: r'\\bgit\\s+commit\\b'")
        print(f"- Command starts with: 'git commit -m \"$(cat'")
        print(
            f"- Word boundary \\b expects simple 'git commit' but gets complex syntax"
        )
        print(f"- The $(cat <<'EOF' syntax confuses the simple regex")


if __name__ == "__main__":
    main()
