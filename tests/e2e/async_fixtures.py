"""Async fixtures for E2E tests using Playwright."""

import os
from typing import AsyncGenerator, Dict

import pytest
import pytest_asyncio
from playwright.async_api import Browser, BrowserContext, Page, async_playwright


@pytest_asyncio.fixture(scope="function")
async def browser() -> AsyncGenerator[Browser, None]:
    """Create and yield a browser instance."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=os.environ.get("E2E_HEADLESS", "true").lower() == "true",
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
            ],
        )
        yield browser
        await browser.close()


@pytest_asyncio.fixture
async def context(browser: Browser) -> AsyncGenerator[BrowserContext, None]:
    """Create a new browser context for each test."""
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        ignore_https_errors=True,
    )
    yield context
    await context.close()


@pytest_asyncio.fixture
async def touch_context(browser: Browser) -> AsyncGenerator[BrowserContext, None]:
    """Create a new browser context with touch support for mobile tests."""
    context = await browser.new_context(
        viewport={"width": 375, "height": 667},  # Mobile viewport
        ignore_https_errors=True,
        has_touch=True,  # Enable touch support
        is_mobile=True,
        device_scale_factor=2,
    )
    yield context
    await context.close()


@pytest_asyncio.fixture
async def async_page(context: BrowserContext) -> AsyncGenerator[Page, None]:
    """Create a new page for each test."""
    page = await context.new_page()
    # Set reasonable timeouts
    page.set_default_timeout(30000)
    page.set_default_navigation_timeout(30000)
    yield page
    await page.close()


@pytest_asyncio.fixture
async def touch_page(touch_context: BrowserContext) -> AsyncGenerator[Page, None]:
    """Create a new page with touch support for mobile tests."""
    page = await touch_context.new_page()
    # Set reasonable timeouts
    page.set_default_timeout(30000)
    page.set_default_navigation_timeout(30000)
    yield page
    await page.close()


@pytest.fixture
def e2e_urls(
    e2e_config: Dict[str, object],
) -> Dict[str, str]:
    """E2E Test URLs - uses Docker container server."""
    return {
        "frontend": str(e2e_config["frontend_url"]),
        "backend": str(e2e_config["backend_url"]),
        "ws": str(e2e_config["ws_url"]),
    }
