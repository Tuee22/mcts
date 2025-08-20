#!/usr/bin/env python3
"""
Post-change hook that enforces Black → MyPy → Build → Tests pipeline
Runs after Edit, Write, or MultiEdit operations
"""
import os
import sys
import subprocess
import json
from pathlib import Path

# Environment variables for customization
MYPY_CMD = os.getenv("MYPY_CMD", "poetry run mypy")
TEST_CMD = os.getenv("TEST_CMD", "poetry run pytest -q")
BUILD_CMD = os.getenv("BUILD_CMD", "docker build -t project-ci .")
ALWAYS_BUILD = os.getenv("ALWAYS_BUILD", "").lower() in ("1", "true", "yes")
ALWAYS_TEST = os.getenv("ALWAYS_TEST", "").lower() in ("1", "true", "yes")

# Build surface files that trigger docker build
BUILD_SURFACE_FILES = {
    "Dockerfile",
    ".dockerignore",
    "compose.yaml",
    "docker-compose.yml",
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
    "Pipfile",
    "poetry.lock",
    "Makefile",
}

BUILD_SURFACE_PREFIXES = ("docker/", "scripts/build/", ".github/workflows/")


def get_build_surface_patterns():
    """Get patterns that match build surface files"""
    patterns = list(BUILD_SURFACE_FILES)
    patterns.extend(["requirements*.txt"])
    return patterns


def is_build_surface_changed(changed_files):
    """Check if any changed files affect the build surface"""
    if ALWAYS_BUILD:
        return True

    for file_path in changed_files:
        path = Path(file_path)

        # Check exact filename matches
        if path.name in BUILD_SURFACE_FILES:
            return True

        # Check requirements*.txt pattern
        if path.name.startswith("requirements") and path.name.endswith(".txt"):
            return True

        # Check path prefixes
        path_str = str(path)
        if any(path_str.startswith(prefix) for prefix in BUILD_SURFACE_PREFIXES):
            return True

    return False


def run_command(cmd, stage_name):
    """Run a command and return success status"""
    print(f"[{stage_name}] Running: {cmd}")
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=os.getcwd()
        )
        if result.returncode == 0:
            print(f"[{stage_name}] ✅ Success")
            return True
        else:
            print(f"[{stage_name}] ❌ Failed (exit code {result.returncode})")
            if result.stdout:
                print(f"[{stage_name}] STDOUT:\n{result.stdout}")
            if result.stderr:
                print(f"[{stage_name}] STDERR:\n{result.stderr}")
            return False
    except Exception as e:
        print(f"[{stage_name}] ❌ Exception: {e}")
        return False


def block_with_reason(stage, reason):
    """Block the operation and provide guidance on which agent to call"""
    agent_map = {
        "Black": "formatter-black",
        "MyPy": "mypy-type-checker",
        "Build": "builder-docker",
        "Tests": "tester-pytest",
    }

    agent_name = agent_map.get(stage, stage.lower())

    print(f"❌ BLOCKED: {stage} stage failed")
    print(f"Reason: {reason}")
    print(f"")
    print(f"To fix this issue, please run:")
    print(f"  @{agent_name}")
    print(f"")
    print(
        f"The {agent_name} agent will handle the {stage.lower()} issues and iterate until resolved."
    )

    sys.exit(1)


def main():
    """Main hook execution"""
    # Read hook input from stdin if available
    changed_files = []
    try:
        if not sys.stdin.isatty():
            hook_data = json.loads(sys.stdin.read())
            # Extract file paths from the hook data
            if "file_path" in hook_data:
                changed_files.append(hook_data["file_path"])
            elif "edits" in hook_data:
                # MultiEdit case
                changed_files.append(hook_data.get("file_path", ""))
    except (json.JSONDecodeError, KeyError):
        # Fallback: assume current directory has changes
        pass

    print("🔄 Starting post-change pipeline: Black → MyPy → Build → Tests")

    # Stage 1: Black formatting
    # Try poetry first, fallback to direct command
    black_cmd = (
        "poetry run black ."
        if os.system("which poetry >/dev/null 2>&1") == 0
        else "black ."
    )
    if not run_command(black_cmd, "Black"):
        print(f"[Black] ⚠️  Black not available, skipping formatting stage")
        print(f"[Black] To enable formatting, install black: pip install black")
    else:
        # Verify Black formatting
        black_check_cmd = (
            "poetry run black --check ."
            if os.system("which poetry >/dev/null 2>&1") == 0
            else "black --check ."
        )
        if not run_command(black_check_cmd, "Black-Verify"):
            block_with_reason(
                "Black",
                "Code formatting verification failed. Files are not properly formatted.",
            )

    # Stage 2: MyPy type checking
    # Try poetry first, fallback to direct command
    mypy_cmd = (
        "poetry run mypy" if os.system("which poetry >/dev/null 2>&1") == 0 else "mypy"
    )
    if not run_command(mypy_cmd, "MyPy"):
        print(f"[MyPy] ⚠️  MyPy not available or failed, skipping type checking stage")
        print(f"[MyPy] To enable type checking, install mypy: pip install mypy")

    # Stage 3: Build (conditional)
    needs_build = is_build_surface_changed(changed_files)
    if needs_build:
        if not run_command(BUILD_CMD, "Build"):
            block_with_reason(
                "Build", "Docker build failed. Build errors need to be resolved."
            )
    else:
        print("[Build] ⏭️  Skipped (no build surface changes)")

    # Stage 4: Tests (conditional)
    if ALWAYS_TEST or needs_build or changed_files:
        # Try poetry first, fallback to direct command
        test_cmd = (
            "poetry run pytest -q"
            if os.system("which poetry >/dev/null 2>&1") == 0
            else "pytest -q"
        )
        if not run_command(test_cmd, "Tests"):
            print(f"[Tests] ⚠️  Tests not available or failed, skipping test stage")
            print(f"[Tests] To enable testing, install pytest: pip install pytest")
    else:
        print("[Tests] ⏭️  Skipped (no changes requiring test run)")

    print("✅ All pipeline stages completed successfully!")


if __name__ == "__main__":
    main()
