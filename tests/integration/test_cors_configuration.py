"""Integration tests for single-server architecture (no CORS needed)."""

import os
import subprocess
from pathlib import Path
from typing import Dict, List

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
class TestSingleServerConfiguration:
    """Test single-server configuration without CORS."""

    async def test_no_cors_headers_in_single_server(
        self, backend_server: subprocess.Popen[bytes], test_config: Dict[str, object]
    ) -> None:
        """Test that CORS headers are NOT present in single-server architecture."""
        async with AsyncClient(
            base_url=f"http://{test_config['api_host']}:{test_config['api_port']}"
        ) as client:
            # Test preflight request - should fail in single-server mode
            response = await client.options(
                "/games",
                headers={
                    "Origin": "http://localhost:3001",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type",
                },
            )

            # OPTIONS method should not be allowed (405 Method Not Allowed)
            assert response.status_code == 405
            # CORS headers should NOT be present
            assert "Access-Control-Allow-Origin" not in response.headers

    async def test_api_requests_work_without_cors(
        self, backend_server: subprocess.Popen[bytes], test_config: Dict[str, object]
    ) -> None:
        """Test that API requests work without CORS headers."""
        async with AsyncClient(
            base_url=f"http://{test_config['api_host']}:{test_config['api_port']}"
        ) as client:
            # Make request with Origin header (would require CORS in multi-server setup)
            response = await client.get(
                "/health", headers={"Origin": "http://localhost:3001"}
            )

            assert response.status_code == 200
            # No CORS headers should be present in single-server architecture
            assert "Access-Control-Allow-Origin" not in response.headers
            assert "Access-Control-Allow-Credentials" not in response.headers

    async def test_frontend_served_from_same_server(
        self, backend_server: subprocess.Popen[bytes], test_config: Dict[str, object]
    ) -> None:
        """Test that frontend is served from the same server as API."""
        async with AsyncClient(
            base_url=f"http://{test_config['api_host']}:{test_config['api_port']}"
        ) as client:
            # Test root path serves frontend
            response = await client.get("/")

            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")
            # Should contain React app HTML
            assert "<!doctype html>" in response.text.lower()
            assert 'id="root"' in response.text

    async def test_websocket_endpoint_no_cors_needed(
        self, backend_server: subprocess.Popen[bytes], test_config: Dict[str, object]
    ) -> None:
        """Test that WebSocket endpoint doesn't need CORS in single-server setup."""
        async with AsyncClient(
            base_url=f"http://{test_config['api_host']}:{test_config['api_port']}"
        ) as client:
            # OPTIONS should not be allowed on WebSocket endpoint
            response = await client.options(
                "/ws",
                headers={
                    "Origin": "http://localhost:3001",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "Upgrade, Connection",
                },
            )

            # WebSocket endpoints don't support OPTIONS
            assert response.status_code == 405
            assert "Access-Control-Allow-Origin" not in response.headers

    async def test_api_works_with_same_origin_requests(
        self, backend_server: subprocess.Popen[bytes], test_config: Dict[str, object]
    ) -> None:
        """Test that API requests work without CORS complexity."""
        async with AsyncClient(
            base_url=f"http://{test_config['api_host']}:{test_config['api_port']}"
        ) as client:
            # This would work in single-server setup without CORS
            response = await client.post(
                "/games",
                json={
                    "player1_type": "human",
                    "player2_type": "machine",
                    "player1_name": "Test",
                    "player2_name": "AI",
                },
                headers={
                    "Origin": f"http://{test_config['api_host']}:{test_config['api_port']}",
                },
            )

            assert response.status_code == 200
            # No CORS headers needed
            assert "Access-Control-Allow-Credentials" not in response.headers

    async def test_single_server_static_assets(
        self, backend_server: subprocess.Popen[bytes], test_config: Dict[str, object]
    ) -> None:
        """Test that static assets are served correctly."""
        async with AsyncClient(
            base_url=f"http://{test_config['api_host']}:{test_config['api_port']}"
        ) as client:
            # Test that CSS files are served - get actual filename from build directory
            build_dir = Path("/app/frontend/build/static")
            if build_dir.exists():
                # Find CSS file
                css_files = list((build_dir / "css").glob("main.*.css"))
                if css_files:
                    css_file = css_files[0].name
                    response = await client.get(f"/static/css/{css_file}")
                    assert response.status_code == 200
                    assert "text/css" in response.headers.get("content-type", "")

                # Find JS file
                js_files = list((build_dir / "js").glob("main.*.js"))
                if js_files:
                    js_file = js_files[0].name
                    response = await client.get(f"/static/js/{js_file}")
                    assert response.status_code == 200
                    assert "javascript" in response.headers.get("content-type", "")
