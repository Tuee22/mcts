#!/usr/bin/env python3
"""
Convenience script to run API tests with various options.
"""
import argparse
import subprocess
import sys
from typing import List


def run_command(cmd: List[str], description: str) -> bool:
    """Run a command and handle output."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        print(f"\n❌ {description} failed with return code {result.returncode}")
        return False
    else:
        print(f"\n✅ {description} completed successfully")
        return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Run API tests")
    parser.add_argument(
        "--type",
        choices=[
            "all",
            "fast",
            "unit",
            "integration",
            "websocket",
            "endpoints",
            "models",
        ],
        default="fast",
        help="Type of tests to run",
    )
    parser.add_argument("--coverage", action="store_true", help="Run with coverage")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Base pytest command
    base_cmd = ["python", "-m", "pytest"]

    # Add verbosity
    if args.verbose:
        base_cmd.append("-v")

    # Add coverage
    if args.coverage:
        base_cmd.extend(
            [
                "--cov=backend.api",
                "--cov-report=html:htmlcov-api",
                "--cov-report=term-missing",
                "--cov-fail-under=70",
            ]
        )

    # Determine test files and markers
    if args.type == "all":
        test_files = ["tests/backend/api/"]
        markers = []
    elif args.type == "fast":
        test_files = ["tests/backend/api/"]
        markers = ["-m", "not slow"]
    elif args.type == "unit":
        test_files = [
            "tests/backend/api/test_models.py",
            "tests/backend/api/test_game_manager.py",
            "tests/backend/api/test_websocket.py",
        ]
        markers = []
    elif args.type == "integration":
        test_files = ["tests/backend/api/test_integration.py"]
        markers = []
    elif args.type == "websocket":
        test_files = ["tests/backend/api/test_websocket.py"]
        markers = []
    elif args.type == "endpoints":
        test_files = ["tests/backend/api/test_endpoints.py"]
        markers = []
    elif args.type == "models":
        test_files = ["tests/backend/api/test_models.py"]
        markers = []

    # Build final command
    cmd = base_cmd + test_files + markers

    # Run the tests
    success = run_command(cmd, f"{str(args.type).title()} API tests")

    if args.coverage and success:
        print(f"\n📊 Coverage report generated at: htmlcov-api/index.html")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
