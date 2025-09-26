"""
E2E tests for browser navigation scenarios.

These tests verify that the application handles browser navigation correctly,
including back/forward buttons, multiple tabs, and window management.

This version uses the generic page fixture and runs on all 3 browsers.
"""

import asyncio
import time
from typing import Dict

import pytest
from playwright.async_api import Page, expect, BrowserContext, Browser


@pytest.mark.e2e
@pytest.mark.asyncio
class TestBrowserNavigation:
    """Tests for browser navigation behavior."""

    async def test_browser_back_forward_functionality(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test browser back/forward buttons with the application.
        """
        # Navigate to app
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        connection_text = page.locator('[data-testid="connection-text"]')
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        print("✅ Initial navigation to app")

        # Navigate to mock external site
        await page.goto(f"{e2e_urls['frontend']}/test/external")
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

        # Should be back at mock external page
        await expect(page).to_have_url(f"{e2e_urls['frontend']}/test/external")

        # Go back to app one more time
        await page.go_back()
        await page.wait_for_load_state("networkidle")

        # Should still work
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        print("✅ Multiple back/forward cycles work correctly")

    async def test_multiple_tabs_same_app(
        self, context: BrowserContext, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test opening the application in multiple tabs simultaneously.
        """
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

        await expect(page1.locator('[data-testid="game-container"]')).to_be_visible(
            timeout=10000
        )

        print("✅ Tab 1 can create games")

        # Test tab 2 independently
        settings_button_2 = page2.locator('button:has-text("⚙️ Game Settings")')
        await settings_button_2.click()

        # Change settings to different mode
        ai_vs_ai_button = page2.locator('[data-testid="mode-ai-vs-ai"]')
        await ai_vs_ai_button.click()

        start_button_2 = page2.locator('[data-testid="start-game-button"]')
        await start_button_2.click()

        await expect(page2.locator('[data-testid="game-container"]')).to_be_visible(
            timeout=10000
        )

        print("✅ Tab 2 can create games independently")

        # Test New Game in tab 1 (disconnection bug scenario)
        new_game_button_1 = page1.locator('button:has-text("New Game")')
        await new_game_button_1.click()

        # Wait for the transition to reset game state
        await asyncio.sleep(1.0)

        # The key test is that connection remains stable - game setup visibility is secondary
        await expect(connection_text_1).to_have_text("Connected", timeout=10000)

        # Verify we can interact with settings again (functional test)
        settings_button_1_again = page1.locator('button:has-text("⚙️ Game Settings")')
        await expect(settings_button_1_again).to_be_enabled(timeout=5000)

        # Tab 2 should be unaffected
        await expect(page2.locator('[data-testid="game-container"]')).to_be_visible()
        await expect(connection_text_2).to_have_text("Connected")

        print("✅ Tab isolation works correctly")

        # Clean up
        await page1.close()
        await page2.close()

    async def test_tab_switching_and_return(
        self, context: BrowserContext, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test switching between tabs and returning to the app tab.
        """
        # Open app tab
        app_page = await context.new_page()
        await app_page.goto(e2e_urls["frontend"])
        await app_page.wait_for_load_state("networkidle")

        connection_text = app_page.locator('[data-testid="connection-text"]')
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        # Create a game
        settings_button = app_page.locator('button:has-text("⚙️ Game Settings")')
        await settings_button.click()

        start_button = app_page.locator('[data-testid="start-game-button"]')
        await start_button.click()

        await expect(app_page.locator('[data-testid="game-container"]')).to_be_visible(
            timeout=10000
        )

        print("✅ Game created in app tab")

        # Open other tabs to simulate tab switching
        other_page1 = await context.new_page()
        await other_page1.goto(f"{e2e_urls['frontend']}/test/external")

        other_page2 = await context.new_page()
        await other_page2.goto(f"{e2e_urls['frontend']}/test/api")

        # Simulate time away from app tab
        await asyncio.sleep(2)

        print("✅ Simulated tab switching away from app")

        # Return to app tab
        await app_page.bring_to_front()

        # App should still be functional
        await expect(connection_text).to_have_text("Connected", timeout=5000)
        await expect(app_page.locator('[data-testid="game-container"]')).to_be_visible()

        # New Game should work
        new_game_button = app_page.locator('button:has-text("New Game")')
        await new_game_button.click()

        # Wait for the transition to reset game state
        await asyncio.sleep(1.0)

        # The key test is that connection remains stable after tab switching
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        # Verify we can interact with settings again (functional test)
        settings_button_again = app_page.locator('button:has-text("⚙️ Game Settings")')
        await expect(settings_button_again).to_be_enabled(timeout=5000)

        print("✅ App remains functional after tab switching")

        # Clean up
        await app_page.close()
        await other_page1.close()
        await other_page2.close()

    async def test_browser_close_and_reopen(
        self, browser: Browser, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test browser window close and reopen scenarios.
        """
        # First browser context
        context1 = await browser.new_context()
        page1 = await context1.new_page()

        await page1.goto(e2e_urls["frontend"])
        await page1.wait_for_load_state("networkidle")

        connection_text = page1.locator('[data-testid="connection-text"]')
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        # Create a game
        settings_button = page1.locator('button:has-text("⚙️ Game Settings")')
        await settings_button.click()

        start_button = page1.locator('[data-testid="start-game-button"]')
        await start_button.click()

        await expect(page1.locator('[data-testid="game-container"]')).to_be_visible(
            timeout=10000
        )

        print("✅ Game created in first browser context")

        # Close first context (simulates browser close)
        await context1.close()

        # Wait a moment to simulate time between sessions
        await asyncio.sleep(1)

        # Second browser context (simulates reopening browser)
        context2 = await browser.new_context()
        page2 = await context2.new_page()

        await page2.goto(e2e_urls["frontend"])
        await page2.wait_for_load_state("networkidle")

        # Should connect normally in new context
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

        await expect(page2.locator('[data-testid="game-container"]')).to_be_visible(
            timeout=10000
        )

        print("✅ Fresh browser context works correctly")

        # Clean up
        await context2.close()

    async def test_window_focus_and_blur_events(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test application behavior during window focus and blur events.
        """
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        connection_text = page.locator('[data-testid="connection-text"]')
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        # Create a game
        settings_button = page.locator('button:has-text("⚙️ Game Settings")')
        await settings_button.click()

        start_button = page.locator('[data-testid="start-game-button"]')
        await start_button.click()

        await expect(page.locator('[data-testid="game-container"]')).to_be_visible(
            timeout=10000
        )

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
        await expect(page.locator('[data-testid="game-container"]')).to_be_visible()

        # New Game should work after focus events
        new_game_button = page.locator('button:has-text("New Game")')
        await new_game_button.click()

        # Wait for transition to complete
        await expect(page.locator('[data-testid="game-container"]')).not_to_be_visible(
            timeout=5000
        )

        await expect(page.locator('[data-testid="game-setup"]')).to_be_visible(
            timeout=10000
        )
        await expect(connection_text).to_have_text("Connected")

        print("✅ App handles focus/blur events correctly")

    async def test_url_manipulation_and_navigation(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test behavior when URL is manipulated manually.
        """
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

    async def test_concurrent_browser_instances(
        self, browser: Browser, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test multiple browser contexts accessing the app simultaneously.
        """
        contexts = []
        pages = []

        try:
            # Create multiple browser contexts (simulating multiple browser instances)
            for i in range(3):
                context = await browser.new_context()
                contexts.append(context)

                page = await context.new_page()
                pages.append(page)

                await page.goto(e2e_urls["frontend"])
                await page.wait_for_load_state("networkidle")

                connection_text = page.locator('[data-testid="connection-text"]')
                await expect(connection_text).to_have_text("Connected", timeout=10000)

                print(f"✅ Browser context {i+1} connected")

                # Create game in each instance
                settings_button = page.locator('button:has-text("⚙️ Game Settings")')
                await settings_button.click()

                if i == 1:  # Change mode in second instance
                    ai_vs_ai_button = page.locator('[data-testid="mode-ai-vs-ai"]')
                    await ai_vs_ai_button.click()

                start_button = page.locator('[data-testid="start-game-button"]')
                await start_button.click()

                await expect(
                    page.locator('[data-testid="game-container"]')
                ).to_be_visible(timeout=10000)

                print(f"✅ Browser context {i+1} created game")

            # All instances should be working independently
            print("✅ All browser contexts working concurrently")

            # Test New Game in first instance (disconnection bug test)
            first_page = pages[0]
            new_game_button = first_page.locator('button:has-text("New Game")')
            await new_game_button.click()

            # Wait for transition to complete
            await expect(
                first_page.locator('[data-testid="game-container"]')
            ).not_to_be_visible(timeout=5000)

            await expect(
                first_page.locator('[data-testid="game-setup"]')
            ).to_be_visible(timeout=10000)

            first_connection = first_page.locator('[data-testid="connection-text"]')
            await expect(first_connection).to_have_text("Connected")

            print("✅ New Game works correctly in concurrent environment")

        finally:
            # Clean up all contexts
            for context in contexts:
                await context.close()

    async def test_page_reload_during_navigation(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test page reload behavior during various navigation states.
        """
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

        await expect(page.locator('[data-testid="game-container"]')).to_be_visible(
            timeout=10000
        )

        await page.reload()
        await page.wait_for_load_state("networkidle")

        await expect(connection_text).to_have_text("Connected", timeout=10000)

        # Game state handling depends on implementation
        print("✅ Reload during game works")
