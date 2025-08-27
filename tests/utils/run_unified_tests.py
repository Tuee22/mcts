#!/usr/bin/env python3
"""
Unified test runner that runs all tests in the correct order: Python → Frontend → E2E.
Ensures services are properly started before E2E tests.
"""
import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


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
                        time.sleep(0.5)  # Give it time to terminate
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass


def ensure_ports_free() -> None:
    """Ensure required ports are free before starting services."""
    ports = [8002, 3002]  # E2E test ports
    for port in ports:
        find_and_kill_process(port)


def run_command(
    cmd: List[str],
    description: str,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
) -> bool:
    """Run a command and handle output."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    if cwd:
        print(f"Working directory: {cwd}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, capture_output=False, cwd=cwd, env=env)
    success = result.returncode == 0

    if success:
        print(f"\n✅ {description} completed successfully")
    else:
        print(f"\n❌ {description} failed with return code {result.returncode}")

    return success


def check_server_health(url: str, max_retries: int = 30) -> bool:
    """Check if a server is healthy."""
    import requests

    for i in range(max_retries):
        try:
            response = requests.get(url, timeout=1)
            if response.status_code == 200:
                return True
        except Exception:
            pass
        if i < max_retries - 1:
            time.sleep(0.5)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run all MCTS tests: Python → Frontend → E2E tests"
    )
    parser.add_argument(
        "--skip-python", action="store_true", help="Skip Python unit/integration tests"
    )
    parser.add_argument(
        "--skip-frontend", action="store_true", help="Skip frontend tests"
    )
    parser.add_argument("--skip-e2e", action="store_true", help="Skip E2E tests")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--headed", action="store_true", help="Run E2E with visible browser"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug output")

    args = parser.parse_args()

    # Get project root
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)

    success = True

    # Run Python tests
    if not args.skip_python:
        print("🐍 Running Python tests...")

        # Run Core tests first
        core_cmd = ["pytest", "tests/backend/core/", "-m", "not e2e"]
        if args.verbose:
            core_cmd.append("-v")
        if args.coverage:
            core_cmd.extend(
                [
                    "--cov=backend.python",
                    "--cov-report=html:htmlcov-core",
                    "--cov-report=term-missing",
                ]
            )

        core_success = run_command(core_cmd, "Python Core Tests")

        # Run API tests
        api_cmd = ["pytest", "tests/backend/api/", "-m", "not e2e"]
        if args.verbose:
            api_cmd.append("-v")
        if args.coverage:
            api_cmd.extend(
                [
                    "--cov=backend.api",
                    "--cov-report=html:htmlcov-api",
                    "--cov-report=term-missing",
                ]
            )

        api_success = run_command(api_cmd, "Python API Tests")
        success = success and core_success and api_success

    # Run Frontend tests
    if not args.skip_frontend and (project_root / "frontend").exists():
        print("\n⚛️  Running Frontend tests...")

        frontend_cmd = ["npm", "test", "--", "--watchAll=false"]
        if args.coverage:
            frontend_cmd.extend(["--coverage"])

        frontend_success = run_command(
            frontend_cmd, "Frontend Tests", cwd=str(project_root / "frontend")
        )
        success = success and frontend_success

    # Run E2E tests
    if not args.skip_e2e:
        print("\n🌐 Running E2E tests with Playwright...")

        # Use our dedicated E2E test runner
        e2e_cmd = ["python", "tests/utils/run_e2e_tests.py"]
        if args.verbose:
            e2e_cmd.append("--verbose")
        if args.headed:
            e2e_cmd.append("--headed")
        if args.debug:
            e2e_cmd.append("--debug")

        e2e_success = run_command(e2e_cmd, "E2E Tests")
        success = success and e2e_success

    # Final summary
    print(f"\n{'='*60}")
    if success:
        print("🎉 All tests passed!")
        if not args.skip_python:
            print("✅ Python tests: PASSED")
        if not args.skip_frontend:
            print("✅ Frontend tests: PASSED")
        if not args.skip_e2e:
            print("✅ E2E tests: PASSED")
    else:
        print("💥 Some tests failed!")
        print("Check the output above for details.")
    print(f"{'='*60}")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
