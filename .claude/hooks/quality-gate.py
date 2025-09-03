#!/usr/bin/env python3
"""
Quality Gate Script for Claude Code Stop Hook

Runs comprehensive quality checks in order:
1. Format (Black)
2. Type Check (MyPy strict)
3. Build (Docker)
4. Tests (pytest)

Exits with specific error codes and helpful messages when checks fail.
This blocks the Stop event and forces the assistant to continue fixing issues.

Exit Codes:
  0 - All checks passed
  1 - Format failed
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


def run_command(
    cmd: List[str], description: str, cwd: Optional[Path] = None
) -> Tuple[int, str, str]:
    """
    Run a command and return (exit_code, stdout, stderr).
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or Path("/app"),
            text=True,
            capture_output=True,
            timeout=300,  # 5 minute timeout per command
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"{description} timed out after 5 minutes"
    except Exception as e:
        return 1, "", f"{description} error: {str(e)}"


def check_tool_available(tool: str) -> bool:
    """Check if a tool is available in PATH."""
    try:
        subprocess.run(["which", tool], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def print_stage_header(stage: str, description: str):
    """Print a consistent stage header."""
    print(f"\n{'='*60}")
    print(f"🔍 QUALITY CHECK: {stage}")
    print(f"📋 {description}")
    print(f"{'='*60}")


def run_format_check() -> bool:
    """Run Python code formatting with Black."""
    print_stage_header("FORMAT", "Checking Python code formatting with Black")

    if not check_tool_available("black"):
        print("❌ FORMAT FAILED: black not found")
        print("🔧 Install black or use @formatter-black agent")
        return False

    # Run black in check mode first
    code, stdout, stderr = run_command(["black", "--check", "."], "black --check")

    if code == 0:
        print("✅ FORMAT PASSED: All files properly formatted")
        return True
    else:
        print("❌ FORMAT FAILED: Files need formatting")
        print("📋 Use @formatter-black agent to fix formatting issues")
        print("🔄 Or run 'black .' to format files")
        if stdout:
            print(f"Details:\n{stdout}")
        if stderr:
            print(f"Errors:\n{stderr}")
        return False


def run_type_check() -> bool:
    """Run MyPy strict type checking."""
    print_stage_header("TYPE CHECK", "Running MyPy strict type checking")

    if not check_tool_available("mypy"):
        print("❌ TYPE CHECK FAILED: mypy not found")
        print("🔧 Install mypy or use @mypy-type-checker agent")
        return False

    code, stdout, stderr = run_command(["mypy", "--strict", "."], "mypy --strict")

    if code == 0:
        print("✅ TYPE CHECK PASSED: No type errors found")
        return True
    else:
        print("❌ TYPE CHECK FAILED: Type errors found")
        print("📋 Use @mypy-type-checker agent to fix type errors")
        print("🔄 Or fix type annotations manually")
        if stdout:
            print(f"Type errors:\n{stdout}")
        if stderr:
            print(f"MyPy errors:\n{stderr}")
        return False


def run_build_check() -> bool:
    """Run Docker build check if applicable."""
    print_stage_header("BUILD", "Checking Docker build")

    # Check if Docker is available
    if not check_tool_available("docker"):
        print("⚠️  BUILD SKIPPED: Docker not available")
        return True

    # Check if we have Docker files
    dockerfile_paths = [
        Path("/app/Dockerfile"),
        Path("/app/docker/Dockerfile"),
        Path("/app/docker/Dockerfile.cpu"),
    ]

    dockerfile_exists = any(p.exists() for p in dockerfile_paths)
    compose_exists = (
        Path("/app/docker-compose.yaml").exists()
        or Path("/app/docker/docker-compose.yaml").exists()
    )

    if not dockerfile_exists and not compose_exists:
        print("⚠️  BUILD SKIPPED: No Dockerfile or docker-compose.yaml found")
        return True

    # Try to build using docker compose if available
    if compose_exists:
        docker_dir = (
            Path("/app/docker") if Path("/app/docker").exists() else Path("/app")
        )
        code, stdout, stderr = run_command(
            ["docker", "compose", "build", "--quiet"],
            "docker compose build",
            cwd=docker_dir,
        )
    else:
        # Try direct docker build
        code, stdout, stderr = run_command(
            ["docker", "build", "-t", "mcts-test", "."], "docker build"
        )

    if code == 0:
        print("✅ BUILD PASSED: Docker build successful")
        return True
    else:
        print("❌ BUILD FAILED: Docker build errors")
        print("📋 Use @builder-docker, @builder-cpu, or @builder-gpu agents")
        print("🔄 Or fix Dockerfile/build issues manually")
        if stdout:
            print(f"Build output:\n{stdout}")
        if stderr:
            print(f"Build errors:\n{stderr}")
        return False


def run_test_check() -> bool:
    """Run test suite."""
    print_stage_header("TESTS", "Running test suite")

    # Check for pytest
    if not check_tool_available("pytest"):
        print("⚠️  TESTS SKIPPED: pytest not found")
        return True

    # Check if tests directory exists
    test_paths = [Path("/app/tests"), Path("/app/test")]
    test_dir_exists = any(p.exists() and p.is_dir() for p in test_paths)

    if not test_dir_exists:
        print("⚠️  TESTS SKIPPED: No tests directory found")
        return True

    # Run pytest with minimal output
    code, stdout, stderr = run_command(["pytest", "-q", "--tb=short"], "pytest")

    if code == 0:
        print("✅ TESTS PASSED: All tests successful")
        if stdout:
            print(f"Test summary:\n{stdout}")
        return True
    else:
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
    print("🚀 QUALITY GATE: Starting automated quality checks")
    print("📋 Running: Format → Type Check → Build → Tests")

    # Track which checks failed
    failed_checks = []

    # 1. Format Check
    if not run_format_check():
        failed_checks.append("FORMAT")

    # 2. Type Check
    if not run_type_check():
        failed_checks.append("TYPE_CHECK")

    # 3. Build Check
    if not run_build_check():
        failed_checks.append("BUILD")

    # 4. Test Check
    if not run_test_check():
        failed_checks.append("TESTS")

    # Final result
    print(f"\n{'='*60}")

    if failed_checks:
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
        print("✅ QUALITY GATE PASSED")
        print("🎉 All checks successful: Format ✓ Type Check ✓ Build ✓ Tests ✓")
        print("💚 Code quality verified - ready for commit")
        print(f"{'='*60}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
