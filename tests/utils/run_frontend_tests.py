#!/usr/bin/env python3
"""
Frontend test runner using Vitest.
Provides a clean interface for running only frontend tests with various options.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


def run_command(cmd: List[str], description: str, cwd: Optional[str] = None) -> bool:
    """Run a command and handle output."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    if cwd:
        print(f"Working directory: {cwd}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, cwd=cwd)
    success = result.returncode == 0

    if success:
        print(f"\n✅ {description} completed successfully")
    else:
        print(f"\n❌ {description} failed with return code {result.returncode}")

    return success


def main() -> None:
    parser = argparse.ArgumentParser(description="Run frontend tests with Vitest")
    parser.add_argument(
        "--coverage", action="store_true", help="Run tests with coverage"
    )
    parser.add_argument("--watch", action="store_true", help="Run tests in watch mode")
    parser.add_argument("--ui", action="store_true", help="Run tests with Vitest UI")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--silent", action="store_true", help="Silent output (only errors)"
    )
    parser.add_argument("--pattern", "-p", type=str, help="Test file pattern to match")
    parser.add_argument(
        "--component", type=str, help="Run tests for specific component"
    )
    parser.add_argument("--service", type=str, help="Run tests for specific service")
    parser.add_argument("--store", action="store_true", help="Run only store tests")
    parser.add_argument(
        "--edge-cases", action="store_true", help="Run only edge case tests"
    )
    parser.add_argument(
        "--performance", action="store_true", help="Run only performance tests"
    )

    args = parser.parse_args()

    # Get project root and frontend test directory
    project_root = Path(__file__).parent.parent.parent
    frontend_test_dir = project_root / "frontend" / "tests"
    frontend_src_dir = project_root / "frontend"

    if not frontend_test_dir.exists():
        print("❌ Frontend test directory not found")
        sys.exit(1)

    if not frontend_src_dir.exists():
        print("❌ Frontend source directory not found")
        sys.exit(1)

    os.chdir(frontend_src_dir)

    # Build npm command to run vitest with proper config
    cmd = ["npm", "run"]
    if args.watch:
        cmd.append("test")  # Interactive watch mode
    else:
        cmd.append("test:run")  # Run once mode

    # Use default config which now points to tests directory
    cmd.append("--")  # Separator for npm run arguments

    # Additional vitest options
    if args.ui:
        cmd.append("--ui")

    if args.coverage:
        cmd.append("--coverage")

    # Reporter options
    if args.silent:
        cmd.extend(["--reporter", "silent"])
    elif args.verbose:
        cmd.extend(["--reporter", "verbose"])
    else:
        cmd.extend(["--reporter", "default"])

    # Test filtering
    test_patterns: List[str] = []

    if args.pattern:
        test_patterns.append(str(args.pattern))

    if args.component:
        test_patterns.append(f"components/{args.component}")

    if args.service:
        test_patterns.append(f"services/{args.service}")

    if args.store:
        test_patterns.append("store/")

    if args.edge_cases:
        test_patterns.append("utils/*EdgeCases*")

    if args.performance:
        test_patterns.append("utils/performanceEdgeCases*")

    # Add test patterns to command
    if test_patterns:
        cmd.extend(test_patterns)

    # Show configuration
    print("🧪 Frontend Test Configuration:")
    print(f"   Working Directory: {frontend_src_dir}")
    print(f"   Test Directory: {frontend_test_dir}")
    print(f"   Coverage: {'Yes' if args.coverage else 'No'}")
    print(f"   Watch Mode: {'Yes' if args.watch else 'No'}")
    print(f"   UI Mode: {'Yes' if args.ui else 'No'}")
    if test_patterns:
        print(f"   Test Patterns: {', '.join(test_patterns)}")

    success = run_command(cmd, "Frontend Tests", cwd=str(frontend_src_dir))

    if success:
        print("\n🎉 All frontend tests passed!")
        if args.coverage:
            coverage_dir = frontend_test_dir / "coverage"
            if coverage_dir.exists():
                print(f"📊 Coverage report available at: {coverage_dir}/index.html")
    else:
        print("\n💥 Some frontend tests failed!")
        print("\n💡 Tips for debugging:")
        print("  - Run with --verbose for more details")
        print("  - Run specific component tests with --component <name>")
        print("  - Run in watch mode with --watch for iterative development")
        print("  - Use --ui for interactive testing")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
