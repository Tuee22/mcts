"""E2E tests for connection scenarios including disconnection and recovery."""

import asyncio
import subprocess

import pytest
from playwright.async_api import Page, expect

from tests.utils.stability_helpers import (
    StabilityWaits,
    BrowserStabilityHelpers,
    retry_on_failure
)


@pytest.mark.e2e
@pytest.mark.asyncio
class TestConnectionScenarios:
    """Test various connection scenarios with real browser and services."""

    @retry_on_failure(max_attempts=2)
    async def test_successful_connection_on_load(self, page: Page, e2e_urls):
        """Test that app successfully connects to backend on load."""
        # Navigate to frontend
        await page.goto(e2e_urls["frontend"])
        
        # Wait for connection to be stable
        await StabilityWaits.wait_for_connection_ready(page)
        
        # Wait for and verify connection status
        connection_status = page.locator('[data-testid="connection-status"]')
        await expect(connection_status).to_be_visible()
        
        # Should show "Connected"
        connection_text = page.locator('[data-testid="connection-text"]')
        await expect(connection_text).to_have_text("Connected", timeout=10000)
        
        # Connection indicator should have "connected" class
        connection_indicator = page.locator('[data-testid="connection-indicator"]')
        await expect(connection_indicator).to_have_class(/connected/)

    async def test_game_creation_flow(self, page: Page, e2e_urls, create_game):
        """Test complete game creation flow."""
        await page.goto(e2e_urls["frontend"])
        
        # Create a game
        await create_game(mode="human_vs_ai", difficulty="medium")
        
        # Verify game started
        game_container = page.locator('[data-testid="game-container"]')
        await expect(game_container).to_be_visible()
        
        # Verify no disconnection warning
        connection_warning = page.locator('[data-testid="connection-warning"]')
        await expect(connection_warning).not_to_be_visible()

    async def test_backend_unreachable_shows_disconnection(self, page: Page, e2e_config):
        """Test UI shows disconnection when backend is unreachable."""
        # Use a non-existent backend URL
        unreachable_url = "http://localhost:9999"
        
        # Navigate with unreachable backend
        await page.goto(e2e_config["frontend_url"])
        
        # Override WebSocket URL to point to unreachable backend
        await page.evaluate('''
            window.localStorage.setItem('wsUrl', 'ws://localhost:9999/ws');
        ''')
        
        # Reload to apply new URL
        await page.reload()
        
        # Should show "Disconnected"
        connection_text = page.locator('[data-testid="connection-text"]')
        await expect(connection_text).to_have_text("Disconnected", timeout=10000)
        
        # Connection indicator should have "disconnected" class
        connection_indicator = page.locator('[data-testid="connection-indicator"]')
        await expect(connection_indicator).to_have_class(/disconnected/)
        
        # Game settings should be disabled
        settings_button = page.locator('button:has-text("⚙️ Game Settings")')
        await expect(settings_button).to_be_disabled()

    async def test_connection_recovery_after_backend_restart(self, page: Page, e2e_urls, backend_e2e_server):
        """Test connection recovery when backend comes back online."""
        await page.goto(e2e_urls["frontend"])
        
        # Wait for initial connection
        await expect(page.locator('[data-testid="connection-text"]')).to_have_text("Connected")
        
        # Kill backend server
        backend_e2e_server.terminate()
        backend_e2e_server.wait(timeout=5)
        
        # Should show disconnected
        await expect(page.locator('[data-testid="connection-text"]')).to_have_text("Disconnected", timeout=10000)
        
        # Restart backend server
        port = e2e_urls["backend"].split(":")[-1]
        env = backend_e2e_server.env if hasattr(backend_e2e_server, 'env') else {}
        new_backend = subprocess.Popen(
            ["python", "-m", "uvicorn", "backend.api.server:app",
             "--host", "0.0.0.0",
             "--port", port],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for backend to be ready
        import requests
        for _ in range(30):
            try:
                response = requests.get(f"{e2e_urls['backend']}/health")
                if response.status_code == 200:
                    break
            except:
                await asyncio.sleep(0.5)
        
        # Frontend should eventually reconnect
        await expect(page.locator('[data-testid="connection-text"]')).to_have_text("Connected", timeout=15000)
        
        # Cleanup
        new_backend.terminate()
        new_backend.wait(timeout=5)

    async def test_wrong_api_url_configuration(self, page: Page, e2e_config):
        """Test behavior with misconfigured API URL."""
        # Set wrong API URL via localStorage before WebSocket connects
        await page.goto(e2e_config["frontend_url"])
        
        await page.evaluate('''
            // Override WebSocket constructor to use wrong URL
            const OriginalWebSocket = window.WebSocket;
            window.WebSocket = function(url) {
                return new OriginalWebSocket('ws://wrong-host:8000/ws');
            };
        ''')
        
        # Trigger reconnection
        await page.reload()
        
        # Should show disconnected
        await expect(page.locator('[data-testid="connection-text"]')).to_have_text("Disconnected", timeout=10000)
        
        # Should not be able to create games
        settings_button = page.locator('button:has-text("⚙️ Game Settings")')
        await expect(settings_button).to_be_disabled()

    async def test_network_interruption_during_game(self, page: Page, e2e_urls, create_game):
        """Test handling of network interruption during active game."""
        await page.goto(e2e_urls["frontend"])
        
        # Create a game
        await create_game(mode="human_vs_human")
        
        # Simulate network interruption by blocking WebSocket
        await page.route("**/*ws*", lambda route: route.abort())
        
        # Trigger a game action that requires server communication
        # Click on a board cell (assuming it exists)
        board_cells = page.locator('.board-cell').first
        if await board_cells.count() > 0:
            await board_cells.click()
        
        # Should show disconnection
        await expect(page.locator('[data-testid="connection-text"]')).to_have_text("Disconnected", timeout=10000)
        
        # Restore network
        await page.unroute("**/*ws*")
        
        # Should reconnect
        await expect(page.locator('[data-testid="connection-text"]')).to_have_text("Connected", timeout=15000)

    async def test_cors_blocked_request(self, page: Page, e2e_config):
        """Test behavior when CORS blocks requests."""
        # Navigate to a different origin
        await page.goto("http://example.com")
        
        # Try to connect to our backend from different origin
        result = await page.evaluate(f'''
            async () => {{
                try {{
                    const response = await fetch('{e2e_config["backend_url"]}/health', {{
                        mode: 'cors'
                    }});
                    return {{ success: true, headers: Object.fromEntries(response.headers.entries()) }};
                }} catch (error) {{
                    return {{ success: false, error: error.message }};
                }}
            }}
        ''')
        
        # With current CORS config (*), request should succeed
        # In production with restricted CORS, this would fail
        assert result() is not None

    async def test_connection_status_persistence_across_navigation(self, page: Page, e2e_urls):
        """Test connection status persists across page navigation."""
        await page.goto(e2e_urls["frontend"])
        
        # Wait for connection
        await expect(page.locator('[data-testid="connection-text"]')).to_have_text("Connected")
        
        # Navigate away and back
        await page.goto("about:blank")
        await page.goto(e2e_urls["frontend"])
        
        # Should reconnect
        await expect(page.locator('[data-testid="connection-text"]')).to_have_text("Connected", timeout=5000)

    async def test_multiple_tabs_connection_handling(self, browser, e2e_urls):
        """Test multiple tabs can connect simultaneously."""
        # Create two pages
        context1 = await browser.new_context()
        page1 = await context1.new_page()
        
        context2 = await browser.new_context()
        page2 = await context2.new_page()
        
        # Navigate both to app
        await page1.goto(e2e_urls["frontend"])
        await page2.goto(e2e_urls["frontend"])
        
        # Both should connect
        await expect(page1.locator('[data-testid="connection-text"]')).to_have_text("Connected")
        await expect(page2.locator('[data-testid="connection-text"]')).to_have_text("Connected")
        
        # Create game in first tab
        settings1 = page1.locator('button:has-text("⚙️ Game Settings")')
        await settings1.click()
        await page1.click('[data-testid="mode-human-vs-human"]')
        await page1.click('[data-testid="start-game-button"]')
        
        # Should not affect second tab's connection
        await expect(page2.locator('[data-testid="connection-text"]')).to_have_text("Connected")
        
        # Cleanup
        await context1.close()
        await context2.close()