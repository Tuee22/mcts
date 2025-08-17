#!/usr/bin/env python3
"""
Frontend test runner for MCTS project.
"""
import subprocess
import sys
import os
import argparse
from pathlib import Path


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
    parser = argparse.ArgumentParser(description="Run frontend tests for MCTS project")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--watch", action="store_true", help="Run in watch mode")

    args = parser.parse_args()

    # Get project root (assumes this script is in tests/utils/)
    project_root = Path(__file__).parent.parent.parent
    frontend_test_dir = project_root / "tests" / "frontend"

    if not frontend_test_dir.exists():
        print(f"❌ Frontend test directory not found: {frontend_test_dir}")
        sys.exit(1)

    print("⚛️  Running Frontend tests...")

    # Build vitest command using npx to use local installation (non-interactive)
    vitest_cmd = ["npx", "--yes", "vitest"]

    if args.watch:
        # Run in watch mode
        pass  # Default vitest behavior
    else:
        vitest_cmd.append("run")

    if args.coverage:
        vitest_cmd.append("--coverage")

    if args.verbose:
        vitest_cmd.append("--reporter=verbose")

    success = run_command(vitest_cmd, "Frontend Tests", cwd=str(frontend_test_dir))

    if args.coverage and success:
        coverage_path = frontend_test_dir / "coverage" / "index.html"
        print(f"📊 Frontend coverage report: {coverage_path}")

    # Final summary
    print(f"\n{'='*60}")
    if success:
        print("🎉 Frontend tests passed!")
    else:
        print("💥 Frontend tests failed!")
    print(f"{'='*60}")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
