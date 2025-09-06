"""Utilities for preventing test flakiness and improving stability."""

import asyncio
import functools
import logging
import os
import time
import uuid
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Optional,
    ParamSpec,
    Set,
    TypeVar,
    Union,
    overload,
)

import pytest
from playwright.async_api import Page

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")
F = TypeVar("F")


def retry_on_failure_sync(
    max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to retry flaky sync test functions with exponential backoff."""

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception: Optional[Exception] = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Test {func.__name__} failed on attempt {attempt + 1}/{max_attempts}: {e}"
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"Test {func.__name__} failed after {max_attempts} attempts"
                        )

            if last_exception is not None:
                raise last_exception
            raise RuntimeError("Unexpected failure in sync retry decorator")

        return sync_wrapper

    return decorator


def retry_on_failure_async(
    max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Decorator to retry flaky async test functions with exponential backoff."""

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception: Optional[Exception] = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Test {func.__name__} failed on attempt {attempt + 1}/{max_attempts}: {e}"
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"Test {func.__name__} failed after {max_attempts} attempts"
                        )

            if last_exception is not None:
                raise last_exception
            raise RuntimeError("Unexpected failure in async retry decorator")

        return async_wrapper

    return decorator


# Legacy compatibility function - detect sync vs async and call appropriate decorator
def retry_on_failure(
    max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0
) -> Callable[
    [Callable[P, Union[T, Awaitable[T]]]], Callable[P, Union[T, Awaitable[T]]]
]:
    """Decorator to retry flaky test functions with exponential backoff."""

    def decorator(
        func: Callable[P, Union[T, Awaitable[T]]]
    ) -> Callable[P, Union[T, Awaitable[T]]]:
        if asyncio.iscoroutinefunction(func):
            async_func = func  # This is guaranteed to be async by the check above
            return retry_on_failure_async(max_attempts, delay, backoff)(async_func)
        else:
            sync_func = func  # This is guaranteed to be sync by the check above
            return retry_on_failure_sync(max_attempts, delay, backoff)(sync_func)

    return decorator


class StabilityWaits:
    """Helper class for stable waiting patterns in tests."""

    @staticmethod
    async def wait_for_element_stable(
        page: Page, selector: str, timeout: int = 10000, stable_time: int = 1000
    ) -> None:
        """Wait for element to be visible and stable (not changing) for specified time."""
        await page.wait_for_selector(selector, state="visible", timeout=timeout)

        # Wait for element to be stable
        last_content: Optional[str] = None
        stable_start: Optional[float] = None

        while True:
            current_content = await page.locator(selector).text_content()
            current_time = time.time() * 1000  # Convert to milliseconds

            if current_content == last_content:
                if stable_start is None:
                    stable_start = current_time
                elif current_time - stable_start >= stable_time:
                    break  # Element has been stable for required time
            else:
                stable_start = None  # Reset stability timer
                last_content = current_content

            await asyncio.sleep(0.1)  # Small delay between checks

    @staticmethod
    async def wait_for_network_idle(page: Page, timeout: int = 5000) -> None:
        """Wait for network to be idle (no requests for specified time)."""
        try:
            await page.wait_for_load_state("networkidle", timeout=timeout)
        except Exception as e:
            logger.warning(f"Network idle wait timed out: {e}")

    @staticmethod
    async def wait_for_connection_ready(page: Page, timeout: int = 10000) -> None:
        """Wait for WebSocket connection to be established and ready."""
        # Wait for connection indicator
        await page.wait_for_selector(
            '[data-testid="connection-text"]:has-text("Connected")', timeout=timeout
        )

        # Additional stability wait
        await StabilityWaits.wait_for_element_stable(
            page, '[data-testid="connection-text"]', stable_time=500
        )

    @staticmethod
    async def wait_for_game_ready(page: Page, timeout: int = 15000) -> None:
        """Wait for game to be fully loaded and ready for interaction."""
        # Wait for game container
        await page.wait_for_selector('[data-testid="game-container"]', timeout=timeout)

        # Wait for network idle to ensure all assets loaded
        await StabilityWaits.wait_for_network_idle(page)

        # Wait for any loading indicators to disappear
        loading_selectors = [
            'text="Loading..."',
            'text="Starting..."',
            ".loading",
            ".spinner",
        ]

        for selector in loading_selectors:
            try:
                await page.wait_for_selector(selector, state="hidden", timeout=2000)
            except Exception:
                pass  # Ignore if selector doesn't exist


class PortManager:
    """Utility to manage test ports and avoid conflicts."""

    _used_ports: Set[int] = set()
    _base_api_port: int = 8000
    _base_frontend_port: int = 3000

    @classmethod
    def get_available_api_port(cls) -> int:
        """Get an available API port for testing."""
        port = cls._base_api_port
        while port in cls._used_ports:
            port += 1
        cls._used_ports.add(port)
        return port

    @classmethod
    def get_available_frontend_port(cls) -> int:
        """Get an available frontend port for testing."""
        port = cls._base_frontend_port
        while port in cls._used_ports:
            port += 1
        cls._used_ports.add(port)
        return port

    @classmethod
    def release_port(cls, port: int) -> None:
        """Release a port back to available pool."""
        cls._used_ports.discard(port)

    @classmethod
    def get_test_config(cls) -> Dict[str, Union[str, int]]:
        """Get test configuration with unique ports."""
        api_port = cls.get_available_api_port()
        frontend_port = cls.get_available_frontend_port()

        return {
            "api_host": "127.0.0.1",
            "api_port": api_port,
            "frontend_host": "127.0.0.1",
            "frontend_port": frontend_port,
            "ws_url": f"ws://127.0.0.1:{api_port}/ws",
            "backend_url": f"http://127.0.0.1:{api_port}",
            "frontend_url": f"http://127.0.0.1:{frontend_port}",
        }


class TestDataIsolation:
    """Utilities for ensuring test data isolation."""

    @staticmethod
    def generate_test_id(prefix: str = "test") -> str:
        """Generate unique test ID with timestamp."""

        return f"{prefix}-{int(time.time())}-{uuid.uuid4().hex[:8]}"

    @staticmethod
    def create_isolated_game_config(name_prefix: str = "isolated") -> Dict[str, object]:
        """Create game config with isolated player names."""
        test_id = TestDataIsolation.generate_test_id()
        return {
            "player1_type": "human",
            "player2_type": "human",
            "player1_name": f"{name_prefix}_p1_{test_id}",
            "player2_name": f"{name_prefix}_p2_{test_id}",
            "settings": {"board_size": 9, "time_limit_seconds": 30},
        }


def quarantine(reason: str) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to mark tests as quarantined due to flakiness."""

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        # Mark test as skipped with quarantine reason
        # We know pytest.mark.skip preserves the function signature
        marked_func = pytest.mark.skip(reason=f"Quarantined: {reason}")(func)
        # Use a controlled assertion to convince mypy
        if not callable(marked_func):
            raise TypeError("pytest.mark.skip should return a callable")
        # Since we verified it's callable and pytest preserves signatures, this is safe
        return marked_func

    return decorator


def flaky_on_ci(
    reason: str = "Flaky on CI",
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to skip tests that are flaky specifically on CI."""

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        if os.environ.get("CI") == "true":
            # We know pytest.mark.skip preserves the function signature
            marked_func = pytest.mark.skip(reason=f"Skipped on CI: {reason}")(func)
            # Use a controlled assertion to convince mypy
            if not callable(marked_func):
                raise TypeError("pytest.mark.skip should return a callable")
            # Since we verified it's callable and pytest preserves signatures, this is safe
            return marked_func
        return func

    return decorator


class AssertionHelpers:
    """Enhanced assertions for better test stability."""

    @staticmethod
    async def assert_eventually(
        assertion_func: Callable[[], Awaitable[bool]],
        timeout: float = 5.0,
        interval: float = 0.1,
        message: str = "Assertion failed within timeout",
    ) -> None:
        """Assert that condition becomes true within timeout."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                if await assertion_func():
                    return
            except Exception:
                pass  # Ignore exceptions during polling

            await asyncio.sleep(interval)

        # Final attempt with proper exception propagation
        if not await assertion_func():
            raise AssertionError(message)

    @staticmethod
    def assert_eventually_sync(
        assertion_func: Callable[[], bool],
        timeout: float = 5.0,
        interval: float = 0.1,
        message: str = "Assertion failed within timeout",
    ) -> None:
        """Synchronous version of assert_eventually."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                if assertion_func():
                    return
            except Exception:
                pass

            time.sleep(interval)

        if not assertion_func():
            raise AssertionError(message)


class BrowserStabilityHelpers:
    """Playwright-specific stability helpers."""

    @staticmethod
    async def click_with_retry(
        page: Page, selector: str, max_attempts: int = 3
    ) -> None:
        """Click element with retries if it becomes detached."""
        for attempt in range(max_attempts):
            try:
                await page.click(selector)
                return
            except Exception as e:
                if attempt < max_attempts - 1 and "detached" in str(e).lower():
                    await asyncio.sleep(0.5)
                    continue
                raise

    @staticmethod
    async def type_with_retry(
        page: Page, selector: str, text: str, max_attempts: int = 3
    ) -> None:
        """Type text with retries if element becomes detached."""
        for attempt in range(max_attempts):
            try:
                await page.fill(selector, text)
                return
            except Exception as e:
                if attempt < max_attempts - 1 and "detached" in str(e).lower():
                    await asyncio.sleep(0.5)
                    continue
                raise

    @staticmethod
    async def ensure_element_ready(
        page: Page, selector: str, timeout: int = 5000
    ) -> None:
        """Ensure element is ready for interaction."""
        locator = page.locator(selector)

        # Wait for element to be attached
        await locator.wait_for(state="attached", timeout=timeout)

        # Wait for element to be visible
        await locator.wait_for(state="visible", timeout=timeout)

        # Ensure element is enabled if it's a form control
        try:
            if await locator.is_enabled():
                # Wait a bit more for stability
                await asyncio.sleep(0.1)
        except Exception:
            pass  # Not a form control
