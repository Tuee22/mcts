# E2E Test Cross-Browser Migration Guide

## Overview
This guide shows how to migrate e2e tests from browser-specific `async_playwright()` usage to the generic `page` fixture that runs on all 3 browsers automatically.

## Migration Pattern

### Before (Browser-Specific)
```python
from playwright.async_api import async_playwright, expect

async def test_something(e2e_urls: Dict[str, str]) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # test code here
            await page.goto(e2e_urls["frontend"])
            # ... test logic
        finally:
            await browser.close()
```

### After (Cross-Browser)
```python
from playwright.async_api import Page, expect

async def test_something(page: Page, e2e_urls: Dict[str, str]) -> None:
    # test code here - same logic, no browser management
    await page.goto(e2e_urls["frontend"])
    # ... test logic
```

## Benefits of Migration
- **3x test coverage**: Each test now runs on Chromium, Firefox, and WebKit
- **No browser-specific logic**: All compatibility handled in fixtures
- **Simpler tests**: No browser setup/teardown code needed
- **DRY principle**: Browser configuration centralized
- **Automatic compatibility**: Firefox mobile limitations handled transparently

## Verification
The migrated tests can be verified by running:
```bash
pytest tests/e2e/test_network_interruptions_migrated.py -v
```

This shows how each test runs 3 times (once per browser) automatically.

## Files to Migrate
- [✓] test_working_connection.py (COMPLETED)
- [✓] test_cross_browser_demo.py (COMPLETED)
- [✓] test_network_interruptions_migrated.py (DEMO COMPLETED)
- [ ] test_network_interruptions.py (8 tests)
- [ ] test_new_game_disconnection_bug.py (6 tests)
- [ ] test_connection_scenarios.py (8 tests)
- [ ] test_network_failures.py (9 tests)
- [ ] test_race_conditions.py (8 tests)
- [ ] test_complete_gameplay.py (5 tests)
- [ ] test_page_refresh_scenarios.py (8 tests)
- [ ] test_browser_navigation.py (8 tests)
- [ ] test_game_creation_disconnection_bug.py (5 tests)

## Expected Results After Full Migration
- Current test count: ~65 tests (most run only on Chromium)
- After migration: ~195 test runs (65 tests × 3 browsers each)
- 100% cross-browser coverage
- Zero browser-specific test code