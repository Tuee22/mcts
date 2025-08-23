"""Integration tests for CORS configuration and cross-origin requests."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
class TestCORSConfiguration:
    """Test CORS configuration for different scenarios."""

    async def test_cors_headers_on_api_endpoints(self, backend_server, test_config):
        """Test that CORS headers are properly set on API responses."""
        async with AsyncClient(
            base_url=f"http://{test_config['api_host']}:{test_config['api_port']}"
        ) as client:
            # Test preflight request
            response = await client.options(
                "/games",
                headers={
                    "Origin": "http://localhost:3001",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type",
                }
            )
            
            assert response.status_code == 200
            assert "Access-Control-Allow-Origin" in response.headers
            assert response.headers["Access-Control-Allow-Origin"] == "*"
            assert "Access-Control-Allow-Methods" in response.headers
            assert "POST" in response.headers["Access-Control-Allow-Methods"]

    async def test_cors_with_actual_request(self, backend_server, test_config):
        """Test CORS headers on actual API requests."""
        async with AsyncClient(
            base_url=f"http://{test_config['api_host']}:{test_config['api_port']}"
        ) as client:
            # Make request with Origin header
            response = await client.get(
                "/health",
                headers={"Origin": "http://localhost:3001"}
            )
            
            assert response.status_code == 200
            assert response.headers.get("Access-Control-Allow-Origin") == "*"
            assert response.headers.get("Access-Control-Allow-Credentials") == "true"

    async def test_cors_with_different_origins(self, backend_server, test_config):
        """Test CORS behavior with different origin headers."""
        origins = [
            "http://localhost:3000",
            "http://localhost:3001", 
            "http://127.0.0.1:3001",
            "https://example.com",
            "http://192.168.1.100:3000"
        ]
        
        async with AsyncClient(
            base_url=f"http://{test_config['api_host']}:{test_config['api_port']}"
        ) as client:
            for origin in origins:
                response = await client.get(
                    "/health",
                    headers={"Origin": origin}
                )
                
                assert response.status_code == 200
                # Current config allows all origins
                assert response.headers.get("Access-Control-Allow-Origin") == "*"

    async def test_cors_preflight_for_websocket_endpoint(self, backend_server, test_config):
        """Test CORS preflight for WebSocket endpoint."""
        async with AsyncClient(
            base_url=f"http://{test_config['api_host']}:{test_config['api_port']}"
        ) as client:
            # WebSocket endpoints typically don't use CORS the same way
            # but we should test the upgrade request headers
            response = await client.options(
                "/ws",
                headers={
                    "Origin": "http://localhost:3001",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "Upgrade, Connection",
                }
            )
            
            assert response.status_code == 200
            assert "Access-Control-Allow-Origin" in response.headers

    async def test_cors_with_credentials(self, backend_server, test_config):
        """Test CORS with credentials flag."""
        async with AsyncClient(
            base_url=f"http://{test_config['api_host']}:{test_config['api_port']}"
        ) as client:
            response = await client.post(
                "/games",
                json={
                    "player1_type": "human",
                    "player2_type": "machine",
                    "player1_name": "Test",
                    "player2_name": "AI"
                },
                headers={
                    "Origin": "http://localhost:3001",
                    "Cookie": "session=test123"  # Simulate credentials
                }
            )
            
            assert response.status_code == 200
            assert response.headers.get("Access-Control-Allow-Credentials") == "true"

    async def test_cors_blocked_methods(self, backend_server, test_config):
        """Test that CORS configuration allows all needed methods."""
        methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
        
        async with AsyncClient(
            base_url=f"http://{test_config['api_host']}:{test_config['api_port']}"
        ) as client:
            for method in methods:
                response = await client.options(
                    "/games",
                    headers={
                        "Origin": "http://localhost:3001",
                        "Access-Control-Request-Method": method,
                    }
                )
                
                assert response.status_code == 200
                allowed_methods = response.headers.get("Access-Control-Allow-Methods", "")
                assert method in allowed_methods or "*" in allowed_methods

    async def test_cors_custom_headers(self, backend_server, test_config):
        """Test CORS with custom headers."""
        async with AsyncClient(
            base_url=f"http://{test_config['api_host']}:{test_config['api_port']}"
        ) as client:
            # Test preflight with custom headers
            response = await client.options(
                "/games",
                headers={
                    "Origin": "http://localhost:3001",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "X-Custom-Header, X-Request-ID",
                }
            )
            
            assert response.status_code == 200
            allowed_headers = response.headers.get("Access-Control-Allow-Headers", "")
            assert "*" in allowed_headers  # Current config allows all headers

    async def test_cors_max_age_header(self, backend_server, test_config):
        """Test CORS max age header for preflight caching."""
        async with AsyncClient(
            base_url=f"http://{test_config['api_host']}:{test_config['api_port']}"
        ) as client:
            response = await client.options(
                "/games",
                headers={
                    "Origin": "http://localhost:3001",
                    "Access-Control-Request-Method": "POST",
                }
            )
            
            assert response.status_code == 200
            # Check if max age is set (optional but good practice)
            max_age = response.headers.get("Access-Control-Max-Age")
            if max_age:
                assert int(max_age) > 0