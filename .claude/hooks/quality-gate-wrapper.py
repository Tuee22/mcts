#!/usr/bin/env python3
"""
Wrapper for quality-gate.py that prevents infinite loops.

This wrapper ensures the quality gate doesn't trigger recursively
by checking if it's already running and by implementing a cooldown period.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

# File to track last run time
LAST_RUN_FILE = Path(__file__).parent / ".quality-gate-last-run"

# Minimum seconds between runs to prevent rapid re-triggering
COOLDOWN_SECONDS = 5

# Environment variable to detect recursive calls
RECURSION_FLAG = "QUALITY_GATE_RUNNING"


def main():
    # Check if we're already running (recursive call)
    if os.environ.get(RECURSION_FLAG) == "1":
        # Silently exit to prevent loops
        sys.exit(0)

    # Check cooldown period
    if LAST_RUN_FILE.exists():
        try:
            last_run = float(LAST_RUN_FILE.read_text().strip())
            elapsed = time.time() - last_run
            if elapsed < COOLDOWN_SECONDS:
                # Too soon since last run, skip silently
                sys.exit(0)
        except (ValueError, IOError):
            # If we can't read the file, continue anyway
            pass

    # Set recursion flag for child processes
    env = os.environ.copy()
    env[RECURSION_FLAG] = "1"

    # Update last run time
    try:
        LAST_RUN_FILE.write_text(str(time.time()))
    except IOError:
        # If we can't write, continue anyway
        pass

    # Run the actual quality gate
    quality_gate_path = Path(__file__).parent / "quality-gate.py"

    try:
        result = subprocess.run(
            [sys.executable, str(quality_gate_path)],
            env=env,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        # Only print output if there are errors or if verbose mode is set
        if result.returncode != 0:
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
        elif os.environ.get("QUALITY_GATE_VERBOSE", "").lower() in ["1", "true", "yes"]:
            if result.stdout:
                print(result.stdout)

        sys.exit(result.returncode)

    except subprocess.TimeoutExpired:
        print("Quality gate timed out after 5 minutes", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Quality gate wrapper error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
