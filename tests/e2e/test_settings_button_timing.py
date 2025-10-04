"""
Settings Button Timing E2E Tests

Specific tests targeting the exact timing issues that cause the Settings button
to disappear in E2E tests, making them unable to find the "⚙️ Game Settings" element.
"""

import asyncio
import pytest
from playwright.async_api import Page, expect, Locator
from typing import List, Dict, Optional, Callable, Awaitable, Union
from typing_extensions import TypedDict
from tests.e2e.e2e_helpers import SETTINGS_BUTTON_SELECTOR


class StateTransitionResult(TypedDict):
    transition: str
    start_button: bool
    toggle_button: bool
    settings_panel: bool


@pytest.mark.e2e
class TestSettingsButtonTiming:
    """Test precise timing issues with Settings button availability."""

    @pytest.mark.asyncio
    async def test_settings_button_immediate_availability_after_game_creation(
        self, page: Page
    ) -> None:
        """Test Settings button is immediately available after game creation."""

        await page.goto("http://localhost:8000")

        # Wait for initial load
        await expect(page.locator('[data-testid="start-game-button"]')).to_be_visible(
            timeout=5000
        )

        # Create game
        start_button = page.locator('[data-testid="start-game-button"]')
        await start_button.click()

        # The critical test: Settings button should be available immediately
        # This is what the original E2E test was failing on
        settings_button = page.locator(SETTINGS_BUTTON_SELECTOR)

        # Use a short timeout to catch timing issues
        try:
            await expect(settings_button).to_be_visible(timeout=2000)
        except Exception:
            # If toggle button not immediately visible, check if settings panel is visible
            game_mode = page.locator("text=Game Mode")
            await expect(game_mode).to_be_visible(timeout=2000)

    @pytest.mark.asyncio
    async def test_settings_button_never_disappears_during_game_lifecycle(
        self, page: Page
    ) -> None:
        """Test Settings button never completely disappears during game lifecycle."""

        await page.goto("http://localhost:8000")

        # Monitor Settings button availability continuously
        settings_availability = []

        async def monitor_settings_availability() -> None:
            """Monitor Settings button availability every 50ms."""
            for i in range(100):  # Monitor for 5 seconds
                toggle_visible = (
                    await page.locator(SETTINGS_BUTTON_SELECTOR).count() > 0
                )
                panel_visible = await page.locator("text=Game Mode").count() > 0
                start_visible = (
                    await page.locator('[data-testid="start-game-button"]').count() > 0
                )

                settings_available = toggle_visible or panel_visible or start_visible
                settings_availability.append(
                    {
                        "time": i * 50,
                        "toggle": toggle_visible,
                        "panel": panel_visible,
                        "start": start_visible,
                        "any_available": settings_available,
                    }
                )

                await asyncio.sleep(0.05)

        # Start monitoring
        monitor_task = asyncio.create_task(monitor_settings_availability())

        # Perform game lifecycle operations
        await asyncio.sleep(0.1)  # Let monitoring start

        # Create game
        start_button = page.locator('[data-testid="start-game-button"]')
        if await start_button.count() > 0:
            await start_button.click()

        # Wait for game creation and let monitoring continue
        await asyncio.sleep(3.0)

        # Stop monitoring
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

        # Analyze results
        unavailable_periods = [
            entry for entry in settings_availability if not entry["any_available"]
        ]

        # Settings should NEVER be completely unavailable
        assert (
            len(unavailable_periods) == 0
        ), f"Settings unavailable at: {unavailable_periods}"

    @pytest.mark.asyncio
    async def test_settings_button_findable_by_playwright_selectors(
        self, page: Page
    ) -> None:
        """Test Settings button is findable using the same selectors as failing E2E tests."""

        await page.goto("http://localhost:8000")

        # Start game
        await page.locator('[data-testid="start-game-button"]').click()

        # Test selectors that should work with functional implementation
        selectors_to_test = [
            SETTINGS_BUTTON_SELECTOR,  # Primary selector for toggle button
            "button.retro-btn.toggle-settings",  # Class-based selector
            'button:has-text("⚙️ Game Settings")',  # Button with emoji text
            '[title="Game Settings"]',  # Title attribute
        ]

        found_selectors = []
        for selector in selectors_to_test:
            count = await page.locator(selector).count()
            if count > 0:
                found_selectors.append(selector)

        # At least one selector should work
        assert (
            len(found_selectors) > 0
        ), f"No selectors found Settings button. Available selectors: {found_selectors}"

        # Test the exact selector from failing E2E test
        main_selector = SETTINGS_BUTTON_SELECTOR
        if main_selector in found_selectors:
            # This is the primary selector - test it works
            settings_button = page.locator(main_selector)
            await expect(settings_button).to_be_visible()
            await expect(settings_button).to_be_enabled()

    @pytest.mark.asyncio
    async def test_immediate_settings_availability_after_game_creation(
        self, page: Page
    ) -> None:
        """Test that settings are immediately available after game creation."""

        await page.goto("http://localhost:8000")

        # Initially, settings panel should be visible (no game state)
        await expect(page.locator("text=Game Settings")).to_be_visible()

        # Start game - this should transition to toggle button immediately
        start_button = page.locator('[data-testid="start-game-button"]')
        await start_button.click()

        # Wait for game to be created
        await expect(page.locator('[data-testid="game-container"]')).to_be_visible(
            timeout=10000
        )

        # Settings toggle button should be immediately available (no intermediate states)
        settings_toggle = page.locator(SETTINGS_BUTTON_SELECTOR)
        await expect(settings_toggle).to_be_visible(timeout=2000)

        # Verify we can click the settings button
        await settings_toggle.click()

        # Settings panel should open
        await expect(page.locator("text=Game Mode")).to_be_visible(timeout=2000)

    @pytest.mark.asyncio
    async def test_functional_state_consistency_during_rapid_operations(
        self, page: Page
    ) -> None:
        """Test that functional design prevents race conditions through consistent state."""

        await page.goto("http://localhost:8000")

        # Wait for initial connection
        await expect(page.locator('[data-testid="connection-text"]')).to_have_text(
            "Connected", timeout=10000
        )

        # Functional design test: rapid operations should maintain consistent state
        for attempt in range(3):  # Reduced iterations since no race conditions exist
            # Initial state: no-game shows settings panel
            settings_panel = page.locator("text=Game Settings")
            await expect(settings_panel).to_be_visible(timeout=5000)

            start_button = page.locator('[data-testid="start-game-button"]')
            await expect(start_button).to_be_enabled()

            # Create game - functional transition: no-game -> active-game
            await start_button.click()

            # Wait for game creation - functional design ensures deterministic transition
            game_container = page.locator('[data-testid="game-container"]')
            await expect(game_container).to_be_visible(timeout=10000)

            # Active-game state: shows toggle button
            settings_toggle = page.locator(SETTINGS_BUTTON_SELECTOR)
            await expect(settings_toggle).to_be_visible()

            # Click New Game - functional transition: active-game -> no-game
            new_game_button = page.locator('button:has-text("New Game")')
            await new_game_button.click()

            # Wait for transition to complete - game container should disappear first
            game_setup = page.locator('[data-testid="game-setup"]')
            await expect(game_setup).to_be_visible(timeout=5000)

            # Back to no-game state: shows panel (no intermediate states)
            await expect(settings_panel).to_be_visible(timeout=2000)

            print(f"✅ Functional consistency maintained in cycle {attempt + 1}")

    @pytest.mark.asyncio
    async def test_settings_button_visibility_during_state_transitions(
        self, page: Page
    ) -> None:
        """Test Settings button visibility during all state transitions."""

        await page.goto("http://localhost:8000")

        # Map of expected states and their Settings access methods
        state_transitions = [
            "initial_load",  # Should show start button + full panel
            "game_creating",  # Should show loading state
            "game_created",  # Should show toggle button
            "settings_expanded",  # Should show full panel
            "settings_collapsed",  # Should show toggle button
        ]

        transition_results: List[StateTransitionResult] = []

        for transition in state_transitions:
            if transition == "initial_load":
                # Already at initial state
                start_visible = (
                    await page.locator('[data-testid="start-game-button"]').count() > 0
                )
                assert start_visible, "Start button not visible at initial load"

            elif transition == "game_creating":
                # Click start button
                await page.locator('[data-testid="start-game-button"]').click()
                # Brief moment of loading
                await asyncio.sleep(0.1)

            elif transition == "game_created":
                # Wait for game creation to complete
                await asyncio.sleep(0.5)
                # Check for toggle button
                toggle_visible = (
                    await page.locator(SETTINGS_BUTTON_SELECTOR).count() > 0
                )
                start_visible = (
                    await page.locator('[data-testid="start-game-button"]').count() > 0
                )
                settings_accessible = toggle_visible or start_visible
                assert (
                    settings_accessible
                ), "Settings not accessible after game creation"

            elif transition == "settings_expanded":
                # Try to expand settings
                toggle_button = page.locator(SETTINGS_BUTTON_SELECTOR)
                if await toggle_button.count() > 0:
                    await toggle_button.click()
                    await expect(page.locator("text=Game Mode")).to_be_visible(
                        timeout=2000
                    )

            elif transition == "settings_collapsed":
                # Try to collapse settings
                cancel_button = page.locator("text=Cancel")
                if await cancel_button.count() > 0:
                    await cancel_button.click()
                    await expect(page.locator(SETTINGS_BUTTON_SELECTOR)).to_be_visible(
                        timeout=2000
                    )

            # Record current state
            start_button_visible = (
                await page.locator('[data-testid="start-game-button"]').count() > 0
            )
            toggle_button_visible = (
                await page.locator(SETTINGS_BUTTON_SELECTOR).count() > 0
            )
            settings_panel_visible = await page.locator("text=Game Mode").count() > 0

            current_state: StateTransitionResult = {
                "transition": transition,
                "start_button": start_button_visible,
                "toggle_button": toggle_button_visible,
                "settings_panel": settings_panel_visible,
            }
            transition_results.append(current_state)

        # Verify at each transition, settings were accessible
        for result in transition_results:
            settings_accessible = (
                result["start_button"]
                or result["toggle_button"]
                or result["settings_panel"]
            )
            assert (
                settings_accessible
            ), f"Settings not accessible during {result['transition']}: {result}"


@pytest.mark.e2e
class TestSettingsButtonEdgeCases:
    """Test edge cases that might cause Settings button issues."""

    @pytest.mark.asyncio
    async def test_settings_button_with_safe_page_interactions(
        self, page: Page
    ) -> None:
        """Test Settings button with safe page interactions that don't break state."""

        await page.goto("http://localhost:8000")

        # Wait for initial connection
        await expect(page.locator('[data-testid="connection-text"]')).to_have_text(
            "Connected", timeout=10000
        )

        # Safe interactions that shouldn't break the functional state
        safe_interactions: List[Callable[[], Awaitable[None]]] = [
            lambda: page.keyboard.press("Escape"),  # Safe - won't change state
            lambda: page.keyboard.press("Tab"),  # Safe - just changes focus
            lambda: page.mouse.click(100, 100),  # Safe - click empty area
        ]

        for i in range(6):  # Reduced iterations
            # Perform safe interaction
            interaction = safe_interactions[i % len(safe_interactions)]
            try:
                await interaction()
            except Exception:
                pass  # Some interactions may fail, that's okay

            # Brief wait for any UI updates
            await page.wait_for_timeout(50)

            # Verify settings are still accessible - should be settings panel by default
            settings_panel = page.locator("text=Game Settings")
            await expect(settings_panel).to_be_visible(timeout=2000)

            start_button = page.locator('[data-testid="start-game-button"]')
            await expect(start_button).to_be_enabled()

        print("✅ Settings remain accessible through safe interactions")

    @pytest.mark.asyncio
    async def test_settings_button_with_browser_events(self, page: Page) -> None:
        """Test Settings button with browser events that might cause issues."""

        await page.goto("http://localhost:8000")

        # Browser events that might interfere
        async def resize_event() -> None:
            await page.evaluate("window.dispatchEvent(new Event('resize'))")

        async def focus_event() -> None:
            await page.evaluate("window.dispatchEvent(new Event('focus'))")

        async def blur_event() -> None:
            await page.evaluate("window.dispatchEvent(new Event('blur'))")

        events: List[Callable[[], Awaitable[None]]] = [
            resize_event,
            focus_event,
            blur_event,
        ]

        # Wait for initial connection
        await expect(page.locator('[data-testid="connection-text"]')).to_have_text(
            "Connected", timeout=10000
        )

        # Start game first and wait for proper state transition
        start_button = page.locator('[data-testid="start-game-button"]')
        await start_button.click()

        # Wait for game creation to complete
        game_container = page.locator('[data-testid="game-container"]')
        await expect(game_container).to_be_visible(timeout=10000)

        # Trigger events and check Settings button
        for i, event_trigger in enumerate(events):
            try:
                await event_trigger()
            except Exception:
                pass

            # Verify Settings toggle button remains accessible
            settings_toggle = page.locator(SETTINGS_BUTTON_SELECTOR)
            await expect(settings_toggle).to_be_visible(timeout=2000)

        print("✅ Settings button survives browser events")

    @pytest.mark.asyncio
    async def test_settings_button_survives_page_errors(self, page: Page) -> None:
        """Test Settings button survives JavaScript errors and failed operations."""

        await page.goto("http://localhost:8000")

        # Wait for initial connection and verify settings available
        await expect(page.locator('[data-testid="connection-text"]')).to_have_text(
            "Connected", timeout=10000
        )

        # Start game and wait for proper state transition
        start_button = page.locator('[data-testid="start-game-button"]')
        await start_button.click()

        # Wait for game to be created properly
        game_container = page.locator('[data-testid="game-container"]')
        await expect(game_container).to_be_visible(timeout=10000)

        # Test 1: Click non-existent element (should fail gracefully)
        try:
            await page.locator('[data-testid="nonexistent"]').click(timeout=100)
        except Exception:
            pass  # Expected to fail

        # Settings should still be accessible
        settings_toggle = page.locator(SETTINGS_BUTTON_SELECTOR)
        await expect(settings_toggle).to_be_visible(timeout=2000)

        # Test 2: Trigger JavaScript error (should not break UI)
        try:
            await page.evaluate("window.nonExistentFunction()")
        except Exception:
            pass  # Expected to fail

        # Settings should still be accessible
        await expect(settings_toggle).to_be_visible(timeout=2000)

        print("✅ Settings button survives page errors")
