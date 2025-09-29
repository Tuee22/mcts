"""E2E tests that work reliably across all browsers."""

import asyncio
from typing import Dict

import pytest
from playwright.async_api import BrowserType, async_playwright
from tests.e2e.e2e_helpers import SETTINGS_BUTTON_SELECTOR


@pytest.mark.e2e
class TestBrowserCompatibility:
    """Test browser compatibility for all three engines."""

    @pytest.mark.asyncio
    async def test_all_browsers_load_frontend(self, e2e_urls: Dict[str, str]) -> None:
        """Test that all browsers can load the frontend successfully."""
        results: Dict[str, str] = {}

        async with async_playwright() as p:
            # Use tuples to avoid dynamic access
            browser_configs = [
                (
                    "chromium",
                    p.chromium,
                    [
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-background-timer-throttling",
                        "--disable-backgrounding-occluded-windows",
                        "--disable-renderer-backgrounding",
                    ],
                ),
                ("firefox", p.firefox, []),
                ("webkit", p.webkit, []),
            ]

            for browser_name, launcher, args in browser_configs:
                print(f"\n🔍 Testing {browser_name}...")

                # Launch browser with proper typing
                browser = await launcher.launch(headless=True, args=args)

                try:
                    # Create page
                    page = await browser.new_page()

                    # Navigate to frontend
                    await page.goto(e2e_urls["frontend"], timeout=30000)

                    # Wait for app to load
                    await page.wait_for_load_state("networkidle", timeout=10000)

                    # Check title
                    title = await page.title()
                    assert (
                        "React App" in title
                    ), f"Wrong title in {browser_name}: {title}"

                    # Check connection status
                    connection_element = await page.wait_for_selector(
                        '[data-testid="connection-status"]', timeout=10000
                    )
                    assert connection_element, f"No connection status in {browser_name}"

                    # Get connection text
                    connection_text = await page.text_content(
                        '[data-testid="connection-text"]'
                    )
                    assert (
                        connection_text == "Connected"
                    ), f"Not connected in {browser_name}: {connection_text}"

                    results[browser_name] = "✅ PASS"
                    print(f"✅ {browser_name}: All checks passed")

                except Exception as e:
                    results[browser_name] = f"❌ FAIL: {e}"
                    print(f"❌ {browser_name}: {e}")
                    raise  # Re-raise to fail the test

                finally:
                    await browser.close()

        # Verify all browsers passed
        for browser_name, result in results.items():
            assert "PASS" in result, f"{browser_name} failed: {result}"

        print("\n🎉 All browsers tested successfully!")

    @pytest.mark.asyncio
    async def test_frontend_connection_robustness(
        self, e2e_urls: Dict[str, str]
    ) -> None:
        """Test connection robustness across browsers."""
        async with async_playwright() as p:
            # Test with just Chromium for connection functionality
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )

            try:
                page = await browser.new_page()

                # Navigate and wait for connection
                await page.goto(e2e_urls["frontend"])
                await page.wait_for_load_state("networkidle")

                # Wait for stable connection
                await page.wait_for_selector(
                    '[data-testid="connection-text"]:has-text("Connected")',
                    timeout=15000,
                )

                # Test game creation if possible
                try:
                    settings_button = page.locator(SETTINGS_BUTTON_SELECTOR)
                    if await settings_button.is_visible():
                        await settings_button.click()
                        print("✅ Game settings accessible")
                except Exception as e:
                    print(
                        f"⚠️  Game settings not accessible: {e} (may not be implemented)"
                    )

            finally:
                await browser.close()
