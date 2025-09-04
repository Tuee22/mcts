#!/usr/bin/env python3
"""
Test Guard Hook for Claude Code

Optional PreToolUse hook that warns when modifying existing tests within the same session.
Allows new test creation and initial red/green cycles but warns about "test hacking".

This is a non-blocking warning by default. Can be made blocking via settings.local.json.

Usage:
- Add to PreToolUse hooks in settings.json for Edit|Write operations
- Configure behavior in .claude/settings.local.json
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Set


def log(message: str) -> None:
    """Log message to stderr."""
    print(f"[test-guard] {message}", file=sys.stderr)


def read_hook_input() -> Dict:
    """Read hook input from stdin."""
    try:
        if not sys.stdin.isatty():
            input_data = sys.stdin.read().strip()
            if input_data:
                return json.loads(input_data)
    except Exception:
        pass
    return {}


def get_session_cache_file() -> Path:
    """Get session cache file path."""
    return Path(tempfile.gettempdir()) / "claude_test_guard_session.json"


def load_session_state() -> Dict:
    """Load session state from cache."""
    cache_file = get_session_cache_file()
    if not cache_file.exists():
        return {"passing_tests": set(), "session_start": time.time()}

    try:
        with open(cache_file, "r") as f:
            data = json.load(f)
            data["passing_tests"] = set(data.get("passing_tests", []))
            return data
    except Exception:
        return {"passing_tests": set(), "session_start": time.time()}


def save_session_state(state: Dict) -> None:
    """Save session state to cache."""
    cache_file = get_session_cache_file()
    try:
        data = state.copy()
        data["passing_tests"] = list(data.get("passing_tests", set()))
        with open(cache_file, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def get_test_files() -> Set[str]:
    """Get list of test files in the repository."""
    try:
        result = subprocess.run(
            [
                "find",
                ".",
                "-name",
                "test_*.py",
                "-o",
                "-name",
                "*_test.py",
                "-o",
                "-path",
                "*/tests/*.py",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return set(
                line.strip() for line in result.stdout.split("\n") if line.strip()
            )
    except Exception:
        pass
    return set()


def is_test_modification(tool_name: str, file_path: str) -> bool:
    """Check if this is a modification to an existing test file."""
    if tool_name not in ["Edit", "Write"]:
        return False

    if not file_path:
        return False

    # Check if it's a test file
    path = Path(file_path)
    if not (
        path.name.startswith("test_")
        or path.name.endswith("_test.py")
        or "tests" in str(path)
    ):
        return False

    # For Write operations, check if file already exists
    if tool_name == "Write":
        return path.exists()

    # For Edit operations, it's always a modification
    return True


def check_local_config() -> Dict:
    """Check for local configuration overrides."""
    project_root = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    local_config = project_root / ".claude" / "settings.local.json"

    if not local_config.exists():
        return {"test_guard": {"mode": "warn"}}  # Default to warn only

    try:
        with open(local_config, "r") as f:
            config = json.load(f)
            return config.get("test_guard", {"mode": "warn"})
    except Exception:
        return {"test_guard": {"mode": "warn"}}


def main() -> int:
    """Main test guard logic."""
    hook_input = read_hook_input()
    tool_name = hook_input.get("tool", "")

    # Extract file path from tool parameters
    file_path = ""
    if "parameters" in hook_input:
        params = hook_input["parameters"]
        file_path = params.get("file_path", "")

    if not is_test_modification(tool_name, file_path):
        return 0  # Not a test modification, allow

    # Load session state
    session_state = load_session_state()
    passing_tests = session_state.get("passing_tests", set())

    # Check if this test file was passing earlier in the session
    if file_path not in passing_tests:
        # This is either a new test file or one we haven't seen pass yet
        # Allow modifications during red/green cycle
        return 0

    # This is a modification to a test that was previously passing
    config = check_local_config()
    mode = config.get("mode", "warn")

    if mode == "block":
        log(f"❌ BLOCKED: Modifying passing test file: {file_path}")
        log("This test was passing earlier in the session.")
        log("Set 'test_guard.mode' to 'warn' in .claude/settings.local.json to allow.")
        return 2  # Blocking exit code
    else:
        log(f"⚠️  WARNING: Modifying passing test file: {file_path}")
        log("This test was passing earlier in the session.")
        log("Consider whether this change is necessary for the feature implementation.")
        return 0  # Non-blocking warning


if __name__ == "__main__":
    sys.exit(main())
