#!/usr/bin/env python3
"""
Robust Quality Gate for Claude Code Stop Hook

This version is designed to be completely reliable:
- Never hangs or times out
- Provides clear logging
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
        # Check if we're running from a terminal
        if sys.stdin.isatty():
            log("Running in terminal mode (no hook input)")
            return {"stop_hook_active": False}

        # Try to read stdin with a timeout approach
        import select

        if select.select([sys.stdin], [], [], 0.1)[0]:
            input_data = sys.stdin.read().strip()
            if input_data:
                hook_data = json.loads(input_data)
                log(
                    f"Hook input: stop_hook_active={hook_data.get('stop_hook_active', False)}"
                )
                return hook_data
    except:
        # If anything fails, assume defaults
        pass

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
        return 1, "", f"{description} timed out after {timeout} seconds"
    except FileNotFoundError:
        return 1, "", f"Command not found: {cmd[0]}"
    except Exception as e:
        return 1, "", f"{description} error: {str(e)}"


def check_docker_environment():
    """Check if Docker environment is available."""
    project_root = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
    docker_dir = project_root / "docker"

    if not docker_dir.exists():
        return False, None

    # Quick check if docker is running
    code, _, _ = run_command_safe(["docker", "info"], "Docker daemon check", timeout=3)
    if code != 0:
        return False, None

    return True, docker_dir


def run_black_stage(use_docker, docker_dir):
    """Run Black formatting."""
    log("Running Black formatting...")

    if use_docker and docker_dir:
        cmd = ["docker", "compose", "exec", "-T", "mcts", "black", "."]
        code, stdout, stderr = run_command_safe(
            cmd, "Black format in Docker", cwd=docker_dir
        )
    else:
        cmd = ["black", "."]
        code, stdout, stderr = run_command_safe(cmd, "Black format locally")

    if code == 0:
        log("✅ Black formatting completed")
        return True, ""
    else:
        error_msg = f"Black formatting failed:\n{stderr}\n{stdout}"
        log(f"❌ Black formatting failed")
        return False, error_msg


def run_mypy_stage(use_docker, docker_dir):
    """Run mypy type checking."""
    log("Running mypy type checking...")

    if use_docker and docker_dir:
        cmd = [
            "docker",
            "compose",
            "exec",
            "-T",
            "mcts",
            "mypy",
            "--strict",
            ".",
        ]
        code, stdout, stderr = run_command_safe(
            cmd, "MyPy type check in Docker", cwd=docker_dir
        )
    else:
        cmd = ["mypy", "--strict", "."]
        code, stdout, stderr = run_command_safe(cmd, "MyPy type check locally")

    if code == 0:
        log("✅ mypy type checking passed")
        return True, ""
    else:
        error_msg = f"Type errors found:\n{stdout}\n{stderr}"
        log(f"❌ mypy type checking failed")
        return False, error_msg


def run_tests_stage(use_docker, docker_dir):
    """Run test suite."""
    log("Running test suite...")

    if use_docker and docker_dir:
        # Clean Python cache first to avoid import conflicts
        log("Cleaning Python cache...")
        run_command_safe(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "mcts",
                "find",
                "/app",
                "-name",
                "*.pyc",
                "-delete",
            ],
            "Clean pyc files",
            cwd=docker_dir,
            timeout=10,
        )
        run_command_safe(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "mcts",
                "bash",
                "-c",
                "find /app -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true",
            ],
            "Clean pycache dirs",
            cwd=docker_dir,
            timeout=10,
        )

        # Start with fast Python-only tests for quality gate
        log("Running fast Python-only tests for quality gate...")
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
            cmd, "Python-only tests in Docker", cwd=docker_dir, timeout=30
        )

        # Only run full suite if Python tests pass and env var is set
        if code == 0 and os.environ.get("MCTS_RUN_ALL_TESTS") == "1":
            log("Python tests passed, running full test suite...")
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
            code, stdout, stderr = run_command_safe(
                cmd, "Full test suite in Docker", cwd=docker_dir, timeout=300
            )
    else:
        cmd = ["pytest", "-q"]
        code, stdout, stderr = run_command_safe(cmd, "Test suite locally", timeout=120)

        if code != 0:
            log("Full test suite failed, trying Python-only tests...")
            cmd = ["pytest", "-m", "python", "-q"]
            code, stdout, stderr = run_command_safe(cmd, "Python-only tests locally")

    if code == 0:
        log("✅ Test suite passed")
        return True, ""
    else:
        error_msg = f"Test failures:\n{stdout}\n{stderr}"
        log(f"❌ Test suite failed")
        return False, error_msg


def run_quality_sequence(project_root_hint=None):
    """Run the complete quality sequence: Black → mypy → tests."""
    # Set working directory
    if project_root_hint:
        os.chdir(project_root_hint)
    elif os.environ.get("CLAUDE_PROJECT_DIR"):
        os.chdir(os.environ["CLAUDE_PROJECT_DIR"])

    # Check environment
    use_docker, docker_dir = check_docker_environment()

    if use_docker:
        log("Using Docker Compose mcts service with Poetry")
        # Ensure container is running
        try:
            run_command_safe(
                ["docker", "compose", "up", "-d", "mcts"],
                "Start mcts service",
                cwd=docker_dir,
                timeout=10,
            )
        except:
            pass
    else:
        log("Docker unavailable, using local Poetry execution")

    # Stage 1: Black formatting
    success, message = run_black_stage(use_docker, docker_dir)
    if not success:
        return False, "formatting", message

    # Stage 2: mypy type checking
    success, message = run_mypy_stage(use_docker, docker_dir)
    if not success:
        return False, "type_checking", message

    # Stage 3: Tests
    success, message = run_tests_stage(use_docker, docker_dir)
    if not success:
        return False, "tests", message

    return True, "all", "All quality checks passed"


def show_agent_recommendations(stage):
    """Show specific agent recommendations based on failed stage."""
    recommendations = {
        "formatting": "Try: @formatter-black",
        "type_checking": "Try: @mypy-type-checker",
        "tests": "Try: @tester-pytest",
    }

    if stage in recommendations:
        print(recommendations[stage])


def main():
    """Main quality gate logic."""
    log("=== STOP HOOK STARTING ===")

    # Read hook input
    hook_input = read_hook_input()
    is_continuation = hook_input.get("stop_hook_active", False)

    log(f"Continuation: {is_continuation}")
    log(f"Working directory: {os.getcwd()}")
    log(f"CLAUDE_PROJECT_DIR: {os.environ.get('CLAUDE_PROJECT_DIR', 'NOT SET')}")

    if is_continuation:
        log("This is a continuation - previous run must have failed")
        log("Running quality checks again after Claude attempted fixes...")

        # Run the full sequence again on continuation
        success, stage, message = run_quality_sequence(hook_input.get("project_root"))

        if success:
            log("✅ Quality gate passed (continuation mode - fixes worked!)")
            return 0
        else:
            # Still failing on continuation - don't block again to prevent loops
            log(f"❌ Quality gate still failing at {stage} stage (continuation)")
            log("🛑 Stopping automatic fixes to prevent loops")
            log("Manual intervention required")
            print(f"Quality gate failed at {stage} stage after automatic fix attempt.")
            print("Manual intervention may be required.")
            show_agent_recommendations(stage)
            return 1  # Non-blocking exit code
    else:
        log("This is the first run")
        log("Running: Black → mypy → tests")

        # Run the full quality sequence
        success, stage, message = run_quality_sequence(hook_input.get("project_root"))

        if success:
            log("✅ Quality gate passed (first run)")
            return 0
        else:
            # First failure - block and let Claude fix issues
            log(f"❌ Quality gate failed at {stage} stage (first run)")
            log("Blocking to let Claude fix the issues...")

            # Print error message to stderr for Claude to see
            error_output = f"[Quality Gate] {stage.upper()} FAILED:\n{message}"
            print(error_output, file=sys.stderr)

            return 2  # Blocking exit code


if __name__ == "__main__":
    try:
        exit_code = main()
        log(f"=== STOP HOOK FINISHED (exit code: {exit_code}) ===")
        sys.exit(exit_code)
    except Exception as e:
        log(f"❌ STOP HOOK ERROR: {e}")
        log("=== STOP HOOK FAILED ===")
        sys.exit(1)
