"""Comprehensive tests for test stability helper functions."""

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Union
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from tests.utils.stability_helpers import (
    retry_on_failure,
    retry_on_failure_async,
    retry_on_failure_sync,
)


class TestRetryOnFailure:
    """Test the retry_on_failure decorator."""

    def test_sync_function_success_first_try(self) -> None:
        """Test sync function that succeeds on first attempt."""
        call_count = 0

        @retry_on_failure_sync(max_attempts=3, delay=0.01)
        def test_func() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = test_func()

        assert result == "success"
        assert call_count == 1

    def test_sync_function_success_after_retries(self) -> None:
        """Test sync function that succeeds after retries."""
        call_count = 0

        @retry_on_failure_sync(max_attempts=3, delay=0.01)
        def test_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = test_func()

        assert result == "success"
        assert call_count == 3

    def test_sync_function_failure_after_all_retries(self) -> None:
        """Test sync function that fails after all retries."""
        call_count = 0

        @retry_on_failure_sync(max_attempts=2, delay=0.01)
        def test_func() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError(f"Failure attempt {call_count}")

        with pytest.raises(ValueError, match="Failure attempt 2"):
            test_func()

        assert call_count == 2

    def test_sync_function_delay_and_backoff(self) -> None:
        """Test that sync retry respects delay and backoff settings."""
        call_count = 0
        start_time = time.time()

        @retry_on_failure_sync(max_attempts=3, delay=0.1, backoff=2.0)
        def test_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = test_func()
        elapsed = time.time() - start_time

        assert result == "success"
        assert call_count == 3
        # Should have delayed: 0.1 + 0.2 = 0.3 seconds minimum
        assert elapsed >= 0.25  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_async_function_success_first_try(self) -> None:
        """Test async function that succeeds on first attempt."""
        call_count = 0

        @retry_on_failure_async(max_attempts=3, delay=0.01)
        async def test_func() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result: str = await test_func()

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_function_success_after_retries(self) -> None:
        """Test async function that succeeds after retries."""
        call_count = 0

        @retry_on_failure_async(max_attempts=3, delay=0.01)
        async def test_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result: str = await test_func()

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_async_function_failure_after_all_retries(self) -> None:
        """Test async function that fails after all retries."""
        call_count = 0

        @retry_on_failure_async(max_attempts=2, delay=0.01)
        async def test_func() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError(f"Failure attempt {call_count}")

        with pytest.raises(ValueError, match="Failure attempt 2"):
            await test_func()

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_async_function_delay_and_backoff(self) -> None:
        """Test that async retry respects delay and backoff settings."""
        call_count = 0
        start_time = time.time()

        @retry_on_failure_async(max_attempts=3, delay=0.1, backoff=2.0)
        async def test_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result: str = await test_func()
        elapsed = time.time() - start_time

        assert result == "success"
        assert call_count == 3
        # Should have delayed: 0.1 + 0.2 = 0.3 seconds minimum
        assert elapsed >= 0.25  # Allow some tolerance

    def test_decorator_preserves_function_metadata(self) -> None:
        """Test that decorator preserves original function metadata."""

        @retry_on_failure(max_attempts=2)
        def test_func() -> str:
            """Test function docstring."""
            return "success"

        assert test_func.__name__ == "test_func"
        assert test_func.__doc__ == "Test function docstring."

    def test_decorator_with_arguments(self) -> None:
        """Test decorator with function arguments."""
        call_count = 0

        @retry_on_failure_sync(max_attempts=2, delay=0.01)
        def test_func(x: int, y: str = "default") -> str:
            nonlocal call_count
            call_count += 1
            return f"{x}_{y}_{call_count}"

        result = test_func(42, y="test")

        assert result == "42_test_1"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_decorator_with_arguments(self) -> None:
        """Test async decorator with function arguments."""
        call_count = 0

        @retry_on_failure_async(max_attempts=2, delay=0.01)
        async def test_func(x: int, y: str = "default") -> str:
            nonlocal call_count
            call_count += 1
            return f"{x}_{y}_{call_count}"

        result: str = await test_func(42, y="test")

        assert result == "42_test_1"
        assert call_count == 1

    def test_logging_on_retries(self) -> None:
        """Test that retry attempts are logged properly."""
        call_count = 0

        @retry_on_failure_sync(max_attempts=3, delay=0.01)
        def test_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Attempt {call_count} failed")
            return "success"

        with patch("tests.utils.stability_helpers.logger") as mock_logger:
            assert isinstance(mock_logger, Mock)
            result = test_func()

            assert result == "success"
            assert call_count == 3

            # Should have logged warning for first two attempts
            assert mock_logger.warning.call_count == 2

            # Check warning messages
            warning_calls = mock_logger.warning.call_args_list
            assert "failed on attempt 1/3" in str(warning_calls[0])
            assert "failed on attempt 2/3" in str(warning_calls[1])

    def test_logging_on_final_failure(self) -> None:
        """Test that final failure is logged as error."""

        @retry_on_failure_sync(max_attempts=2, delay=0.01)
        def test_func() -> str:
            raise ValueError("Always fails")

        with patch("tests.utils.stability_helpers.logger") as mock_logger:
            assert isinstance(mock_logger, Mock)
            with pytest.raises(ValueError):
                test_func()

            # Should have logged one warning and one error
            assert mock_logger.warning.call_count == 1
            assert mock_logger.error.call_count == 1

            # Check error message
            error_call = mock_logger.error.call_args_list[0]
            assert "failed after 2 attempts" in str(error_call)

    @pytest.mark.asyncio
    async def test_async_logging_on_retries(self) -> None:
        """Test that async retry attempts are logged properly."""
        call_count = 0

        @retry_on_failure_async(max_attempts=3, delay=0.01)
        async def test_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Attempt {call_count} failed")
            return "success"

        with patch("tests.utils.stability_helpers.logger") as mock_logger:
            assert isinstance(mock_logger, Mock)
            result: str = await test_func()

            assert result == "success"
            assert call_count == 3
            assert mock_logger.warning.call_count == 2

    def test_custom_retry_parameters(self) -> None:
        """Test decorator with custom retry parameters."""
        call_count = 0

        @retry_on_failure(max_attempts=5, delay=0.05, backoff=3.0)
        def test_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise ValueError("Temporary failure")
            return "success"

        result = test_func()

        assert result == "success"
        assert call_count == 4

    def test_single_attempt_no_retry(self) -> None:
        """Test decorator with max_attempts=1 (no retry)."""
        call_count = 0

        @retry_on_failure_sync(max_attempts=1)
        def test_func() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("Single failure")

        with pytest.raises(ValueError, match="Single failure"):
            test_func()

        assert call_count == 1

    def test_zero_delay_retry(self) -> None:
        """Test decorator with zero delay between retries."""
        call_count = 0
        start_time = time.time()

        @retry_on_failure_sync(max_attempts=3, delay=0.0)
        def test_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = test_func()
        elapsed = time.time() - start_time

        assert result == "success"
        assert call_count == 3
        # Should complete very quickly with no delays
        assert elapsed < 0.1

    def test_exception_type_preservation(self) -> None:
        """Test that original exception type is preserved."""

        @retry_on_failure_sync(max_attempts=2, delay=0.01)
        def test_func() -> str:
            raise KeyError("Custom key error")

        with pytest.raises(KeyError, match="Custom key error"):
            test_func()

    @pytest.mark.asyncio
    async def test_async_exception_type_preservation(self) -> None:
        """Test that original async exception type is preserved."""

        @retry_on_failure_async(max_attempts=2, delay=0.01)
        async def test_func() -> str:
            raise KeyError("Custom key error")

        with pytest.raises(KeyError, match="Custom key error"):
            await test_func()

    def test_return_type_preservation(self) -> None:
        """Test that return type is preserved correctly."""

        @retry_on_failure_sync(max_attempts=2)
        def test_func_str() -> str:
            return "string"

        @retry_on_failure_sync(max_attempts=2)
        def test_func_int() -> int:
            return 42

        @retry_on_failure_sync(max_attempts=2)
        def test_func_dict() -> dict[str, int]:
            return {"key": 123}

        assert isinstance(test_func_str(), str)
        assert isinstance(test_func_int(), int)
        assert isinstance(test_func_dict(), dict)

    @pytest.mark.asyncio
    async def test_async_return_type_preservation(self) -> None:
        """Test that async return type is preserved correctly."""

        @retry_on_failure_async(max_attempts=2)
        async def test_func_str() -> str:
            return "string"

        @retry_on_failure_async(max_attempts=2)
        async def test_func_int() -> int:
            return 42

        result_str: str = await test_func_str()
        result_int: int = await test_func_int()

        assert isinstance(result_str, str)
        assert isinstance(result_int, int)


class TestStabilityHelpersIntegration:
    """Integration tests for stability helpers in realistic scenarios."""

    @pytest.mark.asyncio
    async def test_flaky_network_request_simulation(self) -> None:
        """Test retry decorator with simulated flaky network requests."""
        attempt_count = 0

        @retry_on_failure_async(max_attempts=4, delay=0.01, backoff=1.5)
        async def flaky_api_call() -> dict[str, object]:
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count <= 2:
                raise ConnectionError(f"Network error on attempt {attempt_count}")

            return {"status": "success", "data": "response"}

        result: dict[str, object] = await flaky_api_call()

        assert result == {"status": "success", "data": "response"}
        assert attempt_count == 3

    def test_flaky_file_operation_simulation(self) -> None:
        """Test retry decorator with simulated flaky file operations."""
        attempt_count = 0

        @retry_on_failure_sync(max_attempts=3, delay=0.01)
        def flaky_file_read() -> str:
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count == 1:
                raise FileNotFoundError("File temporarily unavailable")
            elif attempt_count == 2:
                raise PermissionError("Permission denied")

            return "file contents"

        result = flaky_file_read()

        assert result == "file contents"
        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_database_connection_retry_simulation(self) -> None:
        """Test retry decorator with simulated database connection issues."""
        attempt_count = 0

        @retry_on_failure_async(max_attempts=5, delay=0.01, backoff=2.0)
        async def connect_to_database() -> bool:
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count <= 3:
                raise ConnectionError("Database unavailable")

            return True

        result: bool = await connect_to_database()

        assert result is True
        assert attempt_count == 4

    def test_nested_retry_decorators(self) -> None:
        """Test behavior with nested retry decorators (should work independently)."""
        outer_attempts = 0
        inner_attempts = 0

        @retry_on_failure_sync(max_attempts=2, delay=0.01)
        def outer_func() -> str:
            nonlocal outer_attempts
            outer_attempts += 1

            @retry_on_failure_sync(max_attempts=2, delay=0.01)
            def inner_func() -> str:
                nonlocal inner_attempts
                inner_attempts += 1
                if inner_attempts < 2:
                    raise ValueError("Inner failure")
                return "inner success"

            if outer_attempts < 2:
                # This will succeed after inner retry
                inner_result = inner_func()
                raise RuntimeError("Outer failure after inner success")

            inner_result = inner_func()
            assert isinstance(inner_result, str)
            return inner_result

        result = outer_func()

        assert result == "inner success"
        assert outer_attempts == 2
        assert inner_attempts == 3  # 2 from first outer attempt + 1 from second
