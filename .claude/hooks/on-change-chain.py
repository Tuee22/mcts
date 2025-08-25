#!/usr/bin/env python
"""
Robust staged pipeline for Claude Code post-change enforcement.

Enforces: Format → Type Check → Conditional Build → Conditional Tests → Doc Check

Environment Variables:
  MCTS_FORMAT_CMD     - Formatting command (default: black .)
  MCTS_TYPECHECK_CMD  - Type checking command (default: mypy --strict .)
  MCTS_BUILD_CMD      - Build command (default: echo 'Build runs on host')
  MCTS_TEST_CMD       - Test command (default: pytest -q)
  MCTS_DOC_CHECK_CMD  - Documentation check command (default: python /app/.claude/hooks/check_docs.py)
  MCTS_SKIP_BUILD     - Skip build stage if "true" (default: auto-detect)
  MCTS_SKIP_TESTS     - Skip test stage if "true" (default: "false")
  MCTS_SKIP_DOCS      - Skip documentation check if "true" (default: "false")
  MCTS_VERBOSE        - Verbose output if "true" (default: "false")
  MCTS_FAIL_FAST      - Stop on first failure if "true" (default: "true")
  MCTS_AUTO_FIX       - Automatically fix issues if "true" (default: "true")

Exit Codes:
  0  - All stages passed
  1  - Format stage failed
  2  - Type check stage failed
  3  - Build stage failed
  4  - Test stage failed
  5  - Tool not found / setup error
  6  - Documentation check failed
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Stage configuration with agent recommendations
STAGES = {
    "format": {
        "name": "Format",
        "default_cmd": "black .",
        "env_var": "MCTS_FORMAT_CMD",
        "agent": "@formatter-black",
        "exit_code": 1,
        "description": "Python code formatting with Black",
    },
    "typecheck": {
        "name": "Type Check",
        "default_cmd": "mypy --strict .",
        "env_var": "MCTS_TYPECHECK_CMD",
        "agent": "@mypy-type-checker",
        "exit_code": 2,
        "description": "Static type checking with MyPy",
    },
    "build": {
        "name": "Build",
        "default_cmd": "echo 'Build would run on host'",
        "env_var": "MCTS_BUILD_CMD",
        "agent": "@builder-docker (or @builder-cpu/@builder-gpu for multi-arch)",
        "exit_code": 3,
        "description": "Docker container build with dependency management",
    },
    "test": {
        "name": "Test",
        "default_cmd": "pytest -q",
        "env_var": "MCTS_TEST_CMD",
        "agent": "@tester-pytest",
        "exit_code": 4,
        "description": "Test suite execution",
    },
    "doc_check": {
        "name": "Documentation Check",
        "default_cmd": "python /app/.claude/hooks/check_docs.py",
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
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "poetry.lock",
    "Pipfile",
    "Pipfile.lock",
}
BUILD_SURFACE_DIRS = {"backend/core", "docker"}

# Note: Auto-fix is now handled by the intelligent investigation system
# in auto_investigate_fix.py which analyzes errors and applies appropriate fixes


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


def parse_tool_payload() -> Tuple[str, str, Set[str]]:
    """
    Parse JSON from stdin to extract event type, tool name, and changed files.
    Returns (event_type, tool_name, changed_files_set).
    """
    event_type = "Post-Tool-Use"
    tool_name = "Unknown"
    changed_files: Set[str] = set()

    # Try to read JSON from stdin
    if not sys.stdin.isatty():
        try:
            stdin_data = sys.stdin.read()
            if stdin_data:
                payload = json.loads(stdin_data)

                # Extract tool information
                tool_info = payload.get("tool", {})
                tool_name = tool_info.get("name", "Unknown")
                tool_params = tool_info.get("parameters", {})

                # Extract changed files based on tool type
                if tool_name in ["Edit", "Write"]:
                    file_path = tool_params.get("file_path")
                    if file_path:
                        # Convert absolute host path to relative container path
                        if file_path.startswith("/"):
                            # Remove project root from absolute path
                            file_path = file_path.replace(
                                "/Users/matthewnowak/mcts/", ""
                            )
                        changed_files.add(file_path)
                elif tool_name == "MultiEdit":
                    file_path = tool_params.get("file_path")
                    if file_path:
                        # Convert absolute host path to relative container path
                        if file_path.startswith("/"):
                            file_path = file_path.replace(
                                "/Users/matthewnowak/mcts/", ""
                            )
                        changed_files.add(file_path)
                elif tool_name == "Task":
                    # For Task tool, we can't know specific files, so trigger all checks
                    changed_files.add("**")

                log_verbose(f"Parsed tool payload: {tool_name}, files: {changed_files}")
            else:
                log_verbose("No JSON payload in stdin")
        except json.JSONDecodeError as e:
            log_verbose(f"Failed to parse JSON from stdin: {e}")
        except Exception as e:
            log_verbose(f"Error reading stdin: {e}")

    # Fall back to git diff if no files detected
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
            log_verbose(
                f"Fallback: Found {len(changed_files)} changed files via git diff"
            )
        except Exception as e:
            log_verbose(f"Git diff fallback failed: {e}")
            # If git fails, assume all relevant files changed
            changed_files = {"**"}

    return event_type, tool_name, changed_files


def get_changed_files() -> Set[str]:
    """
    Get changed files - kept for compatibility.
    Returns set of relative file paths.
    """
    _, _, changed_files = parse_tool_payload()
    return changed_files


def should_run_build(changed_files: Set[str]) -> bool:
    """Determine if build stage should run based on changed files."""
    if get_env_bool("MCTS_SKIP_BUILD"):
        return False

    # Always build if we can't determine changed files
    if "**" in changed_files:
        return True

    # Check for build surface files
    dependency_files_changed = False
    for file_path in changed_files:
        path = Path(file_path)

        # Check exact filename matches
        if path.name in BUILD_SURFACE_FILES:
            log_verbose(f"Build triggered by: {file_path}")
            # Special handling for dependency files
            if path.name in {"pyproject.toml", "poetry.lock"}:
                dependency_files_changed = True
                log_verbose(
                    f"DEPENDENCY FILE CHANGED: {file_path} - Will trigger full rebuild"
                )
            return True

        # Check directory prefixes
        for build_dir in BUILD_SURFACE_DIRS:
            if str(path).startswith(build_dir):
                log_verbose(f"Build triggered by: {file_path}")
                return True

    log_verbose("No build surface files changed, skipping build")
    return False


def has_dependency_changes(changed_files: Set[str]) -> bool:
    """Check if dependency files (pyproject.toml, poetry.lock) were modified."""
    dependency_files = {"pyproject.toml", "poetry.lock"}

    for file_path in changed_files:
        path = Path(file_path)
        if path.name in dependency_files:
            return True
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


def run_stage(stage_key: str, auto_fix: bool = False) -> bool:
    """
    Run a single stage of the pipeline.
    Returns True if successful, False if failed.
    """
    stage = STAGES[stage_key]
    command = get_env_str(stage["env_var"], stage["default_cmd"])

    log_banner(stage["name"], stage["description"])
    print(f"Command: {command}")

    # Special handling for build stage (needs to run on host)
    if stage_key == "build":
        print("⚠️  Build stage must run on host, skipping in container")
        return True

    # Check if tool is available
    if not check_tool_available(command):
        print(f"❌ TOOL NOT FOUND: {command.split()[0]}")
        print(f"📋 Run agent: {stage['agent']}")
        print(f"🔧 Or install tool and retry")
        return False

    # Run the command - first attempt
    try:
        # Run command in container's working directory
        work_dir = Path("/app")

        # First run with output capture for investigation
        result = subprocess.run(
            command.split(),
            cwd=work_dir,
            text=True,
            capture_output=True,  # Capture for investigation
        )

        # Show output
        if result.stdout:
            print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
        if result.stderr:
            print(
                result.stderr,
                end="" if result.stderr.endswith("\n") else "\n",
                file=sys.stderr,
            )

        if result.returncode == 0:
            print(f"✅ {stage['name']} PASSED")
            return True
        else:
            # Try intelligent auto-investigation and fix if enabled
            if auto_fix:
                print(f"🔍 {stage['name']} FAILED - Investigating issue...")

                # Combine stdout and stderr for investigation
                combined_output = (result.stdout or "") + "\n" + (result.stderr or "")

                # Run the investigation script (we're already in container)
                investigation_result = subprocess.run(
                    [
                        "python",
                        "/app/.claude/hooks/auto_investigate_fix.py",
                        stage_key,
                        str(result.returncode),
                    ],
                    input=combined_output,
                    text=True,
                    capture_output=True,
                )

                if investigation_result.returncode == 0:
                    print(investigation_result.stdout)
                    print(f"🔄 Re-running {stage['name']} after auto-fix...")

                    # Re-run the original command
                    retry_result = subprocess.run(
                        command.split(),
                        cwd=work_dir,
                        text=True,
                        capture_output=False,
                    )

                    if retry_result.returncode == 0:
                        print(f"✅ {stage['name']} PASSED after auto-fix")
                        return True
                    else:
                        print(f"❌ {stage['name']} still failing after auto-fix")
                else:
                    # Investigation couldn't fix it
                    if investigation_result.stdout:
                        print(investigation_result.stdout)

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
    fail_fast = get_env_bool("MCTS_FAIL_FAST", True)
    auto_fix = get_env_bool("MCTS_AUTO_FIX", True)  # Auto-fix enabled by default
    event_type, tool_name, changed_files = parse_tool_payload()

    # Print startup line with event, tool, and changed files
    file_list = sorted(changed_files) if changed_files != {"**"} else ["all"]
    file_summary = (
        ", ".join(file_list) if len(file_list) <= 3 else f"{len(file_list)} files"
    )
    print(f"🚀 {event_type} | Tool: {tool_name} | Files: {file_summary}")

    if get_env_bool("MCTS_VERBOSE"):
        print("=" * 40)
        print(f"Verbose mode enabled")
        print(
            f"Changed files: {sorted(changed_files) if changed_files != {'**'} else 'ALL'}"
        )
        print(f"Fail fast: {fail_fast}")
        print(f"Auto-fix: {auto_fix}")

    # Stage 1: Format (always run for Python files)
    has_python = (
        any(Path(f).suffix in PYTHON_EXTENSIONS for f in changed_files)
        or "**" in changed_files
    )
    if has_python:
        if not run_stage("format", auto_fix):
            if fail_fast:
                return STAGES["format"]["exit_code"]
    else:
        print("\n=== Format: Skipped (no Python files) ===")

    # Stage 2: Type Check (always run for Python files)
    if has_python:
        if not run_stage("typecheck", auto_fix):
            if fail_fast:
                return STAGES["typecheck"]["exit_code"]
    else:
        print("\n=== Type Check: Skipped (no Python files) ===")

    # Stage 3: Build (conditional)
    if should_run_build(changed_files):
        # Check if dependency files changed to trigger enhanced build process
        if has_dependency_changes(changed_files):
            print(
                f"\n🔧 DEPENDENCY CHANGES DETECTED - Enhanced build process will be used"
            )
            print(
                f"📋 Recommended: Use @builder-docker, @builder-cpu, and @builder-gpu agents"
            )
            print(f"⚠️  All container variants will be rebuilt with --no-cache")

            # Set environment variable to signal enhanced build
            os.environ["BUILD_NO_CACHE"] = "1"
            os.environ["MCTS_DEPENDENCY_CHANGE"] = "1"

        if not run_stage("build", auto_fix):
            if fail_fast:
                return STAGES["build"]["exit_code"]
    else:
        print("\n=== Build: Skipped (no build surface changes) ===")

    # Stage 4: Test (conditional)
    if should_run_tests(changed_files):
        if not run_stage("test", auto_fix):
            if fail_fast:
                return STAGES["test"]["exit_code"]
    else:
        print("\n=== Test: Skipped (no Python files changed) ===")

    # Stage 5: Documentation Check (always run unless explicitly skipped)
    if not get_env_bool("MCTS_SKIP_DOCS"):
        if not run_stage("doc_check", auto_fix):
            if fail_fast:
                return STAGES["doc_check"]["exit_code"]
    else:
        print("\n=== Documentation Check: Skipped (MCTS_SKIP_DOCS=true) ===")

    print("\n🎉 All stages completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
