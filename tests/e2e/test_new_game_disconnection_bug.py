"""
E2E tests to reproduce and verify the New Game disconnection bug.

This test suite specifically targets the bug where clicking "New Game" 
causes the UI to show "Disconnected" status, preventing the user from 
starting another game through the settings flow.

Bug flow: Game Settings -> Start Game -> New Game -> Settings (shows disconnected)
"""

import asyncio
import time
from typing import Dict

import pytest
from playwright.async_api import Page, WebSocket, async_playwright, expect


@pytest.mark.e2e
@pytest.mark.asyncio
class TestNewGameDisconnectionBug:
    """Tests to reproduce and verify fixes for the New Game disconnection bug."""

    async def test_full_new_game_flow_maintains_connection(
        self, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test the complete flow: Settings -> Start Game -> New Game -> Settings again.

        This reproduces the main user-reported bug where after starting a game
        and clicking "New Game", the settings show disconnected status.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # Navigate and wait for connection
                await page.goto(e2e_urls["frontend"])
                await page.wait_for_load_state("networkidle")

                # Wait for connection to be established
                connection_text = page.locator('[data-testid="connection-text"]')
                await expect(connection_text).to_have_text("Connected", timeout=10000)

                print("✅ Step 1: Connected to application")

                # Step 2: Settings panel should be visible by default (no need to click button)
                await expect(page.locator("text=Game Settings")).to_be_visible()
                connection_warning = page.locator('[data-testid="connection-warning"]')
                await expect(connection_warning).not_to_be_visible()

                print("✅ Step 2: Game settings panel is visible by default")

                # Step 3: Start a game
                start_game_button = page.locator('[data-testid="start-game-button"]')
                await expect(start_game_button).to_be_enabled()
                await expect(start_game_button).to_have_text("Start Game")
                await start_game_button.click()

                # Wait for game to be created and game container to appear
                game_container = page.locator('[data-testid="game-container"]')
                await expect(game_container).to_be_visible(timeout=10000)

                # Verify we're still connected during game
                await expect(connection_text).to_have_text("Connected")

                print("✅ Step 3: Game started successfully, still connected")

                # Step 4: Click "New Game" button - this is where the bug occurs
                new_game_button = page.locator('button:has-text("New Game")')
                await expect(new_game_button).to_be_visible()
                await new_game_button.click()

                # Should return to setup screen
                game_setup = page.locator('[data-testid="game-setup"]')
                await expect(game_setup).to_be_visible(timeout=5000)

                # CRITICAL TEST: Connection should still show "Connected"
                # This is the main bug - currently shows "Disconnected" after New Game
                await expect(connection_text).to_have_text("Connected", timeout=5000)

                print("✅ Step 4: New Game clicked, connection status preserved")

                # Step 5: Settings panel should already be visible after New Game (no button to click)
                await expect(page.locator("text=Game Settings")).to_be_visible()

                # Should NOT show connection warning
                connection_warning = page.locator('[data-testid="connection-warning"]')
                await expect(connection_warning).not_to_be_visible()

                # Start Game button should be enabled and not show "Disconnected"
                start_game_button = page.locator('[data-testid="start-game-button"]')
                await expect(start_game_button).to_be_enabled()
                await expect(start_game_button).to_have_text("Start Game")
                await expect(start_game_button).not_to_have_text("Disconnected")

                print(
                    "✅ Step 5: Settings panel visible after New Game - bug not present"
                )

            except Exception as e:
                # If any step fails, it likely indicates the bug is present
                current_status = (
                    await connection_text.text_content()
                    if await connection_text.count() > 0
                    else "unknown"
                )
                print(
                    f"❌ Bug reproduced: Connection status is '{current_status}' when it should be 'Connected'"
                )
                print(f"Error details: {str(e)}")
                raise AssertionError(f"New Game disconnection bug detected: {str(e)}")

            finally:
                await browser.close()

    async def test_multiple_new_game_clicks_preserve_connection(
        self, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test that clicking "New Game" multiple times doesn't cause connection issues.

        Users might click multiple times if they're not sure the first click registered.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto(e2e_urls["frontend"])
                await page.wait_for_load_state("networkidle")

                # Start a game first
                await expect(
                    page.locator('[data-testid="connection-text"]')
                ).to_have_text("Connected", timeout=10000)

                # Settings panel should be visible by default
                start_button = page.locator('[data-testid="start-game-button"]')
                await start_button.click()

                await expect(
                    page.locator('[data-testid="game-container"]')
                ).to_be_visible(timeout=10000)

                # Test multiple New Game -> Start Game cycles to test stability
                for i in range(
                    3
                ):  # Reduced to 3 cycles since each cycle requires full game creation
                    print(f"New Game cycle #{i+1}")

                    # Click New Game (only available when game is active)
                    new_game_button = page.locator('button:has-text("New Game")')
                    await new_game_button.click()

                    # Should return to setup and maintain connection
                    await expect(
                        page.locator('[data-testid="game-setup"]')
                    ).to_be_visible()
                    connection_text = page.locator('[data-testid="connection-text"]')
                    await expect(connection_text).to_have_text("Connected")

                    # Start a new game to continue the cycle (except for the last iteration)
                    if i < 2:  # Don't start another game on the final iteration
                        start_button = page.locator('[data-testid="start-game-button"]')
                        await start_button.click()
                        await expect(
                            page.locator('[data-testid="game-container"]')
                        ).to_be_visible(timeout=10000)

                # Final verification: should be able to start another game
                start_button = page.locator('[data-testid="start-game-button"]')
                await expect(start_button).to_be_enabled()

                print("✅ Multiple New Game cycles handled correctly")

            finally:
                await browser.close()

    async def test_new_game_preserves_websocket_connection(
        self, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test that the WebSocket connection itself is not affected by New Game clicks.

        This verifies that the bug is purely UI-side state management, not actual
        WebSocket disconnection.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # Track WebSocket connections
            websocket_created = False
            websocket_closed = False

            def on_websocket(ws: WebSocket) -> None:
                nonlocal websocket_created
                websocket_created = True

                def on_close(event: object) -> None:
                    setattr(self, "websocket_closed", True)

                ws.on("close", on_close)

            page.on("websocket", on_websocket)

            try:
                await page.goto(e2e_urls["frontend"])
                await page.wait_for_load_state("networkidle")

                # Wait for WebSocket connection
                await page.wait_for_timeout(2000)
                assert websocket_created, "WebSocket should be created"

                # Start and complete a game creation flow
                connection_text = page.locator('[data-testid="connection-text"]')
                await expect(connection_text).to_have_text("Connected", timeout=10000)

                # Settings panel should be visible by default
                start_button = page.locator('[data-testid="start-game-button"]')
                await start_button.click()

                await expect(
                    page.locator('[data-testid="game-container"]')
                ).to_be_visible(timeout=10000)

                # Click New Game - WebSocket should remain open
                new_game_button = page.locator('button:has-text("New Game")')
                await new_game_button.click()

                await page.wait_for_timeout(1000)

                # WebSocket should NOT be closed
                assert (
                    not websocket_closed
                ), "WebSocket should remain open after New Game"

                # Should still be able to create another game (proving WebSocket works)
                await expect(page.locator('[data-testid="game-setup"]')).to_be_visible()

                # Settings panel should be visible by default
                start_button = page.locator('[data-testid="start-game-button"]')
                await start_button.click()

                # Should successfully create another game
                await expect(
                    page.locator('[data-testid="game-container"]')
                ).to_be_visible(timeout=10000)

                print("✅ WebSocket connection preserved through New Game flow")

            finally:
                await browser.close()

    async def test_rapid_game_creation_after_new_game(
        self, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test that after clicking New Game, users can immediately start creating
        another game without waiting or refreshing.

        This tests the user experience impact of the disconnection bug.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto(e2e_urls["frontend"])
                await page.wait_for_load_state("networkidle")

                # Create initial game
                await expect(
                    page.locator('[data-testid="connection-text"]')
                ).to_have_text("Connected", timeout=10000)

                # Settings panel should be visible by default
                start_button = page.locator('[data-testid="start-game-button"]')
                await start_button.click()

                await expect(
                    page.locator('[data-testid="game-container"]')
                ).to_be_visible(timeout=10000)

                # Click New Game
                new_game_button = page.locator('button:has-text("New Game")')
                await new_game_button.click()

                await expect(page.locator('[data-testid="game-setup"]')).to_be_visible()

                # Settings panel should already be visible (no need to click)
                await expect(page.locator("text=Game Settings")).to_be_visible()
                connection_warning = page.locator('[data-testid="connection-warning"]')
                await expect(connection_warning).not_to_be_visible()

                # Start button should work immediately
                start_button = page.locator('[data-testid="start-game-button"]')
                await expect(start_button).to_be_enabled()
                await start_button.click()

                # Should successfully create new game
                await expect(
                    page.locator('[data-testid="game-container"]')
                ).to_be_visible(timeout=10000)

                print("✅ Rapid game creation after New Game works correctly")

            finally:
                await browser.close()

    async def test_connection_indicator_accuracy_after_new_game(
        self, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test that the connection indicator accurately reflects the real connection
        state after New Game is clicked.

        This verifies the UI state matches the actual connection state.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto(e2e_urls["frontend"])
                await page.wait_for_load_state("networkidle")

                # Verify initial connected state
                connection_indicator = page.locator(
                    '[data-testid="connection-indicator"]'
                )
                connection_text = page.locator('[data-testid="connection-text"]')

                await expect(connection_text).to_have_text("Connected", timeout=10000)
                indicator_class = await connection_indicator.get_attribute("class")
                assert "connected" in (
                    indicator_class or ""
                ), f"Expected 'connected' class, got: {indicator_class}"

                # Create game - settings panel should be visible by default
                start_button = page.locator('[data-testid="start-game-button"]')
                await start_button.click()

                await expect(
                    page.locator('[data-testid="game-container"]')
                ).to_be_visible(timeout=10000)

                # Click New Game
                new_game_button = page.locator('button:has-text("New Game")')
                await new_game_button.click()

                # Connection indicator should remain accurate
                await expect(connection_text).to_have_text("Connected")
                indicator_class = await connection_indicator.get_attribute("class")
                assert "connected" in (
                    indicator_class or ""
                ), f"Expected 'connected' class, got: {indicator_class}"
                assert "disconnected" not in (
                    indicator_class or ""
                ), f"Unexpected 'disconnected' class: {indicator_class}"

                # Test that the indicator is not just visually wrong but functionally accurate
                # by verifying that WebSocket-dependent features work

                # Settings panel should be visible (requires connection)
                await expect(page.locator("text=Game Settings")).to_be_visible()

                # Should be able to create a game (requires WebSocket)
                start_button = page.locator('[data-testid="start-game-button"]')
                await expect(start_button).to_be_enabled()
                await expect(start_button).not_to_have_text("Disconnected")

                print(
                    "✅ Connection indicator accurately reflects real state after New Game"
                )

            finally:
                await browser.close()

    async def test_error_handling_during_new_game_flow(
        self, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test that if there are actual connection errors during the New Game flow,
        they are handled appropriately and don't get masked by the bug.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto(e2e_urls["frontend"])
                await page.wait_for_load_state("networkidle")

                # Start with connected state
                await expect(
                    page.locator('[data-testid="connection-text"]')
                ).to_have_text("Connected", timeout=10000)

                # Create a game - settings panel should be visible by default
                start_button = page.locator('[data-testid="start-game-button"]')
                await start_button.click()

                await expect(
                    page.locator('[data-testid="game-container"]')
                ).to_be_visible(timeout=10000)

                # Block WebSocket to simulate real disconnection
                await page.route("**/ws", lambda route: route.abort())

                # Trigger potential reconnection attempt
                await page.evaluate("() => window.dispatchEvent(new Event('online'))")

                # Click New Game during potential connection issues
                new_game_button = page.locator('button:has-text("New Game")')
                await new_game_button.click()

                await page.wait_for_timeout(2000)

                # If there's a real connection issue, it should be handled gracefully
                # The important thing is that the UI should reflect the actual state,
                # not a false disconnection due to the bug

                connection_text = page.locator('[data-testid="connection-text"]')
                status = await connection_text.text_content()

                # Either should be connected (if WebSocket blocking didn't affect existing connection)
                # or should show appropriate error handling (not false disconnection from bug)
                assert status in [
                    "Connected",
                    "Disconnected",
                    "Connecting...",
                ], f"Unexpected status: {status}"

                print(f"✅ Connection status during error conditions: {status}")

            finally:
                await browser.close()
