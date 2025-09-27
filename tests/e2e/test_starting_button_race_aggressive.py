"""
Aggressive Starting Button Race Condition Tests

Enhanced tests that reproduce the specific race condition where the Start Game
button gets stuck in "Starting..." state after clicking New Game.
"""

import asyncio
import random
from typing import Dict, List
import pytest
from playwright.async_api import Page, expect, Route


@pytest.mark.e2e
@pytest.mark.asyncio
class TestStartingButtonRaceCondition:
    """Test the specific Starting button race condition found in E2E tests."""

    async def test_starting_button_stuck_after_new_game(self, page: Page) -> None:
        """Reproduce the exact race condition where button stays in Starting... state."""
        await page.goto("http://localhost:8000")

        # Wait for initial connection
        connection_text = page.locator('[data-testid="connection-text"]')
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        # Step 1: Start a game normally
        start_button = page.locator('[data-testid="start-game-button"]')
        await expect(start_button).to_be_enabled()
        await start_button.click()

        # Wait for game to be created
        game_container = page.locator('[data-testid="game-container"]')
        await expect(game_container).to_be_visible(timeout=10000)

        # Step 2: Click New Game - this triggers the race condition
        new_game_button = page.locator('button:has-text("New Game")')
        await expect(new_game_button).to_be_visible()
        await new_game_button.click()

        # Should return to setup
        game_setup = page.locator('[data-testid="game-setup"]')
        await expect(game_setup).to_be_visible(timeout=5000)

        # CRITICAL: Check if button is stuck in Starting... state or disappeared
        start_button_after = page.locator('[data-testid="start-game-button"]')

        # Wait a moment to see if button recovers
        await asyncio.sleep(2.0)

        # Check if button exists at all
        button_count = await start_button_after.count()

        if button_count == 0:
            print(
                f"❌ Race condition reproduced: Start Game button completely disappeared!"
            )
            # Check what's actually visible
            all_button_handles = await page.locator("button").element_handles()
            button_texts = []
            for btn in all_button_handles:
                text = await btn.text_content()
                button_texts.append(text)

            print(f"Available buttons: {button_texts}")
            assert (
                False
            ), f"Start Game button disappeared after New Game - severe race condition"

        button_text = await start_button_after.text_content()
        button_disabled = not await start_button_after.is_enabled()

        if button_text == "Starting..." and button_disabled:
            print(f"❌ Race condition reproduced: Button stuck in 'Starting...' state")
            print(f"Button text: '{button_text}', Disabled: {button_disabled}")

            # This is the race condition - button should be "Start Game" and enabled
            assert (
                False
            ), f"Button stuck in Starting state: text='{button_text}', disabled={button_disabled}"
        else:
            print(
                f"✅ Button recovered: text='{button_text}', disabled={button_disabled}"
            )
            assert button_text == "Start Game"
            assert not button_disabled

    async def test_multiple_rapid_new_game_cycles(self, page: Page) -> None:
        """Test multiple rapid New Game cycles to consistently trigger the race condition."""
        await page.goto("http://localhost:8000")

        connection_text = page.locator('[data-testid="connection-text"]')
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        stuck_count = 0
        total_cycles = 5

        for cycle in range(total_cycles):
            print(f"--- Cycle {cycle + 1} ---")

            # Start game
            start_button = page.locator('[data-testid="start-game-button"]')
            if await start_button.count() > 0 and await start_button.is_enabled():
                await start_button.click()

                # Wait for game (but not too long)
                try:
                    game_container = page.locator('[data-testid="game-container"]')
                    await expect(game_container).to_be_visible(timeout=5000)
                except:
                    print(f"Game creation timed out in cycle {cycle + 1}")
                    continue

                # Rapid New Game click
                new_game_button = page.locator('button:has-text("New Game")')
                if await new_game_button.count() > 0:
                    await new_game_button.click()

                    # Check for stuck state
                    await asyncio.sleep(1.0)

                    start_button_after = page.locator(
                        '[data-testid="start-game-button"]'
                    )
                    if await start_button_after.count() > 0:
                        button_text = await start_button_after.text_content()
                        button_disabled = not await start_button_after.is_enabled()

                        if button_text == "Starting..." and button_disabled:
                            stuck_count += 1
                            print(
                                f"❌ Cycle {cycle + 1}: Button stuck in Starting state"
                            )
                        else:
                            print(f"✅ Cycle {cycle + 1}: Button OK - '{button_text}'")

            # Small delay between cycles
            await asyncio.sleep(0.5)

        print(f"Stuck count: {stuck_count}/{total_cycles}")

        # If more than 20% of cycles result in stuck state, it's a consistent race condition
        if stuck_count > 0:
            assert (
                False
            ), f"Button stuck in {stuck_count}/{total_cycles} cycles - race condition detected"

    async def test_network_delay_triggers_race_condition(self, page: Page) -> None:
        """Test with network delays to make race condition more likely."""

        # Add delays to game creation requests
        async def delay_games_request(route: Route) -> None:
            if "games" in route.request.url:
                await asyncio.sleep(1.0)  # 1 second delay
            await route.continue_()

        await page.route("**/games**", delay_games_request)

        await page.goto("http://localhost:8000")

        connection_text = page.locator('[data-testid="connection-text"]')
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        # Start game with delayed response
        start_button = page.locator('[data-testid="start-game-button"]')
        await start_button.click()

        # Wait for button to show "Starting..."
        await expect(start_button).to_have_text("Starting...")
        await expect(start_button).to_be_disabled()

        # Wait for delayed game creation
        game_container = page.locator('[data-testid="game-container"]')
        await expect(game_container).to_be_visible(timeout=8000)

        # Rapid New Game during potential state confusion
        new_game_button = page.locator('button:has-text("New Game")')
        await new_game_button.click()

        # Check for race condition
        await asyncio.sleep(2.0)

        start_button_final = page.locator('[data-testid="start-game-button"]')
        button_text = await start_button_final.text_content()
        button_disabled = not await start_button_final.is_enabled()

        if button_text == "Starting..." and button_disabled:
            assert (
                False
            ), f"Race condition with network delay: button stuck in Starting state"

    async def test_websocket_disconnection_during_new_game(self, page: Page) -> None:
        """Test WebSocket disconnection during New Game to trigger race condition."""
        await page.goto("http://localhost:8000")

        connection_text = page.locator('[data-testid="connection-text"]')
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        # Start game
        start_button = page.locator('[data-testid="start-game-button"]')
        await start_button.click()

        game_container = page.locator('[data-testid="game-container"]')
        await expect(game_container).to_be_visible(timeout=8000)

        # Block WebSocket before New Game click
        await page.route("**/ws", lambda route: route.abort())

        # Click New Game while WebSocket is blocked
        new_game_button = page.locator('button:has-text("New Game")')
        await new_game_button.click()

        # Wait a moment
        await asyncio.sleep(1.0)

        # Restore WebSocket
        await page.unroute("**/ws")

        # Check for stuck button after restoration
        await asyncio.sleep(2.0)

        start_button_final = page.locator('[data-testid="start-game-button"]')
        if await start_button_final.count() > 0:
            button_text = await start_button_final.text_content()
            button_disabled = not await start_button_final.is_enabled()

            if button_text == "Starting..." and button_disabled:
                assert (
                    False
                ), f"Race condition with WebSocket disconnection: button stuck"

    async def test_concurrent_operations_during_state_transition(
        self, page: Page
    ) -> None:
        """Test concurrent operations during critical state transitions."""
        await page.goto("http://localhost:8000")

        connection_text = page.locator('[data-testid="connection-text"]')
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        # Start game
        start_button = page.locator('[data-testid="start-game-button"]')
        await start_button.click()

        game_container = page.locator('[data-testid="game-container"]')
        await expect(game_container).to_be_visible(timeout=8000)

        # Concurrent operations: New Game + rapid clicking
        async def rapid_clicks() -> None:
            for _ in range(5):
                try:
                    elements = await page.locator("button").element_handles()
                    for element in elements:
                        if await element.is_visible() and await element.is_enabled():
                            await element.click(timeout=100)
                            break
                except:
                    pass
                await asyncio.sleep(0.05)

        new_game_button = page.locator('button:has-text("New Game")')

        # Start both operations concurrently
        await asyncio.gather(
            new_game_button.click(), rapid_clicks(), return_exceptions=True
        )

        # Check final state
        await asyncio.sleep(2.0)

        start_button_final = page.locator('[data-testid="start-game-button"]')
        if await start_button_final.count() > 0:
            button_text = await start_button_final.text_content()
            button_disabled = not await start_button_final.is_enabled()

            if button_text == "Starting..." and button_disabled:
                assert False, f"Race condition with concurrent operations: button stuck"

    async def test_dom_corruption_during_transition(self, page: Page) -> None:
        """Test DOM corruption during state transitions."""
        await page.goto("http://localhost:8000")

        connection_text = page.locator('[data-testid="connection-text"]')
        await expect(connection_text).to_have_text("Connected", timeout=10000)

        # Start game
        start_button = page.locator('[data-testid="start-game-button"]')
        await start_button.click()

        game_container = page.locator('[data-testid="game-container"]')
        await expect(game_container).to_be_visible(timeout=8000)

        # Corrupt DOM during New Game click
        await page.evaluate(
            """
            () => {
                // Force React re-renders by modifying DOM
                const elements = document.querySelectorAll('[data-testid]');
                elements.forEach(el => {
                    el.setAttribute('data-corrupted', 'true');
                    el.style.display = 'none';
                    setTimeout(() => {
                        el.style.display = '';
                        el.removeAttribute('data-corrupted');
                    }, Math.random() * 100);
                });
            }
        """
        )

        # Click New Game during DOM corruption
        new_game_button = page.locator('button:has-text("New Game")')
        await new_game_button.click()

        # Wait for DOM to settle
        await asyncio.sleep(2.0)

        # Check for stuck state
        start_button_final = page.locator('[data-testid="start-game-button"]')
        if await start_button_final.count() > 0:
            button_text = await start_button_final.text_content()
            button_disabled = not await start_button_final.is_enabled()

            if button_text == "Starting..." and button_disabled:
                assert (
                    False
                ), f"Race condition with DOM corruption: button stuck in Starting state"
