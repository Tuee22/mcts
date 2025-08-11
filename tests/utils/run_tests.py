#!/usr/bin/env python3
"""
Master test runner for the entire MCTS project.
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
    success = result.returncode == 0
    
    if success:
        print(f"\n✅ {description} completed successfully")
    else:
        print(f"\n❌ {description} failed with return code {result.returncode}")
    
    return success


def main():
    parser = argparse.ArgumentParser(description="Run MCTS project tests")
    parser.add_argument(
        "--suite", 
        choices=["all", "api", "core", "benchmarks"],
        default="all",
        help="Test suite to run"
    )
    parser.add_argument(
        "--type",
        choices=["all", "fast", "unit", "integration", "performance"],
        default="fast", 
        help="Type of tests within suite"
    )
    parser.add_argument("--coverage", action="store_true", help="Run with coverage")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--parallel", "-n", type=int, help="Run tests in parallel")
    
    args = parser.parse_args()
    
    # Base pytest command
    base_cmd = ["python", "-m", "pytest"]
    
    if args.verbose:
        base_cmd.append("-v")
    
    if args.parallel:
        base_cmd.extend(["-n", str(args.parallel)])
    
    # Coverage settings
    coverage_args = []
    if args.coverage:
        if args.suite in ["all", "api"]:
            coverage_args.extend(["--cov=api"])
        if args.suite in ["all", "core"]: 
            coverage_args.extend(["--cov=python"])
        coverage_args.extend([
            "--cov-report=html:htmlcov-all",
            "--cov-report=term-missing",
            "--cov-fail-under=70"
        ])
    
    # Determine test paths and markers
    test_paths = []
    markers = []
    
    if args.suite == "all":
        test_paths = ["tests/"]
        if args.type != "all":
            markers = ["-m", f"{args.type}" if args.type != "fast" else "not slow"]
    elif args.suite == "api":
        test_paths = ["tests/api/"]
        if args.type == "integration":
            test_paths = ["tests/api/test_integration.py"]
        elif args.type == "unit":
            test_paths = ["tests/api/"]
            markers = ["-m", "not integration"]
        elif args.type == "fast":
            markers = ["-m", "not slow"]
    elif args.suite == "core":
        test_paths = ["tests/core/"]
        if args.type == "performance":
            test_paths = ["tests/core/test_performance.py"] 
        elif args.type == "fast":
            markers = ["-m", "not slow"]
    elif args.suite == "benchmarks":
        test_paths = ["tests/benchmarks/"]
    
    # Build and run command
    cmd = base_cmd + test_paths + markers + coverage_args
    
    success = run_command(cmd, f"{args.suite.title()} {args.type} tests")
    
    if args.coverage and success:
        print(f"\n📊 Coverage report: htmlcov-all/index.html")
    
    # Summary
    if success:
        print(f"\n🎉 All {args.suite} tests passed!")
    else:
        print(f"\n💥 Some {args.suite} tests failed!")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()