#!/usr/bin/env python
"""Run the complete test suite including E2E tests with proper server setup."""

import subprocess
import sys
from typing import Dict, List


def run_test_category(name: str, command: List[str]) -> bool:
    """Run a category of tests and report results."""
    print(f"\n{'='*60}")
    print(f"Running: {name}")
    print(f"Command: {' '.join(command)}")
    print(f"{'='*60}")

    result = subprocess.run(command)

    if result.returncode == 0:
        print(f"\n✅ {name} completed successfully")
        return True
    else:
        print(f"\n❌ {name} failed with exit code {result.returncode}")
        return False


def main() -> int:
    """Run all test categories."""
    test_results: Dict[str, bool] = {}

    # Backend tests (Core + API)
    test_results["Backend Tests"] = run_test_category(
        "Backend Tests", [sys.executable, "-m", "pytest", "tests/backend/", "-v"]
    )

    # Benchmark tests
    test_results["Benchmark Tests"] = run_test_category(
        "Benchmark Tests", [sys.executable, "-m", "pytest", "tests/benchmarks/", "-v"]
    )

    # Integration tests
    test_results["Integration Tests"] = run_test_category(
        "Integration Tests",
        [sys.executable, "-m", "pytest", "tests/integration/", "-v", "-x"],
    )

    # Frontend unit tests
    test_results["Frontend Tests"] = run_test_category(
        "Frontend Tests", [sys.executable, "-m", "tests.utils.run_frontend_tests"]
    )

    # E2E tests with servers
    test_results["E2E Tests"] = run_test_category(
        "E2E Tests with Servers",
        [sys.executable, "tests/utils/run_e2e_with_servers.py"],
    )

    # Type checking
    test_results["Type Checking"] = run_test_category(
        "MyPy Type Checking", ["mypy", "--strict", "."]
    )

    # Summary
    print("\n" + "=" * 60)
    print("🎯 TEST SUITE SUMMARY")
    print("=" * 60)

    all_passed = True
    for test_name, passed in test_results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
