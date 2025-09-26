"""Async fixtures for E2E tests using Playwright."""

import os
from typing import AsyncGenerator, Dict, List

import pytest
import pytest_asyncio
from _pytest.fixtures import FixtureRequest
from playwright.async_api import Browser, BrowserContext, Page, async_playwright


# Browser-specific compatibility configuration
# Centralized handling of all browser differences to ensure tests remain browser-agnostic

# Mobile emulation support
# IMPORTANT: Firefox does not support the is_mobile flag in Playwright.
# This limitation is a known Playwright issue where Firefox's browser.new_context()
# raises an error when is_mobile=True is passed. We explicitly set this to False
# for Firefox to ensure cross-browser compatibility.
BROWSER_MOBILE_SUPPORT: Dict[str, bool] = {
    "chromium": True,  # Chromium supports full mobile emulation
    "firefox": False,  # Firefox does NOT support is_mobile flag
    "webkit": True,  # Webkit supports full mobile emulation
}

# Browser-specific launch arguments
# Chromium needs sandbox disabling in containerized environments
BROWSER_LAUNCH_ARGS: Dict[str, List[str]] = {
    "chromium": [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
    ],
    "firefox": [],  # Firefox doesn't need special container args
    "webkit": [],  # Webkit doesn't need special container args
}

# Base mobile context configuration (without browser-specific flags)
MOBILE_CONTEXT_BASE = {
    "viewport": {"width": 375, "height": 667},  # iPhone-like viewport
    "ignore_https_errors": True,
    "has_touch": True,  # Touch events work in all browsers
    "device_scale_factor": 2,  # 2x pixel density for retina displays
}


@pytest_asyncio.fixture(scope="function", params=["chromium", "firefox", "webkit"])
async def browser(request: FixtureRequest) -> AsyncGenerator[Browser, None]:
    """Create and yield a browser instance for each browser type with appropriate launch args."""
    browser_name = request.param
    assert isinstance(
        browser_name, str
    ), f"Expected string browser name, got {type(browser_name)}"

    async with async_playwright() as p:
        if not hasattr(p, browser_name):
            pytest.fail(f"Browser {browser_name} not available in Playwright")

        launcher = getattr(p, browser_name)
        # Get browser-specific launch arguments from centralized config
        launch_args = BROWSER_LAUNCH_ARGS.get(browser_name, [])

        browser = await launcher.launch(
            headless=os.environ.get("E2E_HEADLESS", "true").lower() == "true",
            args=launch_args,
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
    """Create a new browser context with touch support for mobile tests.

    Note: Firefox does not support the is_mobile flag, so it's explicitly set
    to False for Firefox while True for Chromium and Webkit. This ensures
    cross-browser compatibility while maintaining the best possible mobile
    emulation for each browser.
    """
    # Get browser name and look up its mobile support capability
    browser_name = browser.browser_type.name

    # Build context options using functional composition
    # This will raise KeyError if an unknown browser is used (intentional - fail loudly)
    context_options = {
        **MOBILE_CONTEXT_BASE,
        "is_mobile": BROWSER_MOBILE_SUPPORT[browser_name],  # No fallback - fail loudly
    }

    context = await browser.new_context(**context_options)
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
async def page(context: BrowserContext) -> AsyncGenerator[Page, None]:
    """
    Standard page fixture that runs on all browsers.

    This is the primary fixture that all e2e tests should use.
    It automatically runs tests across all 3 browsers (Chromium, Firefox, WebKit)
    with all browser-specific compatibility handled transparently.
    """
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
