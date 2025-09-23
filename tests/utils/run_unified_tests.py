#!/usr/bin/env python
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
from typing import Dict, List, Optional, Tuple, TypedDict


class TestSuite(TypedDict):
    """Type definition for test suite configuration."""

    name: str
    path: str
    markers: str
    coverage_target: Optional[str]
    skip_flag: bool
    emoji: str


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
    timeout_seconds: Optional[int] = None,
) -> bool:
    """Run a command and handle output."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    if cwd:
        print(f"Working directory: {cwd}")
    if timeout_seconds:
        print(f"Timeout: {timeout_seconds}s")
    print(f"{'='*60}")

    # Add timeout if specified
    if timeout_seconds:
        cmd = ["timeout", str(timeout_seconds)] + cmd

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


def check_docker_container_health() -> bool:
    """Check if we're running inside Docker container and server is healthy."""
    try:
        # When running inside Docker container, just check if server is healthy
        # The server should be running on localhost:8000 in the same container
        if not check_server_health("http://localhost:8000/health"):
            print("❌ Server is not healthy on localhost:8000")
            return False

        print("✅ Server is running and healthy on port 8000")
        return True

    except Exception as e:
        print(f"❌ Failed to check server health: {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run all MCTS tests: Python (Unit → Integration → Benchmarks) → Frontend → E2E"
    )
    parser.add_argument(
        "--skip-python", action="store_true", help="Skip all Python tests"
    )
    parser.add_argument(
        "--skip-unit",
        action="store_true",
        help="Skip unit tests (backend/core, backend/api)",
    )
    parser.add_argument(
        "--skip-integration", action="store_true", help="Skip integration tests"
    )
    parser.add_argument(
        "--skip-benchmarks", action="store_true", help="Skip benchmark tests"
    )
    parser.add_argument(
        "--skip-utils", action="store_true", help="Skip utility/fixture tests"
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
    parser.add_argument(
        "--fail-fast", action="store_true", help="Stop on first test failure"
    )

    args = parser.parse_args()

    # Type assertions for argparse namespace attributes
    skip_unit: bool = bool(args.skip_unit)
    skip_integration: bool = bool(args.skip_integration)
    skip_utils: bool = bool(args.skip_utils)
    skip_benchmarks: bool = bool(args.skip_benchmarks)

    # Get project root
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)

    success = True
    test_results = {}

    # Define test suites with their configurations
    python_test_suites: List[TestSuite] = [
        {
            "name": "Unit Tests - Core",
            "path": "tests/backend/core/",
            "markers": "not e2e and not slow",
            "coverage_target": "backend.python",
            "skip_flag": skip_unit,
            "emoji": "🧪",
        },
        {
            "name": "Unit Tests - API",
            "path": "tests/backend/api/",
            "markers": "not e2e and not slow",
            "coverage_target": "backend.api",
            "skip_flag": skip_unit,
            "emoji": "🌐",
        },
        {
            "name": "Integration Tests",
            "path": "tests/integration/",
            "markers": "not e2e",
            "coverage_target": "backend",
            "skip_flag": skip_integration,
            "emoji": "🔗",
        },
        {
            "name": "Utility & Fixture Tests",
            "path": "tests/test_utilities/",
            "markers": "not e2e and not benchmark",
            "coverage_target": "tests.utils tests.fixtures",  # Test the utilities themselves
            "skip_flag": skip_utils,
            "emoji": "🛠️",
        },
        {
            "name": "Benchmark Tests",
            "path": "tests/benchmarks/",
            "markers": "benchmark",
            "coverage_target": None,  # Skip coverage for benchmarks
            "skip_flag": skip_benchmarks,
            "emoji": "⚡",
        },
    ]

    # Run Python test suites
    if not args.skip_python:
        print("🐍 Running Python Test Suites...")
        print("=" * 80)

        for suite in python_test_suites:
            if suite["skip_flag"]:
                print(f"⏭️  Skipping {suite['name']}")
                test_results[suite["name"]] = "SKIPPED"
                continue

            print(f"\n{suite['emoji']} Running {suite['name']}...")

            # Build pytest command
            cmd = ["pytest"] + suite["path"].split()

            if suite["markers"]:
                cmd.extend(["-m", suite["markers"]])

            if args.verbose:
                cmd.append("-v")
            elif not args.debug:
                cmd.append("-q")

            if args.fail_fast:
                cmd.append("-x")

            # Add coverage if requested and applicable
            if args.coverage and suite["coverage_target"]:
                coverage_dir = suite["name"].lower().replace(" ", "-").replace("-", "_")
                cmd.extend(
                    [
                        f"--cov={suite['coverage_target']}",
                        f"--cov-report=html:htmlcov-{coverage_dir}",
                        "--cov-report=term-missing",
                    ]
                )

            # Set reasonable timeouts for different test types
            timeout_map = {
                "Unit Tests - Core": 120,  # 2 minutes
                "Unit Tests - API": 180,  # 3 minutes
                "Integration Tests": 300,  # 5 minutes
                "Utility & Fixture Tests": 60,  # 1 minute
                "Benchmark Tests": 600,  # 10 minutes
            }
            timeout = timeout_map.get(suite["name"], 300)  # Default 5 minutes

            suite_success = run_command(cmd, suite["name"], timeout_seconds=timeout)
            test_results[suite["name"]] = "PASSED" if suite_success else "FAILED"
            success = success and suite_success

            if args.fail_fast and not suite_success:
                break

    # Initialize result tracking for frontend and e2e
    frontend_success = True
    e2e_success = True

    # Run Frontend tests
    if not args.skip_frontend:
        frontend_test_dir = project_root / "frontend" / "tests"
        frontend_src_dir = project_root / "frontend"
        if frontend_test_dir.exists() and frontend_src_dir.exists():
            print("\n⚛️  Running Frontend tests with Vitest...")

            # Use npm run test:run from frontend build directory where dependencies exist
            frontend_build_dir = Path("/opt/mcts/frontend-build")
            frontend_cmd = ["npm", "run", "test:run"]
            if args.coverage:
                frontend_cmd.extend(["--coverage"])
            if args.verbose:
                frontend_cmd.append("--reporter=verbose")

            # Set up environment to use the build directory with dependencies
            frontend_env = os.environ.copy()
            frontend_env["VITEST_CONFIG"] = str(frontend_src_dir / "vitest.config.ts")

            frontend_success = run_command(
                frontend_cmd,
                "Frontend Tests",
                cwd=str(frontend_build_dir),
                env=frontend_env,
                timeout_seconds=300,
            )
            test_results["Frontend Tests"] = "PASSED" if frontend_success else "FAILED"
            success = success and frontend_success

            if args.fail_fast and not frontend_success:
                print("❌ Stopping due to --fail-fast flag")
        else:
            print("\n⚛️  Skipping Frontend tests (frontend directories not found)")
            test_results["Frontend Tests"] = "SKIPPED"

    # Run E2E tests
    if not args.skip_e2e and (not args.fail_fast or success):
        print("\n🌐 Running E2E tests with Playwright...")

        # Check Docker container health before running E2E tests
        if not check_docker_container_health():
            print("❌ Docker container is not healthy, E2E tests cannot run")
            test_results["E2E Tests"] = "FAILED"
            success = False
        else:
            # Set up environment for E2E tests to use Docker container
            env = os.environ.copy()
            env["E2E_BACKEND_URL"] = "http://localhost:8000"
            env["E2E_FRONTEND_URL"] = "http://localhost:8000"
            env["E2E_WS_URL"] = "ws://localhost:8000/ws"

            if args.headed:
                env["E2E_HEADLESS"] = "false"
            if args.debug:
                env["PWDEBUG"] = "1"

            # Run E2E tests directly with pytest
            e2e_cmd = ["pytest", "tests/e2e/", "-v"]
            if args.verbose:
                e2e_cmd.append("-s")

            e2e_success = run_command(
                e2e_cmd, "E2E Tests", env=env, timeout_seconds=1200
            )  # 20 minutes
            test_results["E2E Tests"] = "PASSED" if e2e_success else "FAILED"
            success = success and e2e_success

    # Final summary
    print(f"\n{'='*80}")
    print("📊 TEST EXECUTION SUMMARY")
    print(f"{'='*80}")

    if success:
        print("🎉 All executed tests passed!")
    else:
        print("💥 Some tests failed!")

    # Show detailed results for each test suite
    if test_results:
        print("\n📋 Test Suite Results:")
        for suite_name, result in test_results.items():
            status_emoji = {"PASSED": "✅", "FAILED": "❌", "SKIPPED": "⏭️"}[result]
            print(f"  {status_emoji} {suite_name}: {result}")

    # Show counts
    passed = sum(1 for r in test_results.values() if r == "PASSED")
    failed = sum(1 for r in test_results.values() if r == "FAILED")
    skipped = sum(1 for r in test_results.values() if r == "SKIPPED")
    total = len(test_results)

    print(
        f"\n📊 Summary: {passed} passed, {failed} failed, {skipped} skipped (of {total} suites)"
    )

    print(f"\n{'='*80}")
    if not success:
        print(
            "💡 TIP: Use specific --skip-* flags to run subsets, or --fail-fast to stop on first failure"
        )
        print("📖 Example: poetry run test-all --skip-benchmarks --skip-e2e")

    print(f"{'='*80}")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
