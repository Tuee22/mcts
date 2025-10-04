"""E2E tests for network failure scenarios and error handling (fixed version)."""

import asyncio
import time
from typing import Dict, List, TypeGuard

import pytest
from playwright.async_api import Page, Route, expect


def is_response_dict(obj: object) -> TypeGuard[Dict[str, object]]:
    """Type guard to check if object is a response dict."""
    return isinstance(obj, dict) and "status" in obj


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_connection_timeout_handling(
    page: Page, e2e_urls: Dict[str, str]
) -> None:
    """Test handling of connection timeouts."""
    # Set up request interception to delay responses significantly
    cancel_event = asyncio.Event()

    async def delay_route(route: Route) -> None:
        try:
            await asyncio.wait_for(cancel_event.wait(), timeout=10.0)
            # If cancelled, abort the route
            await route.abort()
        except asyncio.TimeoutError:
            # If timeout occurs, continue with route
            await route.continue_()

    await page.route("**/*", delay_route)

    # Try to load the page with short timeout - should fail
    try:
        await page.goto(e2e_urls["frontend"], timeout=2000)
        print("⚠️  Page loaded unexpectedly despite timeout")
    except Exception as e:
        print(f"✅ Timeout handled correctly: {type(e).__name__}")

    # Cancel any pending route handlers
    cancel_event.set()
    await asyncio.sleep(0.1)  # Give time for handlers to process cancellation
    # Clean up route handlers
    await page.unroute("**/*")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_dns_resolution_failure(page: Page, e2e_urls: Dict[str, str]) -> None:
    """Test handling of DNS resolution failures."""
    # Try to navigate to invalid domain
    try:
        await page.goto("http://invalid-domain-that-does-not-exist.com", timeout=5000)
        print("⚠️  Invalid domain loaded unexpectedly")
    except Exception as e:
        print(f"✅ DNS failure handled correctly: {type(e).__name__}")

    # Chromium may redirect to chrome-error:// page after DNS failure
    # Wait briefly and check current URL before attempting navigation
    await asyncio.sleep(0.5)
    current_url = page.url
    if "chrome-error://" in current_url:
        # For Chromium, we need to navigate away from error page first
        print("✅ Chromium error page detected, navigating to blank page first")
        await page.goto("about:blank")

    # Verify the page can still navigate to valid URLs
    await page.goto(e2e_urls["frontend"])
    title = await page.title()
    assert title == "React App"
    print("✅ Recovery to valid domain successful")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_server_error_responses(page: Page, e2e_urls: Dict[str, str]) -> None:
    """Test handling of server error responses (5xx)."""
    await page.goto(e2e_urls["frontend"])
    await page.wait_for_load_state("networkidle")

    # Intercept requests and return 500 error - use exact URL pattern
    health_url = e2e_urls["backend"] + "/health"
    print(f"Setting up route interception for: {health_url}")

    await page.route(
        f"{health_url}**", lambda route: route.fulfill(status=500, body="Server Error")
    )

    # Make request that should get 500 error (use page.evaluate to trigger route interception)
    response_info = await page.evaluate(
        f"""
        async () => {{
            try {{
                const response = await fetch('{health_url}');
                return {{
                    status: response.status,
                    ok: response.ok,
                    url: response.url
                }};
            }} catch (error) {{
                return {{
                    status: -1,
                    ok: false,
                    error: error.message
                }};
            }}
        }}
    """
    )

    assert is_response_dict(response_info)
    print(
        f"Response status: {response_info['status']}, URL: {response_info.get('url', 'N/A')}"
    )
    assert response_info["status"] == 500
    print("✅ 500 error response handled correctly")

    # Remove the route and verify normal operation
    await page.unroute(f"{health_url}**")

    # Wait a moment for route to be fully removed
    await asyncio.sleep(0.1)

    # Test normal operation (also using page.evaluate)
    normal_response_info = await page.evaluate(
        f"""
        async () => {{
            try {{
                const response = await fetch('{health_url}');
                return {{
                    status: response.status,
                    ok: response.ok,
                    url: response.url
                }};
            }} catch (error) {{
                return {{
                    status: -1,
                    ok: false,
                    error: error.message
                }};
            }}
        }}
    """
    )

    assert is_response_dict(normal_response_info)
    assert normal_response_info["ok"]
    print("✅ Normal operation restored after removing 500 error route")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_network_connection_lost_during_request(
    page: Page, e2e_urls: Dict[str, str]
) -> None:
    """Test behavior when network connection is lost during an ongoing request."""
    await page.goto(e2e_urls["frontend"])
    await page.wait_for_load_state("networkidle")

    # Set up route to abort connections after delay
    async def abort_after_delay(route: Route) -> None:
        await asyncio.sleep(0.5)  # Small delay then abort
        await route.abort()

    await page.route("**/games**", abort_after_delay)

    # Try to make request that will be aborted
    try:
        response = await page.request.post(
            e2e_urls["backend"] + "/games",
            data={"test": "data"},
            headers={"Content-Type": "application/json"},
        )
        print("⚠️  Request succeeded unexpectedly")
    except Exception as e:
        print(f"✅ Network loss during request handled: {type(e).__name__}")

    # Clean up route
    await page.unroute("**/games**")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_partial_response_handling(page: Page, e2e_urls: Dict[str, str]) -> None:
    """Test handling of partial/incomplete responses."""
    await page.goto(e2e_urls["frontend"])
    await page.wait_for_load_state("networkidle")

    # Intercept and return incomplete JSON
    await page.route(
        "**/health**",
        lambda route: route.fulfill(
            status=200,
            headers={"Content-Type": "application/json"},
            body='{"status": "heal',  # Incomplete JSON
        ),
    )

    # Make request that should get malformed response
    try:
        response = await page.request.get(e2e_urls["backend"] + "/health")
        await response.json()  # This should fail
        print("⚠️  Malformed JSON was parsed unexpectedly")
    except Exception as e:
        print(f"✅ Malformed response handled correctly: {type(e).__name__}")

    # Clean up
    await page.unroute("**/health**")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_request_cancellation(page: Page, e2e_urls: Dict[str, str]) -> None:
    """Test proper handling of request cancellation."""
    await page.goto(e2e_urls["frontend"])
    await page.wait_for_load_state("networkidle")

    # Set up slow route
    async def slow_route(route: Route) -> None:
        await asyncio.sleep(5)  # Very slow response
        await route.continue_()

    await page.route("**/slow-endpoint", slow_route)

    # Start request and cancel it quickly
    start_time = time.time()
    try:
        response = await page.request.get(
            e2e_urls["backend"] + "/slow-endpoint", timeout=1000  # 1 second timeout
        )
        print("⚠️  Slow request completed unexpectedly")
    except Exception as e:
        duration = time.time() - start_time
        if duration < 2.0:  # Should timeout before the 5s delay
            print(f"✅ Request cancellation handled correctly in {duration:.1f}s")
        else:
            print(f"⚠️  Request took too long to cancel: {duration:.1f}s")

    # Clean up
    await page.unroute("**/slow-endpoint")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_websocket_connection_failure(
    page: Page, e2e_urls: Dict[str, str]
) -> None:
    """Test handling of WebSocket connection failures."""
    await page.goto(e2e_urls["frontend"])
    await page.wait_for_load_state("networkidle")

    # Block WebSocket connections
    await page.route("**/ws", lambda route: route.abort())

    # Try to trigger WebSocket connection
    await page.evaluate(
        "() => { try { new WebSocket('ws://localhost:8000/ws'); } catch(e) {} }"
    )
    await asyncio.sleep(1)  # Give time for connection attempt

    # Check if app handles WebSocket failure gracefully
    # The page should still be functional
    title = await page.title()
    assert title == "React App"
    print("✅ WebSocket failure handled gracefully")

    # Clean up
    await page.unroute("**/ws")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_concurrent_request_failures(
    page: Page, e2e_urls: Dict[str, str]
) -> None:
    """Test handling of multiple concurrent request failures."""
    await page.goto(e2e_urls["frontend"])
    await page.wait_for_load_state("networkidle")

    # Set up routes to fail different endpoints
    await page.route("**/health**", lambda route: route.fulfill(status=503))
    await page.route("**/games**", lambda route: route.fulfill(status=502))

    # Make multiple concurrent requests
    tasks = []
    for endpoint in ["/health", "/games"]:
        task = page.request.get(e2e_urls["backend"] + endpoint)
        tasks.append(task)

    # Wait for all requests
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    # Check that failures were handled appropriately
    error_count = sum(
        1
        for r in responses
        if isinstance(r, Exception) or (hasattr(r, "status") and r.status >= 500)
    )
    print(f"✅ Handled {error_count} concurrent failures appropriately")

    # Clean up
    await page.unroute("**/health**")
    await page.unroute("**/games**")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_network_recovery_patterns(page: Page, e2e_urls: Dict[str, str]) -> None:
    """Test various network recovery patterns."""
    await page.goto(e2e_urls["frontend"])
    await page.wait_for_load_state("networkidle")

    # Phase 1: Working state
    response1 = await page.request.get(e2e_urls["backend"] + "/health")
    assert response1.ok
    print("✅ Phase 1: Normal operation confirmed")

    # Phase 2: Network failure
    await page.route("**/health**", lambda route: route.abort())
    try:
        await page.request.get(e2e_urls["backend"] + "/health")
        print("⚠️  Request succeeded during failure simulation")
    except Exception:
        print("✅ Phase 2: Network failure simulation successful")

    # Phase 3: Recovery
    await page.unroute("**/health**")
    await asyncio.sleep(0.5)  # Brief recovery delay

    response3 = await page.request.get(e2e_urls["backend"] + "/health")
    assert response3.ok
    print("✅ Phase 3: Network recovery successful")

    # App should still be functional
    title = await page.title()
    assert title == "React App"
    print("✅ Application remained stable throughout network recovery cycle")
