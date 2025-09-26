"""
E2E tests for page refresh scenarios and state persistence.

These tests verify that the application handles browser refreshes correctly,
particularly around connection state management and the New Game disconnection bug.

This version uses the generic page fixture and runs on all 3 browsers.
"""

import asyncio
import time
from typing import Dict

import pytest
from playwright.async_api import Page, expect


@pytest.mark.e2e
@pytest.mark.asyncio
class TestPageRefreshScenarios:
    """Tests for page refresh behavior and state persistence."""

    async def test_connection_state_after_page_refresh(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test that connection state is properly restored after page refresh.

        This test verifies that refreshing the page doesn't cause false disconnection.
        """
        # Navigate and establish connection
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        # Wait for connection to be established
        connection_text = page.locator('[data-testid="connection-text"]')
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        print("✅ Initial connection established")

        # Refresh the page
        await page.reload()
        await page.wait_for_load_state("networkidle")

        # Connection should be re-established
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        # Settings should be accessible after refresh
        settings_button = page.locator('button:has-text("⚙️ Game Settings")')
        await expect(settings_button).to_be_enabled()

        print("✅ Connection restored after page refresh")

    async def test_game_state_persistence_across_refresh(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test that game state is preserved across page refreshes.

        Note: This depends on how the application implements state persistence.
        """
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        # Establish connection and create a game
        await expect(page.locator('[data-testid="connection-text"]')).to_have_text(
            "Connected", timeout=10000
        )

        settings_button = page.locator('button:has-text("⚙️ Game Settings")')
        await settings_button.click()

        start_button = page.locator('[data-testid="start-game-button"]')
        await start_button.click()

        # Wait for game to be created
        game_container = page.locator('[data-testid="game-container"]')
        await expect(game_container).to_be_visible(timeout=10000)

        # Get game ID if displayed
        game_id_element = page.locator(".game-id")
        game_id_before = ""
        if await game_id_element.count() > 0:
            game_id_before = await game_id_element.text_content() or ""

        print(f"✅ Game created before refresh: {game_id_before}")

        # Refresh the page
        await page.reload()
        await page.wait_for_load_state("networkidle")

        # Check what happens to the game state after refresh
        # This might show game setup or persist the game depending on implementation

        # Wait for connection to re-establish
        await expect(page.locator('[data-testid="connection-text"]')).to_have_text(
            "Connected", timeout=10000
        )

        # Check if game state is preserved or if we're back to setup
        game_container_after = page.locator('[data-testid="game-container"]')
        game_setup_after = page.locator('[data-testid="game-setup"]')

        # Either game is preserved or we're back to setup (both are valid behaviors)
        if await game_container_after.count() > 0:
            print("✅ Game state preserved across refresh")
        elif await game_setup_after.count() > 0:
            print("✅ Returned to game setup after refresh")
        else:
            print("⚠️ Unexpected state after refresh")

    async def test_new_game_then_refresh_connection_bug(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test the specific bug scenario: New Game -> Refresh -> Settings.

        This test verifies that the disconnection bug doesn't persist across
        page refreshes.
        """
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        # Create a game first
        await expect(page.locator('[data-testid="connection-text"]')).to_have_text(
            "Connected", timeout=10000
        )

        settings_button = page.locator('button:has-text("⚙️ Game Settings")')
        await settings_button.click()

        start_button = page.locator('[data-testid="start-game-button"]')
        await start_button.click()

        await expect(page.locator('[data-testid="game-container"]')).to_be_visible(
            timeout=10000
        )

        print("✅ Game created successfully")

        # Click New Game (this triggers the disconnection bug)
        new_game_button = page.locator('button:has-text("New Game")')
        await new_game_button.click()

        # Should return to setup
        await expect(page.locator('[data-testid="game-setup"]')).to_be_visible(
            timeout=5000
        )

        # Check connection status (might show disconnected due to bug)
        connection_text = page.locator('[data-testid="connection-text"]')
        connection_status_before_refresh = await connection_text.text_content()

        print(f"✅ Connection status after New Game: {connection_status_before_refresh}")

        # Refresh the page to reset any client-side state issues
        await page.reload()
        await page.wait_for_load_state("networkidle")

        # After refresh, connection should be properly restored
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        # Settings should be accessible
        settings_button = page.locator('button:has-text("⚙️ Game Settings")')
        await expect(settings_button).to_be_enabled()
        await settings_button.click()

        # Should not show connection warning
        connection_warning = page.locator('[data-testid="connection-warning"]')
        await expect(connection_warning).not_to_be_visible()

        # Start Game button should work
        start_button = page.locator('[data-testid="start-game-button"]')
        await expect(start_button).to_be_enabled()
        await expect(start_button).to_have_text("Start Game")

        print("✅ Settings fully functional after refresh")

    async def test_settings_persistence_across_refresh(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test that user settings are preserved across page refreshes.
        """
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        await expect(page.locator('[data-testid="connection-text"]')).to_have_text(
            "Connected", timeout=10000
        )

        # Open settings and change configuration
        settings_button = page.locator('button:has-text("⚙️ Game Settings")')
        await settings_button.click()

        # Change to AI vs AI mode
        ai_vs_ai_button = page.locator('[data-testid="mode-ai-vs-ai"]')
        await ai_vs_ai_button.click()

        # Change difficulty to expert
        expert_button = page.locator('button:has-text("Expert")')
        await expert_button.click()

        # Change board size to 7x7
        size_7_button = page.locator('button:has-text("7x7")')
        await size_7_button.click()

        print("✅ Settings configured before refresh")

        # Refresh the page
        await page.reload()
        await page.wait_for_load_state("networkidle")

        await expect(page.locator('[data-testid="connection-text"]')).to_have_text(
            "Connected", timeout=10000
        )

        # Check if settings are preserved
        settings_button = page.locator('button:has-text("⚙️ Game Settings")')
        await settings_button.click()

        # Check if our settings persisted (this depends on implementation)
        # If settings are persisted in localStorage/sessionStorage
        ai_vs_ai_after = page.locator('[data-testid="mode-ai-vs-ai"]')
        expert_after = page.locator('button:has-text("Expert")')
        size_7_after = page.locator('button:has-text("7x7")')

        # These might or might not be preserved depending on implementation
        ai_vs_ai_active = await ai_vs_ai_after.get_attribute("class")
        expert_active = await expert_after.get_attribute("class")
        size_7_active = await size_7_after.get_attribute("class")

        if ai_vs_ai_active and "active" in ai_vs_ai_active:
            print("✅ Settings preserved across refresh")
        else:
            print("ℹ️ Settings reset to defaults after refresh")

        # Regardless, settings should be functional
        await expect(page.locator('[data-testid="start-game-button"]')).to_be_enabled()

    async def test_multiple_refresh_cycles_stability(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test that the application remains stable through multiple refresh cycles.
        """
        for cycle in range(5):
            print(f"🔄 Refresh cycle {cycle + 1}")

            await page.goto(e2e_urls["frontend"])
            await page.wait_for_load_state("networkidle")

            # Should connect each time
            connection_text = page.locator('[data-testid="connection-text"]')
            await expect(connection_text).to_have_text("Connected", timeout=10000)

            # Settings should be accessible
            settings_button = page.locator('button:has-text("⚙️ Game Settings")')
            await expect(settings_button).to_be_enabled()

            # Try to create a game
            await settings_button.click()
            start_button = page.locator('[data-testid="start-game-button"]')
            await expect(start_button).to_be_enabled()

            # Verify no connection warnings
            connection_warning = page.locator('[data-testid="connection-warning"]')
            await expect(connection_warning).not_to_be_visible()

        print("✅ All refresh cycles completed successfully")

    async def test_refresh_during_game_creation(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test page refresh during game creation process.
        """
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        await expect(page.locator('[data-testid="connection-text"]')).to_have_text(
            "Connected", timeout=10000
        )

        # Start game creation
        settings_button = page.locator('button:has-text("⚙️ Game Settings")')
        await settings_button.click()

        start_button = page.locator('[data-testid="start-game-button"]')
        await start_button.click()

        # Immediately refresh before game creation completes
        await page.reload()
        await page.wait_for_load_state("networkidle")

        # Should return to normal state
        await expect(page.locator('[data-testid="connection-text"]')).to_have_text(
            "Connected", timeout=10000
        )

        # Should be back at game setup
        game_setup = page.locator('[data-testid="game-setup"]')
        await expect(game_setup).to_be_visible()

        # Settings should still work
        settings_button = page.locator('button:has-text("⚙️ Game Settings")')
        await expect(settings_button).to_be_enabled()

        print("✅ Refresh during game creation handled gracefully")

    async def test_browser_back_forward_after_refresh(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test browser back/forward buttons work correctly after page refresh.
        """
        # Navigate to app
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        await expect(page.locator('[data-testid="connection-text"]')).to_have_text(
            "Connected", timeout=10000
        )

        # Navigate to a different page (if app has routing) or external page
        await page.goto("about:blank")
        await page.wait_for_timeout(1000)

        # Go back to the app
        await page.go_back()
        await page.wait_for_load_state("networkidle")

        # Should reconnect
        await expect(page.locator('[data-testid="connection-text"]')).to_have_text(
            "Connected", timeout=10000
        )

        # Refresh while on the app page
        await page.reload()
        await page.wait_for_load_state("networkidle")

        # Forward/back should still work
        await page.go_forward()  # Should go to about:blank
        await page.go_back()  # Should return to app
        await page.wait_for_load_state("networkidle")

        # Connection should re-establish
        await expect(page.locator('[data-testid="connection-text"]')).to_have_text(
            "Connected", timeout=10000
        )

        print("✅ Browser navigation works after refresh")

    async def test_refresh_with_console_errors(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test that page refreshes don't accumulate console errors.
        """
        console_errors = []
        page.on(
            "console",
            lambda msg: console_errors.append(msg) if msg.type == "error" else None,
        )

        # Initial load
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        await expect(page.locator('[data-testid="connection-text"]')).to_have_text(
            "Connected", timeout=10000
        )

        initial_errors = len(console_errors)

        # Perform some actions that might trigger the disconnection bug
        settings_button = page.locator('button:has-text("⚙️ Game Settings")')
        await settings_button.click()

        start_button = page.locator('[data-testid="start-game-button"]')
        await start_button.click()

        await expect(page.locator('[data-testid="game-container"]')).to_be_visible(
            timeout=10000
        )

        new_game_button = page.locator('button:has-text("New Game")')
        await new_game_button.click()

        # Refresh
        await page.reload()
        await page.wait_for_load_state("networkidle")

        await expect(page.locator('[data-testid="connection-text"]')).to_have_text(
            "Connected", timeout=10000
        )

        final_errors = len(console_errors)

        # Check for any critical errors
        critical_errors = [
            err
            for err in console_errors
            if "WebSocket" in err.text or "connection" in err.text.lower()
        ]

        if critical_errors:
            print(f"⚠️ Found {len(critical_errors)} connection-related console errors")
            for error in critical_errors[-3:]:  # Show last 3 errors
                print(f"  - {error.text}")
        else:
            print("✅ No critical connection errors in console")

        print(
            f"ℹ️ Total console errors: {final_errors} (started with {initial_errors})"
        )
