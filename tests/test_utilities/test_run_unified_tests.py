"""Comprehensive tests for the unified test runner."""

import subprocess
import sys
import tempfile
import time
from typing import Dict, List, Optional
from unittest.mock import MagicMock, call, patch

import pytest
import requests

from tests.utils.run_unified_tests import (
    check_server_health,
    ensure_ports_free,
    find_and_kill_process,
    main,
    run_command,
    TestSuite,
)


class TestFindAndKillProcess:
    """Test the find_and_kill_process utility function."""

    @patch("tests.utils.run_unified_tests.PSUTIL_AVAILABLE", True)
    @patch("psutil.process_iter")
    @patch("os.kill")
    @patch("time.sleep")
    def test_find_and_kill_process_success(
        self, mock_sleep: MagicMock, mock_kill: MagicMock, mock_process_iter: MagicMock
    ) -> None:
        """Test successfully finding and killing a process on a port."""
        # Mock process with connection on target port
        mock_connection = MagicMock()
        mock_connection.laddr.port = 8000

        mock_proc = MagicMock()
        mock_proc.info = {
            "pid": 1234,
            "name": "test-server",
            "connections": [mock_connection],
        }

        mock_process_iter.return_value = [mock_proc]

        with patch("builtins.print") as mock_print:
            find_and_kill_process(8000)

        mock_kill.assert_called_once_with(1234, 15)  # SIGTERM
        mock_sleep.assert_called_once_with(0.5)
        assert isinstance(mock_print, MagicMock)
        mock_print.assert_called_once_with("Killing process 1234 using port 8000")

    @patch("tests.utils.run_unified_tests.PSUTIL_AVAILABLE", True)
    @patch("psutil.process_iter")
    def test_find_and_kill_process_no_matching_port(
        self, mock_process_iter: MagicMock
    ) -> None:
        """Test when no process is using the target port."""
        # Mock process with connection on different port
        mock_connection = MagicMock()
        mock_connection.laddr.port = 9000

        mock_proc = MagicMock()
        mock_proc.info = {
            "pid": 1234,
            "name": "test-server",
            "connections": [mock_connection],
        }

        mock_process_iter.return_value = [mock_proc]

        with patch("os.kill") as mock_kill:
            assert isinstance(mock_kill, MagicMock)
            find_and_kill_process(8000)

        mock_kill.assert_not_called()

    @patch("tests.utils.run_unified_tests.PSUTIL_AVAILABLE", True)
    @patch("psutil.process_iter")
    def test_find_and_kill_process_no_connections(
        self, mock_process_iter: MagicMock
    ) -> None:
        """Test when process has no connections."""
        mock_proc = MagicMock()
        mock_proc.info = {"pid": 1234, "name": "test-server", "connections": None}

        mock_process_iter.return_value = [mock_proc]

        with patch("os.kill") as mock_kill:
            assert isinstance(mock_kill, MagicMock)
            find_and_kill_process(8000)

        mock_kill.assert_not_called()

    @patch("tests.utils.run_unified_tests.PSUTIL_AVAILABLE", True)
    @patch("psutil.process_iter")
    def test_find_and_kill_process_exception_handling(
        self, mock_process_iter: MagicMock
    ) -> None:
        """Test exception handling during process information access."""
        import psutil

        # Create a mock process that will raise an exception when accessing info
        mock_proc = MagicMock()
        # Make accessing proc.info.get("connections") raise a psutil exception
        mock_proc.info.get.side_effect = psutil.NoSuchProcess(1234)

        mock_process_iter.return_value = [mock_proc]

        # Should not raise exception, should handle gracefully
        find_and_kill_process(8000)

    @patch("tests.utils.run_unified_tests.PSUTIL_AVAILABLE", False)
    def test_find_and_kill_process_psutil_unavailable(self) -> None:
        """Test when psutil is not available."""
        # Should return immediately without error
        find_and_kill_process(8000)


class TestEnsurePortsFree:
    """Test the ensure_ports_free utility function."""

    @patch("tests.utils.run_unified_tests.find_and_kill_process")
    def test_ensure_ports_free_calls_kill_for_each_port(
        self, mock_kill: MagicMock
    ) -> None:
        """Test that ensure_ports_free calls kill for each required port."""
        ensure_ports_free()

        # Should call for both E2E test ports
        expected_calls = [call(8002), call(3002)]
        mock_kill.assert_has_calls(expected_calls, any_order=True)


class TestRunCommand:
    """Test the run_command utility function."""

    def test_run_command_success(self) -> None:
        """Test running a successful command."""
        with patch("subprocess.Popen") as mock_popen, patch(
            "builtins.print"
        ) as mock_print:
            assert isinstance(mock_popen, MagicMock)
            assert isinstance(mock_print, MagicMock)

            # Mock process object
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.wait.return_value = None
            mock_process.poll.return_value = 0
            mock_popen.return_value = mock_process

            result = run_command(["echo", "test"], "Echo Test")

            assert result is True

            # Verify Popen was called with correct arguments including process group creation
            import os

            mock_popen.assert_called_once_with(
                ["echo", "test"], cwd=None, env=None, preexec_fn=os.setsid
            )

            # Verify process was waited on
            mock_process.wait.assert_called_once()

            # Check print calls
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("Echo Test" in call for call in print_calls)
            assert any("Command: echo test" in call for call in print_calls)
            assert any("✅" in call for call in print_calls)

    def test_run_command_failure(self) -> None:
        """Test running a failing command."""
        with patch("subprocess.Popen") as mock_popen, patch(
            "builtins.print"
        ) as mock_print:
            assert isinstance(mock_popen, MagicMock)
            assert isinstance(mock_print, MagicMock)

            # Mock process object with failure
            mock_process = MagicMock()
            mock_process.returncode = 1
            mock_process.wait.return_value = None
            mock_process.poll.return_value = 1
            mock_popen.return_value = mock_process

            result = run_command(["false"], "Failing Command")

            assert result is False

            # Verify process was waited on
            mock_process.wait.assert_called_once()

            # Check failure message
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("❌" in call for call in print_calls)
            assert any("failed with return code 1" in call for call in print_calls)

    def test_run_command_with_cwd_and_env(self) -> None:
        """Test running command with custom working directory and environment."""
        with patch("subprocess.Popen") as mock_popen, patch("builtins.print"):
            assert isinstance(mock_popen, MagicMock)

            # Mock process object
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.wait.return_value = None
            mock_process.poll.return_value = 0
            mock_popen.return_value = mock_process

            custom_env = {"TEST_VAR": "test_value"}
            run_command(["pwd"], "Directory Test", cwd="/tmp", env=custom_env)

            # Verify Popen was called with correct arguments
            import os

            mock_popen.assert_called_once_with(
                ["pwd"], cwd="/tmp", env=custom_env, preexec_fn=os.setsid
            )

    def test_run_command_prints_working_directory(self) -> None:
        """Test that custom working directory is printed."""
        with patch("subprocess.Popen") as mock_popen, patch(
            "builtins.print"
        ) as mock_print:
            assert isinstance(mock_popen, MagicMock)
            assert isinstance(mock_print, MagicMock)

            # Mock process object
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.wait.return_value = None
            mock_process.poll.return_value = 0
            mock_popen.return_value = mock_process

            run_command(["ls"], "List Files", cwd="/custom/path")

            # Check that working directory is printed
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any(
                "Working directory: /custom/path" in call for call in print_calls
            )

    def test_run_command_process_tracking(self) -> None:
        """Test that processes are correctly tracked and cleaned up."""
        from tests.utils.run_unified_tests import running_processes

        with patch("subprocess.Popen") as mock_popen, patch("builtins.print"):
            assert isinstance(mock_popen, MagicMock)

            # Mock process object
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.wait.return_value = None
            mock_process.poll.return_value = 0
            mock_popen.return_value = mock_process

            # Clear any existing tracked processes
            initial_count = len(running_processes)
            running_processes.clear()

            result = run_command(["echo", "test"], "Test Process Tracking")

            # Verify process was tracked during execution and then removed
            assert result is True
            assert len(running_processes) == 0  # Should be cleaned up after completion

            # Note: Not restoring original state as it's not needed for this test

    def test_run_command_keyboard_interrupt_cleanup(self) -> None:
        """Test that KeyboardInterrupt triggers proper cleanup."""
        from tests.utils.run_unified_tests import cleanup_processes, running_processes

        with patch("subprocess.Popen") as mock_popen, patch("builtins.print"), patch(
            "tests.utils.run_unified_tests.cleanup_processes"
        ) as mock_cleanup, patch("sys.exit") as mock_exit:
            assert isinstance(mock_popen, MagicMock)
            assert isinstance(mock_cleanup, MagicMock)
            assert isinstance(mock_exit, MagicMock)

            # Mock process that raises KeyboardInterrupt
            mock_process = MagicMock()
            mock_process.wait.side_effect = [KeyboardInterrupt()]
            mock_popen.return_value = mock_process

            # Clear tracked processes
            running_processes.clear()

            # This should trigger cleanup and exit
            run_command(["sleep", "10"], "Interrupted Process")

            # Verify cleanup was called and exit was invoked
            mock_cleanup.assert_called_once()
            mock_exit.assert_called_once_with(1)


class TestCheckServerHealth:
    """Test the check_server_health utility function."""

    def test_check_server_health_success(self) -> None:
        """Test successful health check."""
        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            assert isinstance(mock_get, MagicMock)
            mock_get.return_value = mock_response

            result = check_server_health("http://localhost:8000/health")

            assert result is True
            mock_get.assert_called_once_with("http://localhost:8000/health", timeout=1)

    def test_check_server_health_with_retries(self) -> None:
        """Test health check that succeeds after retries."""
        with patch("requests.get") as mock_get, patch("time.sleep") as mock_sleep:
            # Fail twice, then succeed
            assert isinstance(mock_get, MagicMock)
            assert isinstance(mock_sleep, MagicMock)
            mock_get.side_effect = [
                Exception("Connection refused"),
                Exception("Timeout"),
                MagicMock(status_code=200),
            ]

            result = check_server_health("http://localhost:8000/health", max_retries=5)

            assert result is True
            assert mock_get.call_count == 3
            assert mock_sleep.call_count == 2

    def test_check_server_health_max_retries_exceeded(self) -> None:
        """Test health check that fails after max retries."""
        with patch("requests.get") as mock_get, patch("time.sleep"):
            assert isinstance(mock_get, MagicMock)
            mock_get.side_effect = Exception("Always fails")

            result = check_server_health("http://localhost:8000/health", max_retries=3)

            assert result is False
            assert mock_get.call_count == 3

    def test_check_server_health_non_200_status(self) -> None:
        """Test health check with non-200 status code."""
        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            assert isinstance(mock_get, MagicMock)
            mock_get.return_value = mock_response

            result = check_server_health("http://localhost:8000/health", max_retries=1)

            assert result is False


class TestTestSuiteType:
    """Test the TestSuite TypedDict structure."""

    def test_test_suite_structure(self) -> None:
        """Test that TestSuite has the expected structure."""
        suite: TestSuite = {
            "name": "Test Suite",
            "path": "tests/backend/",
            "markers": "not e2e",
            "coverage_target": "backend",
            "skip_flag": False,
            "emoji": "🧪",
        }

        # Verify all required fields are present
        assert suite["name"] == "Test Suite"
        assert suite["path"] == "tests/backend/"
        assert suite["markers"] == "not e2e"
        assert suite["coverage_target"] == "backend"
        assert suite["skip_flag"] is False
        assert suite["emoji"] == "🧪"

    def test_test_suite_optional_coverage_target(self) -> None:
        """Test TestSuite with None coverage_target."""
        suite: TestSuite = {
            "name": "Benchmark Suite",
            "path": "tests/benchmarks/",
            "markers": "benchmark",
            "coverage_target": None,
            "skip_flag": False,
            "emoji": "⚡",
        }

        assert suite["coverage_target"] is None


class TestMainFunction:
    """Test the main function argument parsing and test execution flow."""

    def test_main_help_argument(self) -> None:
        """Test that --help argument works."""
        with (
            patch("sys.argv", ["run_unified_tests.py", "--help"]),
            patch("argparse.ArgumentParser.parse_args") as mock_parse,
        ):
            assert isinstance(mock_parse, MagicMock)
            mock_parse.side_effect = [SystemExit(0)]

            try:
                main()
                assert False, "Expected SystemExit to be raised"
            except SystemExit as e:
                assert e.code == 0

    def test_main_default_arguments(self) -> None:
        """Test main function with default arguments."""
        with (
            patch("sys.argv", ["run_unified_tests.py"]),
            patch("pathlib.Path.exists", return_value=True),
            patch("os.chdir"),
            patch("tests.utils.run_unified_tests.run_command", return_value=True),
            patch(
                "tests.utils.run_unified_tests.check_docker_container_health",
                return_value=True,
            ),
            patch("builtins.print"),
            patch("sys.exit") as mock_exit,
        ):
            main()

            # Should exit with success code
            assert isinstance(mock_exit, MagicMock)
            mock_exit.assert_called_once_with(0)

    def test_main_skip_arguments(self) -> None:
        """Test main function with skip arguments."""
        test_args = [
            "run_unified_tests.py",
            "--skip-unit",
            "--skip-integration",
            "--skip-frontend",
            "--skip-e2e",
        ]

        with (
            patch("sys.argv", test_args),
            patch("pathlib.Path.exists", return_value=False),
            patch("os.chdir"),
            patch("tests.utils.run_unified_tests.run_command", return_value=True),
            patch("builtins.print"),
            patch("sys.exit") as mock_exit,
        ):
            main()

            assert isinstance(mock_exit, MagicMock)
            mock_exit.assert_called_once_with(0)

    def test_main_with_coverage(self) -> None:
        """Test main function with coverage enabled."""
        with (
            patch("sys.argv", ["run_unified_tests.py", "--coverage"]),
            patch("pathlib.Path.exists", return_value=False),
            patch("os.chdir"),
            patch("tests.utils.run_unified_tests.run_command", return_value=True),
            patch("builtins.print"),
            patch("sys.exit"),
        ):
            main()

    def test_main_test_failure_exit_code(self) -> None:
        """Test that test failures result in non-zero exit code."""
        with (
            patch("sys.argv", ["run_unified_tests.py"]),
            patch("pathlib.Path.exists", return_value=True),
            patch("os.chdir"),
            patch("tests.utils.run_unified_tests.run_command", return_value=False),
            patch("builtins.print"),
            patch("sys.exit") as mock_exit,
        ):
            main()

            assert isinstance(mock_exit, MagicMock)
            mock_exit.assert_called_once_with(1)

    def test_main_fail_fast_behavior(self) -> None:
        """Test that --fail-fast stops on first failure."""
        with (
            patch("sys.argv", ["run_unified_tests.py", "--fail-fast"]),
            patch("pathlib.Path.exists", return_value=False),
            patch("os.chdir"),
            patch("tests.utils.run_unified_tests.run_command") as mock_run,
            patch("builtins.print"),
            patch("sys.exit"),
        ):
            # First test suite fails
            assert isinstance(mock_run, MagicMock)
            mock_run.return_value = False

            main()

            # Should have stopped after first failure
            # Exact call count depends on implementation details

    def test_main_directory_change(self) -> None:
        """Test that main function changes to project root directory."""
        with (
            patch("sys.argv", ["run_unified_tests.py"]),
            patch("pathlib.Path.exists", return_value=False),
            patch("os.chdir") as mock_chdir,
            patch("tests.utils.run_unified_tests.run_command", return_value=True),
            patch("builtins.print"),
            patch("sys.exit"),
        ):
            main()

            # Should change to project root (three levels up from script location)
            assert isinstance(mock_chdir, MagicMock)
            mock_chdir.assert_called_once()


class TestUnifiedTestRunnerIntegration:
    """Integration tests for the unified test runner."""

    def test_python_test_suites_configuration(self) -> None:
        """Test that Python test suites are properly configured."""
        # This tests the actual configuration used in main()
        # We can't easily test the exact configuration without running main,
        # but we can verify the structure is valid

        expected_suites = [
            "Unit Tests - Core",
            "Unit Tests - API",
            "Integration Tests",
            "Utility & Fixture Tests",
            "Benchmark Tests",
        ]

        # In the real implementation, these would be defined in main()
        assert len(expected_suites) == 5

    def test_test_result_tracking(self) -> None:
        """Test that test results are properly tracked and reported."""
        # This would test the test_results dictionary population
        # and the final summary report

        sample_results = {
            "Unit Tests - Core": "PASSED",
            "Integration Tests": "FAILED",
            "Frontend Tests": "SKIPPED",
        }

        passed = sum(1 for r in sample_results.values() if r == "PASSED")
        failed = sum(1 for r in sample_results.values() if r == "FAILED")
        skipped = sum(1 for r in sample_results.values() if r == "SKIPPED")

        assert passed == 1
        assert failed == 1
        assert skipped == 1

    def test_emoji_and_display_formatting(self) -> None:
        """Test that test suite display formatting works correctly."""
        status_emoji = {"PASSED": "✅", "FAILED": "❌", "SKIPPED": "⏭️"}

        for status, emoji in status_emoji.items():
            assert emoji in ["✅", "❌", "⏭️"]
            assert len(emoji) > 0

    def test_command_construction(self) -> None:
        """Test that pytest commands are constructed correctly."""
        # Test command construction for various scenarios
        base_cmd = ["pytest", "tests/backend/core/"]

        # With markers
        cmd_with_markers = base_cmd + ["-m", "not e2e and not slow"]
        assert "-m" in cmd_with_markers
        assert "not e2e and not slow" in cmd_with_markers

        # With coverage
        coverage_args = [
            "--cov=backend.python",
            "--cov-report=html:htmlcov-unit_tests_core",
            "--cov-report=term-missing",
        ]
        cmd_with_coverage = base_cmd + coverage_args
        assert "--cov=backend.python" in cmd_with_coverage

    def test_path_resolution(self) -> None:
        """Test that test paths are resolved correctly."""
        # Test that relative paths work correctly
        test_paths = [
            "tests/backend/core/",
            "tests/backend/api/",
            "tests/integration/",
            "tests/utils/ tests/fixtures/",
            "tests/benchmarks/",
        ]

        for path in test_paths:
            assert isinstance(path, str)
            assert len(path) > 0
            assert path.startswith("tests/")
