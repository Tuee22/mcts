#!/usr/bin/env python3
"""
Robust staged pipeline for Claude Code post-change enforcement.

Enforces: Format → Type Check → Conditional Build → Conditional Tests → Doc Check

Environment Variables:
  MCTS_FORMAT_CMD     - Formatting command (default: docker compose exec mcts-dev black .)
  MCTS_TYPECHECK_CMD  - Type checking command (default: docker compose exec mcts-dev mypy --strict .)
  MCTS_BUILD_CMD      - Build command (default: docker compose build)
  MCTS_TEST_CMD       - Test command (default: docker compose exec mcts-dev pytest -q)
  MCTS_DOC_CHECK_CMD  - Documentation check command (default: docker compose exec mcts python .claude/hooks/check_docs.py)
  MCTS_SKIP_BUILD     - Skip build stage if "true" (default: auto-detect)
  MCTS_SKIP_TESTS     - Skip test stage if "true" (default: "false")
  MCTS_SKIP_DOCS      - Skip documentation check if "true" (default: "false")
  MCTS_VERBOSE        - Verbose output if "true" (default: "false")
  MCTS_FAIL_FAST      - Stop on first failure if "true" (default: "true")

Exit Codes:
  0  - All stages passed
  1  - Format stage failed
  2  - Type check stage failed
  3  - Build stage failed
  4  - Test stage failed
  5  - Tool not found / setup error
  6  - Documentation check failed
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Stage configuration with agent recommendations
STAGES = {
    "format": {
        "name": "Format",
        "default_cmd": "docker compose exec mcts black .",
        "env_var": "MCTS_FORMAT_CMD",
        "agent": "@formatter-black",
        "exit_code": 1,
        "description": "Python code formatting with Black",
    },
    "typecheck": {
        "name": "Type Check",
        "default_cmd": "docker compose exec mcts mypy --strict .",
        "env_var": "MCTS_TYPECHECK_CMD",
        "agent": "@mypy-type-checker",
        "exit_code": 2,
        "description": "Static type checking with MyPy",
    },
    "build": {
        "name": "Build",
        "default_cmd": "docker compose build",
        "env_var": "MCTS_BUILD_CMD",
        "agent": "@builder-docker",
        "exit_code": 3,
        "description": "Docker container build",
    },
    "test": {
        "name": "Test",
        "default_cmd": "docker compose exec mcts pytest -q",
        "env_var": "MCTS_TEST_CMD",
        "agent": "@tester-pytest",
        "exit_code": 4,
        "description": "Test suite execution",
    },
    "doc_check": {
        "name": "Documentation Check",
        "default_cmd": "docker compose exec mcts python .claude/hooks/check_docs.py",
        "env_var": "MCTS_DOC_CHECK_CMD",
        "agent": "@doc-consistency-checker",
        "exit_code": 6,
        "description": "Documentation consistency validation",
    },
}

# File extensions that trigger different stages
PYTHON_EXTENSIONS = {".py", ".pyi"}
BUILD_SURFACE_FILES = {
    "Dockerfile",
    "docker-compose.yaml",
    "docker-compose.yml",
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "poetry.lock",
    "Pipfile",
    "Pipfile.lock",
}
BUILD_SURFACE_DIRS = {"backend/core", "docker"}


def get_env_bool(var_name: str, default: bool = False) -> bool:
    """Get boolean environment variable."""
    return os.getenv(var_name, "").lower() in ("true", "1", "yes")


def get_env_str(var_name: str, default: str = "") -> str:
    """Get string environment variable."""
    return os.getenv(var_name, default)


def log_banner(stage_name: str, description: str) -> None:
    """Print stage banner."""
    banner = f"=== {stage_name}: {description} ==="
    print(f"\n{banner}")
    print("=" * len(banner))


def log_verbose(message: str) -> None:
    """Print verbose message if verbose mode enabled."""
    if get_env_bool("MCTS_VERBOSE"):
        print(f"[VERBOSE] {message}")


def check_tool_available(command: str) -> bool:
    """Check if a command/tool is available in PATH."""
    cmd_parts = command.split()
    if not cmd_parts:
        return False

    try:
        subprocess.run(["which", cmd_parts[0]], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_changed_files() -> Set[str]:
    """
    Get changed files from stdin (if available) or git working tree diff.
    Returns set of relative file paths.
    """
    changed_files: Set[str] = set()

    # Try to read from stdin first (if hook provides changed files)
    if not sys.stdin.isatty():
        try:
            for line in sys.stdin:
                file_path = line.strip()
                if file_path:
                    changed_files.add(file_path)
            log_verbose(f"Read {len(changed_files)} changed files from stdin")
        except Exception as e:
            log_verbose(f"Failed to read from stdin: {e}")

    # Fall back to git diff if no stdin or empty
    if not changed_files:
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            changed_files = {
                line.strip() for line in result.stdout.splitlines() if line.strip()
            }
            log_verbose(f"Found {len(changed_files)} changed files via git diff")
        except Exception as e:
            log_verbose(f"Git diff failed: {e}")
            # If git fails, assume all relevant files changed
            changed_files = {"**"}

    return changed_files


def should_run_build(changed_files: Set[str]) -> bool:
    """Determine if build stage should run based on changed files."""
    if get_env_bool("MCTS_SKIP_BUILD"):
        return False

    # Always build if we can't determine changed files
    if "**" in changed_files:
        return True

    # Check for build surface files
    for file_path in changed_files:
        path = Path(file_path)

        # Check exact filename matches
        if path.name in BUILD_SURFACE_FILES:
            log_verbose(f"Build triggered by: {file_path}")
            return True

        # Check directory prefixes
        for build_dir in BUILD_SURFACE_DIRS:
            if str(path).startswith(build_dir):
                log_verbose(f"Build triggered by: {file_path}")
                return True

    log_verbose("No build surface files changed, skipping build")
    return False


def should_run_tests(changed_files: Set[str]) -> bool:
    """Determine if test stage should run."""
    if get_env_bool("MCTS_SKIP_TESTS"):
        return False

    # Always test if we can't determine changed files
    if "**" in changed_files:
        return True

    # Run tests if any Python files changed
    for file_path in changed_files:
        if Path(file_path).suffix in PYTHON_EXTENSIONS:
            log_verbose(f"Tests triggered by: {file_path}")
            return True

    log_verbose("No Python files changed, skipping tests")
    return False


def ensure_docker_services() -> bool:
    """Ensure Docker services are running."""
    docker_dir = Path.cwd() / "docker"
    if not docker_dir.exists():
        print("⚠️  Docker directory not found, assuming host execution")
        return True

    try:
        # Check if services are already running
        result = subprocess.run(
            ["docker", "compose", "ps", "--services", "--filter", "status=running"],
            cwd=docker_dir,
            text=True,
            capture_output=True,
        )

        if result.returncode == 0 and "mcts" in result.stdout:
            log_verbose("Docker services already running")
            return True

        # Start services if not running
        print("🐳 Starting Docker services...")
        result = subprocess.run(
            ["docker", "compose", "up", "-d"],
            cwd=docker_dir,
            text=True,
            capture_output=False,
        )

        return result.returncode == 0

    except Exception as e:
        print(f"❌ Docker service error: {e}")
        return False


def run_stage(stage_key: str) -> bool:
    """
    Run a single stage of the pipeline.
    Returns True if successful, False if failed.
    """
    stage = STAGES[stage_key]
    command = get_env_str(stage["env_var"], stage["default_cmd"])

    log_banner(stage["name"], stage["description"])
    print(f"Command: {command}")

    # Ensure Docker services are running for container commands
    if "docker compose exec" in command:
        if not ensure_docker_services():
            print("❌ Failed to start Docker services")
            print(f"📋 Run agent: {stage['agent']}")
            return False

    # Check if tool is available
    if not check_tool_available(command):
        print(f"❌ TOOL NOT FOUND: {command.split()[0]}")
        print(f"📋 Run agent: {stage['agent']}")
        print(f"🔧 Or install tool and retry")
        return False

    # Run the command
    try:
        # Determine working directory based on command type
        if "docker compose" in command:
            work_dir = Path.cwd() / "docker"
        else:
            work_dir = Path.cwd()

        result = subprocess.run(
            command.split(),
            cwd=work_dir,
            text=True,
            capture_output=False,  # Show output in real-time
        )

        if result.returncode == 0:
            print(f"✅ {stage['name']} PASSED")
            return True
        else:
            print(f"❌ {stage['name']} FAILED (exit code: {result.returncode})")
            print(f"📋 Run agent: {stage['agent']}")
            print(f"🔄 Or fix issues manually and retry")
            return False

    except Exception as e:
        print(f"❌ {stage['name']} ERROR: {e}")
        print(f"📋 Run agent: {stage['agent']}")
        return False


def main() -> int:
    """Main pipeline execution."""
    print("🚀 Claude Code Post-Change Pipeline")
    print("=" * 40)

    fail_fast = get_env_bool("MCTS_FAIL_FAST", True)
    changed_files = get_changed_files()

    if get_env_bool("MCTS_VERBOSE"):
        print(
            f"Changed files: {sorted(changed_files) if changed_files != {'**'} else 'ALL'}"
        )
        print(f"Fail fast: {fail_fast}")

    # Stage 1: Format (always run for Python files)
    has_python = (
        any(Path(f).suffix in PYTHON_EXTENSIONS for f in changed_files)
        or "**" in changed_files
    )
    if has_python:
        if not run_stage("format"):
            if fail_fast:
                return STAGES["format"]["exit_code"]
    else:
        print("\n=== Format: Skipped (no Python files) ===")

    # Stage 2: Type Check (always run for Python files)
    if has_python:
        if not run_stage("typecheck"):
            if fail_fast:
                return STAGES["typecheck"]["exit_code"]
    else:
        print("\n=== Type Check: Skipped (no Python files) ===")

    # Stage 3: Build (conditional)
    if should_run_build(changed_files):
        if not run_stage("build"):
            if fail_fast:
                return STAGES["build"]["exit_code"]
    else:
        print("\n=== Build: Skipped (no build surface changes) ===")

    # Stage 4: Test (conditional)
    if should_run_tests(changed_files):
        if not run_stage("test"):
            if fail_fast:
                return STAGES["test"]["exit_code"]
    else:
        print("\n=== Test: Skipped (no Python files changed) ===")

    # Stage 5: Documentation Check (always run unless explicitly skipped)
    if not get_env_bool("MCTS_SKIP_DOCS"):
        if not run_stage("doc_check"):
            if fail_fast:
                return STAGES["doc_check"]["exit_code"]
    else:
        print("\n=== Documentation Check: Skipped (MCTS_SKIP_DOCS=true) ===")

    print("\n🎉 All stages completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
