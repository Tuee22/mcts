#!/usr/bin/env python3
"""
Auto-fixing Quality Gate Script for Claude Code Stop Hook

Runs comprehensive quality checks and auto-fixes when possible:
1. Format (Black + isort) - AUTO-FIXES formatting and import sorting
2. Type Check (MyPy strict) - Reports errors only (cannot auto-fix)
3. Build (Docker) - Reports build errors only
4. Tests (pytest) - Reports test failures only

Exits with specific error codes when checks fail.
This blocks the Stop event and forces the assistant to continue fixing issues.

Exit Codes:
  0 - All checks passed
  1 - Format tools failed (should rarely happen with auto-fix)
  2 - Type check failed  
  3 - Build failed
  4 - Tests failed
  5 - Setup/tool error
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Handle working directory - script is in .claude/hooks/
# Get absolute path to repo root (.claude/hooks/script.py -> .claude/hooks -> .claude -> repo_root)
repo_root = Path(__file__).parent.parent.parent.absolute()
# Don't change directory - just use repo_root for paths
print(f"Quality gate repo root: {repo_root}")


def run_command(
    cmd: List[str], description: str, cwd: Optional[Path] = None
) -> Tuple[int, str, str]:
    """
    Run a command inside Docker container and return (exit_code, stdout, stderr).
    """
    try:
        # Check if docker/ subdirectory exists
        docker_dir = (
            repo_root / "docker" if (repo_root / "docker").exists() else repo_root
        )

        # Run commands inside Docker container
        docker_cmd = ["docker", "compose", "exec", "-T", "mcts"] + cmd
        result = subprocess.run(
            docker_cmd,
            cwd=cwd or docker_dir,
            text=True,
            capture_output=True,
            timeout=60,  # 1 minute timeout per command
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"{description} timed out after 1 minute"
    except Exception as e:
        return 1, "", f"{description} error: {str(e)}"


def run_host_command(
    cmd: List[str], description: str, cwd: Optional[Path] = None
) -> Tuple[int, str, str]:
    """
    Run a command on the host (for Docker builds) and return (exit_code, stdout, stderr).
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or repo_root,
            text=True,
            capture_output=True,
            timeout=60,  # 1 minute timeout per command
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"{description} timed out after 1 minute"
    except Exception as e:
        return 1, "", f"{description} error: {str(e)}"


def check_tool_available(tool: str) -> bool:
    """Check if a tool is available inside Docker container."""
    try:
        # Check if docker/ subdirectory exists
        docker_dir = (
            repo_root / "docker" if (repo_root / "docker").exists() else repo_root
        )

        result = subprocess.run(
            ["docker", "compose", "exec", "-T", "mcts", "which", tool],
            capture_output=True,
            check=True,
            cwd=docker_dir,
            timeout=10,  # 10 second timeout for which command
        )
        return True
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        return False


def check_host_tool_available(tool: str) -> bool:
    """Check if a tool is available on the host."""
    try:
        subprocess.run(["which", tool], capture_output=True, check=True, cwd=repo_root)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def print_stage_header(stage: str, description: str):
    """Print a consistent stage header."""
    print(f"\n{'='*60}")
    print(f"🔍 QUALITY CHECK: {stage}")
    print(f"📋 {description}")
    print(f"{'='*60}")


def run_format_check(verbose: bool = False) -> bool:
    """Run Python code formatting with Black and isort."""
    if verbose:
        print_stage_header("FORMAT", "Auto-formatting Python code with Black and isort")

    if not check_tool_available("black"):
        print("❌ FORMAT FAILED: black not found")
        print("🔧 Install black or use @formatter-black agent")
        return False

    # Run isort first if available (import sorting)
    if check_tool_available("isort"):
        if verbose:
            print("🔧 Running isort to organize imports...")
        isort_code, isort_stdout, isort_stderr = run_command(
            ["isort", "/app"], "isort auto-format"
        )
        if isort_code != 0 and verbose:
            print("⚠️  ISORT WARNING: Issues with import sorting")
            if isort_stderr:
                print(f"Isort errors:\n{isort_stderr}")

    # Run black to auto-fix formatting issues
    if verbose:
        print("🔧 Running Black to format code...")
    code, stdout, stderr = run_command(["black", "/app"], "black auto-format")

    if code == 0:
        if verbose:
            print("✅ FORMAT PASSED: All files formatted successfully")
            if stdout:
                print(f"Formatted files:\n{stdout}")
        return True
    else:
        # Always print errors
        print("❌ FORMAT FAILED: Black encountered errors")
        print("📋 Use @formatter-black agent to investigate issues")
        if stdout:
            print(f"Output:\n{stdout}")
        if stderr:
            print(f"Errors:\n{stderr}")
        return False


def run_type_check(verbose: bool = False) -> bool:
    """Run MyPy strict type checking."""
    if verbose:
        print_stage_header("TYPE CHECK", "Running MyPy strict type checking")

    if not check_tool_available("mypy"):
        print("❌ TYPE CHECK FAILED: mypy not found")
        print("🔧 Install mypy or use @mypy-type-checker agent")
        return False

    code, stdout, stderr = run_command(["mypy", "--strict", "/app"], "mypy --strict")

    if code == 0:
        if verbose:
            print("✅ TYPE CHECK PASSED: No type errors found")
        return True
    else:
        # Always print errors
        print("❌ TYPE CHECK FAILED: Type errors found")
        print("📋 Use @mypy-type-checker agent to fix type errors")
        print("🔄 Or fix type annotations manually")
        if stdout:
            print(f"Type errors:\n{stdout}")
        if stderr:
            print(f"MyPy errors:\n{stderr}")
        return False


def run_build_check(verbose: bool = False) -> bool:
    """Run Docker build check if applicable."""
    if verbose:
        print_stage_header("BUILD", "Checking Docker build")

    # Check if Docker is available on host (for builds)
    if not check_host_tool_available("docker"):
        if verbose:
            print("⚠️  BUILD SKIPPED: Docker not available")
        return True

    # Check if we have Docker files (on host filesystem)
    dockerfile_paths = [
        repo_root / "Dockerfile",
        repo_root / "docker" / "Dockerfile",
        repo_root / "docker" / "Dockerfile.cpu",
    ]

    dockerfile_exists = any(p.exists() for p in dockerfile_paths)
    compose_exists = (repo_root / "docker-compose.yaml").exists() or (
        repo_root / "docker" / "docker-compose.yaml"
    ).exists()

    if not dockerfile_exists and not compose_exists:
        if verbose:
            print("⚠️  BUILD SKIPPED: No Dockerfile or docker-compose.yaml found")
        return True

    # Try to build using docker compose if available
    if compose_exists:
        # Check if compose file is in docker/ subdirectory
        docker_dir = (
            repo_root / "docker"
            if (repo_root / "docker" / "docker-compose.yaml").exists()
            else repo_root
        )
        code, stdout, stderr = run_host_command(
            ["docker", "compose", "build", "--quiet"],
            "docker compose build",
            cwd=docker_dir,
        )
    else:
        # Try direct docker build
        code, stdout, stderr = run_host_command(
            ["docker", "build", "-t", "mcts-test", "."], "docker build"
        )

    if code == 0:
        if verbose:
            print("✅ BUILD PASSED: Docker build successful")
        return True
    else:
        # Always print errors
        print("❌ BUILD FAILED: Docker build errors")
        print("📋 Use @builder-docker, @builder-cpu, or @builder-gpu agents")
        print("🔄 Or fix Dockerfile/build issues manually")
        if stdout:
            print(f"Build output:\n{stdout}")
        if stderr:
            print(f"Build errors:\n{stderr}")
        return False


def run_test_check(verbose: bool = False) -> bool:
    """Run test suite."""
    if verbose:
        print_stage_header("TESTS", "Running test suite")

    # Check for pytest
    if not check_tool_available("pytest"):
        if verbose:
            print("⚠️  TESTS SKIPPED: pytest not found")
        return True

    # Check if tests directory exists (inside container)
    test_paths = ["/app/tests", "/app/test"]
    test_dir_exists = any(
        run_command(["test", "-d", path], f"check {path}")[0] == 0
        for path in test_paths
    )

    if not test_dir_exists:
        if verbose:
            print("⚠️  TESTS SKIPPED: No tests directory found")
        return True

    # Run pytest with minimal output - skip slow tests to avoid timeout
    code, stdout, stderr = run_command(
        ["pytest", "-q", "--tb=short", "-m", "not slow"], "pytest"
    )

    if code == 0:
        if verbose:
            print("✅ TESTS PASSED: All tests successful")
            if stdout:
                print(f"Test summary:\n{stdout}")
        return True
    else:
        # Always print errors
        print("❌ TESTS FAILED: Test failures or errors")
        print("📋 Use @tester-pytest agent to fix test failures")
        print("🔄 Or fix failing tests manually")
        if stdout:
            print(f"Test output:\n{stdout}")
        if stderr:
            print(f"Test errors:\n{stderr}")
        return False


def main() -> int:
    """Run all quality checks in sequence."""
    # Run silently by default to avoid infinite loops
    # Only print output if QUALITY_GATE_VERBOSE env var is set or if there are failures
    verbose = os.environ.get("QUALITY_GATE_VERBOSE", "").lower() in ["1", "true", "yes"]

    if verbose:
        print("🚀 QUALITY GATE: Starting automated quality checks")
        print("📋 Running: Format → Type Check → Build → Tests")

    # Track which checks failed
    failed_checks = []

    # 1. Format Check
    if not run_format_check(verbose):
        failed_checks.append("FORMAT")

    # 2. Type Check
    if not run_type_check(verbose):
        failed_checks.append("TYPE_CHECK")

    # 3. Build Check
    if not run_build_check(verbose):
        failed_checks.append("BUILD")

    # 4. Test Check
    if not run_test_check(verbose):
        failed_checks.append("TESTS")

    # Final result - only print if there are failures or verbose mode
    if failed_checks:
        # Always print failures
        print(f"\n{'='*60}")
        print("❌ QUALITY GATE FAILED")
        print(f"🔧 Failed checks: {', '.join(failed_checks)}")
        print("📋 Use the appropriate agents to fix issues:")
        print("   • @formatter-black for formatting")
        print("   • @mypy-type-checker for type errors")
        print("   • @builder-docker/@builder-cpu/@builder-gpu for builds")
        print("   • @tester-pytest for test failures")
        print("🔄 Session will continue until all checks pass")
        print(f"{'='*60}")

        # Return specific exit code for first failure
        if "FORMAT" in failed_checks:
            return 1
        elif "TYPE_CHECK" in failed_checks:
            return 2
        elif "BUILD" in failed_checks:
            return 3
        elif "TESTS" in failed_checks:
            return 4
        else:
            return 5
    else:
        # Only print success if verbose mode is enabled
        if verbose:
            print(f"\n{'='*60}")
            print("✅ QUALITY GATE PASSED")
            print("🎉 All checks successful: Format ✓ Type Check ✓ Build ✓ Tests ✓")
            print("💚 Code quality verified - ready for commit")
            print(f"{'='*60}")
        # Silent success - return 0 without printing anything
        return 0


if __name__ == "__main__":
    sys.exit(main())
