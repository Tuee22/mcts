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
    """E2E test configuration."""
    return E2EConfig(
        backend_url=os.environ.get("E2E_BACKEND_URL", "http://localhost:8002"),
        frontend_url=os.environ.get("E2E_FRONTEND_URL", "http://localhost:3002"),
        ws_url=os.environ.get("E2E_WS_URL", "ws://localhost:8002/ws"),
        headless=os.environ.get("E2E_HEADLESS", "true").lower() == "true",
        slow_mo=int(os.environ.get("E2E_SLOW_MO", "0")),
        timeout=int(os.environ.get("E2E_TIMEOUT", "30000")),
        screenshot_on_failure=True,
        video=os.environ.get("E2E_VIDEO", "retain-on-failure"),
        trace=os.environ.get("E2E_TRACE", "retain-on-failure"),
    )


@pytest.fixture(scope="session")
def backend_e2e_server(
    e2e_config: E2EConfig,
) -> Generator[Optional[subprocess.Popen[bytes]], None, None]:
    """Start backend server for E2E tests if not already running."""
    # Check if server is already running
    try:
        response = requests.get(f"{e2e_config['backend_url']}/health", timeout=2)
        if response.status_code == 200:
            print("Backend server already running, reusing existing server")
            yield None
            return
    except Exception:
        pass

    port = e2e_config["backend_url"].split(":")[-1]
    env = os.environ.copy()
    env.update(
        {
            "MCTS_API_HOST": "0.0.0.0",
            "MCTS_API_PORT": port,
            "MCTS_CORS_ORIGINS": "*",  # Allow all origins for E2E tests
        }
    )

    # Start backend server
    process: subprocess.Popen[bytes] = subprocess.Popen(
        [
            "python",
            "-m",
            "uvicorn",
            "backend.api.server:app",
            "--host",
            "0.0.0.0",
            "--port",
            port,
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to be ready
    print(f"Starting backend server on port {port}...")
    max_retries = 60  # Increased retries
    for i in range(max_retries):
        try:
            response = requests.get(f"{e2e_config['backend_url']}/health", timeout=2)
            if response.status_code == 200:
                print(f"✅ Backend server ready on {e2e_config['backend_url']}")
                break
        except Exception as e:
            if i % 10 == 0:  # Print progress every 10 attempts
                print(f"Waiting for backend server... attempt {i+1}/{max_retries}")
            time.sleep(1.0)  # Increased wait time
    else:
        # Get error output before terminating
        stdout, stderr = process.communicate(timeout=5)
        print(f"Backend server stdout: {stdout.decode() if stdout else 'None'}")
        print(f"Backend server stderr: {stderr.decode() if stderr else 'None'}")
        process.terminate()
        raise RuntimeError("Backend server failed to start for E2E tests")

    yield process

    # Cleanup
    print("Stopping backend server...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


@pytest.fixture(scope="session")
def frontend_e2e_server(
    e2e_config: E2EConfig,
    backend_e2e_server: Optional[subprocess.Popen[bytes]],
) -> Generator[Optional[subprocess.Popen[bytes]], None, None]:
    """Start frontend server for E2E tests if not already running."""
    # Check if server is already running
    try:
        response = requests.get(e2e_config["frontend_url"], timeout=2)
        if response.status_code == 200:
            print("Frontend server already running, reusing existing server")
            yield None
            return
    except Exception:
        pass

    port = e2e_config["frontend_url"].split(":")[-1]
    env = os.environ.copy()
    env.update(
        {
            "REACT_APP_API_URL": e2e_config["backend_url"],
            "REACT_APP_WS_URL": e2e_config["ws_url"],
            "PORT": port,
        }
    )

    # Build frontend if not already built
    if not os.path.exists("frontend/build"):
        print("Building frontend...")
        result = subprocess.run(["npm", "run", "build"], cwd="frontend", env=env)
        if result.returncode != 0:
            print("Warning: Frontend build failed, continuing anyway")

    # Start frontend server using serve
    print(f"Starting frontend server on port {port}...")
    process: subprocess.Popen[bytes] = subprocess.Popen(
        ["npx", "serve", "-s", "build", "-l", port],
        cwd="frontend",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to be ready
    max_retries = 60  # Increased retries
    for i in range(max_retries):
        try:
            response = requests.get(e2e_config["frontend_url"], timeout=2)
            if response.status_code == 200:
                print(f"✅ Frontend server ready on {e2e_config['frontend_url']}")
                break
        except Exception:
            if i % 10 == 0:  # Print progress every 10 attempts
                print(f"Waiting for frontend server... attempt {i+1}/{max_retries}")
            time.sleep(1.0)
    else:
        # Get error output before terminating
        stdout, stderr = process.communicate(timeout=5)
        print(f"Frontend server stdout: {stdout.decode() if stdout else 'None'}")
        print(f"Frontend server stderr: {stderr.decode() if stderr else 'None'}")
        process.terminate()
        raise RuntimeError("Frontend server failed to start for E2E tests")

    yield process

    # Cleanup
    print("Stopping frontend server...")
    if process:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


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
