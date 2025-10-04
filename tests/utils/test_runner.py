"""Main test runner entry point for Poetry scripts.

This script serves as the entry point for the 'test-runner' Poetry script
defined in pyproject.toml. It delegates to the comprehensive unified test runner.
"""

from tests.utils.run_unified_tests import main


if __name__ == "__main__":
    main()
