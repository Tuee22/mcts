#!/usr/bin/env python3
"""
Comprehensive test suite for the enhanced git-commit-guard.

Tests various git command patterns to ensure the enhanced guard
catches bypasses while allowing legitimate commands.
"""

import json
import os
import subprocess
import sys
import tempfile
from typing import List, Tuple, Dict


def run_git_guard_test(command: str, expect_blocked: bool = True) -> Tuple[bool, str, int]:
    """
    Test a command against the git-commit-guard.
    
    Args:
        command: Command to test
        expect_blocked: Whether we expect this command to be blocked
        
    Returns:
        (test_passed, output, return_code)
    """
    # Path to the enhanced git guard
    guard_script = "/Users/matthewnowak/mcts/.claude/hooks/git-commit-guard.py"
    
    # Create tool call JSON that mimics what Claude Code provides
    tool_call = {
        "parameters": {
            "command": command,
            "description": "Test command"
        }
    }
    
    try:
        # Run the guard with the tool call as stdin
        result = subprocess.run(
            [sys.executable, guard_script],
            input=json.dumps(tool_call),
            text=True,
            capture_output=True,
            timeout=10
        )
        
        # Check if test passed based on expectations
        if expect_blocked:
            # Command should be blocked (return code 1)
            test_passed = result.returncode == 1
        else:
            # Command should be allowed (return code 0)
            test_passed = result.returncode == 0
            
        return test_passed, result.stderr, result.returncode
        
    except Exception as e:
        return False, f"Test execution error: {e}", -1


def run_test_suite():
    """Run comprehensive test suite for git-commit-guard."""
    
    # Test cases that SHOULD BE BLOCKED
    commands_should_be_blocked = [
        # Basic git commits
        ('git commit -m "simple message"', "Basic git commit"),
        ('git commit --message="message"', "Git commit with --message"),
        ('git commit -am "all files"', "Git commit with -am"),
        
        # The original bypassing command
        ('''git commit -m "$(cat <<'EOF'
Fix cross-architecture .so file handling and container crashes

- Add 'file' package to Dockerfile for architecture detection
- Enhance entrypoint.sh with validation of .so file architectures  
- Remove contaminated architecture-specific files with wrong architectures
- Fix symlink creation to work from correct directory with -L flag
- Prevent silent failures when 'file' command unavailable

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"''', "Original bypassing heredoc command"),
        
        # Command substitution variations
        ('git commit -m "$(echo test)"', "Command substitution with echo"),
        ('git commit -m `echo test`', "Backtick command substitution"),
        ('git commit -m "$(printf "line1\\nline2")"', "Command substitution with printf"),
        
        # Heredoc variations
        ('git commit -m "$(cat <<EOF\ntest message\nEOF\n)"', "Heredoc without quotes"),
        ('git commit -m "$(cat <<\'EOF\'\ntest message\nEOF\n)"', "Heredoc with single quotes"),
        
        # Complex quoting
        ('git commit -m $\'multiline\\nmessage\'', "Complex quoting with $'...'"),
        ('git commit -m "message with \\"quotes\\""', "Escaped quotes in message"),
        
        # Various git commit forms
        ('git commit --all -m "message"', "Git commit --all"),
        ('git commit --amend -m "message"', "Git commit --amend"),
        ('git-commit -m "message"', "Hyphenated git-commit"),
        
        # Git push commands
        ('git push origin main', "Basic git push"),
        ('git push --force origin main', "Force push"),
        ('git push -f origin main', "Force push short flag"),
        ('git push -u origin feature-branch', "Push with upstream"),
        ('git-push origin main', "Hyphenated git-push"),
        
        # Tricky cases with extra text
        ('echo "setup" && git commit -m "message" && echo "done"', "Git commit in command chain"),
        ('git status && git commit -m "message"', "Git commit after status"),
    ]
    
    # Test cases that SHOULD BE ALLOWED
    commands_should_be_allowed = [
        # Safe git commands
        ('git status', "Git status command"),
        ('git add file.txt', "Git add command"),
        ('git diff', "Git diff command"),
        ('git log --oneline', "Git log command"),
        ('git show commit-hash', "Git show command"),
        ('git branch', "Git branch command"),
        ('git checkout main', "Git checkout command"),
        ('git reset HEAD~1', "Git reset command"),
        
        # Non-git commands that might contain "git commit" text
        ('echo "git commit test"', "Echo containing git commit text"),
        ('grep "commit" file.txt', "Grep for commit text"),
        ('cat commit-message.txt', "Cat command on commit file"),
        ('vim commit-template.txt', "Edit commit template"),
        
        # Build and development commands
        ('docker compose up', "Docker compose command"),
        ('poetry run pytest', "Poetry test command"),
        ('black .', "Code formatting"),
        ('mypy --strict .', "Type checking"),
        ('npm run build', "NPM build command"),
        ('python script.py', "Python script execution"),
        
        # Commands with commit-like words but not git
        ('svn commit -m "message"', "SVN commit (not git)"),
        ('hg commit -m "message"', "Mercurial commit (not git)"),
        ('commitizen commit', "Commitizen tool"),
    ]
    
    print("🧪 COMPREHENSIVE GIT-COMMIT-GUARD TEST SUITE")
    print("=" * 80)
    
    # Test blocked commands
    print(f"\n📌 TESTING COMMANDS THAT SHOULD BE BLOCKED ({len(commands_should_be_blocked)} tests)")
    print("-" * 50)
    
    blocked_passed = 0
    blocked_total = len(commands_should_be_blocked)
    
    for command, description in commands_should_be_blocked:
        test_passed, output, return_code = run_git_guard_test(command, expect_blocked=True)
        status = "✅ PASS" if test_passed else "❌ FAIL"
        
        # Truncate long commands for display
        display_cmd = command[:60] + "..." if len(command) > 60 else command
        print(f"{status} | {description}")
        print(f"      Command: {display_cmd}")
        print(f"      Return code: {return_code}")
        
        if not test_passed:
            print(f"      ⚠️  EXPECTED: Blocked (code 1), GOT: code {return_code}")
            if output:
                print(f"      Output: {output[:100]}...")
        
        if test_passed:
            blocked_passed += 1
        
        print()
    
    # Test allowed commands  
    print(f"\n📌 TESTING COMMANDS THAT SHOULD BE ALLOWED ({len(commands_should_be_allowed)} tests)")
    print("-" * 50)
    
    allowed_passed = 0
    allowed_total = len(commands_should_be_allowed)
    
    for command, description in commands_should_be_allowed:
        test_passed, output, return_code = run_git_guard_test(command, expect_blocked=False)
        status = "✅ PASS" if test_passed else "❌ FAIL"
        
        print(f"{status} | {description}")
        print(f"      Command: {command}")
        print(f"      Return code: {return_code}")
        
        if not test_passed:
            print(f"      ⚠️  EXPECTED: Allowed (code 0), GOT: code {return_code}")
            if output:
                print(f"      Output: {output}")
        
        if test_passed:
            allowed_passed += 1
        
        print()
    
    # Summary
    total_passed = blocked_passed + allowed_passed
    total_tests = blocked_total + allowed_total
    
    print("=" * 80)
    print("📊 TEST RESULTS SUMMARY")
    print("-" * 30)
    print(f"Commands that should be blocked: {blocked_passed}/{blocked_total} passed")
    print(f"Commands that should be allowed: {allowed_passed}/{allowed_total} passed")
    print(f"Overall test success rate: {total_passed}/{total_tests} ({100*total_passed/total_tests:.1f}%)")
    
    if total_passed == total_tests:
        print("🎉 ALL TESTS PASSED! Git guard is working correctly.")
    else:
        print(f"⚠️  {total_tests - total_passed} tests failed. Review the failures above.")
        
    # Test the original bypassing command specifically
    print("\n" + "=" * 80)
    print("🎯 SPECIFIC TEST: Original Bypassing Command")
    print("-" * 50)
    
    original_command = '''git commit -m "$(cat <<'EOF'
Fix cross-architecture .so file handling and container crashes
EOF
)"'''
    
    test_passed, output, return_code = run_git_guard_test(original_command, expect_blocked=True)
    
    print(f"Original bypassing command test: {'✅ BLOCKED' if test_passed else '❌ BYPASSED'}")
    print(f"Return code: {return_code}")
    if output:
        print(f"Guard output: {output}")
        
    return total_passed == total_tests


if __name__ == "__main__":
    success = run_test_suite()
    sys.exit(0 if success else 1)