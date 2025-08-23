"""Pytest configuration for E2E tests with Playwright."""

import asyncio
import os
import subprocess
import time
from typing import Dict, Generator

import pytest
from playwright.async_api import async_playwright, Browser, BrowserContext, Page


@pytest.fixture(scope="session")
def e2e_config() -> Dict[str, any]:
    """E2E test configuration."""
    return {
        "backend_url": os.environ.get("E2E_BACKEND_URL", "http://localhost:8002"),
        "frontend_url": os.environ.get("E2E_FRONTEND_URL", "http://localhost:3002"),
        "ws_url": os.environ.get("E2E_WS_URL", "ws://localhost:8002/ws"),
        "headless": os.environ.get("E2E_HEADLESS", "true").lower() == "true",
        "slow_mo": int(os.environ.get("E2E_SLOW_MO", "0")),
        "timeout": int(os.environ.get("E2E_TIMEOUT", "30000")),
        "screenshot_on_failure": True,
        "video": os.environ.get("E2E_VIDEO", "retain-on-failure"),
        "trace": os.environ.get("E2E_TRACE", "retain-on-failure"),
    }


@pytest.fixture(scope="session")
def backend_e2e_server(e2e_config):
    """Start backend server for E2E tests."""
    port = e2e_config["backend_url"].split(":")[-1]
    env = os.environ.copy()
    env.update({
        "MCTS_API_HOST": "0.0.0.0",
        "MCTS_API_PORT": port,
        "MCTS_CORS_ORIGINS": "*",  # Allow all origins for E2E tests
    })
    
    # Start backend server
    process = subprocess.Popen(
        ["python", "-m", "uvicorn", "backend.api.server:app",
         "--host", "0.0.0.0",
         "--port", port],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to be ready
    import requests
    max_retries = 30
    for _ in range(max_retries):
        try:
            response = requests.get(f"{e2e_config['backend_url']}/health")
            if response.status_code == 200:
                break
        except:
            time.sleep(0.5)
    else:
        process.terminate()
        raise RuntimeError("Backend server failed to start for E2E tests")
    
    yield process
    
    # Cleanup
    process.terminate()
    process.wait(timeout=5)


@pytest.fixture(scope="session")
def frontend_e2e_server(e2e_config, backend_e2e_server):
    """Start frontend server for E2E tests."""
    port = e2e_config["frontend_url"].split(":")[-1]
    env = os.environ.copy()
    env.update({
        "REACT_APP_API_URL": e2e_config["backend_url"],
        "REACT_APP_WS_URL": e2e_config["ws_url"],
        "PORT": port,
    })
    
    # Build frontend if not already built
    if not os.path.exists("frontend/build"):
        subprocess.run(
            ["npm", "run", "build"],
            cwd="frontend",
            env=env,
            check=True
        )
    
    # Start frontend server using serve
    process = subprocess.Popen(
        ["npx", "serve", "-s", "build", "-l", port],
        cwd="frontend",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to be ready
    import requests
    max_retries = 30
    for _ in range(max_retries):
        try:
            response = requests.get(e2e_config["frontend_url"])
            if response.status_code == 200:
                break
        except:
            time.sleep(0.5)
    else:
        process.terminate()
        raise RuntimeError("Frontend server failed to start for E2E tests")
    
    yield process
    
    # Cleanup
    process.terminate()
    process.wait(timeout=5)


@pytest.fixture(scope="session")
async def browser(e2e_config):
    """Create Playwright browser instance."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=e2e_config["headless"],
            slow_mo=e2e_config["slow_mo"],
        )
        yield browser
        await browser.close()


@pytest.fixture
async def context(browser: Browser, e2e_config, request):
    """Create browser context with video and tracing."""
    context_options = {
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
    }
    
    # Add video recording
    if e2e_config["video"]:
        test_name = request.node.name
        context_options["record_video_dir"] = f"tests/e2e/videos/{test_name}"
        context_options["record_video_size"] = {"width": 1280, "height": 720}
    
    context = await browser.new_context(**context_options)
    
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
async def page(context: BrowserContext, e2e_config, request):
    """Create page and handle screenshots on failure."""
    page = await context.new_page()
    
    yield page
    
    # Take screenshot on failure
    if e2e_config["screenshot_on_failure"] and hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        test_name = request.node.name
        await page.screenshot(path=f"tests/e2e/screenshots/{test_name}.png", full_page=True)


@pytest.fixture
def e2e_urls(e2e_config, frontend_e2e_server):
    """Provide URLs for E2E tests."""
    return {
        "frontend": e2e_config["frontend_url"],
        "backend": e2e_config["backend_url"],
        "ws": e2e_config["ws_url"],
    }


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Make test results available to fixtures."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)


@pytest.fixture
async def wait_for_connection(page: Page):
    """Helper to wait for WebSocket connection."""
    async def _wait():
        # Wait for connection indicator to show "Connected"
        await page.wait_for_selector('[data-testid="connection-text"]:has-text("Connected")', 
                                    state="visible", 
                                    timeout=10000)
    return _wait


@pytest.fixture
async def create_game(page: Page, wait_for_connection):
    """Helper to create a new game."""
    async def _create(mode="human_vs_ai", difficulty="medium"):
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