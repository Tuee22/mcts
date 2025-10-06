"""Enhanced E2E test runner with validation to ensure no tests are missed."""

import sys
import subprocess
from typing import List, Optional, Tuple
import re


def count_e2e_tests() -> Tuple[int, int]:
    """Count expected e2e tests by collecting them first.

    Returns:
        Tuple of (test_functions, total_test_cases)
        test_functions = number of test functions found
        total_test_cases = test_functions * 3 browsers
    """
    # Use pytest to collect tests and count them
    cmd = ["pytest", "tests/e2e/", "-m", "e2e", "--collect-only", "-q"]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error collecting e2e tests: {result.stderr}")
        sys.exit(1)

    # Parse output to count test cases
    # pytest --collect-only shows lines like "test_file.py::test_function[browser]"
    stdout = result.stdout or ""
    output_lines = stdout.split("\n")
    test_cases = 0
    test_functions = set()

    for line in output_lines:
        # Look for test collection lines
        if "::test_" in line and "[" in line:
            test_cases += 1
            # Extract function name (before the [browser] part)
            function_part = line.split("[")[0]
            if "::test_" in function_part:
                function_name = function_part.split("::test_")[-1]
                test_functions.add(function_name)

    return len(test_functions), test_cases


def validate_e2e_test_discovery() -> None:
    """Validate that e2e test discovery is working correctly."""
    print("🔍 Validating E2E test discovery...")

    test_functions, total_cases = count_e2e_tests()
    expected_browsers = 3  # chromium, firefox, webkit
    expected_total = test_functions * expected_browsers

    print(f"📊 Test Discovery Results:")
    print(f"   - Test functions found: {test_functions}")
    print(f"   - Expected browsers: {expected_browsers}")
    print(f"   - Total test cases found: {total_cases}")
    print(f"   - Expected total cases: {expected_total}")

    if total_cases != expected_total:
        print(f"❌ ERROR: Test case count mismatch!")
        print(
            f"   Expected {expected_total} test cases ({test_functions} functions × {expected_browsers} browsers)"
        )
        print(f"   But found {total_cases} test cases")
        print(f"   This suggests browser parametrization is not working correctly.")
        sys.exit(1)

    print(f"✅ Test discovery validation passed!")
    print(
        f"   All {test_functions} test functions are properly parametrized across {expected_browsers} browsers"
    )
    print()


def run_e2e_tests_with_validation() -> None:
    """Run all E2E tests with pre-validation."""
    # First validate test discovery
    validate_e2e_test_discovery()

    # Now run the actual tests
    print("🚀 Starting E2E test execution...")

    cmd = [
        "pytest",
        "tests/e2e/",
        "-m",
        "e2e",
        "-v",
        "--tb=short",  # Short traceback format for better output
        "--show-capture=no",  # Reduce output clutter
        "--maxfail=5",  # Stop after 5 failures to prevent infinite hanging
    ]

    print(f"📝 Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd)

    if result.returncode != 0:
        print("❌ E2E tests failed!")
        sys.exit(result.returncode)
    else:
        print("✅ All E2E tests passed!")


def list_e2e_tests() -> None:
    """List all E2E tests that would be run."""
    print("📋 E2E Tests Discovery Report")
    print("=" * 50)

    cmd = ["pytest", "tests/e2e/", "-m", "e2e", "--collect-only", "-v"]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error listing e2e tests: {result.stderr}")
        sys.exit(1)

    # Parse and organize the output
    stdout = result.stdout or ""
    lines = stdout.split("\n")
    current_file = None
    test_count = 0

    for line in lines:
        line = line.strip()
        if line.startswith("<Module"):
            # Extract filename from <Module tests/e2e/test_file.py>
            match = re.search(r"<Module (.+\.py)>", line)
            if match:
                current_file = match.group(1).split("/")[-1]  # Get just the filename
                print(f"\n📁 {current_file}")
        elif "::test_" in line and "[" in line:
            # This is a test case line
            test_count += 1
            # Extract test name and browser
            if "::" in line:
                test_part = line.split("::")[-1]
                print(f"   • {test_part}")

    test_functions, total_cases = count_e2e_tests()
    print(f"\n📊 Summary:")
    print(f"   • Total test functions: {test_functions}")
    print(f"   • Total test cases: {total_cases}")
    print(f"   • Browsers per test: 3 (chromium, firefox, webkit)")
    print()


# Entry point functions for Poetry scripts
def main_validate() -> None:
    """Entry point for test-e2e-validate command."""
    validate_e2e_test_discovery()


def main_list() -> None:
    """Entry point for test-e2e-list command."""
    list_e2e_tests()


def main_run() -> None:
    """Entry point for test-e2e-full command."""
    run_e2e_tests_with_validation()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "validate":
            validate_e2e_test_discovery()
        elif command == "list":
            list_e2e_tests()
        elif command == "run":
            run_e2e_tests_with_validation()
        else:
            print(f"Unknown command: {command}")
            print("Usage: python e2e_test_runner.py [validate|list|run]")
            sys.exit(1)
    else:
        # Default action is to run with validation
        run_e2e_tests_with_validation()
