"""
E2E tests to reproduce and verify the game creation disconnection bug.

This test suite specifically targets the bug where the UI shows "Disconnected"
when attempting to create a new game, even when the connection should be available.
"""

import asyncio
import time
from typing import Dict

import pytest
from playwright.async_api import Page, Route, async_playwright, expect


@pytest.mark.e2e
@pytest.mark.asyncio
class TestGameCreationDisconnectionBug:
    """Tests to reproduce and verify fixes for the game creation disconnection bug."""

    async def test_game_creation_immediately_on_page_load(
        self, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test creating a game immediately after page load.

        This reproduces the bug where the WebSocket might not be fully connected
        when the user tries to create a game right away.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # Navigate to frontend
                await page.goto(e2e_urls["frontend"])

                # Immediately try to click game settings without waiting
                # This simulates a user quickly trying to start a game
                settings_button = page.locator('button:has-text("⚙️ Game Settings")')

                # Check if button exists and try to click it immediately
                if await settings_button.count() > 0:
                    # Don't wait for connection - click immediately
                    await settings_button.click(timeout=1000)

                    # Check for disconnection warning
                    disconnection_warning = page.locator(
                        '[data-testid="connection-warning"]'
                    )
                    if await disconnection_warning.count() > 0:
                        warning_text = await disconnection_warning.text_content()
                        assert (
                            warning_text is None
                            or "Connection Required" not in warning_text
                        ), "Bug reproduced: Shows disconnection warning when should be connected"

                    # Try to start game
                    start_button = page.locator('[data-testid="start-game-button"]')
                    if await start_button.count() > 0:
                        is_enabled = await start_button.is_enabled()
                        button_text = await start_button.text_content()

                        # Check if button shows "Disconnected" or is disabled
                        assert is_enabled and (
                            button_text is None or "Disconnected" not in button_text
                        ), f"Bug reproduced: Start button disabled or shows 'Disconnected': {button_text}"

                        # If enabled, try to create game
                        if is_enabled:
                            await start_button.click()

                            # Wait for either game creation or error
                            await page.wait_for_timeout(2000)

                            # Check if game was created or if we got disconnection error
                            game_container = page.locator(
                                '[data-testid="game-container"]'
                            )
                            error_message = page.locator(
                                '[data-testid="error-message"]'
                            )

                            if await error_message.count() > 0:
                                error_text = await error_message.text_content()
                                assert (
                                    error_text is None
                                    or "disconnect" not in error_text.lower()
                                ), f"Bug reproduced: Got disconnection error: {error_text}"

                print("✅ Game creation immediately on load handled correctly")

            finally:
                await browser.close()

    async def test_game_creation_during_websocket_connecting(
        self, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test creating a game while WebSocket is still connecting.

        This tests the race condition between WebSocket connection establishment
        and game creation attempts.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # Intercept WebSocket to delay connection
                await page.route(
                    "**/ws",
                    lambda route: asyncio.create_task(
                        self._delay_and_continue(route, delay_ms=2000)
                    ),
                )

                # Navigate to frontend
                await page.goto(e2e_urls["frontend"])

                # Immediately check connection status
                connection_status = page.locator('[data-testid="connection-status"]')
                if await connection_status.count() > 0:
                    status_text = await connection_status.text_content()
                    print(f"Initial connection status: {status_text}")

                # Try to interact with game settings while connecting
                await page.wait_for_timeout(
                    500
                )  # Small delay to ensure we're mid-connection

                settings_button = page.locator('button:has-text("⚙️ Game Settings")')
                if await settings_button.count() > 0:
                    is_enabled = await settings_button.is_enabled()

                    # Button should either be disabled with clear messaging or queue the action
                    if not is_enabled:
                        # Check for appropriate "connecting" messaging
                        # Check button title attribute if available
                        try:
                            title_attr = await settings_button.get_attribute("title")  # type: ignore
                            if title_attr and "connect" in title_attr.lower():
                                print("✅ Button shows appropriate connecting message")
                        except AttributeError:
                            # getAttribute might not exist in some Playwright versions
                            print("ℹ️ Cannot check button title attribute")
                    else:
                        # If enabled, clicking should queue the action or show appropriate feedback
                        await settings_button.click()

                        # Should show connecting state or queue the request
                        loading_indicator = page.locator(
                            '[data-testid="loading-indicator"]'
                        )
                        connection_message = page.locator(
                            '[data-testid="connection-message"]'
                        )

                        has_feedback = (await loading_indicator.count() > 0) or (
                            await connection_message.count() > 0
                        )
                        assert (
                            has_feedback
                        ), "Bug: No feedback shown when attempting action during connection"

                # Wait for connection to complete
                await page.unroute("**/ws")
                await page.wait_for_timeout(3000)

                # Now verify game creation works after connection
                if (
                    await settings_button.count() > 0
                    and await settings_button.is_enabled()
                ):
                    await settings_button.click()
                    start_button = page.locator('[data-testid="start-game-button"]')
                    if (
                        await start_button.count() > 0
                        and await start_button.is_enabled()
                    ):
                        await start_button.click()

                        # Should successfully create game
                        game_container = page.locator('[data-testid="game-container"]')
                        await expect(game_container).to_be_visible(timeout=5000)
                        print(
                            "✅ Game created successfully after connection established"
                        )

            finally:
                await browser.close()

    async def test_ui_connection_status_accuracy(
        self, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test that UI connection status accurately reflects actual connection state.

        This verifies that the connection indicator matches the real WebSocket state
        and that game creation is properly gated on actual connectivity.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto(e2e_urls["frontend"])
                await page.wait_for_load_state("networkidle")

                # Get initial connection status
                connection_indicator = page.locator(
                    '[data-testid="connection-indicator"]'
                )
                connection_text = page.locator('[data-testid="connection-text"]')

                if await connection_indicator.count() > 0:
                    # Should show connected after network idle
                    await expect(connection_text).to_have_text(
                        "Connected", timeout=5000
                    )

                    # Now break the connection
                    await page.route("**/ws", lambda route: route.abort())
                    await page.route("**/health", lambda route: route.abort())
                    await page.route("**/games", lambda route: route.abort())

                    # Force a reconnection attempt by interacting with the page
                    await page.evaluate(
                        "() => window.dispatchEvent(new Event('online'))"
                    )
                    await page.wait_for_timeout(2000)

                    # Should show disconnected
                    status_text = await connection_text.text_content()
                    assert status_text in [
                        "Disconnected",
                        "Connecting...",
                    ], f"Bug: Shows '{status_text}' when actually disconnected"

                    # Game creation should be disabled
                    settings_button = page.locator(
                        'button:has-text("⚙️ Game Settings")'
                    )
                    if await settings_button.count() > 0:
                        is_enabled = await settings_button.is_enabled()
                        assert (
                            not is_enabled
                        ), "Bug: Game settings accessible when disconnected"

                    # Restore connection
                    await page.unroute("**/ws")
                    await page.unroute("**/health")
                    await page.unroute("**/games")

                    # Trigger reconnection
                    await page.evaluate(
                        "() => window.dispatchEvent(new Event('online'))"
                    )
                    await page.wait_for_timeout(3000)

                    # Should show connected again
                    await expect(connection_text).to_have_text(
                        "Connected", timeout=10000
                    )

                    # Game creation should work now
                    if await settings_button.count() > 0:
                        is_enabled = await settings_button.is_enabled()
                        assert (
                            is_enabled
                        ), "Bug: Game settings still disabled after reconnection"

                print("✅ Connection status accurately reflects actual state")

            finally:
                await browser.close()

    async def test_race_condition_rest_api_vs_websocket(
        self, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test race condition between REST API and WebSocket availability.

        The bug might occur when REST API is available but WebSocket isn't ready,
        or vice versa. This tests that game creation properly checks both.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # Scenario 1: WebSocket works but REST API fails
                await page.route("**/games", lambda route: route.abort())

                await page.goto(e2e_urls["frontend"])
                await page.wait_for_load_state("networkidle")

                # Try to create a game
                settings_button = page.locator('button:has-text("⚙️ Game Settings")')
                if (
                    await settings_button.count() > 0
                    and await settings_button.is_enabled()
                ):
                    await settings_button.click()

                    start_button = page.locator('[data-testid="start-game-button"]')
                    if (
                        await start_button.count() > 0
                        and await start_button.is_enabled()
                    ):
                        await start_button.click()

                        # Should show error about game creation failure
                        await page.wait_for_timeout(2000)
                        error_toast = page.locator(
                            '.toast-error, [data-testid="error-toast"]'
                        )
                        if await error_toast.count() > 0:
                            error_text = await error_toast.text_content()
                            # Should indicate API failure, not generic disconnection
                            assert (
                                error_text is None
                                or "disconnect" not in error_text.lower()
                                or "create" in error_text.lower()
                            ), f"Bug: Shows generic disconnection instead of specific error: {error_text}"

                # Restore REST API
                await page.unroute("**/games")

                # Scenario 2: REST API works but WebSocket fails
                await page.route("**/ws", lambda route: route.abort())
                await page.reload()
                await page.wait_for_timeout(2000)

                # Check if UI properly indicates WebSocket issue
                connection_text = page.locator('[data-testid="connection-text"]')
                if await connection_text.count() > 0:
                    status = await connection_text.text_content()
                    assert (
                        status != "Connected"
                    ), "Bug: Shows connected when WebSocket is actually broken"

                print("✅ REST API vs WebSocket race conditions handled correctly")

            finally:
                await browser.close()

    async def test_rapid_game_creation_attempts(self, e2e_urls: Dict[str, str]) -> None:
        """
        Test rapid successive game creation attempts.

        Users might click the start button multiple times quickly,
        which could expose race conditions in the connection/creation flow.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto(e2e_urls["frontend"])
                await page.wait_for_load_state("networkidle")

                # Open game settings
                settings_button = page.locator('button:has-text("⚙️ Game Settings")')
                if await settings_button.count() > 0:
                    await settings_button.click()

                    start_button = page.locator('[data-testid="start-game-button"]')
                    if await start_button.count() > 0:
                        # Click start button rapidly multiple times
                        for _ in range(5):
                            await start_button.click()
                            await page.wait_for_timeout(100)

                        # Should only create one game, not multiple
                        await page.wait_for_timeout(2000)

                        # Check that we're in a game
                        game_container = page.locator('[data-testid="game-container"]')
                        game_count = await game_container.count()

                        if game_count > 0:
                            # Good - game was created
                            print("✅ Single game created despite rapid clicks")

                            # Verify no duplicate game creation errors
                            error_messages = page.locator(
                                '[data-testid="error-message"]'
                            )
                            if await error_messages.count() > 0:
                                # Get text from first error message
                                first_error = error_messages.first
                                error_text = await first_error.text_content()
                                if error_text:
                                    assert (
                                        "duplicate" not in error_text.lower()
                                    ), f"Bug: Duplicate game creation attempted: {error_text}"
                        else:
                            # Check if we got appropriate error handling
                            error_toast = page.locator(
                                '.toast-error, [data-testid="error-toast"]'
                            )
                            assert (
                                await error_toast.count() > 0
                            ), "Bug: No game created and no error shown after rapid clicks"

            finally:
                await browser.close()

    # Helper method for delaying routes
    @staticmethod
    async def _delay_and_continue(route: Route, delay_ms: int) -> None:
        """Helper to delay a route before continuing."""
        await asyncio.sleep(delay_ms / 1000)
        await route.continue_()
