#!/usr/bin/env python3
"""
Test runner for core MCTS and board logic tests.
"""
import subprocess
import sys
import argparse


def run_command(cmd, description):
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


def main():
    parser = argparse.ArgumentParser(description="Run core MCTS tests")
    parser.add_argument(
        "--type", 
        choices=["all", "fast", "cpp", "python", "integration", "performance"],
        default="fast",
        help="Type of tests to run"
    )
    parser.add_argument("--coverage", action="store_true", help="Run with coverage")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--benchmarks", action="store_true", help="Include benchmarks")
    
    args = parser.parse_args()
    
    # Base pytest command
    base_cmd = ["python", "-m", "pytest"]
    
    # Add verbosity
    if args.verbose:
        base_cmd.append("-v")
    
    # Add coverage
    if args.coverage:
        base_cmd.extend([
            "--cov=python",
            "--cov-report=html:htmlcov-core",
            "--cov-report=term-missing",
            "--cov-fail-under=70"
        ])
    
    # Determine test files and markers
    test_paths = []
    markers = []
    
    if args.type == "all":
        test_paths = ["tests/core/"]
        if args.benchmarks:
            test_paths.append("tests/benchmarks/")
    elif args.type == "fast":
        test_paths = ["tests/core/"]
        markers = ["-m", "not slow"]
    elif args.type == "cpp":
        test_paths = ["tests/core/"]
        markers = ["-m", "cpp"]
    elif args.type == "python":
        test_paths = ["tests/core/"]
        markers = ["-m", "python"]
    elif args.type == "integration":
        test_paths = ["tests/core/test_integration.py"]
    elif args.type == "performance":
        test_paths = ["tests/core/test_performance.py", "tests/benchmarks/"]
    
    # Build final command
    cmd = base_cmd + test_paths + markers
    
    # Run the tests
    success = run_command(cmd, f"{args.type.title()} core tests")
    
    if args.coverage and success:
        print(f"\n📊 Coverage report generated at: htmlcov-core/index.html")
    
    if args.benchmarks and success:
        print(f"\n⚡ Benchmark results available")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()