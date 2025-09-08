"""Pytest configuration for E2E tests with Playwright."""

import asyncio
import os
import subprocess
import time
from typing import (
    TYPE_CHECKING,
    AsyncGenerator,
    Awaitable,
    Callable,
    Dict,
    Generator,
    Optional,
    TypedDict,
    Union,
)

from _pytest.fixtures import FixtureRequest

if TYPE_CHECKING:
    from pytest import Item

import pytest
import requests
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import Timeout as RequestsTimeout
from playwright.async_api import Browser, BrowserContext, Page, async_playwright


class E2EConfig(TypedDict):
    backend_url: str
    frontend_url: str
    ws_url: str
    headless: bool
    slow_mo: int
    timeout: int
    screenshot_on_failure: bool
    video: str
    trace: str


@pytest.fixture(scope="session")
def e2e_config() -> E2EConfig:
    """E2E test configuration - uses Docker container server on port 8000."""
    return E2EConfig(
        backend_url=os.environ.get("E2E_BACKEND_URL", "http://127.0.0.1:8000"),
        frontend_url=os.environ.get("E2E_FRONTEND_URL", "http://127.0.0.1:8000"),
        ws_url=os.environ.get("E2E_WS_URL", "ws://127.0.0.1:8000/ws"),
        headless=os.environ.get("E2E_HEADLESS", "true").lower() == "true",
        slow_mo=int(os.environ.get("E2E_SLOW_MO", "0")),
        timeout=int(os.environ.get("E2E_TIMEOUT", "30000")),
        screenshot_on_failure=True,
        video=os.environ.get("E2E_VIDEO", "retain-on-failure"),
        trace=os.environ.get("E2E_TRACE", "retain-on-failure"),
    )


# Import async fixtures for Playwright
from .async_fixtures import async_page, browser, context, e2e_urls  # noqa: F401

# Moved to async_fixtures.py
# @pytest.fixture
# def e2e_urls(
#     e2e_config: E2EConfig,
#     frontend_e2e_server: Optional[subprocess.Popen[bytes]],
# ) -> Dict[str, str]:
#     """Provide URLs for E2E tests."""
#     return {
#         "frontend": e2e_config["frontend_url"],
#         "backend": e2e_config["backend_url"],
#         "ws": e2e_config["ws_url"],
#     }


# Note: pytest hook disabled to avoid Any types in strict mode
# @pytest.hookimpl(tryfirst=True, hookwrapper=True)
# def pytest_runtest_makereport(item: object, call: object) -> Generator[None, None, None]:
#     """Make test results available to fixtures."""
#     outcome = yield
#     # Hook would access dynamic attributes that return Any types


@pytest.fixture
async def wait_for_connection(
    page: Page,
) -> Callable[[], Awaitable[None]]:
    """Helper to wait for WebSocket connection."""

    async def _wait() -> None:
        # Wait for connection indicator to show "Connected"
        await page.wait_for_selector(
            '[data-testid="connection-text"]:has-text("Connected")',
            state="visible",
            timeout=10000,
        )

    return _wait


@pytest.fixture
async def create_game(
    page: Page, wait_for_connection: Callable[[], Awaitable[None]]
) -> Callable[[str, str], Awaitable[None]]:
    """Helper to create a new game."""

    async def _create(mode: str = "human_vs_ai", difficulty: str = "medium") -> None:
        await wait_for_connection()

        # Click game settings if not already open
        settings_button = page.locator('button:has-text("⚙️ Game Settings")')
        if await settings_button.is_visible():
            await settings_button.click()

        # Select game mode
        await page.click(f'[data-testid="mode-{mode.replace("_", "-")}"]')

        # Select difficulty if AI is involved
        if mode != "human_vs_human" and difficulty:
            await page.click(f'button:has-text("{difficulty.capitalize()}")')

        # Start game
        await page.click('[data-testid="start-game-button"]')

        # Wait for game to start
        await page.wait_for_selector('[data-testid="game-container"]', state="visible")

    return _create
