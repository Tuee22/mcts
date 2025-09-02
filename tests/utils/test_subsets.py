#!/usr/bin/env python3
"""
Simple wrapper scripts for running common test subsets.
Provides Poetry script entry points for granular test execution.
"""
import sys
from .run_unified_tests import main


def run_unit_tests() -> None:
    """Run only unit tests (backend/core + backend/api)."""
    sys.argv = [
        "test-unit",
        "--skip-integration",
        "--skip-benchmarks",
        "--skip-utils",
        "--skip-frontend",
        "--skip-e2e",
    ]
    main()


def run_integration_tests() -> None:
    """Run only integration tests."""
    sys.argv = [
        "test-integration",
        "--skip-unit",
        "--skip-benchmarks",
        "--skip-utils",
        "--skip-frontend",
        "--skip-e2e",
    ]
    main()


def run_benchmark_tests() -> None:
    """Run only benchmark tests."""
    sys.argv = [
        "test-benchmarks",
        "--skip-unit",
        "--skip-integration",
        "--skip-utils",
        "--skip-frontend",
        "--skip-e2e",
    ]
    main()


def run_python_tests() -> None:
    """Run all Python tests (unit + integration + benchmarks + utils)."""
    sys.argv = ["test-python", "--skip-frontend", "--skip-e2e"]
    main()


def run_frontend_tests() -> None:
    """Run only frontend tests."""
    sys.argv = ["test-frontend", "--skip-python", "--skip-e2e"]
    main()


def run_e2e_tests() -> None:
    """Run only E2E tests."""
    sys.argv = ["test-e2e", "--skip-python", "--skip-frontend"]
    main()


def run_fast_tests() -> None:
    """Run fast tests (excludes benchmarks and E2E)."""
    sys.argv = ["test-fast", "--skip-benchmarks", "--skip-e2e"]
    main()


def run_quick_tests() -> None:
    """Run quickest tests (only unit tests)."""
    sys.argv = [
        "test-quick",
        "--skip-integration",
        "--skip-benchmarks",
        "--skip-utils",
        "--skip-frontend",
        "--skip-e2e",
    ]
    main()
