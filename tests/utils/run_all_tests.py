#!/usr/bin/env python3
"""
Combined test runner for Python and Frontend tests.
"""
import subprocess
import sys
import os
import argparse


def run_command(cmd, description, cwd=None):
    """Run a command and handle output."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    if cwd:
        print(f"Working directory: {cwd}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, capture_output=False, cwd=cwd)
    success = result.returncode == 0

    if success:
        print(f"\n✅ {description} completed successfully")
    else:
        print(f"\n❌ {description} failed with return code {result.returncode}")

    return success


def main():
    parser = argparse.ArgumentParser(
        description="Run all MCTS project tests (Python + Frontend)"
    )
    parser.add_argument(
        "--python-only", action="store_true", help="Run only Python tests"
    )
    parser.add_argument(
        "--frontend-only", action="store_true", help="Run only frontend tests"
    )
    parser.add_argument("--coverage", action="store_true", help="Run with coverage")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Get project root (assumes this script is in tests/utils/)
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    frontend_test_dir = os.path.join(project_root, "tests", "frontend")

    success = True

    # Run Python tests unless frontend-only
    if not args.frontend_only:
        print("🐍 Running Python tests (Core + API separately)...")

        # Run Core tests first (these load the C++ module)
        core_cmd = ["python3", "-m", "pytest", "tests/backend/core/"]
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

        core_success = run_command(core_cmd, "Python Core Tests", cwd=project_root)
        
        # Run API tests in a separate process to avoid pybind11 double registration
        api_cmd = ["python3", "-m", "pytest", "tests/backend/api/"]
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

        api_success = run_command(api_cmd, "Python API Tests", cwd=project_root)
        
        python_success = core_success and api_success
        success = success and python_success

        if args.coverage and python_success:
            print(f"📊 Python coverage report: htmlcov/index.html")

    # Run Frontend tests unless python-only
    if not args.python_only:
        print("\n⚛️  Running Frontend tests...")

        # Use our dedicated frontend test runner
        frontend_cmd = [sys.executable, "-m", "tests.utils.run_frontend_tests"]
        if args.coverage:
            frontend_cmd.append("--coverage")
        if args.verbose:
            frontend_cmd.append("--verbose")

        frontend_success = run_command(
            frontend_cmd, "Frontend Tests", cwd=project_root
        )
        success = success and frontend_success

    # Final summary
    print(f"\n{'='*60}")
    if success:
        print("🎉 All tests passed!")
        print("✅ Python tests: PASSED")
        if not args.python_only:
            print("✅ Frontend tests: PASSED")
    else:
        print("💥 Some tests failed!")
        if not args.frontend_only:
            print("❌ Check Python test output above")
        if not args.python_only:
            print("❌ Check Frontend test output above")
    print(f"{'='*60}")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
