"""Helper functions for E2E tests."""

from playwright.async_api import Page, expect


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
    settings_button = page.locator('button:has-text("⚙️ Game Settings")')
    settings_panel = page.locator("text=Game Settings").first

    if await settings_button.count() > 0:
        # We have a toggle button (game exists) - click it to open settings
        print("✅ Settings toggle button found")
        await settings_button.click()
        await page.wait_for_timeout(500)
    elif await settings_panel.count() > 0:
        # Settings panel is already visible (no game exists)
        print("✅ Settings panel is already visible")
    else:
        raise AssertionError("Neither settings button nor panel found")

    if should_click_start_game:
        # Look for and click start game button
        start_button = page.locator('[data-testid="start-game-button"]')
        await expect(start_button).to_be_visible(timeout=5000)
        print("✅ Start Game button found")
        await start_button.click()
        await page.wait_for_timeout(3000)


async def wait_for_game_settings_available(page: Page, timeout: int = 5000) -> bool:
    """
    Wait for either the settings panel or toggle button to be available.

    Returns True if settings are available, False if timeout.
    """
    try:
        # Wait for either the toggle button or settings panel to be visible
        await page.wait_for_function(
            """() => {
                const toggleButton = document.querySelector('button:has-text("⚙️ Game Settings")');
                const settingsPanel = document.querySelector('[data-testid="game-settings"], .game-settings');
                const gameSettingsText = Array.from(document.querySelectorAll('*')).find(el => el.textContent?.includes('Game Settings'));
                return toggleButton || settingsPanel || gameSettingsText;
            }""",
            timeout=timeout,
        )
        return True
    except Exception:
        return False
