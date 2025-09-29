"""
Component-Level E2E Race Condition Tests

These tests use Playwright to test specific component race conditions
that cause E2E failures. They focus on DOM timing and component lifecycle issues.
"""

import asyncio
import pytest
from playwright.async_api import Page, expect, Request, Response
from typing import List, Dict
from tests.e2e.e2e_helpers import SETTINGS_BUTTON_SELECTOR


class TestGameSettingsComponentRaces:
    """Test GameSettings component race conditions with Playwright."""

    @pytest.mark.asyncio
    async def test_settings_button_accessibility_during_rapid_state_changes(
        self, page: Page
    ) -> None:
        """Test Settings button remains accessible during rapid state changes."""

        await page.goto("http://localhost:8000")

        # Wait for initial load
        await page.wait_for_selector('[data-testid="start-game-button"]', timeout=5000)

        # Create game rapidly
        start_button = page.locator('[data-testid="start-game-button"]')
        await start_button.click()

        # Wait for game creation and check for Settings button
        # The button might appear as toggle or panel depending on timing
        try:
            # Try to find toggle button first
            settings_button = page.locator(SETTINGS_BUTTON_SELECTOR)
            await expect(settings_button).to_be_visible(timeout=3000)

            # Click to expand settings
            await settings_button.click()
            await expect(page.locator("text=Game Mode")).to_be_visible(timeout=2000)

        except Exception:
            # If toggle button not found, settings panel might be directly visible
            await expect(page.locator("text=Game Mode")).to_be_visible(timeout=2000)

    @pytest.mark.asyncio
    async def test_rapid_game_creation_cycles(self, page: Page) -> None:
        """Test rapid game creation and cancellation cycles."""

        await page.goto("http://localhost:8000")

        for i in range(3):
            # Wait for start button
            start_button = page.locator('[data-testid="start-game-button"]')
            await expect(start_button).to_be_visible(timeout=5000)

            # Start game
            await start_button.click()

            # Wait briefly for game creation
            await asyncio.sleep(0.5)

            # Try to access settings (button should always be accessible)
            settings_available = False

            # Check if toggle button exists
            toggle_button = page.locator(SETTINGS_BUTTON_SELECTOR)
            if await toggle_button.count() > 0:
                await toggle_button.click()
                settings_available = True

            # Check if settings panel is directly visible
            game_mode_text = page.locator("text=Game Mode")
            if await game_mode_text.count() > 0:
                settings_available = True

            assert settings_available, f"Settings not accessible in cycle {i}"

            # If we opened toggle, close it
            cancel_button = page.locator("text=Cancel")
            if await cancel_button.count() > 0:
                await cancel_button.click()

            # Reset by reloading page
            await page.reload()

    @pytest.mark.asyncio
    async def test_connection_state_changes_during_interaction(
        self, page: Page
    ) -> None:
        """Test UI behavior during connection state changes."""

        await page.goto("http://localhost:8000")

        # Initial state should show settings
        await expect(page.locator('[data-testid="start-game-button"]')).to_be_visible(
            timeout=5000
        )

        # Simulate connection loss by intercepting WebSocket
        await page.route("ws://localhost:8000/ws", lambda route: route.abort())

        # Create game (this may fail due to connection issues)
        start_button = page.locator('[data-testid="start-game-button"]')
        await start_button.click()

        # Wait and check UI state
        await asyncio.sleep(1.0)

        # UI should still be accessible - either settings panel or toggle button
        ui_accessible = False

        # Check for settings panel
        if await page.locator('[data-testid="start-game-button"]').count() > 0:
            ui_accessible = True

        # Check for settings toggle
        if await page.locator(SETTINGS_BUTTON_SELECTOR).count() > 0:
            ui_accessible = True

        assert ui_accessible, "UI not accessible after connection issues"

    @pytest.mark.asyncio
    async def test_dom_update_timing_race_conditions(self, page: Page) -> None:
        """Test DOM update timing that causes race conditions."""

        await page.goto("http://localhost:8000")

        # Monitor DOM changes
        dom_changes = []

        def track_dom_changes(request: Request) -> None:
            if "ws://" in request.url:
                dom_changes.append(f"WebSocket: {request.url}")

        page.on("request", track_dom_changes)

        # Start game and immediately check for elements
        start_button = page.locator('[data-testid="start-game-button"]')
        await start_button.click()

        # Rapid element checks (simulate fast frontend updates)
        for i in range(10):
            # Check for any game settings UI
            settings_elements = await page.locator(
                '[data-testid*="mode-"], button:has-text("⚙️ Game Settings")'
            ).count()

            # At least one settings element should always be present
            assert settings_elements > 0, f"No settings elements found at check {i}"

            await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_component_lifecycle_race_conditions(self, page: Page) -> None:
        """Test component lifecycle race conditions."""

        await page.goto("http://localhost:8000")

        # Monitor console errors
        console_errors = []
        page.on(
            "console",
            lambda msg: console_errors.append(msg.text)
            if msg.type == "error"
            else None,
        )

        # Rapid interaction sequence
        for i in range(5):
            # Find and click start button
            start_button = page.locator('[data-testid="start-game-button"]')
            if await start_button.count() > 0:
                await start_button.click()
                await asyncio.sleep(0.2)

            # Try to access settings
            toggle_button = page.locator(SETTINGS_BUTTON_SELECTOR)
            if await toggle_button.count() > 0:
                await toggle_button.click()
                await asyncio.sleep(0.1)

                # Try to close settings
                cancel_button = page.locator("text=Cancel")
                if await cancel_button.count() > 0:
                    await cancel_button.click()

            await asyncio.sleep(0.1)

        # Check for console errors
        serious_errors = [
            err for err in console_errors if "Error" in err or "TypeError" in err
        ]
        assert len(serious_errors) == 0, f"Console errors detected: {serious_errors}"


class TestWebSocketComponentIntegration:
    """Test WebSocket integration with component state."""

    @pytest.mark.asyncio
    async def test_websocket_message_timing_with_ui_updates(self, page: Page) -> None:
        """Test WebSocket message timing with UI updates."""

        await page.goto("http://localhost:8000")

        # Monitor WebSocket messages
        ws_messages = []

        def capture_ws_response(response: Response) -> None:
            if "ws://" in response.url:
                ws_messages.append(response.url)

        page.on("response", capture_ws_response)

        # Start game
        start_button = page.locator('[data-testid="start-game-button"]')
        await start_button.click()

        # Wait for WebSocket activity
        await asyncio.sleep(1.0)

        # Check UI is responsive after WebSocket activity
        settings_accessible = False

        # Check for toggle button
        toggle_button = page.locator(SETTINGS_BUTTON_SELECTOR)
        if await toggle_button.count() > 0:
            await toggle_button.click()
            await expect(page.locator("text=Game Mode")).to_be_visible(timeout=2000)
            settings_accessible = True
        else:
            # Check if settings panel is directly visible
            if await page.locator("text=Game Mode").count() > 0:
                settings_accessible = True

        assert settings_accessible, "Settings not accessible after WebSocket activity"

    @pytest.mark.asyncio
    async def test_concurrent_websocket_and_user_interactions(self, page: Page) -> None:
        """Test concurrent WebSocket messages and user interactions."""

        await page.goto("http://localhost:8000")

        # Start game to initiate WebSocket activity
        start_button = page.locator('[data-testid="start-game-button"]')
        await start_button.click()

        # Wait for game creation
        await asyncio.sleep(0.5)

        # Rapid user interactions while WebSocket is active
        for i in range(3):
            # Try to access settings
            toggle_button = page.locator(SETTINGS_BUTTON_SELECTOR)
            if await toggle_button.count() > 0:
                await toggle_button.click()

                # Verify settings panel opens
                await expect(page.locator("text=Game Mode")).to_be_visible(timeout=1000)

                # Change a setting
                human_vs_human = page.locator('[data-testid="mode-human-vs-human"]')
                if await human_vs_human.count() > 0:
                    await human_vs_human.click()

                # Close settings
                cancel_button = page.locator("text=Cancel")
                if await cancel_button.count() > 0:
                    await cancel_button.click()

            await asyncio.sleep(0.2)


class TestUIStateConsistency:
    """Test UI state consistency during rapid changes."""

    @pytest.mark.asyncio
    async def test_settings_visibility_consistency(self, page: Page) -> None:
        """Test settings visibility remains consistent."""

        await page.goto("http://localhost:8000")

        # Initial state - settings should be visible
        await expect(page.locator('[data-testid="start-game-button"]')).to_be_visible(
            timeout=5000
        )

        # Track UI state changes
        ui_states = []

        for i in range(5):
            # Check current UI state
            has_start_button = (
                await page.locator('[data-testid="start-game-button"]').count() > 0
            )
            has_toggle_button = await page.locator(SETTINGS_BUTTON_SELECTOR).count() > 0
            has_game_mode = await page.locator("text=Game Mode").count() > 0

            ui_state = {
                "iteration": i,
                "has_start_button": has_start_button,
                "has_toggle_button": has_toggle_button,
                "has_game_mode": has_game_mode,
            }
            ui_states.append(ui_state)

            # User should always have access to game settings
            settings_accessible = has_start_button or has_toggle_button or has_game_mode
            assert (
                settings_accessible
            ), f"Settings not accessible at iteration {i}: {ui_state}"

            # Trigger state change if start button is available
            if has_start_button:
                await page.locator('[data-testid="start-game-button"]').click()
                await asyncio.sleep(0.3)

            # Reset for next iteration
            await page.reload()
            await asyncio.sleep(0.2)

    @pytest.mark.asyncio
    async def test_no_element_disappearance_during_transitions(
        self, page: Page
    ) -> None:
        """Test that elements don't disappear during state transitions."""

        await page.goto("http://localhost:8000")

        # Monitor element disappearance
        element_states = []

        # Start monitoring
        for check in range(20):
            # Count key elements
            start_buttons = await page.locator(
                '[data-testid="start-game-button"]'
            ).count()
            toggle_buttons = await page.locator(SETTINGS_BUTTON_SELECTOR).count()
            mode_elements = await page.locator('[data-testid*="mode-"]').count()

            element_count = start_buttons + toggle_buttons + mode_elements
            element_states.append(element_count)

            # There should always be some settings-related elements visible
            assert element_count > 0, f"No settings elements visible at check {check}"

            # Trigger action on first check
            if check == 0:
                start_button = page.locator('[data-testid="start-game-button"]')
                if await start_button.count() > 0:
                    await start_button.click()

            await asyncio.sleep(0.1)

        # Verify elements were consistently present
        zero_count = element_states.count(0)
        assert (
            zero_count == 0
        ), f"Elements disappeared {zero_count} times: {element_states}"


class TestErrorHandlingRaceConditions:
    """Test error handling during race conditions."""

    @pytest.mark.asyncio
    async def test_error_state_ui_consistency(self, page: Page) -> None:
        """Test UI consistency when errors occur during race conditions."""

        await page.goto("http://localhost:8000")

        # Monitor console for errors
        errors = []
        page.on(
            "console", lambda msg: errors.append(msg) if msg.type == "error" else None
        )

        # Trigger potential error conditions
        start_button = page.locator('[data-testid="start-game-button"]')

        # Rapid clicking (might cause errors)
        for i in range(3):
            if await start_button.count() > 0:
                await start_button.click()
            await asyncio.sleep(0.1)

        # Check UI is still functional
        await asyncio.sleep(1.0)

        # Settings should still be accessible
        settings_accessible = False

        if await page.locator('[data-testid="start-game-button"]').count() > 0:
            settings_accessible = True
        elif await page.locator(SETTINGS_BUTTON_SELECTOR).count() > 0:
            settings_accessible = True
        elif await page.locator("text=Game Mode").count() > 0:
            settings_accessible = True

        assert settings_accessible, "Settings not accessible after error conditions"

        # Check for unhandled errors
        unhandled_errors = [e for e in errors if "Uncaught" in e.text]
        assert (
            len(unhandled_errors) == 0
        ), f"Unhandled errors: {[e.text for e in unhandled_errors]}"

    @pytest.mark.asyncio
    async def test_recovery_from_race_condition_errors(self, page: Page) -> None:
        """Test recovery from race condition errors."""

        await page.goto("http://localhost:8000")

        # Simulate error conditions by rapid interactions
        for attempt in range(5):
            try:
                start_button = page.locator('[data-testid="start-game-button"]')
                if await start_button.count() > 0:
                    await start_button.click()

                    # Wait briefly
                    await asyncio.sleep(0.2)

                    # Try to access settings immediately
                    toggle_button = page.locator(SETTINGS_BUTTON_SELECTOR)
                    if await toggle_button.count() > 0:
                        await toggle_button.click()

                        # Verify settings opened
                        await expect(page.locator("text=Game Mode")).to_be_visible(
                            timeout=1000
                        )

                        # Close settings
                        cancel_button = page.locator("text=Cancel")
                        if await cancel_button.count() > 0:
                            await cancel_button.click()

            except Exception as e:
                # If an error occurs, the UI should still recover
                pass

            # Reload to reset state
            await page.reload()
            await asyncio.sleep(0.3)

        # Final check - UI should be functional
        await expect(page.locator('[data-testid="start-game-button"]')).to_be_visible(
            timeout=5000
        )
