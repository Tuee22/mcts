"""
E2E tests for network interruption scenarios and recovery.

These tests simulate various network failure conditions to verify that
the application handles connection issues gracefully and recovers properly.

This version uses the generic page fixture and runs on all 3 browsers.
"""

import asyncio
import time
from typing import Dict

import pytest
from playwright.async_api import Page, Route, expect
from tests.e2e.e2e_helpers import SETTINGS_BUTTON_SELECTOR, handle_settings_interaction


@pytest.mark.e2e
@pytest.mark.asyncio
class TestNetworkInterruptions:
    """Tests for network interruption handling and recovery."""

    async def test_brief_network_blip_recovery(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test recovery from brief network interruptions (< 1 second).

        These are common in mobile networks and WiFi transitions.
        """
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        # Establish initial connection
        connection_text = page.locator('[data-testid="connection-text"]')
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        print("✅ Initial connection established")

        # Create a game to have some state
        settings_button = page.locator(SETTINGS_BUTTON_SELECTOR)
        if await settings_button.count() > 0:
            await handle_settings_interaction(page)

            start_button = page.locator('[data-testid="start-game-button"]')
            if await start_button.count() > 0:
                await start_button.click()

        print("✅ Game setup attempted")

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

        print("✅ Recovered from brief network blip")

    async def test_extended_network_outage_recovery(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test recovery from extended network outages (> 30 seconds).
        """
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

        # Restore network by removing blocks
        await page.unroute("**/ws")
        await page.unroute("**/games/**")
        await page.unroute("**/health")

        # Should recover within reasonable time
        await expect(connection_text).to_have_text("Connected", timeout=15000)

        print("✅ Recovered from extended network outage")

    async def test_network_failure_during_startup(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """Test behavior when network fails during initial app startup."""
        # Block network before loading
        await page.route("**/ws", lambda route: route.abort())
        await page.route("**/health", lambda route: route.abort())

        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        # App should still load but show disconnected state
        title = await page.title()
        assert title == "React App"

        # Restore network
        await page.unroute("**/ws")
        await page.unroute("**/health")

        # Should eventually connect
        connection_text = page.locator('[data-testid="connection-text"]')
        if await connection_text.count() > 0:
            await expect(connection_text).to_have_text("Connected", timeout=10000)

        print("✅ Handled network failure during startup")

    async def test_intermittent_connectivity_flapping(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """Test handling of intermittent connectivity (connect/disconnect cycles)."""
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        connection_text = page.locator('[data-testid="connection-text"]')
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        print("✅ Initial connection established")

        # Simulate flapping by alternating blocks and unblocks
        for i in range(3):
            # Block connections
            await page.route("**/ws", lambda route: route.abort())
            await page.evaluate("() => window.dispatchEvent(new Event('offline'))")
            await page.wait_for_timeout(1000)

            # Unblock connections
            await page.unroute("**/ws")
            await page.evaluate("() => window.dispatchEvent(new Event('online'))")
            await page.wait_for_timeout(1000)

            print(f"✅ Flapping cycle {i+1} completed")

        # Should end up connected
        await expect(connection_text).to_have_text("Connected", timeout=10000)
        print("✅ Handled intermittent connectivity flapping")

    async def test_connection_loss_during_game_creation(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """Test network failure during game creation process."""
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        connection_text = page.locator('[data-testid="connection-text"]')
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        print("✅ Initial connection established")

        # Start game creation process
        settings_button = page.locator(SETTINGS_BUTTON_SELECTOR)
        if await settings_button.count() > 0:
            await handle_settings_interaction(page)

        # Block network during game creation
        await page.route("**/games**", lambda route: route.abort())

        # Try to start game (should fail gracefully)
        start_button = page.locator('[data-testid="start-game-button"]')
        if await start_button.count() > 0:
            await start_button.click()
            await page.wait_for_timeout(2000)

        # Restore network
        await page.unroute("**/games**")

        # Should recover
        await expect(connection_text).to_have_text("Connected", timeout=10000)
        print("✅ Handled connection loss during game creation")

    async def test_websocket_vs_http_failure_isolation(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """Test that WebSocket and HTTP failures are handled independently."""
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        connection_text = page.locator('[data-testid="connection-text"]')
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        print("✅ Initial connection established")

        # Block only WebSocket connections
        await page.route("**/ws", lambda route: route.abort())

        # HTTP should still work - test with health endpoint
        response = await page.request.get(f"{e2e_urls['backend']}/health")
        assert response.ok

        print("✅ HTTP requests work while WebSocket is blocked")

        # Restore WebSocket
        await page.unroute("**/ws")

        # Should recover
        await expect(connection_text).to_have_text("Connected", timeout=10000)
        print("✅ WebSocket vs HTTP failure isolation tested")

    async def test_network_recovery_after_server_restart(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """Test recovery after simulated server restart."""
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        connection_text = page.locator('[data-testid="connection-text"]')
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        print("✅ Initial connection established")

        # Block all server endpoints to simulate server down
        await page.route("**/*", lambda route: route.abort())
        await page.wait_for_timeout(3000)

        # Restore all endpoints to simulate server back up
        await page.unroute("**/*")

        # Should recover
        await expect(connection_text).to_have_text("Connected", timeout=20000)
        print("✅ Recovered after simulated server restart")

    async def test_slow_network_conditions(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """Test behavior under slow network conditions."""
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        connection_text = page.locator('[data-testid="connection-text"]')
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        print("✅ Initial connection established")

        # Simulate slow network by delaying all requests
        async def slow_network(route: Route) -> None:
            await asyncio.sleep(2)  # 2 second delay
            await route.continue_()

        await page.route("**/*", slow_network)

        # App should still function, just slower
        await page.wait_for_timeout(5000)

        # Remove slow network simulation
        await page.unroute("**/*")

        # Should still be connected
        await expect(connection_text).to_have_text("Connected", timeout=10000)
        print("✅ Handled slow network conditions")
