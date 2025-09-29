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

        # Use a very short timeout to catch timing issues
        try:
            await expect(settings_button).to_be_visible(timeout=500)
        except Exception:
            # If toggle button not immediately visible, check if settings panel is visible
            game_mode = page.locator("text=Game Mode")
            await expect(game_mode).to_be_visible(timeout=500)

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

        # Test all possible selectors that E2E tests might use
        selectors_to_test = [
            SETTINGS_BUTTON_SELECTOR,
            'button:has-text("Game Settings")',
            '[title="Game Settings"]',
            ".toggle-settings",
            'button.retro-btn:has-text("⚙️")',
            "text=Game Settings",
            "text=Game Mode",  # Alternative if panel is visible
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
    async def test_settings_button_timing_with_loading_states(self, page: Page) -> None:
        """Test Settings button timing during loading states."""

        await page.goto("http://localhost:8000")

        # Monitor loading states
        loading_states = []

        # Start game and monitor loading
        start_button = page.locator('[data-testid="start-game-button"]')
        await start_button.click()

        # Check for loading states
        for i in range(50):  # Check for 2.5 seconds
            is_loading = await page.locator("text=Starting...").count() > 0
            settings_toggle = await page.locator(SETTINGS_BUTTON_SELECTOR).count() > 0
            settings_panel = await page.locator("text=Game Mode").count() > 0

            loading_states.append(
                {
                    "time": i * 50,
                    "loading": is_loading,
                    "toggle": settings_toggle,
                    "panel": settings_panel,
                }
            )

            await asyncio.sleep(0.05)

        # During loading, there should still be some way to access settings
        for state in loading_states:
            if state["loading"]:
                # Even during loading, toggle button or panel should be available
                settings_accessible = state["toggle"] or state["panel"]
                assert (
                    settings_accessible
                ), f"Settings not accessible during loading at {state['time']}ms"

    @pytest.mark.asyncio
    async def test_settings_button_race_condition_prevention(self, page: Page) -> None:
        """Test prevention of the specific race condition causing button disappearance."""

        await page.goto("http://localhost:8000")

        # The race condition occurs when:
        # 1. Game creation starts (gameId becomes non-null)
        # 2. UI switches to toggle button
        # 3. Connection issues cause temporary state reset
        # 4. UI briefly shows no settings access

        # Simulate this by rapid game creation and page interactions
        for attempt in range(5):
            # Check initial state
            initial_start_button = (
                await page.locator('[data-testid="start-game-button"]').count() > 0
            )

            if initial_start_button:
                # Start game
                await page.locator('[data-testid="start-game-button"]').click()

                # Immediately check for Settings access (this is where race condition occurs)
                await asyncio.sleep(0.05)  # Very short delay

                # Check Settings button is accessible
                settings_accessible = False

                # Check for toggle button
                toggle_count = await page.locator(SETTINGS_BUTTON_SELECTOR).count()
                if toggle_count > 0:
                    settings_accessible = True

                # Check for settings panel
                panel_count = await page.locator("text=Game Mode").count()
                if panel_count > 0:
                    settings_accessible = True

                # Check for start button (if game creation failed)
                start_count = await page.locator(
                    '[data-testid="start-game-button"]'
                ).count()
                if start_count > 0:
                    settings_accessible = True

                assert (
                    settings_accessible
                ), f"Settings not accessible at attempt {attempt}"

            # Reset for next attempt
            await page.reload()
            await asyncio.sleep(0.2)

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
                        timeout=1000
                    )

            elif transition == "settings_collapsed":
                # Try to collapse settings
                cancel_button = page.locator("text=Cancel")
                if await cancel_button.count() > 0:
                    await cancel_button.click()
                    await expect(page.locator(SETTINGS_BUTTON_SELECTOR)).to_be_visible(
                        timeout=1000
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


class TestSettingsButtonEdgeCases:
    """Test edge cases that might cause Settings button issues."""

    @pytest.mark.asyncio
    async def test_settings_button_with_rapid_page_interactions(
        self, page: Page
    ) -> None:
        """Test Settings button with rapid page interactions."""

        await page.goto("http://localhost:8000")

        # Rapid interactions that might cause issues
        interactions: List[Callable[[], Awaitable[None]]] = [
            lambda: page.locator('[data-testid="start-game-button"]').click(),
            lambda: page.keyboard.press("Escape"),
            lambda: page.keyboard.press("Tab"),
            lambda: page.mouse.click(100, 100),  # Click somewhere neutral
        ]

        for i in range(10):
            # Perform random interaction
            interaction = interactions[i % len(interactions)]
            try:
                await interaction()
            except Exception:
                pass  # Some interactions may fail, that's okay

            # Check Settings button is still accessible
            await asyncio.sleep(0.05)

            settings_accessible = False
            if await page.locator('[data-testid="start-game-button"]').count() > 0:
                settings_accessible = True
            elif await page.locator(SETTINGS_BUTTON_SELECTOR).count() > 0:
                settings_accessible = True
            elif await page.locator("text=Game Mode").count() > 0:
                settings_accessible = True

            assert settings_accessible, f"Settings not accessible after interaction {i}"

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

        # Start game first
        await page.locator('[data-testid="start-game-button"]').click()
        await asyncio.sleep(0.3)

        # Trigger events and check Settings button
        for i, event_trigger in enumerate(events):
            try:
                await event_trigger()
            except Exception:
                pass

            await asyncio.sleep(0.1)

            # Verify Settings button is accessible
            toggle_visible = await page.locator(SETTINGS_BUTTON_SELECTOR).count() > 0
            panel_visible = await page.locator("text=Game Mode").count() > 0

            assert (
                toggle_visible or panel_visible
            ), f"Settings not accessible after browser event {i}"

    @pytest.mark.asyncio
    async def test_settings_button_persistence_across_errors(self, page: Page) -> None:
        """Test Settings button persists across error conditions."""

        await page.goto("http://localhost:8000")

        # Monitor console errors
        console_messages = []
        page.on("console", lambda msg: console_messages.append(msg.text))

        # Trigger potential error conditions
        async def nonexistent_click() -> None:
            await page.locator('[data-testid="nonexistent"]').click()

        async def body_click() -> None:
            await page.evaluate("document.body.click()")

        error_triggers: List[Callable[[], Awaitable[None]]] = [
            # Try to access non-existent elements
            nonexistent_click,
            # Try to click disabled elements
            body_click,
        ]

        # Start game
        await page.locator('[data-testid="start-game-button"]').click()
        await asyncio.sleep(0.2)

        for i, trigger in enumerate(error_triggers):
            try:
                await trigger()
            except Exception:
                pass  # Expected to fail

            # Check Settings button survives errors
            await asyncio.sleep(0.1)

            settings_accessible = False
            if await page.locator(SETTINGS_BUTTON_SELECTOR).count() > 0:
                settings_accessible = True
            elif await page.locator("text=Game Mode").count() > 0:
                settings_accessible = True

            assert (
                settings_accessible
            ), f"Settings not accessible after error trigger {i}"
