"""
Demonstration of generic cross-browser e2e testing.

This test shows how simple it is to write tests that automatically run
on all 3 browsers (Chromium, Firefox, WebKit) without any browser-specific code.
"""

from typing import Dict

import pytest
from playwright.async_api import Page, expect


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cross_browser_demo(page: Page, e2e_urls: Dict[str, str]) -> None:
    """
    Demo test that runs on all 3 browsers automatically.

    This test demonstrates the new fixture system:
    - No manual browser setup/teardown
    - No browser-specific code
    - All browser compatibility handled transparently
    - Runs on Chromium, Firefox, and WebKit automatically
    """
    # Navigate to the frontend
    await page.goto(e2e_urls["frontend"], timeout=30000)

    # Wait for the page to load
    await page.wait_for_load_state("networkidle", timeout=15000)

    # Basic assertions that should work across all browsers
    title = await page.title()
    assert title == "React App"

    # Check that the app root element exists
    app_root = page.locator("#root")
    await expect(app_root).to_be_visible(timeout=5000)

    # Test that we can make API requests from any browser
    response = await page.request.get(f"{e2e_urls['backend']}/health")
    assert response.ok

    health_data = await response.json()
    assert health_data["status"] == "healthy"

    # The test framework handles all browser differences:
    # - Launch arguments (--no-sandbox for Chromium)
    # - Mobile emulation support (Firefox limitation)
    # - Context configuration
    # - Cleanup

    print(f"✅ Cross-browser test completed successfully")
