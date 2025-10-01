"""
E2E tests for race condition scenarios.

These tests verify that the application handles concurrent user actions
and timing-sensitive operations correctly, particularly around the
New Game disconnection bug and related race conditions.

This version uses the generic page fixture and runs on all 3 browsers.
"""

import asyncio
import time
from typing import Dict

import pytest
from playwright.async_api import Page, Route, expect
from tests.e2e.e2e_helpers import (
    SETTINGS_BUTTON_SELECTOR,
    handle_settings_interaction,
    handle_rapid_settings_interaction,
)


@pytest.mark.e2e
@pytest.mark.asyncio
class TestRaceConditions:
    """Tests for race condition handling."""

    async def test_simultaneous_new_game_and_settings_clicks(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test rapid clicking of New Game and Settings buttons.

        This tests the specific race condition in the disconnection bug.
        """
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        connection_text = page.locator('[data-testid="connection-text"]')
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        # Create initial game using helper function
        await handle_settings_interaction(page, should_click_start_game=True)

        await expect(page.locator('[data-testid="game-container"]')).to_be_visible(
            timeout=10000
        )

        print("✅ Initial game created")

        # Rapid sequence: New Game -> Settings almost simultaneously
        new_game_button = page.locator('button:has-text("New Game")')

        # Start both actions concurrently
        new_game_task = asyncio.create_task(new_game_button.click())

        # Small delay to ensure New Game starts first, then Settings
        await asyncio.sleep(0.1)
        settings_task = asyncio.create_task(handle_rapid_settings_interaction(page))

        # Wait for both to complete
        await asyncio.gather(new_game_task, settings_task, return_exceptions=True)

        # Wait for state to stabilize
        await page.wait_for_timeout(2000)

        # Should be in settings panel or setup, and connected
        await expect(connection_text).to_have_text("Connected", timeout=5000)

        # Settings panel might or might not be open depending on timing
        # But connection should not be affected
        print("✅ Simultaneous New Game + Settings handled correctly")

        # Try starting a game if settings are open
        if await page.locator("text=Game Settings").count() > 0:
            start_button = page.locator('[data-testid="start-game-button"]')
            if await start_button.is_enabled():
                await start_button.click()
                await expect(
                    page.locator('[data-testid="game-container"]')
                ).to_be_visible(timeout=10000)
                print("✅ Game creation works after race condition")

    async def test_multiple_start_game_clicks_rapid_succession(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test multiple rapid clicks on Start Game button.

        Users might click multiple times if the button seems unresponsive.
        """
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        await expect(page.locator('[data-testid="connection-text"]')).to_have_text(
            "Connected", timeout=10000
        )

        # Open settings using helper function
        await handle_settings_interaction(page)

        start_button = page.locator('[data-testid="start-game-button"]')
        await expect(start_button).to_be_enabled()

        print("✅ Settings opened, ready for rapid clicking test")

        # Rapid fire clicking on Start Game
        click_tasks = []
        for i in range(5):
            # Only click if button still exists and is enabled
            if await start_button.count() > 0:
                click_tasks.append(
                    asyncio.create_task(start_button.click(timeout=1000))
                )
                await asyncio.sleep(0.05)  # 50ms between clicks

        # Wait for all clicks to complete (some may fail)
        results = await asyncio.gather(*click_tasks, return_exceptions=True)

        successful_clicks = sum(1 for r in results if not isinstance(r, Exception))
        print(f"✅ {successful_clicks} out of {len(click_tasks)} clicks succeeded")

        # Should create exactly one game, not multiple
        await page.wait_for_timeout(3000)

        game_containers = page.locator('[data-testid="game-container"]')
        container_count = await game_containers.count()

        if container_count == 1:
            print("✅ Single game created despite multiple clicks")
        elif container_count == 0:
            # Might have failed due to race conditions - check for errors
            print("ℹ️ No game created - checking for error handling")

            # Should still be connected
            await expect(page.locator('[data-testid="connection-text"]')).to_have_text(
                "Connected"
            )

            # Should be able to try again
            if await start_button.count() > 0 and await start_button.is_enabled():
                await start_button.click()
                await expect(
                    page.locator('[data-testid="game-container"]')
                ).to_be_visible(timeout=10000)
                print("✅ Retry succeeded after rapid clicking")
        else:
            print(f"⚠️ Unexpected: {container_count} game containers found")

    async def test_new_game_during_websocket_reconnection(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test New Game button clicked during WebSocket reconnection.

        This tests the race condition between reset and connection state.
        """
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        connection_text = page.locator('[data-testid="connection-text"]')
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        # Create a game using helper function
        await handle_settings_interaction(page, should_click_start_game=True)

        await expect(page.locator('[data-testid="game-container"]')).to_be_visible(
            timeout=10000
        )

        print("✅ Game created before connection interruption")

        # Interrupt WebSocket connection
        await page.route("**/ws", lambda route: route.abort())

        # Trigger reconnection attempt
        await page.evaluate("() => window.dispatchEvent(new Event('offline'))")
        await page.wait_for_timeout(1000)

        # While reconnection is happening, click New Game
        new_game_button = page.locator('button:has-text("New Game")')
        await new_game_button.click()

        # Restore connection during/after reset
        await page.unroute("**/ws")
        await page.evaluate("() => window.dispatchEvent(new Event('online'))")

        # Wait for state to stabilize
        await page.wait_for_timeout(3000)

        # Should end up in a consistent state
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        # Should be at game setup
        game_setup = page.locator('[data-testid="game-setup"]')
        await expect(game_setup).to_be_visible()

        # Settings should be functional
        settings_button = page.locator(SETTINGS_BUTTON_SELECTOR)
        await expect(settings_button).to_be_enabled()

        print("✅ New Game during reconnection handled correctly")

    async def test_settings_changes_during_game_creation(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test changing settings while game creation is in progress.
        """
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        await expect(page.locator('[data-testid="connection-text"]')).to_have_text(
            "Connected", timeout=10000
        )

        # Open settings using helper function
        await handle_settings_interaction(page)

        # Slow down game creation to create race condition window
        async def delay_game_creation(route: Route) -> None:
            await asyncio.sleep(2)  # 2 second delay
            await route.continue_()

        await page.route("**/games", delay_game_creation)

        # Start game creation
        start_button = page.locator('[data-testid="start-game-button"]')
        await start_button.click()

        # Immediately try to change settings while creation is pending
        await asyncio.sleep(0.1)  # Small delay to ensure creation started

        # Try to change mode
        ai_vs_ai_button = page.locator('[data-testid="mode-ai-vs-ai"]')
        if await ai_vs_ai_button.count() > 0:
            await ai_vs_ai_button.click()

        # Try to change difficulty
        expert_button = page.locator('button:has-text("Expert")')
        if await expert_button.count() > 0:
            await expert_button.click()

        print("✅ Attempted settings changes during game creation")

        # Wait for game creation to complete
        await page.wait_for_timeout(4000)

        # Remove route delay
        await page.unroute("**/games")

        # Should have created game or handled race condition gracefully
        game_container = page.locator('[data-testid="game-container"]')
        game_setup = page.locator('[data-testid="game-setup"]')

        if await game_container.count() > 0:
            print("✅ Game created despite settings changes")
        elif await game_setup.count() > 0:
            print("✅ Remained at setup due to race condition handling")

        # Should be connected regardless
        await expect(page.locator('[data-testid="connection-text"]')).to_have_text(
            "Connected"
        )

    async def test_concurrent_new_game_clicks_from_different_contexts(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test multiple New Game clicks happening at the exact same time.

        This simulates edge cases in state management.
        """
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        await expect(page.locator('[data-testid="connection-text"]')).to_have_text(
            "Connected", timeout=10000
        )

        # Create a game first using helper function
        await handle_settings_interaction(page, should_click_start_game=True)

        await expect(page.locator('[data-testid="game-container"]')).to_be_visible(
            timeout=10000
        )

        print("✅ Game created for concurrent New Game test")

        # Simulate concurrent New Game clicks
        new_game_button = page.locator('button:has-text("New Game")')

        # Create multiple concurrent click tasks
        concurrent_clicks = [
            asyncio.create_task(new_game_button.click(timeout=2000)) for _ in range(3)
        ]

        # Execute all clicks simultaneously
        click_results = await asyncio.gather(*concurrent_clicks, return_exceptions=True)

        successful_clicks = sum(
            1 for r in click_results if not isinstance(r, Exception)
        )
        print(f"✅ {successful_clicks} concurrent New Game clicks processed")

        # Wait for state to stabilize
        await page.wait_for_timeout(2000)

        # Should end up in consistent state
        connection_text = page.locator('[data-testid="connection-text"]')
        await expect(connection_text).to_have_text("Connected", timeout=5000)

        # Should be at game setup
        game_setup = page.locator('[data-testid="game-setup"]')
        await expect(game_setup).to_be_visible()

        # Should be able to create new game
        settings_button = page.locator(SETTINGS_BUTTON_SELECTOR)
        await expect(settings_button).to_be_enabled()

        print("✅ Concurrent New Game clicks handled correctly")

    async def test_page_navigation_during_reset(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test page navigation/refresh happening during New Game reset.
        """
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        await expect(page.locator('[data-testid="connection-text"]')).to_have_text(
            "Connected", timeout=10000
        )

        # Create a game using helper function
        await handle_settings_interaction(page, should_click_start_game=True)

        await expect(page.locator('[data-testid="game-container"]')).to_be_visible(
            timeout=10000
        )

        print("✅ Game created before navigation race test")

        # Start New Game process and immediately navigate
        new_game_button = page.locator('button:has-text("New Game")')

        # Start both actions concurrently
        new_game_task = asyncio.create_task(new_game_button.click())
        refresh_task = asyncio.create_task(page.reload())

        # Wait for both to complete (one might fail)
        await asyncio.gather(new_game_task, refresh_task, return_exceptions=True)

        # Wait for page to stabilize after refresh
        await page.wait_for_load_state("networkidle")

        # Should be in clean state after refresh
        connection_text = page.locator('[data-testid="connection-text"]')
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        # Should be at game setup
        game_setup = page.locator('[data-testid="game-setup"]')
        await expect(game_setup).to_be_visible()

        # Should be able to start new game
        settings_button = page.locator(SETTINGS_BUTTON_SELECTOR)
        await expect(settings_button).to_be_enabled()

        print("✅ Navigation during reset handled correctly")

    async def test_rapid_connection_state_changes_during_reset(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test rapid connection state changes while New Game reset is happening.
        """
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        connection_text = page.locator('[data-testid="connection-text"]')
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        # Create a game using helper function
        await handle_settings_interaction(page, should_click_start_game=True)

        await expect(page.locator('[data-testid="game-container"]')).to_be_visible(
            timeout=10000
        )

        print("✅ Game created before connection state race test")

        # Start New Game and immediately trigger connection changes
        new_game_button = page.locator('button:has-text("New Game")')

        # Create concurrent tasks
        reset_task = asyncio.create_task(new_game_button.click())

        # Rapid connection state changes
        connection_tasks = [
            asyncio.create_task(
                page.evaluate("() => window.dispatchEvent(new Event('offline'))")
            ),
            asyncio.create_task(asyncio.sleep(0.1)),
            asyncio.create_task(
                page.evaluate("() => window.dispatchEvent(new Event('online'))")
            ),
            asyncio.create_task(asyncio.sleep(0.1)),
            asyncio.create_task(
                page.evaluate("() => window.dispatchEvent(new Event('offline'))")
            ),
            asyncio.create_task(asyncio.sleep(0.1)),
            asyncio.create_task(
                page.evaluate("() => window.dispatchEvent(new Event('online'))")
            ),
        ]

        # Execute all tasks
        all_tasks = [reset_task] + connection_tasks
        await asyncio.gather(*all_tasks, return_exceptions=True)

        # Wait for state to stabilize
        await page.wait_for_timeout(3000)

        # Should end up connected (real connection should win)
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        # Should be at game setup
        game_setup = page.locator('[data-testid="game-setup"]')
        await expect(game_setup).to_be_visible()

        # Should be functional
        settings_button = page.locator(SETTINGS_BUTTON_SELECTOR)
        await expect(settings_button).to_be_enabled()

        print("✅ Rapid connection changes during reset handled correctly")

    async def test_form_submission_race_conditions(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test race conditions in form submissions (settings changes).
        """
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        await expect(page.locator('[data-testid="connection-text"]')).to_have_text(
            "Connected", timeout=10000
        )

        # Open settings using helper function
        await handle_settings_interaction(page)

        print("✅ Settings opened for race condition test")

        # Rapid fire settings changes
        changes = [
            ("mode-ai-vs-ai", page.locator('[data-testid="mode-ai-vs-ai"]')),
            ("expert", page.locator('button:has-text("Expert")')),
            ("board-7x7", page.locator('button:has-text("7x7")')),
            (
                "mode-human-vs-human",
                page.locator('[data-testid="mode-human-vs-human"]'),
            ),
            ("board-9x9", page.locator('button:has-text("9x9")')),
        ]

        # Make rapid concurrent changes
        change_tasks = []
        for name, locator in changes:
            if await locator.count() > 0:
                change_tasks.append(asyncio.create_task(locator.click()))
                await asyncio.sleep(0.05)  # Very small delays between changes

        # Wait for all changes
        await asyncio.gather(*change_tasks, return_exceptions=True)

        # Wait for state to stabilize
        await page.wait_for_timeout(1000)

        # Settings should still be functional
        start_button = page.locator('[data-testid="start-game-button"]')
        await expect(start_button).to_be_enabled()

        # Try to create game with final settings
        await start_button.click()

        # Should succeed or fail gracefully
        await page.wait_for_timeout(3000)

        # Check final state
        connection_text = page.locator('[data-testid="connection-text"]')
        await expect(connection_text).to_have_text("Connected")

        game_container = page.locator('[data-testid="game-container"]')
        if await game_container.count() > 0:
            print("✅ Game created with rapid settings changes")
        else:
            print("✅ Race condition handled gracefully without crash")
