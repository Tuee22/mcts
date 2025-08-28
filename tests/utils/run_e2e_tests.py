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


def start_backend_server() -> "subprocess.Popen[bytes]":
    """Start backend server for E2E tests."""
    env = os.environ.copy()
    env.update(
        {
            "MCTS_API_HOST": "0.0.0.0",
            "MCTS_API_PORT": "8002",
            "MCTS_CORS_ORIGINS": "*",
        }
    )

    process: subprocess.Popen[bytes] = subprocess.Popen(
        [
            "python",
            "-m",
            "uvicorn",
            "backend.api.server:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8002",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to be ready
    if not check_server_health("http://localhost:8002/health"):
        process.terminate()
        raise RuntimeError("Backend server failed to start for E2E tests")

    print("✅ Backend server started on port 8002")
    return process


def start_frontend_server() -> "subprocess.Popen[bytes]":
    """Start frontend server for E2E tests."""
    # Build frontend if not already built
    if not os.path.exists("frontend/build"):
        print("📦 Building frontend...")
        result = subprocess.run(["npm", "run", "build"], cwd="frontend", check=True)
        if result.returncode != 0:
            raise RuntimeError("Frontend build failed")

    env = os.environ.copy()
    env.update(
        {
            "REACT_APP_API_URL": "http://localhost:8002",
            "REACT_APP_WS_URL": "ws://localhost:8002/ws",
        }
    )

    process: subprocess.Popen[bytes] = subprocess.Popen(
        ["npx", "serve", "-s", "build", "-l", "3002"],
        cwd="frontend",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to be ready
    if not check_server_health("http://localhost:3002"):
        process.terminate()
        raise RuntimeError("Frontend server failed to start for E2E tests")

    print("✅ Frontend server started on port 3002")
    return process


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

    # Ensure ports are free before starting E2E tests
    ensure_ports_free()
    time.sleep(1)  # Give ports time to be freed

    # Start backend and frontend servers
    backend_process = None
    frontend_process = None

    try:
        print("🚀 Starting backend server...")
        backend_process = start_backend_server()

        print("🚀 Starting frontend server...")
        frontend_process = start_frontend_server()

        # Set up environment for E2E tests
        env = os.environ.copy()
        env["E2E_BACKEND_URL"] = "http://localhost:8002"
        env["E2E_FRONTEND_URL"] = "http://localhost:3002"
        env["E2E_WS_URL"] = "ws://localhost:8002/ws"

        if args.headed:
            env["E2E_HEADLESS"] = "false"
        if args.debug:
            env["PWDEBUG"] = "1"

        # Run ALL E2E tests
        e2e_cmd = [
            "pytest",
            "tests/e2e/",
            "-v",
        ]

        if args.verbose:
            e2e_cmd.append("-s")  # Add -s for verbose output since -v is already there

        success = run_command(e2e_cmd, "E2E Tests", env=env)

    finally:
        # Clean up servers
        print("\n🧹 Cleaning up servers...")
        if backend_process:
            backend_process.terminate()
            backend_process.wait(timeout=5)
        if frontend_process:
            frontend_process.terminate()
            frontend_process.wait(timeout=5)

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
