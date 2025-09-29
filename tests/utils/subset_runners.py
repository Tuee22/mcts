"""Test subset runners for specific test categories."""

import sys
import subprocess
from typing import List


def run_pytest_subset(
    markers: str, paths: List[str], description: str, parallel: bool = False
) -> None:
    """Run pytest with specific markers and paths."""
    cmd = ["pytest"] + paths
    if markers:
        cmd.extend(["-m", markers])
    cmd.extend(["-v"])

    # Add parallel execution for E2E tests
    if parallel and "e2e" in paths[0] if paths else False:
        cmd.extend(
            [
                "-n",
                "4",  # Run with 4 parallel workers
                "--dist",
                "loadfile",  # Distribute tests by file for better isolation
                "--timeout",
                "30",  # 30s timeout per test
            ]
        )

    print(f"Running {description}...")
    print(f"Command: {' '.join(cmd)}")

    result = subprocess.run(cmd)
    sys.exit(result.returncode)


def run_unit_tests() -> None:
    """Run unit tests (backend/core and backend/api)."""
    run_pytest_subset(
        "not e2e and not slow",
        ["tests/backend/core/", "tests/backend/api/"],
        "Unit Tests",
    )


def run_integration_tests() -> None:
    """Run integration tests."""
    run_pytest_subset(
        "integration and not e2e", ["tests/integration/"], "Integration Tests"
    )


def run_benchmark_tests() -> None:
    """Run benchmark tests."""
    run_pytest_subset("benchmark", ["tests/benchmarks/"], "Benchmark Tests")


def run_python_tests() -> None:
    """Run all Python tests (excluding e2e)."""
    run_pytest_subset(
        "not e2e",
        ["tests/backend/", "tests/integration/", "tests/test_utilities/"],
        "Python Tests",
    )


def run_frontend_tests() -> None:
    """Run frontend tests using npm."""
    cmd = ["npm", "test", "--", "--watchAll=false"]
    print("Running Frontend Tests...")
    print(f"Command: {' '.join(cmd)}")

    result = subprocess.run(cmd, cwd="frontend")
    sys.exit(result.returncode)


def run_e2e_tests() -> None:
    """Run end-to-end tests with parallel execution."""
    run_pytest_subset("e2e", ["tests/e2e/"], "End-to-End Tests", parallel=True)


def run_fast_tests() -> None:
    """Run fast tests (excluding slow and e2e)."""
    run_pytest_subset(
        "not slow and not e2e and not benchmark",
        ["tests/backend/", "tests/integration/", "tests/test_utilities/"],
        "Fast Tests",
    )


def run_quick_tests() -> None:
    """Run quick tests (minimal subset for rapid feedback)."""
    run_pytest_subset(
        "not slow and not e2e and not benchmark and not integration",
        ["tests/backend/core/", "tests/test_utilities/"],
        "Quick Tests",
    )
