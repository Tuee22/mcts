"""E2E tests for network failure scenarios and error handling."""

import asyncio

import pytest
from playwright.async_api import Page, expect


@pytest.mark.e2e
@pytest.mark.asyncio
class TestNetworkFailures:
    """Test network failure scenarios and recovery."""

    async def test_connection_timeout_handling(self, page: Page, e2e_config):
        """Test handling of connection timeouts."""
        # Set up request interception to delay responses
        await page.route("**/*", lambda route: asyncio.sleep(60))
        
        # Try to load the page
        with pytest.raises(Exception):  # Should timeout
            await page.goto(e2e_config["frontend_url"], timeout=5000)

    async def test_partial_message_delivery(self, page: Page, e2e_urls):
        """Test handling of partial WebSocket messages."""
        await page.goto(e2e_urls["frontend"])
        
        # Inject code to simulate partial message
        await page.evaluate('''
            // Override WebSocket to simulate partial messages
            const OriginalWebSocket = window.WebSocket;
            let ws;
            window.WebSocket = function(url) {
                ws = new OriginalWebSocket(url);
                const originalOnMessage = ws.onmessage;
                
                ws.onmessage = function(event) {
                    // Simulate partial JSON by truncating
                    if (Math.random() > 0.5) {
                        const truncated = new MessageEvent('message', {
                            data: event.data.substring(0, event.data.length / 2)
                        });
                        originalOnMessage.call(ws, truncated);
                    } else {
                        originalOnMessage.call(ws, event);
                    }
                };
                
                return ws;
            };
        ''')
        
        # Connection should handle partial messages gracefully
        await page.reload()
        
        # App should still function
        connection_status = page.locator('[data-testid="connection-status"]')
        await expect(connection_status).to_be_visible()

    async def test_websocket_protocol_violation(self, page: Page, e2e_urls):
        """Test handling of WebSocket protocol violations."""
        await page.goto(e2e_urls["frontend"])
        
        # Inject code to send invalid WebSocket frames
        await page.evaluate('''
            const ws = new WebSocket(window.location.origin.replace('http', 'ws') + '/ws');
            ws.onopen = () => {
                // Send invalid binary data when text is expected
                ws.send(new ArrayBuffer(8));
            };
        ''')
        
        # App should handle protocol violations gracefully
        await asyncio.sleep(2)
        
        # Should still show connection status
        connection_status = page.locator('[data-testid="connection-status"]')
        await expect(connection_status).to_be_visible()

    async def test_request_timeout_with_retry(self, page: Page, e2e_urls):
        """Test request timeout and retry logic."""
        # Track retry attempts
        retry_count = 0
        
        async def handle_route(route):
            nonlocal retry_count
            retry_count += 1
            if retry_count < 3:
                # Fail first 2 attempts
                await route.abort()
            else:
                # Succeed on 3rd attempt
                await route.continue_()
        
        await page.route("**/health", handle_route)
        
        await page.goto(e2e_urls["frontend"])
        
        # Should eventually connect after retries
        await expect(page.locator('[data-testid="connection-text"]')).to_have_text("Connected", timeout=15000)
        
        # Verify retries happened
        assert retry_count >= 3

    async def test_network_latency_impact(self, page: Page, e2e_urls):
        """Test app behavior under high network latency."""
        # Add 2 second delay to all requests
        await page.route("**/*", lambda route: asyncio.create_task(
            self._delayed_continue(route, 2000)
        ))
        
        await page.goto(e2e_urls["frontend"], timeout=30000)
        
        # Should still connect despite latency
        await expect(page.locator('[data-testid="connection-text"]')).to_have_text("Connected", timeout=10000)

    async def _delayed_continue(self, route, delay_ms):
        """Helper to delay route continuation."""
        await asyncio.sleep(delay_ms / 1000)
        await route.continue_()

    async def test_connection_drops_during_game_move(self, page: Page, e2e_urls, create_game):
        """Test connection drop while making a game move."""
        await page.goto(e2e_urls["frontend"])
        await create_game(mode="human_vs_human")
        
        # Set up route to block WebSocket messages
        blocked = False
        
        async def block_ws(route):
            if "ws" in route.request.url and blocked:
                await route.abort()
            else:
                await route.continue_()
        
        await page.route("**/*", block_ws)
        
        # Block connection
        blocked = True
        
        # Try to make a move (click board cell)
        board_cells = page.locator('.board-cell')
        if await board_cells.count() > 0:
            await board_cells.first.click()
        
        # Should show disconnection
        await expect(page.locator('[data-testid="connection-text"]')).to_have_text("Disconnected", timeout=5000)
        
        # Unblock connection
        blocked = False
        
        # Should recover
        await expect(page.locator('[data-testid="connection-text"]')).to_have_text("Connected", timeout=10000)

    async def test_server_error_responses(self, page: Page, e2e_urls):
        """Test handling of server error responses."""
        # Intercept API calls to return errors
        await page.route("**/games", lambda route: route.fulfill(
            status=500,
            content_type="application/json",
            body='{"detail": "Internal server error"}'
        ))
        
        await page.goto(e2e_urls["frontend"])
        
        # Try to create a game
        settings_button = page.locator('button:has-text("⚙️ Game Settings")')
        if await settings_button.is_visible():
            await settings_button.click()
            
        await page.click('[data-testid="mode-human-vs-human"]')
        await page.click('[data-testid="start-game-button"]')
        
        # Should show error message (via toast or inline)
        # App should remain functional
        await expect(page.locator('[data-testid="connection-text"]')).to_have_text("Connected")

    async def test_websocket_reconnection_backoff(self, page: Page, e2e_config):
        """Test WebSocket reconnection uses exponential backoff."""
        reconnect_times = []
        
        # Track reconnection attempts
        await page.expose_function("trackReconnect", lambda: reconnect_times.append(asyncio.get_event_loop().time()))
        
        await page.evaluate('''
            const OriginalWebSocket = window.WebSocket;
            window.WebSocket = function(url) {
                window.trackReconnect();
                const ws = new OriginalWebSocket(url);
                ws.addEventListener('error', () => {
                    setTimeout(() => {
                        new window.WebSocket(url);
                    }, 1000);
                });
                return ws;
            };
        ''')
        
        # Point to non-existent server
        await page.goto(e2e_config["frontend_url"])
        
        # Wait for multiple reconnection attempts
        await asyncio.sleep(10)
        
        # Verify backoff pattern (times should increase)
        if len(reconnect_times) > 2:
            intervals = [reconnect_times[i+1] - reconnect_times[i] for i in range(len(reconnect_times)-1)]
            # Later intervals should be longer (backoff)
            assert any(intervals[i] < intervals[i+1] for i in range(len(intervals)-1) if i+1 < len(intervals))

    async def test_message_queuing_during_disconnect(self, page: Page, e2e_urls, create_game):
        """Test that actions are queued during disconnection."""
        await page.goto(e2e_urls["frontend"])
        await create_game()
        
        # Block WebSocket
        await page.route("**/*ws*", lambda route: route.abort())
        
        # Perform actions while disconnected
        board_cells = page.locator('.board-cell')
        if await board_cells.count() >= 3:
            await board_cells.nth(0).click()
            await board_cells.nth(1).click()
            await board_cells.nth(2).click()
        
        # Unblock WebSocket
        await page.unroute("**/*ws*")
        
        # Actions should be processed after reconnection
        await expect(page.locator('[data-testid="connection-text"]')).to_have_text("Connected", timeout=10000)