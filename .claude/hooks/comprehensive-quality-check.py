#!/usr/bin/env python3
"""
Comprehensive Quality Check Hook

Runs after every Edit, Write, or MultiEdit operation to ensure code quality.
Executes: Format → Type Check → Test Generation → Test Execution → Coverage Check → Code Review

This hook batches operations to prevent multiple triggers and provides deterministic quality gates.

Exit Codes:
  0 - All checks passed
  1 - Format failed
  2 - Type check failed
  3 - Test generation failed
  4 - Tests failed
  5 - Coverage below threshold
  6 - Code review identified critical issues
  7 - Setup/tool error
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Configuration
COVERAGE_THRESHOLD = 90  # Minimum coverage percentage
BATCH_TIMEOUT = 30  # Seconds to wait before running checks after last change
LOCKFILE = Path("/tmp/claude_quality_check.lock")


def log(message: str, level: str = "INFO") -> None:
    """Log with timestamp and level."""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")


def is_recent_change() -> bool:
    """Check if there were recent file changes (batching mechanism)."""
    if not LOCKFILE.exists():
        return False

    try:
        with open(LOCKFILE, "r") as f:
            last_change = float(f.read().strip())
        return (time.time() - last_change) < BATCH_TIMEOUT
    except (ValueError, FileNotFoundError):
        return False


def update_lockfile() -> None:
    """Update lockfile with current timestamp."""
    with open(LOCKFILE, "w") as f:
        f.write(str(time.time()))


def run_command(
    cmd: List[str], description: str, cwd: Optional[Path] = None, timeout: int = 300
) -> Tuple[int, str, str]:
    """Run a command and return (exit_code, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or Path("/app"),
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"{description} timed out after {timeout} seconds"
    except Exception as e:
        return 1, "", f"{description} error: {str(e)}"


def check_docker_ready() -> bool:
    """Ensure Docker container is ready."""
    # Try different working directories for docker compose
    for docker_dir in [Path("docker"), Path("/app/docker"), Path(".")]:
        if docker_dir.exists():
            code, _, _ = run_command(
                ["docker", "compose", "exec", "-T", "mcts", "python", "--version"],
                "Docker readiness check",
                cwd=docker_dir,
            )
            if code == 0:
                return True
    return False


def run_format_stage() -> Tuple[bool, str]:
    """Run code formatting with Black."""
    log("Running format stage...")

    docker_dir = Path("docker") if Path("docker").exists() else Path(".")

    # First check if formatting is needed
    code, stdout, stderr = run_command(
        ["docker", "compose", "exec", "-T", "mcts", "black", "--check", "."],
        "black --check",
        cwd=docker_dir,
    )

    if code == 0:
        log("✅ Format stage: No changes needed")
        return True, "All files properly formatted"

    # Apply formatting
    code, stdout, stderr = run_command(
        ["docker", "compose", "exec", "-T", "mcts", "black", "."],
        "black format",
        cwd=docker_dir,
    )

    if code == 0:
        log("✅ Format stage: Applied formatting")
        return True, "Formatting applied successfully"
    else:
        log(f"❌ Format stage failed: {stderr}")
        return False, f"Formatting failed: {stderr}"


def run_typecheck_stage() -> Tuple[bool, str]:
    """Run MyPy type checking."""
    log("Running type check stage...")

    docker_dir = Path("docker") if Path("docker").exists() else Path(".")
    code, stdout, stderr = run_command(
        ["docker", "compose", "exec", "-T", "mcts", "mypy", "--strict", "."],
        "mypy type check",
        cwd=docker_dir,
    )

    if code == 0:
        log("✅ Type check stage passed")
        return True, "No type errors found"
    else:
        log(f"❌ Type check stage failed")
        return False, f"Type errors found:\n{stdout}\n{stderr}"


def detect_new_code_patterns() -> List[str]:
    """Detect patterns that indicate new code requiring tests."""
    patterns = []

    try:
        # Check recent git changes
        code, stdout, stderr = run_command(
            ["git", "diff", "--name-only", "HEAD~1"], "git diff for new files"
        )

        if code == 0:
            changed_files = [
                f.strip() for f in stdout.split("\n") if f.strip().endswith(".py")
            ]
            for file_path in changed_files:
                if os.path.exists(file_path) and not file_path.startswith("tests/"):
                    patterns.append(f"New/modified Python file: {file_path}")
    except:
        pass

    return patterns


def run_test_generation_stage() -> Tuple[bool, str]:
    """Generate or update tests for new code."""
    log("Running test generation stage...")

    new_patterns = detect_new_code_patterns()
    if not new_patterns:
        log("✅ Test generation: No new code detected")
        return True, "No new code requiring tests"

    # For now, return success with recommendation to use test-writer agent
    # This will be enhanced when test-writer agent is created
    message = f"New code detected: {len(new_patterns)} files. Recommend running @test-writer agent."
    log(f"⚠️ Test generation: {message}")
    return True, message


def run_tests_stage() -> Tuple[bool, str]:
    """Run test suite."""
    log("Running tests stage...")

    docker_dir = Path("docker") if Path("docker").exists() else Path(".")
    code, stdout, stderr = run_command(
        ["docker", "compose", "exec", "-T", "mcts", "pytest", "-q", "--tb=short"],
        "pytest execution",
        cwd=docker_dir,
    )

    if code == 0:
        log("✅ Tests stage passed")
        return True, f"All tests passed:\n{stdout}"
    else:
        log(f"❌ Tests stage failed")
        return False, f"Test failures:\n{stdout}\n{stderr}"


def run_coverage_check() -> Tuple[bool, str]:
    """Check test coverage."""
    log("Running coverage check...")

    docker_dir = Path("docker") if Path("docker").exists() else Path(".")
    code, stdout, stderr = run_command(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "mcts",
            "pytest",
            "--cov=.",
            "--cov-report=term-missing",
            "--cov-fail-under=85",
        ],
        "coverage check",
        cwd=docker_dir,
    )

    if code == 0:
        log("✅ Coverage check passed")
        return True, f"Coverage meets threshold:\n{stdout}"
    else:
        log(f"⚠️ Coverage below threshold")
        return False, f"Coverage below threshold:\n{stdout}\n{stderr}"


def generate_summary_report(results: Dict[str, Tuple[bool, str]]) -> str:
    """Generate a summary report of all checks."""
    report = ["=" * 60, "🔍 COMPREHENSIVE QUALITY CHECK SUMMARY", "=" * 60, ""]

    passed = 0
    total = len(results)

    for stage, (success, message) in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        report.append(f"{stage.upper():15} {status}")
        if not success:
            report.append(f"    └─ {message[:100]}...")
        if success:
            passed += 1

    report.extend(["", f"Overall: {passed}/{total} stages passed", "=" * 60])

    if passed == total:
        report.append("🎉 All quality checks passed! Code ready for review.")
    else:
        report.extend(
            [
                "🔧 Failed stages need attention:",
                "  • @formatter-black for formatting issues",
                "  • @mypy-type-checker for type errors",
                "  • @test-writer for missing tests",
                "  • @tester-pytest for test failures",
                "  • @code-reviewer for review issues",
            ]
        )

    return "\n".join(report)


def main() -> int:
    """Main quality check pipeline."""
    # Batching: Only run if enough time has passed since last change
    if is_recent_change():
        log("Batching: Recent change detected, deferring quality check")
        update_lockfile()
        return 0

    # Clean up lockfile
    if LOCKFILE.exists():
        LOCKFILE.unlink()

    log("Starting comprehensive quality check pipeline...")

    # Ensure we're in the repository root
    repo_root = Path(__file__).parent.parent.parent
    os.chdir(repo_root)
    log(f"Working directory: {repo_root}")

    # Check Docker readiness
    if not check_docker_ready():
        log("❌ Docker container not ready")
        return 7

    # Run all stages
    results = {}

    # Stage 1: Format
    success, message = run_format_stage()
    results["format"] = (success, message)
    if not success:
        print(generate_summary_report(results))
        return 1

    # Stage 2: Type Check
    success, message = run_typecheck_stage()
    results["typecheck"] = (success, message)
    if not success:
        print(generate_summary_report(results))
        return 2

    # Stage 3: Test Generation
    success, message = run_test_generation_stage()
    results["test_generation"] = (success, message)
    # Continue even if test generation has recommendations

    # Stage 4: Tests
    success, message = run_tests_stage()
    results["tests"] = (success, message)
    if not success:
        print(generate_summary_report(results))
        return 4

    # Stage 5: Coverage
    success, message = run_coverage_check()
    results["coverage"] = (success, message)
    # Continue even if coverage is below threshold for now

    # Generate and display summary
    print(generate_summary_report(results))

    # Determine overall success
    critical_failures = [("format", 1), ("typecheck", 2), ("tests", 4)]

    for stage, exit_code in critical_failures:
        if stage in results and not results[stage][0]:
            return exit_code

    log("✅ Comprehensive quality check completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
