"""Helper functions for E2E tests."""

from playwright.async_api import Page, expect

# Centralized selectors to avoid duplication and ensure consistency
SETTINGS_BUTTON_SELECTOR = '[data-testid="settings-toggle-button"]'


async def handle_settings_interaction(
    page: Page, should_click_start_game: bool = False
) -> None:
    """
    Handle settings interaction in a consistent way across all e2e tests.

    The GameSettings component shows different UI based on state:
    - When no game exists: Shows settings panel directly
    - When game exists: Shows toggle button that must be clicked first

    Args:
        page: Playwright page object
        should_click_start_game: Whether to click the Start Game button after ensuring settings are accessible
    """
    # Check if we have the settings toggle button or panel
    settings_button = page.locator(SETTINGS_BUTTON_SELECTOR)
    settings_panel = page.locator("text=Game Settings").first

    # WebKit-specific: Add extra wait time for elements to be ready
    await page.wait_for_timeout(300)

    # Try up to 3 times with exponential backoff for WebKit
    for attempt in range(3):
        if await settings_button.count() > 0:
            # We have a toggle button (game exists) - click it to open settings
            print(f"✅ Settings toggle button found (attempt {attempt + 1})")

            # WebKit-specific: Ensure button is actually clickable with polling
            try:
                await expect(settings_button).to_be_visible(timeout=2000)
                await expect(settings_button).to_be_enabled(timeout=2000)

                # Additional WebKit check: ensure button is in viewport and not covered
                is_clickable = await page.evaluate(
                    """
                    (selector) => {
                        const btn = document.querySelector(selector);
                        if (!btn) return false;
                        const rect = btn.getBoundingClientRect();
                        return rect.top >= 0 && rect.left >= 0 && 
                               rect.bottom <= window.innerHeight && 
                               rect.right <= window.innerWidth &&
                               !btn.disabled;
                    }
                """,
                    SETTINGS_BUTTON_SELECTOR,
                )

                if is_clickable:
                    await settings_button.click()
                    await page.wait_for_timeout(
                        600 + attempt * 200
                    )  # Progressive delay

                    # Verify the settings panel opened
                    panel_opened = await settings_panel.count() > 0
                    if panel_opened:
                        print(f"✅ Settings panel opened successfully")
                        break
                    else:
                        print(f"⚠️ Settings panel not opened, retrying...")
                        continue
                else:
                    print(f"⚠️ Settings button not clickable, waiting longer...")
                    await page.wait_for_timeout(500 * (attempt + 1))
                    continue

            except Exception as e:
                print(
                    f"⚠️ Settings button interaction failed (attempt {attempt + 1}): {e}"
                )
                await page.wait_for_timeout(500 * (attempt + 1))
                continue

        elif await settings_panel.count() > 0:
            # Settings panel is already visible (no game exists)
            print("✅ Settings panel is already visible")
            break
        else:
            # WebKit fallback: Try waiting longer for elements to appear
            wait_time = 1000 * (attempt + 1)
            print(f"⚠️ No settings UI found, waiting {wait_time}ms...")
            await page.wait_for_timeout(wait_time)
            continue
    else:
        # All attempts failed
        raise AssertionError(
            "Neither settings button nor panel found after 3 attempts with progressive delays"
        )

    if should_click_start_game:
        # Look for and click start game button
        start_button = page.locator('[data-testid="start-game-button"]')

        # WebKit-specific: More robust start button interaction
        for attempt in range(3):
            try:
                await expect(start_button).to_be_visible(timeout=5000)
                await expect(start_button).to_be_enabled(timeout=2000)

                # Ensure button is clickable
                is_clickable = await page.evaluate(
                    """
                    () => {
                        const btn = document.querySelector('[data-testid="start-game-button"]');
                        if (!btn) return false;
                        const rect = btn.getBoundingClientRect();
                        return rect.top >= 0 && rect.left >= 0 && 
                               rect.bottom <= window.innerHeight && 
                               rect.right <= window.innerWidth &&
                               !btn.disabled;
                    }
                """
                )

                if is_clickable:
                    print(
                        f"✅ Start Game button found and clickable (attempt {attempt + 1})"
                    )
                    await start_button.click()
                    await page.wait_for_timeout(3000 + attempt * 500)
                    break
                else:
                    await page.wait_for_timeout(500 * (attempt + 1))

            except Exception as e:
                print(
                    f"⚠️ Start Game button interaction failed (attempt {attempt + 1}): {e}"
                )
                await page.wait_for_timeout(500 * (attempt + 1))
        else:
            raise AssertionError("Start Game button not clickable after 3 attempts")


async def wait_for_game_settings_available(page: Page, timeout: int = 5000) -> bool:
    """
    Wait for either the settings panel or toggle button to be available.

    Returns True if settings are available, False if timeout.
    """
    try:
        # WebKit-enhanced: More comprehensive element detection
        await page.wait_for_function(
            """() => {
                const toggleButton = document.querySelector('[data-testid="settings-toggle-button"]');
                const settingsPanel = document.querySelector('[data-testid="game-settings-panel"]');
                const gameSettingsText = Array.from(document.querySelectorAll('*')).find(el => el.textContent?.includes('Game Settings'));
                
                // WebKit-specific: Also check for button visibility and enabled state
                if (toggleButton) {
                    const rect = toggleButton.getBoundingClientRect();
                    const isVisible = rect.width > 0 && rect.height > 0 && toggleButton.offsetParent !== null;
                    const isEnabled = !toggleButton.disabled && !toggleButton.hasAttribute('aria-disabled');
                    return isVisible && isEnabled;
                }
                
                return settingsPanel || gameSettingsText;
            }""",
            timeout=timeout,
        )
        return True
    except Exception:
        return False


async def handle_rapid_settings_interaction(page: Page) -> None:
    """
    Handle rapid settings interaction for race condition tests.

    This function is used for race condition scenarios where we need to click
    settings rapidly but handle both panel and button states.
    """
    settings_button = page.locator(SETTINGS_BUTTON_SELECTOR)
    settings_panel = page.locator("text=Game Settings").first

    if await settings_button.count() > 0:
        # Settings button exists - use it for race condition
        await settings_button.click()
    elif await settings_panel.count() > 0:
        # Panel is already visible - interaction successful
        print("✅ Settings panel already visible for race condition test")
    else:
        # Fallback - wait briefly for UI to stabilize then check again
        await page.wait_for_timeout(100)
        if await settings_button.count() > 0:
            await settings_button.click()
        else:
            print("⚠️ Neither settings button nor panel found for race condition test")
