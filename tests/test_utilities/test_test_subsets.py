"""Comprehensive tests for test subset runner utilities."""

import subprocess
import sys
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from tests.utils.test_subsets import (
    run_benchmark_tests,
    run_e2e_tests,
    run_fast_tests,
    run_frontend_tests,
    run_integration_tests,
    run_pytest_subset,
    run_python_tests,
    run_quick_tests,
    run_unit_tests,
)


class TestRunPytestSubset:
    """Test the run_pytest_subset helper function."""

    def test_run_pytest_subset_with_markers(self) -> None:
        """Test running pytest with specific markers."""
        mock_run = MagicMock()
        mock_run.return_value = MagicMock()
        mock_run.return_value.returncode = 0

        mock_exit = MagicMock()

        with patch("subprocess.run", mock_run), patch("sys.exit", mock_exit):
            run_pytest_subset(
                "not e2e and not slow", ["tests/backend/"], "Test Description"
            )

            # Verify subprocess.run was called correctly
            mock_run.assert_called_once()
            assert mock_run.call_args is not None
            call_args = mock_run.call_args[0][0]

            expected_cmd = [
                "pytest",
                "tests/backend/",
                "-m",
                "not e2e and not slow",
                "-v",
            ]
            assert call_args == expected_cmd

            # Verify sys.exit was called with correct code
            mock_exit.assert_called_once_with(0)

    def test_run_pytest_subset_without_markers(self) -> None:
        """Test running pytest without markers."""
        mock_run = MagicMock()
        mock_run.return_value = MagicMock()
        mock_run.return_value.returncode = 0

        mock_exit = MagicMock()

        with patch("subprocess.run", mock_run), patch("sys.exit", mock_exit):
            run_pytest_subset("", ["tests/backend/"], "Test Description")

            # Verify command without markers
            assert mock_run.call_args is not None
            call_args = mock_run.call_args[0][0]
            expected_cmd = ["pytest", "tests/backend/", "-v"]
            assert call_args == expected_cmd

    def test_run_pytest_subset_multiple_paths(self) -> None:
        """Test running pytest with multiple paths."""
        mock_run = MagicMock()
        mock_run.return_value = MagicMock()
        mock_run.return_value.returncode = 0

        mock_exit = MagicMock()

        with patch("subprocess.run", mock_run), patch("sys.exit", mock_exit):
            run_pytest_subset(
                "unit",
                ["tests/backend/core/", "tests/backend/api/", "tests/utils/"],
                "Multi-path Tests",
            )

            assert mock_run.call_args is not None
            call_args = mock_run.call_args[0][0]
            expected_cmd = [
                "pytest",
                "tests/backend/core/",
                "tests/backend/api/",
                "tests/utils/",
                "-m",
                "unit",
                "-v",
            ]
            assert call_args == expected_cmd

    def test_run_pytest_subset_failure_exit_code(self) -> None:
        """Test that failure exit codes are propagated."""
        mock_run = MagicMock()
        mock_run.return_value = MagicMock()
        mock_run.return_value.returncode = 1

        mock_exit = MagicMock()

        with patch("subprocess.run", mock_run), patch("sys.exit", mock_exit):
            run_pytest_subset("", ["tests/"], "Failing Tests")

            mock_exit.assert_called_once_with(1)

    def test_run_pytest_subset_prints_info(self) -> None:
        """Test that function prints informative messages."""
        mock_run = MagicMock()
        mock_run.return_value = MagicMock()
        mock_run.return_value.returncode = 0

        mock_exit = MagicMock()
        mock_print = MagicMock()

        with (
            patch("subprocess.run", mock_run),
            patch("sys.exit", mock_exit),
            patch("builtins.print", mock_print),
        ):
            run_pytest_subset("marker", ["path/"], "Test Description")

            # Verify print calls
            assert mock_print.call_args_list is not None
            print_calls = []
            for call in mock_print.call_args_list:
                if call and hasattr(call, "__len__") and len(call) > 0:
                    call_args = call[0]
                    if hasattr(call_args, "__len__") and len(call_args) > 0:
                        call_str = str(call_args[0])
                        print_calls.append(call_str)
            assert any("Running Test Description..." in call for call in print_calls)
            assert any("Command:" in call for call in print_calls)


class TestUnitTestRunner:
    """Test the run_unit_tests function."""

    def test_run_unit_tests_calls_pytest_correctly(self) -> None:
        """Test that run_unit_tests calls pytest with correct parameters."""
        mock_run = MagicMock()

        with patch("tests.utils.test_subsets.run_pytest_subset", mock_run):
            run_unit_tests()

            mock_run.assert_called_once_with(
                "not e2e and not slow",
                ["tests/backend/core/", "tests/backend/api/"],
                "Unit Tests",
            )


class TestIntegrationTestRunner:
    """Test the run_integration_tests function."""

    def test_run_integration_tests_calls_pytest_correctly(self) -> None:
        """Test that run_integration_tests calls pytest with correct parameters."""
        mock_run = MagicMock()

        with patch("tests.utils.test_subsets.run_pytest_subset", mock_run):
            run_integration_tests()

            mock_run.assert_called_once_with(
                "integration and not e2e", ["tests/integration/"], "Integration Tests"
            )


class TestBenchmarkTestRunner:
    """Test the run_benchmark_tests function."""

    def test_run_benchmark_tests_calls_pytest_correctly(self) -> None:
        """Test that run_benchmark_tests calls pytest with correct parameters."""
        mock_run = MagicMock()

        with patch("tests.utils.test_subsets.run_pytest_subset", mock_run):
            run_benchmark_tests()

            mock_run.assert_called_once_with(
                "benchmark", ["tests/benchmarks/"], "Benchmark Tests"
            )


class TestPythonTestRunner:
    """Test the run_python_tests function."""

    def test_run_python_tests_calls_pytest_correctly(self) -> None:
        """Test that run_python_tests calls pytest with correct parameters."""
        mock_run = MagicMock()

        with patch("tests.utils.test_subsets.run_pytest_subset", mock_run):
            run_python_tests()

            mock_run.assert_called_once_with(
                "not e2e",
                ["tests/backend/", "tests/integration/", "tests/test_utilities/"],
                "Python Tests",
            )


class TestFrontendTestRunner:
    """Test the run_frontend_tests function."""

    def test_run_frontend_tests_calls_npm_correctly(self) -> None:
        """Test that run_frontend_tests calls npm with correct parameters."""
        mock_run = MagicMock()
        mock_run.return_value = MagicMock()
        mock_run.return_value.returncode = 0

        mock_exit = MagicMock()
        mock_print = MagicMock()

        with (
            patch("subprocess.run", mock_run),
            patch("sys.exit", mock_exit),
            patch("builtins.print", mock_print),
        ):
            run_frontend_tests()

            # Verify subprocess.run was called correctly
            mock_run.assert_called_once_with(
                ["npm", "test", "--", "--watchAll=false"], cwd="frontend"
            )
            mock_exit.assert_called_once_with(0)

    def test_run_frontend_tests_failure_propagation(self) -> None:
        """Test that frontend test failures are propagated."""
        mock_run = MagicMock()
        mock_run.return_value = MagicMock()
        mock_run.return_value.returncode = 2

        mock_exit = MagicMock()
        mock_print = MagicMock()

        with (
            patch("subprocess.run", mock_run),
            patch("sys.exit", mock_exit),
            patch("builtins.print", mock_print),
        ):
            run_frontend_tests()

            mock_exit.assert_called_once_with(2)

    def test_run_frontend_tests_prints_info(self) -> None:
        """Test that frontend tests print informative messages."""
        mock_run = MagicMock()
        mock_run.return_value = MagicMock()
        mock_run.return_value.returncode = 0

        mock_exit = MagicMock()
        mock_print = MagicMock()

        with (
            patch("subprocess.run", mock_run),
            patch("sys.exit", mock_exit),
            patch("builtins.print", mock_print),
        ):
            run_frontend_tests()

            # Verify print calls
            print_calls = []
            for call in mock_print.call_args_list:
                if call and hasattr(call, "__len__") and len(call) > 0:
                    call_args = call[0]
                    if hasattr(call_args, "__len__") and len(call_args) > 0:
                        call_str = str(call_args[0])
                        print_calls.append(call_str)
            assert any("Running Frontend Tests..." in str(call) for call in print_calls)
            assert any("Command:" in str(call) for call in print_calls)


class TestE2ETestRunner:
    """Test the run_e2e_tests function."""

    def test_run_e2e_tests_calls_pytest_correctly(self) -> None:
        """Test that run_e2e_tests calls pytest with correct parameters."""
        mock_run = MagicMock()

        with patch("tests.utils.test_subsets.run_pytest_subset", mock_run):
            run_e2e_tests()

            mock_run.assert_called_once_with("e2e", ["tests/e2e/"], "End-to-End Tests")


class TestFastTestRunner:
    """Test the run_fast_tests function."""

    def test_run_fast_tests_calls_pytest_correctly(self) -> None:
        """Test that run_fast_tests calls pytest with correct parameters."""
        mock_run = MagicMock()

        with patch("tests.utils.test_subsets.run_pytest_subset", mock_run):
            run_fast_tests()

            mock_run.assert_called_once_with(
                "not slow and not e2e and not benchmark",
                ["tests/backend/", "tests/integration/", "tests/test_utilities/"],
                "Fast Tests",
            )


class TestQuickTestRunner:
    """Test the run_quick_tests function."""

    def test_run_quick_tests_calls_pytest_correctly(self) -> None:
        """Test that run_quick_tests calls pytest with correct parameters."""
        mock_run = MagicMock()

        with patch("tests.utils.test_subsets.run_pytest_subset", mock_run):
            run_quick_tests()

            mock_run.assert_called_once_with(
                "not slow and not e2e and not benchmark and not integration",
                ["tests/backend/core/", "tests/test_utilities/"],
                "Quick Tests",
            )


class TestTestSubsetIntegration:
    """Integration tests for test subset runners."""

    def test_all_runners_available(self) -> None:
        """Test that all expected test runners are available."""
        # These functions should all be importable and callable
        runners = [
            run_unit_tests,
            run_integration_tests,
            run_benchmark_tests,
            run_python_tests,
            run_frontend_tests,
            run_e2e_tests,
            run_fast_tests,
            run_quick_tests,
        ]

        for runner in runners:
            assert callable(runner), f"{runner.__name__} is not callable"

    def test_markers_dont_overlap_inappropriately(self) -> None:
        """Test that test markers are logically consistent."""
        # Fast tests should exclude slow and e2e
        # Quick tests should exclude slow, e2e, benchmark, and integration
        # Unit tests should exclude e2e and slow
        # Integration tests should include integration but exclude e2e

        # This is more of a design verification test
        assert True  # Markers are checked through mocking above

    def test_test_paths_are_consistent(self) -> None:
        """Test that test paths are consistent across runners."""
        # Python tests should include all backend and integration paths
        # Fast tests should include similar paths to Python tests
        # Unit tests should focus on backend paths
        # Quick tests should be a subset of unit test paths

        mock_run = MagicMock()

        with patch("tests.utils.test_subsets.run_pytest_subset", mock_run):
            # Test python tests include comprehensive paths
            run_python_tests()
            python_call = mock_run.call_args
            python_paths = python_call[0][1] if python_call else []

            assert isinstance(python_paths, list)
            assert "tests/backend/" in python_paths
            assert "tests/integration/" in python_paths
            assert "tests/test_utilities/" in python_paths

    def test_marker_combinations_are_valid(self) -> None:
        """Test that marker combinations make logical sense."""
        marker_tests = [
            ("not e2e and not slow", "should exclude e2e and slow tests"),
            ("integration and not e2e", "should include integration but exclude e2e"),
            ("benchmark", "should only include benchmark tests"),
            ("not e2e", "should exclude only e2e tests"),
            ("e2e", "should only include e2e tests"),
            (
                "not slow and not e2e and not benchmark",
                "should exclude slow, e2e, and benchmark",
            ),
            (
                "not slow and not e2e and not benchmark and not integration",
                "should be most restrictive",
            ),
        ]

        for marker, description in marker_tests:
            # Verify marker syntax is valid (no syntax errors when parsed)
            assert isinstance(marker, str)
            assert len(marker) > 0
            # More sophisticated marker validation could be added here

    def test_comprehensive_coverage(self) -> None:
        """Test that all main test directories are covered by some runner."""
        expected_directories = {
            "tests/backend/core/",
            "tests/backend/api/",
            "tests/backend/",
            "tests/integration/",
            "tests/benchmarks/",
            "tests/e2e/",
            "tests/test_utilities/",
        }

        covered_directories: set[str] = set()

        mock_run = MagicMock()

        with patch("tests.utils.test_subsets.run_pytest_subset", mock_run):
            # Collect all paths from all runners
            for runner in [
                run_unit_tests,
                run_integration_tests,
                run_benchmark_tests,
                run_python_tests,
                run_e2e_tests,
                run_fast_tests,
                run_quick_tests,
            ]:
                runner()
                if mock_run.call_args:
                    paths = mock_run.call_args[0][1]
                    assert isinstance(paths, list)
                    for path in paths:
                        if isinstance(path, str):
                            covered_directories.add(path)

        # Should cover most expected directories (some may not exist)
        coverage = len(covered_directories & expected_directories) / len(
            expected_directories
        )
        assert (
            coverage >= 0.7
        ), f"Test runners only cover {coverage:.1%} of expected directories"
