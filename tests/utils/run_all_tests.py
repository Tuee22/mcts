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
    parser = argparse.ArgumentParser(description="Run all MCTS project tests (Python + Frontend)")
    parser.add_argument("--python-only", action="store_true", help="Run only Python tests")
    parser.add_argument("--frontend-only", action="store_true", help="Run only frontend tests")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Get project root (assumes this script is in tests/utils/)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    frontend_test_dir = os.path.join(project_root, "tests", "frontend")
    
    success = True
    
    # Run Python tests unless frontend-only
    if not args.frontend_only:
        print("🐍 Running Python tests (API + Core)...")
        
        # Build pytest command
        pytest_cmd = ["python3", "-m", "pytest", "tests/"]
        
        if args.verbose:
            pytest_cmd.append("-v")
        
        if args.coverage:
            pytest_cmd.extend([
                "--cov=api",
                "--cov=python", 
                "--cov-report=html:htmlcov",
                "--cov-report=term-missing"
            ])
        
        python_success = run_command(pytest_cmd, "Python Tests", cwd=project_root)
        success = success and python_success
        
        if args.coverage and python_success:
            print(f"📊 Python coverage report: htmlcov/index.html")
    
    # Run Frontend tests unless python-only
    if not args.python_only:
        print("\n⚛️  Running Frontend tests...")
        
        # Check if frontend test directory exists
        if not os.path.exists(frontend_test_dir):
            print(f"⚠️  Frontend test directory not found: {frontend_test_dir}")
            print("Skipping frontend tests")
        else:
            # Build npm test command
            npm_cmd = ["npm", "test"]
            if args.coverage:
                npm_cmd = ["npm", "run", "test:coverage"]
            
            frontend_success = run_command(npm_cmd, "Frontend Tests", cwd=frontend_test_dir)
            success = success and frontend_success
            
            if args.coverage and frontend_success:
                print(f"📊 Frontend coverage report: {frontend_test_dir}/coverage/index.html")
    
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