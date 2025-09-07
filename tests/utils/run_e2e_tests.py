#!/usr/bin/env python3
"""
E2E test runner for Playwright browser tests.
"""
import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

import requests


def find_and_kill_process(port: int) -> None:
    """Find and kill any process using the given port."""
    if not PSUTIL_AVAILABLE:
        return

    for proc in psutil.process_iter(["pid", "name", "connections"]):
        try:
            connections = proc.info.get("connections")
            if connections and isinstance(connections, list):
                for conn in connections:
                    if hasattr(conn, "laddr") and conn.laddr.port == port:
                        pid = proc.info["pid"]
                        if isinstance(pid, int):
                            print(f"Killing process {pid} using port {port}")
                            os.kill(pid, signal.SIGTERM)
                        time.sleep(0.5)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass


def ensure_ports_free() -> None:
    """Ensure required ports are free before starting services."""
    ports = [8002, 3002]  # E2E test ports
    for port in ports:
        find_and_kill_process(port)


def check_server_health(url: str, max_retries: int = 30) -> bool:
    """Check if a server is healthy."""
    for i in range(max_retries):
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                return True
        except Exception:
            pass
        if i < max_retries - 1:
            time.sleep(1)
    return False


def check_docker_container_health() -> bool:
    """Check if Docker container is running and healthy."""
    try:
        # Check if docker compose service is running
        result = subprocess.run(
            ["docker", "compose", "ps", "--services", "--filter", "status=running"],
            cwd="../docker",
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0 or not result.stdout or "mcts" not in result.stdout:
            print("❌ Docker container not running, starting it...")
            # Start the container
            start_result = subprocess.run(
                ["docker", "compose", "up", "-d"], cwd="../docker", timeout=60
            )
            if start_result.returncode != 0:
                return False

            # Wait a bit for container to fully start
            time.sleep(5)

        # Check if the server is healthy
        if not check_server_health("http://localhost:8000/health"):
            return False

        print("✅ Docker container is running and healthy on port 8000")
        return True

    except Exception as e:
        print(f"❌ Failed to check/start Docker container: {e}")
        return False


def run_command(
    cmd: list[str], description: str, env: dict[str, str] | None = None
) -> bool:
    """Run a command and handle output."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, capture_output=False, env=env)
    success = result.returncode == 0

    if success:
        print(f"\n✅ {description} completed successfully")
    else:
        print(f"\n❌ {description} failed with return code {result.returncode}")

    return success


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run E2E tests with Playwright across all browsers"
    )
    parser.add_argument(
        "--headed", action="store_true", help="Run with visible browser"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    # Note: Browser filtering removed - our tests run all browsers in single test methods
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Get project root
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)

    print("🌐 Running E2E tests with Playwright...")

    # Clean up any leftover processes from previous test runs
    ensure_ports_free()
    time.sleep(1)  # Give ports time to be freed

    # Check Docker container health and start if needed
    try:
        print("🐳 Checking Docker container status...")
        if not check_docker_container_health():
            raise RuntimeError("Docker container failed to start or is unhealthy")

        # Set up environment for E2E tests to use Docker container
        env = os.environ.copy()
        env["E2E_BACKEND_URL"] = "http://localhost:8000"
        env["E2E_FRONTEND_URL"] = "http://localhost:8000"
        env["E2E_WS_URL"] = "ws://localhost:8000/ws"

        if args.headed:
            env["E2E_HEADLESS"] = "false"
        if args.debug:
            env["PWDEBUG"] = "1"

        # Run ALL E2E tests against Docker container
        e2e_cmd = [
            "pytest",
            "tests/e2e/",
            "-v",
        ]

        if args.verbose:
            e2e_cmd.append("-s")  # Add -s for verbose output since -v is already there

        success = run_command(e2e_cmd, "E2E Tests", env=env)

    finally:
        # Docker container continues running for other uses
        print("\n✅ Docker container remains running for continued use")

    # Final summary
    print(f"\n{'='*60}")
    if success:
        print("🎉 E2E tests passed!")
        print("✅ E2E tests (all browsers): PASSED")
    else:
        print("💥 E2E tests failed!")
        print("Check the output above for details.")
    print(f"{'='*60}")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
