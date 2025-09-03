#!/usr/bin/env python3
"""Minimal quality gate for testing"""

import subprocess
import sys
from pathlib import Path

# Get repo root
repo_root = Path(__file__).parent.parent.parent.absolute()
docker_dir = repo_root / "docker"

print(f"Repo root: {repo_root}")
print(f"Docker dir: {docker_dir}")

# Test running pytest
print("\nRunning pytest in container...")
try:
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "mcts", "pytest", "-q", "--tb=short"],
        cwd=docker_dir,
        capture_output=True,
        text=True,
        timeout=30,
    )
    print(f"Exit code: {result.returncode}")
    if result.stdout:
        print(f"Stdout:\n{result.stdout}")
    if result.stderr:
        print(f"Stderr:\n{result.stderr}")

    sys.exit(0 if result.returncode == 0 else 4)
except subprocess.TimeoutExpired:
    print("Command timed out")
    sys.exit(5)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(5)
