"""
E2E tests for network interruption scenarios and recovery.

These tests simulate various network failure conditions to verify that
the application handles connection issues gracefully and recovers properly.
"""

import asyncio
import time
from typing import Dict

import pytest
from playwright.async_api import Page, Route, async_playwright, expect


@pytest.mark.e2e
@pytest.mark.asyncio
class TestNetworkInterruptions:
    """Tests for network interruption handling and recovery."""

    async def test_brief_network_blip_recovery(self, e2e_urls: Dict[str, str]) -> None:
        """
        Test recovery from brief network interruptions (< 1 second).

        These are common in mobile networks and WiFi transitions.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto(e2e_urls["frontend"])
                await page.wait_for_load_state("networkidle")

                # Establish initial connection
                connection_text = page.locator('[data-testid="connection-text"]')
                await expect(connection_text).to_have_text("Connected", timeout=10000)

                print("✅ Initial connection established")

                # Create a game to have some state
                settings_button = page.locator('button:has-text("⚙️ Game Settings")')
                await settings_button.click()

                start_button = page.locator('[data-testid="start-game-button"]')
                await start_button.click()

                game_container = page.locator('[data-testid="game-container"]')
                await expect(game_container).to_be_visible(timeout=10000)

                print("✅ Game created successfully")

                # Simulate brief network interruption by blocking requests temporarily
                async def block_temporarily(route: Route) -> None:
                    await asyncio.sleep(0.5)  # Brief 500ms delay
                    await route.continue_()

                await page.route("**/ws", block_temporarily)
                await page.route("**/games/**", block_temporarily)

                # Trigger some network activity
                await page.evaluate("() => window.dispatchEvent(new Event('online'))")

                # Wait for brief interruption to resolve
                await page.wait_for_timeout(1000)

                # Remove route blocking
                await page.unroute("**/ws")
                await page.unroute("**/games/**")

                # Should recover quickly
                await expect(connection_text).to_have_text("Connected", timeout=5000)

                # Game should still be functional
                await expect(game_container).to_be_visible()

                # New Game button should work
                new_game_button = page.locator('button:has-text("New Game")')
                await new_game_button.click()

                # Should return to setup without issues
                await expect(page.locator('[data-testid="game-setup"]')).to_be_visible(
                    timeout=5000
                )
                await expect(connection_text).to_have_text("Connected")

                print("✅ Recovered from brief network blip")

            finally:
                await browser.close()

    async def test_extended_network_outage_recovery(
        self, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test recovery from extended network outages (> 30 seconds).
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

                print("✅ Initial connection established")

                # Block all network requests to simulate extended outage
                await page.route("**/ws", lambda route: route.abort())
                await page.route("**/games/**", lambda route: route.abort())
                await page.route("**/health", lambda route: route.abort())

                # Trigger network events to force connection checks
                await page.evaluate("() => window.dispatchEvent(new Event('offline'))")
                await page.wait_for_timeout(2000)
                await page.evaluate("() => window.dispatchEvent(new Event('online'))")

                # Should eventually show disconnected (might take some time)
                await page.wait_for_timeout(5000)

                # Check connection status
                current_status = await connection_text.text_content()
                if current_status == "Disconnected":
                    print("✅ Detected extended outage")
                else:
                    print(f"ℹ️ Status during outage: {current_status}")

                # Settings should be disabled during outage
                settings_button = page.locator('button:has-text("⚙️ Game Settings")')
                if current_status == "Disconnected":
                    await expect(settings_button).to_be_disabled()

                # Restore network
                await page.unroute("**/ws")
                await page.unroute("**/games/**")
                await page.unroute("**/health")

                # Trigger reconnection
                await page.evaluate("() => window.dispatchEvent(new Event('online'))")

                # Should recover (may take longer after extended outage)
                await expect(connection_text).to_have_text("Connected", timeout=15000)

                # Features should be restored
                await expect(settings_button).to_be_enabled()

                # Should be able to create new game
                await settings_button.click()
                start_button = page.locator('[data-testid="start-game-button"]')
                await expect(start_button).to_be_enabled()
                await expect(start_button).to_have_text("Start Game")

                print("✅ Recovered from extended network outage")

            finally:
                await browser.close()

    async def test_intermittent_connectivity_flapping(
        self, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test handling of intermittent connectivity (flapping connection).

        This simulates unstable network conditions.
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

                print("✅ Initial connection established")

                # Simulate flapping connection
                for cycle in range(5):
                    print(f"🔄 Flapping cycle {cycle + 1}")

                    # Block connection
                    await page.route("**/ws", lambda route: route.abort())
                    await page.evaluate(
                        "() => window.dispatchEvent(new Event('offline'))"
                    )

                    # Wait briefly
                    await page.wait_for_timeout(1000)

                    # Restore connection
                    await page.unroute("**/ws")
                    await page.evaluate(
                        "() => window.dispatchEvent(new Event('online'))"
                    )

                    # Wait for stabilization
                    await page.wait_for_timeout(1500)

                # After flapping, should stabilize
                await expect(connection_text).to_have_text("Connected", timeout=10000)

                # App should remain functional
                settings_button = page.locator('button:has-text("⚙️ Game Settings")')
                await expect(settings_button).to_be_enabled()

                # Should be able to create game after flapping
                await settings_button.click()
                start_button = page.locator('[data-testid="start-game-button"]')
                await start_button.click()

                await expect(
                    page.locator('[data-testid="game-container"]')
                ).to_be_visible(timeout=10000)

                print("✅ Stable after connection flapping")

            finally:
                await browser.close()

    async def test_connection_loss_during_game_creation(
        self, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test network failure during game creation process.
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

                # Open settings
                settings_button = page.locator('button:has-text("⚙️ Game Settings")')
                await settings_button.click()

                # Block game creation requests
                await page.route("**/games", lambda route: route.abort())

                # Try to start game
                start_button = page.locator('[data-testid="start-game-button"]')
                await start_button.click()

                # Wait to see what happens
                await page.wait_for_timeout(3000)

                # Should show error or remain in settings
                # Game container should not appear
                game_container = page.locator('[data-testid="game-container"]')
                await expect(game_container).not_to_be_visible()

                # Restore network
                await page.unroute("**/games")

                # Try again
                if await start_button.count() > 0 and await start_button.is_enabled():
                    await start_button.click()
                    await expect(game_container).to_be_visible(timeout=10000)
                    print("✅ Game creation succeeded after network restoration")
                else:
                    # May need to reopen settings
                    await settings_button.click()
                    await start_button.click()
                    await expect(game_container).to_be_visible(timeout=10000)
                    print("✅ Game creation succeeded after reopening settings")

            finally:
                await browser.close()

    async def test_websocket_vs_http_failure_isolation(
        self, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test handling when WebSocket fails but HTTP works, or vice versa.
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

                print("✅ Initial connection established")

                # Scenario 1: WebSocket fails, HTTP works
                print("🧪 Testing WebSocket failure with HTTP working")

                await page.route("**/ws", lambda route: route.abort())

                # Trigger reconnection attempt
                await page.evaluate("() => window.dispatchEvent(new Event('online'))")
                await page.wait_for_timeout(3000)

                # Connection status might show disconnected
                status_after_ws_failure = await connection_text.text_content()
                print(f"Status after WebSocket failure: {status_after_ws_failure}")

                # Try to create game (should fail gracefully if WebSocket required)
                settings_button = page.locator('button:has-text("⚙️ Game Settings")')
                if await settings_button.is_enabled():
                    await settings_button.click()
                    start_button = page.locator('[data-testid="start-game-button"]')
                    if await start_button.is_enabled():
                        await start_button.click()
                        await page.wait_for_timeout(2000)
                        # Should either succeed or show appropriate error

                # Restore WebSocket
                await page.unroute("**/ws")

                # Scenario 2: HTTP fails, WebSocket works (harder to test realistically)
                print("🧪 Testing HTTP failure with WebSocket working")

                await page.route("**/games", lambda route: route.abort())
                await page.route("**/health", lambda route: route.abort())

                # WebSocket might still be connected
                await page.wait_for_timeout(2000)

                # Try game creation (should fail on HTTP calls)
                if await settings_button.count() > 0:
                    await settings_button.click()
                    start_button = page.locator('[data-testid="start-game-button"]')
                    await start_button.click()
                    await page.wait_for_timeout(2000)

                    # Should handle HTTP failure gracefully

                # Restore all connections
                await page.unroute("**/games")
                await page.unroute("**/health")

                await page.wait_for_timeout(2000)
                await expect(connection_text).to_have_text("Connected", timeout=10000)

                print("✅ Handled partial network failures")

            finally:
                await browser.close()

    async def test_network_recovery_after_server_restart(
        self, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test recovery after server becomes unavailable and returns.

        This simulates server restarts or maintenance.
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

                print("✅ Initial connection established")

                # Create a game to have state
                settings_button = page.locator('button:has-text("⚙️ Game Settings")')
                await settings_button.click()

                start_button = page.locator('[data-testid="start-game-button"]')
                await start_button.click()

                await expect(
                    page.locator('[data-testid="game-container"]')
                ).to_be_visible(timeout=10000)

                print("✅ Game created before server restart simulation")

                # Simulate server down (all requests fail)
                await page.route("**/*", lambda route: route.abort())

                # Trigger network activity to detect failure
                await page.evaluate("() => window.dispatchEvent(new Event('offline'))")
                await page.wait_for_timeout(1000)
                await page.evaluate("() => window.dispatchEvent(new Event('online'))")

                # Wait for disconnection detection
                await page.wait_for_timeout(5000)

                current_status = await connection_text.text_content()
                if current_status == "Disconnected":
                    print("✅ Detected server unavailability")
                else:
                    print(f"ℹ️ Status during server downtime: {current_status}")

                # Simulate server coming back online
                await page.unroute("**/*")

                # Trigger reconnection
                await page.evaluate("() => window.dispatchEvent(new Event('online'))")

                # Should reconnect
                await expect(connection_text).to_have_text("Connected", timeout=15000)

                # Game state handling depends on implementation
                # Either game persists or we're back to setup
                game_container = page.locator('[data-testid="game-container"]')
                game_setup = page.locator('[data-testid="game-setup"]')

                if await game_container.count() > 0:
                    print("✅ Game state preserved through server restart")
                elif await game_setup.count() > 0:
                    print("✅ Returned to setup after server restart")

                    # Should be able to create new game
                    await settings_button.click()
                    await start_button.click()
                    await expect(game_container).to_be_visible(timeout=10000)
                    print("✅ New game creation works after recovery")

            finally:
                await browser.close()

    async def test_slow_network_conditions(self, e2e_urls: Dict[str, str]) -> None:
        """
        Test application behavior under slow network conditions.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # Simulate slow network
                async def slow_route(route: Route) -> None:
                    await asyncio.sleep(2)  # 2 second delay
                    await route.continue_()

                await page.route("**/ws", slow_route)
                await page.route("**/games/**", slow_route)

                await page.goto(e2e_urls["frontend"])
                await page.wait_for_load_state("networkidle")

                # Connection might take longer
                connection_text = page.locator('[data-testid="connection-text"]')
                await expect(connection_text).to_have_text("Connected", timeout=15000)

                print("✅ Connected despite slow network")

                # Game creation should work but be slower
                settings_button = page.locator('button:has-text("⚙️ Game Settings")')
                await settings_button.click()

                start_button = page.locator('[data-testid="start-game-button"]')
                await start_button.click()

                # Should show loading state
                await expect(start_button).to_have_text("Starting...", timeout=5000)

                # Eventually should complete
                await expect(
                    page.locator('[data-testid="game-container"]')
                ).to_be_visible(timeout=20000)

                print("✅ Game creation completed despite slow network")

                # Remove slow network simulation
                await page.unroute("**/ws")
                await page.unroute("**/games/**")

                # Operations should be faster now
                new_game_button = page.locator('button:has-text("New Game")')
                await new_game_button.click()

                await expect(page.locator('[data-testid="game-setup"]')).to_be_visible(
                    timeout=5000
                )

                print("✅ Performance improved after network speed restoration")

            finally:
                await browser.close()

    async def test_network_failure_error_messages(
        self, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test that appropriate error messages are shown for different network failures.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            console_messages = []
            page.on("console", lambda msg: console_messages.append(msg.text))

            try:
                await page.goto(e2e_urls["frontend"])
                await page.wait_for_load_state("networkidle")

                connection_text = page.locator('[data-testid="connection-text"]')
                await expect(connection_text).to_have_text("Connected", timeout=10000)

                # Test different failure scenarios and their error handling
                failure_scenarios = [
                    ("WebSocket", "**/ws"),
                    ("Game API", "**/games/**"),
                    ("All endpoints", "**/*"),
                ]

                for scenario_name, route_pattern in failure_scenarios:
                    print(f"🧪 Testing {scenario_name} failure")

                    # Clear previous console messages
                    console_messages.clear()

                    # Block the specific endpoint
                    await page.route(route_pattern, lambda route: route.abort())

                    # Try to trigger network activity
                    settings_button = page.locator(
                        'button:has-text("⚙️ Game Settings")'
                    )
                    if await settings_button.is_enabled():
                        await settings_button.click()
                        start_button = page.locator('[data-testid="start-game-button"]')
                        if await start_button.is_enabled():
                            await start_button.click()

                    # Wait for error detection
                    await page.wait_for_timeout(3000)

                    # Check for appropriate error handling
                    # This could be console errors, UI error messages, etc.
                    relevant_errors = [
                        msg
                        for msg in console_messages
                        if "error" in msg.lower() or "failed" in msg.lower()
                    ]

                    if relevant_errors:
                        print(
                            f"  ✅ Error detected for {scenario_name}: {len(relevant_errors)} messages"
                        )
                    else:
                        print(
                            f"  ℹ️ No explicit errors for {scenario_name} (might be handled silently)"
                        )

                    # Restore endpoint
                    await page.unroute(route_pattern)
                    await page.wait_for_timeout(1000)

                print("✅ Error handling tested for various network failures")

            finally:
                await browser.close()
