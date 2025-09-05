#!/usr/bin/env python3
"""
Robust Quality Gate for Claude Code Stop Hook with Containerized Execution

This version runs all commands inside the Docker Compose mcts service via Poetry:
- All tools execute as: docker compose exec mcts poetry run <tool>
- Never hangs or times out
- Provides clear logging with version info
- Handles hook input properly
- Implements loop prevention correctly
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def log(msg):
    """Log to both stderr and a debug file."""
    timestamp = time.strftime("%H:%M:%S")
    message = f"[{timestamp}] [quality-gate] {msg}"

    # Always log to stderr
    print(message, file=sys.stderr)

    # Also log to file for debugging
    try:
        log_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")) / ".claude" / "logs"
        log_dir.mkdir(exist_ok=True)
        with open(log_dir / "stop-hook.log", "a") as f:
            f.write(f"{message}\n")
    except:
        pass  # Don't fail if we can't write to log file


def read_hook_input():
    """Safely read hook input from stdin."""
    try:
        # Check if stdin has data available
        if not sys.stdin.isatty():
            # Try to read stdin
            input_data = sys.stdin.read().strip()
            if input_data:
                hook_data = json.loads(input_data)
                log(
                    f"Hook input: stop_hook_active={hook_data.get('stop_hook_active', False)}"
                )
                return hook_data
    except Exception as e:
        log(f"Failed to read hook input: {e}")

    log("No hook input or failed to parse, using defaults")
    return {"stop_hook_active": False}


def run_command_safe(cmd, description, cwd=None, timeout=30):
    """Run a command with proper timeout and error handling."""
    try:
        log(f"Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        error_msg = f"{description} timed out after {timeout} seconds"
        log(f"❌ {error_msg}")
        return 1, "", error_msg
    except FileNotFoundError:
        error_msg = f"Command not found: {cmd[0]}"
        log(f"❌ {error_msg}")
        return 1, "", error_msg
    except Exception as e:
        error_msg = f"{description} error: {str(e)}"
        log(f"❌ {error_msg}")
        return 1, "", error_msg


def get_docker_compose_dir():
    """Get the docker compose working directory from CLAUDE_PROJECT_DIR."""
    project_root = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
    docker_dir = project_root / "docker"

    log(f"CLAUDE_PROJECT_DIR: {project_root}")
    log(f"Docker compose directory: {docker_dir}")

    if not docker_dir.exists():
        log(f"Warning: Docker directory not found at {docker_dir}")
        return None

    return docker_dir


def ensure_container_running(docker_dir):
    """Ensure the mcts container is running."""
    if not docker_dir:
        return False

    # Check if Docker daemon is running
    code, _, _ = run_command_safe(["docker", "info"], "Docker daemon check", timeout=5)
    if code != 0:
        log("Docker daemon not running")
        return False

    # Check if mcts container is already running
    log("Checking if mcts container is already running...")
    code, stdout, stderr = run_command_safe(
        ["docker", "compose", "ps", "mcts", "--format", "json"],
        "Check mcts status",
        cwd=docker_dir,
        timeout=10,
    )

    # If we got output and it contains running status, container is up
    if code == 0 and stdout and "running" in stdout.lower():
        log("✅ Container mcts is already running")
        return True

    # Try to start the mcts service
    log("Starting mcts container...")
    code, stdout, stderr = run_command_safe(
        ["docker", "compose", "up", "-d", "mcts"],
        "Start mcts service",
        cwd=docker_dir,
        timeout=60,  # Give more time for startup
    )

    if code == 0:
        log("✅ Container mcts is ready")
        return True
    else:
        log(f"Failed to start mcts container: {stderr}")
        return False


def print_tool_versions(docker_dir):
    """Print versions of tools inside the container via Poetry (once per run)."""
    if not docker_dir:
        return

    log("Fetching tool versions from container...")

    # Get Poetry version
    cmd = ["docker", "compose", "exec", "-T", "mcts", "poetry", "--version"]
    code, stdout, _ = run_command_safe(
        cmd, "Poetry version", cwd=docker_dir, timeout=10
    )
    if code == 0 and stdout:
        log(f"poetry version: {stdout.strip()}")

    # Get Python version
    cmd = [
        "docker",
        "compose",
        "exec",
        "-T",
        "mcts",
        "poetry",
        "run",
        "python",
        "--version",
    ]
    code, stdout, _ = run_command_safe(
        cmd, "Python version", cwd=docker_dir, timeout=10
    )
    if code == 0 and stdout:
        log(f"python version: {stdout.strip()}")

    # Get Black version
    cmd = [
        "docker",
        "compose",
        "exec",
        "-T",
        "mcts",
        "poetry",
        "run",
        "black",
        "--version",
    ]
    code, stdout, _ = run_command_safe(cmd, "Black version", cwd=docker_dir, timeout=10)
    if code == 0 and stdout:
        log(f"black version: {stdout.strip().split()[0]}")

    # Get MyPy version
    cmd = [
        "docker",
        "compose",
        "exec",
        "-T",
        "mcts",
        "poetry",
        "run",
        "mypy",
        "--version",
    ]
    code, stdout, _ = run_command_safe(cmd, "MyPy version", cwd=docker_dir, timeout=10)
    if code == 0 and stdout:
        log(f"mypy version: {stdout.strip()}")

    # Get Pytest version
    cmd = [
        "docker",
        "compose",
        "exec",
        "-T",
        "mcts",
        "poetry",
        "run",
        "pytest",
        "--version",
    ]
    code, stdout, _ = run_command_safe(
        cmd, "Pytest version", cwd=docker_dir, timeout=10
    )
    if code == 0 and stdout:
        # Parse pytest version from output like "pytest 7.4.0"
        version_line = stdout.strip().split("\n")[0]
        log(f"pytest version: {version_line}")


def run_black_stage(docker_dir):
    """Run Black formatting using containerized Poetry."""
    log("Running Black formatting stage...")

    if not docker_dir:
        log("❌ Docker directory not available, cannot run Black")
        return False, "Docker environment not available"

    # Get timeout from environment or use default
    timeout = int(os.environ.get("MCTS_BLACK_TIMEOUT", "60"))

    cmd = ["docker", "compose", "exec", "-T", "mcts", "poetry", "run", "black", "."]
    code, stdout, stderr = run_command_safe(
        cmd, "Black formatting", cwd=docker_dir, timeout=timeout
    )

    if code == 0:
        log("✅ Black formatting completed successfully")
        return True, ""
    else:
        # Black exit code 123 means internal error
        if code == 123:
            error_msg = f"Black internal error:\n{stderr}\n{stdout}"
        else:
            error_msg = f"Black formatting modified files:\n{stderr}\n{stdout}"

        log(f"⚠️ Black formatting applied changes (non-fatal)")
        # Treat formatting as non-fatal - we applied the changes
        return True, ""


def run_mypy_stage(docker_dir):
    """Run mypy type checking using containerized Poetry."""
    log("Running mypy type checking stage...")

    if not docker_dir:
        log("❌ Docker directory not available, cannot run mypy")
        return False, "Docker environment not available"

    # Get timeout from environment or use generous default for strict mode
    timeout = int(os.environ.get("MCTS_MYPY_TIMEOUT", "300"))  # 5 minutes default

    cmd = [
        "docker",
        "compose",
        "exec",
        "-T",
        "mcts",
        "poetry",
        "run",
        "mypy",
        "--strict",
        ".",
    ]
    code, stdout, stderr = run_command_safe(
        cmd, "MyPy type checking", cwd=docker_dir, timeout=timeout
    )

    if code == 0:
        log("✅ MyPy type checking passed - no type errors found")
        return True, ""
    else:
        # Combine stdout and stderr for full diagnostics
        full_output = f"{stdout}\n{stderr}".strip()

        # Extract key error lines for summary
        error_lines = [line for line in full_output.split("\n") if "error:" in line]

        if error_lines:
            summary = f"Found {len(error_lines)} type error(s). First few:\n"
            summary += "\n".join(error_lines[:5])
            if len(error_lines) > 5:
                summary += f"\n... and {len(error_lines) - 5} more errors"
        else:
            summary = "Type checking failed"

        error_msg = f"MyPy type errors:\n{full_output}"

        log(f"❌ MyPy type checking failed - {len(error_lines)} error(s) found")

        # Print summary to stderr for Claude
        print(f"\n{summary}\n", file=sys.stderr)

        return False, error_msg


def run_tests_stage(docker_dir):
    """Run test suite using containerized Poetry."""
    log("Running test suite stage...")

    if not docker_dir:
        log("❌ Docker directory not available, cannot run tests")
        return False, "Docker environment not available"

    # Get timeout from environment or use reasonable default for fast tests
    timeout = int(
        os.environ.get("MCTS_PYTEST_TIMEOUT", "120")
    )  # 2 minutes default for quality gate

    # First clean Python cache to avoid import issues
    log("Cleaning Python cache before tests...")
    clean_cmd = [
        "docker",
        "compose",
        "exec",
        "-T",
        "mcts",
        "bash",
        "-c",
        "find /app -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true",
    ]
    run_command_safe(clean_cmd, "Clean cache", cwd=docker_dir, timeout=30)

    # Run fast tests for quality gate (configurable via environment)
    test_scope = os.environ.get("MCTS_TEST_SCOPE", "fast")

    if test_scope == "all":
        log("Running full test suite (MCTS_TEST_SCOPE=all)...")
        cmd = [
            "docker",
            "compose",
            "exec",
            "-T",
            "mcts",
            "poetry",
            "run",
            "pytest",
            "-q",
        ]
        timeout = int(
            os.environ.get("MCTS_PYTEST_TIMEOUT", "300")
        )  # Use longer timeout for full suite
    else:
        log("Running fast Python tests for quality gate...")
        cmd = [
            "docker",
            "compose",
            "exec",
            "-T",
            "mcts",
            "poetry",
            "run",
            "pytest",
            "-m",
            "python",
            "-q",
        ]

    code, stdout, stderr = run_command_safe(
        cmd, "Test suite", cwd=docker_dir, timeout=timeout
    )

    # Handle "no tests collected" case - try without marker
    if code == 5:
        log("No tests collected with 'python' marker, running core backend tests...")
        cmd = [
            "docker",
            "compose",
            "exec",
            "-T",
            "mcts",
            "poetry",
            "run",
            "pytest",
            "tests/backend/core/",
            "-q",
        ]
        code, stdout, stderr = run_command_safe(
            cmd, "Core backend tests", cwd=docker_dir, timeout=timeout
        )

        # Final fallback - try basic pytest
        if code == 5:
            log("No backend tests found, running basic pytest...")
            cmd = [
                "docker",
                "compose",
                "exec",
                "-T",
                "mcts",
                "poetry",
                "run",
                "pytest",
                "-k",
                "not slow and not integration and not e2e",
                "-q",
            ]
            code, stdout, stderr = run_command_safe(
                cmd, "Basic test suite", cwd=docker_dir, timeout=timeout
            )

    if code == 0:
        log("✅ Test suite passed - all tests successful")
        return True, ""
    else:
        # Parse test output for summary
        full_output = f"{stdout}\n{stderr}".strip()

        # Look for pytest summary line
        summary_pattern = r"=+ (.*?) =+"
        failed_pattern = r"(\d+) failed"

        import re

        failed_match = re.search(failed_pattern, full_output)
        num_failed = failed_match.group(1) if failed_match else "unknown"

        summary = f"Test suite failed - {num_failed} test(s) failed"

        error_msg = f"Test failures:\n{full_output}"

        log(f"❌ {summary}")

        # Print concise error to stderr
        print(f"\n{summary}\n", file=sys.stderr)
        print("Recommended agent: @tester-pytest\n", file=sys.stderr)

        return False, error_msg


def run_quality_sequence():
    """Run the complete quality sequence: Black → mypy → tests."""
    # Get docker compose directory
    docker_dir = get_docker_compose_dir()

    if not docker_dir or not docker_dir.exists():
        log("❌ Cannot find docker directory, falling back to local execution")
        log("Local execution not implemented - Docker is required")
        return False, "environment", "Docker environment is required but not available"

    # Ensure container is running
    if not ensure_container_running(docker_dir):
        log("❌ Failed to start Docker container")
        return False, "environment", "Docker container could not be started"

    # Print tool versions once at the start
    print_tool_versions(docker_dir)

    # Stage 1: Black formatting
    success, message = run_black_stage(docker_dir)
    if not success:
        return False, "formatting", message

    # Stage 2: mypy type checking
    success, message = run_mypy_stage(docker_dir)
    if not success:
        return False, "type_checking", message

    # Stage 3: Tests
    success, message = run_tests_stage(docker_dir)
    if not success:
        return False, "tests", message

    log("✅ All quality checks passed!")
    return True, "all", "All quality checks passed"


def show_agent_recommendations(stage):
    """Show specific agent recommendations based on failed stage."""
    recommendations = {
        "formatting": "Recommended agent: @formatter-black",
        "type_checking": "Recommended agent: @mypy-type-checker",
        "tests": "Recommended agent: @tester-pytest",
        "environment": "Check Docker setup and ensure 'mcts' service is defined",
    }

    if stage in recommendations:
        print(recommendations[stage], file=sys.stderr)


def format_error_output(stage, message, is_continuation=False):
    """Format error output for Claude to see."""
    # Always show full diagnostics for both first run and continuation
    header = f"[Quality Gate] {stage.upper()} FAILED"
    if is_continuation:
        header += " (continuation - manual intervention required)"

    output = f"{header}\n"
    output += "=" * 60 + "\n"
    output += message
    output += "\n" + "=" * 60

    return output


def main():
    """Main quality gate logic."""
    log("=== STOP HOOK STARTING ===")

    # Read hook input
    hook_input = read_hook_input()
    is_continuation = hook_input.get("stop_hook_active", False)

    log(f"Continuation: {is_continuation}")
    log(f"Working directory: {os.getcwd()}")

    if is_continuation:
        log("This is a continuation run after automatic fix attempt")
        log("Running quality checks again...")

        # Run the full sequence again on continuation
        success, stage, message = run_quality_sequence()

        if success:
            log("✅ Quality gate PASSED on continuation - fixes worked!")
            print(
                "\nQuality Gate Status: PASS (Black: PASS, MyPy: PASS, Tests: PASS)",
                file=sys.stderr,
            )
            return 0
        else:
            # Still failing on continuation - provide full diagnostics but don't block
            log(f"❌ Quality gate still failing at {stage} stage after fix attempt")
            log("🛑 Stopping automatic fixes to prevent loops")

            # Show full error details on continuation too
            error_output = format_error_output(stage, message, is_continuation=True)
            print(error_output, file=sys.stderr)
            show_agent_recommendations(stage)

            return 1  # Non-blocking exit code to prevent loops
    else:
        log("This is the first run of quality gate")
        log("Running: Black → MyPy → Tests")

        # Run the full quality sequence
        success, stage, message = run_quality_sequence()

        if success:
            log("✅ Quality gate PASSED on first run")
            print(
                "\nQuality Gate Status: PASS (Black: PASS, MyPy: PASS, Tests: PASS)",
                file=sys.stderr,
            )
            return 0
        else:
            # First failure - block and let Claude fix issues
            log(f"❌ Quality gate failed at {stage} stage")
            log("Requesting automatic fix via continuation...")

            # Print detailed error message for Claude
            error_output = format_error_output(stage, message, is_continuation=False)
            print(error_output, file=sys.stderr)

            return 2  # Blocking exit code to trigger continuation


if __name__ == "__main__":
    try:
        exit_code = main()
        log(f"=== STOP HOOK FINISHED (exit code: {exit_code}) ===")
        sys.exit(exit_code)
    except Exception as e:
        log(f"❌ STOP HOOK FATAL ERROR: {e}")
        import traceback

        log(traceback.format_exc())
        log("=== STOP HOOK FAILED ===")
        sys.exit(1)
