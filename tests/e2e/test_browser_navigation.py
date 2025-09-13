"""
E2E tests for browser navigation scenarios.

These tests verify that the application handles browser navigation correctly,
including back/forward buttons, multiple tabs, and window management.
"""

import asyncio
import time
from typing import Dict

import pytest
from playwright.async_api import Page, async_playwright, expect, BrowserContext


@pytest.mark.e2e
@pytest.mark.asyncio
class TestBrowserNavigation:
    """Tests for browser navigation behavior."""

    async def test_browser_back_forward_functionality(
        self, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test browser back/forward buttons with the application.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # Navigate to app
                await page.goto(e2e_urls["frontend"])
                await page.wait_for_load_state("networkidle")

                connection_text = page.locator('[data-testid="connection-text"]')
                await expect(connection_text).to_have_text("Connected", timeout=10000)

                print("✅ Initial navigation to app")

                # Navigate to external site
                await page.goto("https://example.com")
                await page.wait_for_load_state("networkidle")

                # Go back to app
                await page.go_back()
                await page.wait_for_load_state("networkidle")

                # Should reconnect
                await expect(connection_text).to_have_text("Connected", timeout=10000)

                # Settings should be functional
                settings_button = page.locator('button:has-text("⚙️ Game Settings")')
                await expect(settings_button).to_be_enabled()

                print("✅ Back navigation restored functionality")

                # Go forward again
                await page.go_forward()
                await page.wait_for_load_state("networkidle")

                # Should be back at example.com
                await expect(page).to_have_url("https://example.com")

                # Go back to app one more time
                await page.go_back()
                await page.wait_for_load_state("networkidle")

                # Should still work
                await expect(connection_text).to_have_text("Connected", timeout=10000)

                print("✅ Multiple back/forward cycles work correctly")

            finally:
                await browser.close()

    async def test_multiple_tabs_same_app(self, e2e_urls: Dict[str, str]) -> None:
        """
        Test opening the application in multiple tabs simultaneously.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()

            try:
                # Open first tab
                page1 = await context.new_page()
                await page1.goto(e2e_urls["frontend"])
                await page1.wait_for_load_state("networkidle")

                connection_text_1 = page1.locator('[data-testid="connection-text"]')
                await expect(connection_text_1).to_have_text("Connected", timeout=10000)

                print("✅ Tab 1 connected")

                # Open second tab
                page2 = await context.new_page()
                await page2.goto(e2e_urls["frontend"])
                await page2.wait_for_load_state("networkidle")

                connection_text_2 = page2.locator('[data-testid="connection-text"]')
                await expect(connection_text_2).to_have_text("Connected", timeout=10000)

                print("✅ Tab 2 connected")

                # Both tabs should be functional independently
                # Test tab 1
                settings_button_1 = page1.locator('button:has-text("⚙️ Game Settings")')
                await settings_button_1.click()

                start_button_1 = page1.locator('[data-testid="start-game-button"]')
                await start_button_1.click()

                await expect(
                    page1.locator('[data-testid="game-container"]')
                ).to_be_visible(timeout=10000)

                print("✅ Tab 1 can create games")

                # Test tab 2 independently
                settings_button_2 = page2.locator('button:has-text("⚙️ Game Settings")')
                await settings_button_2.click()

                # Change settings to different mode
                ai_vs_ai_button = page2.locator('[data-testid="mode-ai-vs-ai"]')
                await ai_vs_ai_button.click()

                start_button_2 = page2.locator('[data-testid="start-game-button"]')
                await start_button_2.click()

                await expect(
                    page2.locator('[data-testid="game-container"]')
                ).to_be_visible(timeout=10000)

                print("✅ Tab 2 can create games independently")

                # Test New Game in tab 1 (disconnection bug scenario)
                new_game_button_1 = page1.locator('button:has-text("New Game")')
                await new_game_button_1.click()

                await expect(page1.locator('[data-testid="game-setup"]')).to_be_visible(
                    timeout=5000
                )
                await expect(connection_text_1).to_have_text("Connected")

                # Tab 2 should be unaffected
                await expect(
                    page2.locator('[data-testid="game-container"]')
                ).to_be_visible()
                await expect(connection_text_2).to_have_text("Connected")

                print("✅ Tab isolation works correctly")

            finally:
                await browser.close()

    async def test_tab_switching_and_return(self, e2e_urls: Dict[str, str]) -> None:
        """
        Test switching between tabs and returning to the app tab.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()

            try:
                # Open app tab
                app_page = await context.new_page()
                await app_page.goto(e2e_urls["frontend"])
                await app_page.wait_for_load_state("networkidle")

                connection_text = app_page.locator('[data-testid="connection-text"]')
                await expect(connection_text).to_have_text("Connected", timeout=10000)

                # Create a game
                settings_button = app_page.locator(
                    'button:has-text("⚙️ Game Settings")'
                )
                await settings_button.click()

                start_button = app_page.locator('[data-testid="start-game-button"]')
                await start_button.click()

                await expect(
                    app_page.locator('[data-testid="game-container"]')
                ).to_be_visible(timeout=10000)

                print("✅ Game created in app tab")

                # Open other tabs to simulate tab switching
                other_page1 = await context.new_page()
                await other_page1.goto("https://example.com")

                other_page2 = await context.new_page()
                await other_page2.goto("https://httpbin.org/get")

                # Simulate time away from app tab
                await asyncio.sleep(2)

                print("✅ Simulated tab switching away from app")

                # Return to app tab
                await app_page.bring_to_front()

                # App should still be functional
                await expect(connection_text).to_have_text("Connected", timeout=5000)
                await expect(
                    app_page.locator('[data-testid="game-container"]')
                ).to_be_visible()

                # New Game should work
                new_game_button = app_page.locator('button:has-text("New Game")')
                await new_game_button.click()

                await expect(
                    app_page.locator('[data-testid="game-setup"]')
                ).to_be_visible(timeout=5000)
                await expect(connection_text).to_have_text("Connected")

                print("✅ App remains functional after tab switching")

            finally:
                await browser.close()

    async def test_browser_close_and_reopen(self, e2e_urls: Dict[str, str]) -> None:
        """
        Test browser window close and reopen scenarios.
        """
        async with async_playwright() as p:
            # First browser session
            browser1 = await p.chromium.launch(headless=True)
            context1 = await browser1.new_context()
            page1 = await context1.new_page()

            try:
                await page1.goto(e2e_urls["frontend"])
                await page1.wait_for_load_state("networkidle")

                connection_text = page1.locator('[data-testid="connection-text"]')
                await expect(connection_text).to_have_text("Connected", timeout=10000)

                # Create a game
                settings_button = page1.locator('button:has-text("⚙️ Game Settings")')
                await settings_button.click()

                start_button = page1.locator('[data-testid="start-game-button"]')
                await start_button.click()

                await expect(
                    page1.locator('[data-testid="game-container"]')
                ).to_be_visible(timeout=10000)

                print("✅ Game created in first browser session")

            finally:
                # Close first browser
                await browser1.close()

            # Wait a moment to simulate time between sessions
            await asyncio.sleep(1)

            # Second browser session (simulates reopening browser)
            browser2 = await p.chromium.launch(headless=True)
            context2 = await browser2.new_context()
            page2 = await context2.new_page()

            try:
                await page2.goto(e2e_urls["frontend"])
                await page2.wait_for_load_state("networkidle")

                # Should connect normally in new session
                connection_text = page2.locator('[data-testid="connection-text"]')
                await expect(connection_text).to_have_text("Connected", timeout=10000)

                # Should be at game setup (state not preserved across browser sessions)
                game_setup = page2.locator('[data-testid="game-setup"]')
                await expect(game_setup).to_be_visible()

                # Should be able to create new game
                settings_button = page2.locator('button:has-text("⚙️ Game Settings")')
                await expect(settings_button).to_be_enabled()
                await settings_button.click()

                start_button = page2.locator('[data-testid="start-game-button"]')
                await start_button.click()

                await expect(
                    page2.locator('[data-testid="game-container"]')
                ).to_be_visible(timeout=10000)

                print("✅ Fresh browser session works correctly")

            finally:
                await browser2.close()

    async def test_window_focus_and_blur_events(self, e2e_urls: Dict[str, str]) -> None:
        """
        Test application behavior during window focus and blur events.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto(e2e_urls["frontend"])
                await page.wait_for_load_state("networkidle")

                connection_text = page.locator('[data-testid="connection-text"]')
                await expect(connection_text).to_have_text("Connected", timeout=10000)

                # Create a game
                settings_button = page.locator('button:has-text("⚙️ Game Settings")')
                await settings_button.click()

                start_button = page.locator('[data-testid="start-game-button"]')
                await start_button.click()

                await expect(
                    page.locator('[data-testid="game-container"]')
                ).to_be_visible(timeout=10000)

                print("✅ Game created before focus tests")

                # Simulate window blur (user switches to another app)
                await page.evaluate("() => window.dispatchEvent(new Event('blur'))")
                await page.evaluate(
                    "() => document.dispatchEvent(new Event('visibilitychange'))"
                )

                # Wait a moment
                await asyncio.sleep(1)

                # Simulate window focus (user returns)
                await page.evaluate("() => window.dispatchEvent(new Event('focus'))")
                await page.evaluate(
                    "() => document.dispatchEvent(new Event('visibilitychange'))"
                )

                # App should remain functional
                await expect(connection_text).to_have_text("Connected", timeout=5000)
                await expect(
                    page.locator('[data-testid="game-container"]')
                ).to_be_visible()

                # New Game should work after focus events
                new_game_button = page.locator('button:has-text("New Game")')
                await new_game_button.click()

                await expect(page.locator('[data-testid="game-setup"]')).to_be_visible(
                    timeout=5000
                )
                await expect(connection_text).to_have_text("Connected")

                print("✅ App handles focus/blur events correctly")

            finally:
                await browser.close()

    async def test_url_manipulation_and_navigation(
        self, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test behavior when URL is manipulated manually.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # Navigate to app
                await page.goto(e2e_urls["frontend"])
                await page.wait_for_load_state("networkidle")

                connection_text = page.locator('[data-testid="connection-text"]')
                await expect(connection_text).to_have_text("Connected", timeout=10000)

                original_url = page.url
                print(f"✅ Original URL: {original_url}")

                # Try navigating to non-existent path (if app has routing)
                fake_path = f"{original_url}fake-path"
                await page.goto(fake_path)
                await page.wait_for_load_state("networkidle")

                # App should handle gracefully (either 404 or redirect)
                # Check if we get back to a working state
                current_url = page.url

                if current_url == fake_path:
                    # App might show 404 or handle the route
                    print("ℹ️ App handles fake path")
                else:
                    # App might have redirected
                    print(f"ℹ️ App redirected to: {current_url}")

                # Navigate back to main app
                await page.goto(e2e_urls["frontend"])
                await page.wait_for_load_state("networkidle")

                # Should work normally
                await expect(connection_text).to_have_text("Connected", timeout=10000)

                settings_button = page.locator('button:has-text("⚙️ Game Settings")')
                await expect(settings_button).to_be_enabled()

                print("✅ App recovers from URL manipulation")

                # Test with query parameters
                url_with_params = f"{original_url}?test=123&debug=true"
                await page.goto(url_with_params)
                await page.wait_for_load_state("networkidle")

                # Should still work with query params
                await expect(connection_text).to_have_text("Connected", timeout=10000)
                await expect(settings_button).to_be_enabled()

                print("✅ App works with query parameters")

            finally:
                await browser.close()

    async def test_concurrent_browser_instances(self, e2e_urls: Dict[str, str]) -> None:
        """
        Test multiple browser instances accessing the app simultaneously.
        """
        async with async_playwright() as p:
            browsers = []
            try:
                # Create multiple browser instances
                for i in range(3):
                    browser = await p.chromium.launch(headless=True)
                    browsers.append(browser)

                    context = await browser.new_context()
                    page = await context.new_page()

                    await page.goto(e2e_urls["frontend"])
                    await page.wait_for_load_state("networkidle")

                    connection_text = page.locator('[data-testid="connection-text"]')
                    await expect(connection_text).to_have_text(
                        "Connected", timeout=10000
                    )

                    print(f"✅ Browser instance {i+1} connected")

                    # Create game in each instance
                    settings_button = page.locator(
                        'button:has-text("⚙️ Game Settings")'
                    )
                    await settings_button.click()

                    if i == 1:  # Change mode in second instance
                        ai_vs_ai_button = page.locator('[data-testid="mode-ai-vs-ai"]')
                        await ai_vs_ai_button.click()

                    start_button = page.locator('[data-testid="start-game-button"]')
                    await start_button.click()

                    await expect(
                        page.locator('[data-testid="game-container"]')
                    ).to_be_visible(timeout=10000)

                    print(f"✅ Browser instance {i+1} created game")

                # All instances should be working independently
                print("✅ All browser instances working concurrently")

                # Test New Game in first instance (disconnection bug test)
                first_browser_page = browsers[0].contexts[0].pages[0]
                new_game_button = first_browser_page.locator(
                    'button:has-text("New Game")'
                )
                await new_game_button.click()

                await expect(
                    first_browser_page.locator('[data-testid="game-setup"]')
                ).to_be_visible(timeout=5000)

                first_connection = first_browser_page.locator(
                    '[data-testid="connection-text"]'
                )
                await expect(first_connection).to_have_text("Connected")

                print("✅ New Game works correctly in concurrent environment")

            finally:
                # Clean up all browsers
                for browser in browsers:
                    await browser.close()

    async def test_page_reload_during_navigation(
        self, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test page reload behavior during various navigation states.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto(e2e_urls["frontend"])
                await page.wait_for_load_state("networkidle")

                connection_text = page.locator('[data-testid="connection-text"]')
                await expect(connection_text).to_have_text("Connected", timeout=10000)

                # Reload immediately after load
                await page.reload()
                await page.wait_for_load_state("networkidle")

                await expect(connection_text).to_have_text("Connected", timeout=10000)
                print("✅ Reload after initial load works")

                # Open settings and reload
                settings_button = page.locator('button:has-text("⚙️ Game Settings")')
                await settings_button.click()

                await page.reload()
                await page.wait_for_load_state("networkidle")

                await expect(connection_text).to_have_text("Connected", timeout=10000)

                # Should be back to initial state
                game_setup = page.locator('[data-testid="game-setup"]')
                await expect(game_setup).to_be_visible()

                print("✅ Reload during settings works")

                # Create game and reload
                await settings_button.click()
                start_button = page.locator('[data-testid="start-game-button"]')
                await start_button.click()

                await expect(
                    page.locator('[data-testid="game-container"]')
                ).to_be_visible(timeout=10000)

                await page.reload()
                await page.wait_for_load_state("networkidle")

                await expect(connection_text).to_have_text("Connected", timeout=10000)

                # Game state handling depends on implementation
                print("✅ Reload during game works")

            finally:
                await browser.close()
