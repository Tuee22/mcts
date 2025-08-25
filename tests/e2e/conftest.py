"""Pytest configuration for E2E tests with Playwright."""

import asyncio
import os
import subprocess
import time
from typing import (
    Dict,
    Generator,
    Union,
    Callable,
    Awaitable,
    AsyncGenerator,
    TypedDict,
)
from _pytest.fixtures import FixtureRequest
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest import Item

import pytest
import requests
from playwright.async_api import async_playwright, Browser, BrowserContext, Page


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
) -> Generator[subprocess.Popen[bytes], None, None]:
    """Start backend server for E2E tests."""
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
    process = subprocess.Popen(
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

    max_retries = 30
    for _ in range(max_retries):
        try:
            response = requests.get(f"{e2e_config['backend_url']}/health")
            if response.status_code == 200:
                break
        except Exception:
            time.sleep(0.5)
    else:
        process.terminate()
        raise RuntimeError("Backend server failed to start for E2E tests")

    yield process

    # Cleanup
    process.terminate()
    process.wait(timeout=5)


@pytest.fixture(scope="session")
def frontend_e2e_server(
    e2e_config: E2EConfig,
    backend_e2e_server: subprocess.Popen[bytes],
) -> Generator[subprocess.Popen[bytes], None, None]:
    """Start frontend server for E2E tests."""
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
        subprocess.run(["npm", "run", "build"], cwd="frontend", env=env, check=True)

    # Start frontend server using serve
    process = subprocess.Popen(
        ["npx", "serve", "-s", "build", "-l", port],
        cwd="frontend",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to be ready

    max_retries = 30
    for _ in range(max_retries):
        try:
            response = requests.get(e2e_config["frontend_url"])
            if response.status_code == 200:
                break
        except Exception:
            time.sleep(0.5)
    else:
        process.terminate()
        raise RuntimeError("Frontend server failed to start for E2E tests")

    yield process

    # Cleanup
    process.terminate()
    process.wait(timeout=5)


@pytest.fixture(scope="session")
async def browser(e2e_config: E2EConfig) -> AsyncGenerator[Browser, None]:
    """Create Playwright browser instance."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=e2e_config["headless"],
            slow_mo=e2e_config["slow_mo"],
        )
        yield browser
        await browser.close()


@pytest.fixture
async def context(
    browser: Browser,
    e2e_config: E2EConfig,
    request: FixtureRequest,
) -> AsyncGenerator[BrowserContext, None]:
    """Create browser context with video and tracing."""
    # Create context with basic options
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        ignore_https_errors=True,
        record_video_dir=(
            f"tests/e2e/videos/{request.node.name}" if e2e_config["video"] else None
        ),
        record_video_size={"width": 1280, "height": 720}
        if e2e_config["video"]
        else None,
    )

    # Start tracing
    if e2e_config["trace"]:
        await context.tracing.start(screenshots=True, snapshots=True, sources=True)

    # Set default timeout
    context.set_default_timeout(e2e_config["timeout"])

    yield context

    # Save trace on failure
    if e2e_config["trace"] and request.node.rep_call.failed:
        test_name = request.node.name
        await context.tracing.stop(path=f"tests/e2e/traces/{test_name}.zip")

    await context.close()


@pytest.fixture
async def page(
    context: BrowserContext,
    e2e_config: E2EConfig,
    request: FixtureRequest,
) -> AsyncGenerator[Page, None]:
    """Create page and handle screenshots on failure."""
    page = await context.new_page()

    yield page

    # Take screenshot on failure
    if (
        e2e_config["screenshot_on_failure"]
        and hasattr(request.node, "rep_call")
        and request.node.rep_call.failed
    ):
        test_name = request.node.name
        await page.screenshot(
            path=f"tests/e2e/screenshots/{test_name}.png", full_page=True
        )


@pytest.fixture
def e2e_urls(
    e2e_config: E2EConfig,
    frontend_e2e_server: subprocess.Popen[bytes],
) -> Dict[str, str]:
    """Provide URLs for E2E tests."""
    return {
        "frontend": e2e_config["frontend_url"],
        "backend": e2e_config["backend_url"],
        "ws": e2e_config["ws_url"],
    }


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(
    item: object, call: object
) -> Generator[None, None, None]:
    """Make test results available to fixtures."""
    outcome = yield
    rep = getattr(outcome, "get_result", lambda: None)()
    if rep is not None and hasattr(rep, "when"):
        setattr(item, "rep_" + rep.when, rep)


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
