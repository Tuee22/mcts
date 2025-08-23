"""Integration tests for WebSocket connection handling and error scenarios."""

import asyncio
import json
import os
from typing import Any, Dict

import pytest
import websockets
from httpx import AsyncClient

from backend.api.models import GameCreateRequest, PlayerType


@pytest.mark.integration
@pytest.mark.asyncio
class TestWebSocketConnection:
    """Test WebSocket connection scenarios including failures and recovery."""

    async def test_successful_websocket_connection(self, backend_server, test_config):
        """Test successful WebSocket connection to running backend."""
        uri = f"ws://{test_config['api_host']}:{test_config['api_port']}/ws"
        
        async with websockets.connect(uri) as websocket:
            # Should receive connection confirmation
            message = await websocket.recv()
            data = json.loads(message)
            
            assert data["type"] == "connect"
            assert "Connected" in data["message"]
            
            # Test ping/pong
            await websocket.send(json.dumps({"type": "ping"}))
            response = await websocket.recv()
            pong = json.loads(response)
            assert pong["type"] == "pong"

    async def test_websocket_connection_with_invalid_url(self, test_config):
        """Test WebSocket connection with wrong URL fails gracefully."""
        # Try connecting to wrong port
        uri = f"ws://{test_config['api_host']}:9999/ws"
        
        with pytest.raises(OSError):
            async with websockets.connect(uri, close_timeout=1):
                pass

    async def test_websocket_reconnection_after_disconnect(self, backend_server, test_config):
        """Test reconnection behavior after unexpected disconnect."""
        uri = f"ws://{test_config['api_host']}:{test_config['api_port']}/ws"
        
        # First connection
        websocket1 = await websockets.connect(uri)
        message = await websocket1.recv()
        data = json.loads(message)
        assert data["type"] == "connect"
        
        # Close connection
        await websocket1.close()
        
        # Should be able to reconnect
        async with websockets.connect(uri) as websocket2:
            message = await websocket2.recv()
            data = json.loads(message)
            assert data["type"] == "connect"

    async def test_websocket_with_game_session(self, backend_server, test_config, test_client):
        """Test WebSocket connection for specific game session."""
        # Create a game first
        game_data = {
            "player1_type": "human",
            "player2_type": "machine",
            "player1_name": "Test Player",
            "player2_name": "AI"
        }
        
        response = await test_client.post("/games", json=game_data)
        assert response.status_code == 200
        game = response.json()
        game_id = game["game_id"]
        
        # Connect to game-specific WebSocket
        uri = f"ws://{test_config['api_host']}:{test_config['api_port']}/games/{game_id}/ws"
        
        async with websockets.connect(uri) as websocket:
            # Should receive initial game state
            message = await websocket.recv()
            data = json.loads(message)
            
            # Verify we received game state
            assert "game_id" in data or "type" in data

    async def test_websocket_handles_malformed_messages(self, backend_server, test_config):
        """Test WebSocket gracefully handles malformed messages."""
        uri = f"ws://{test_config['api_host']}:{test_config['api_port']}/ws"
        
        async with websockets.connect(uri) as websocket:
            # Skip connection message
            await websocket.recv()
            
            # Send malformed JSON
            await websocket.send("not json")
            
            # Connection should remain open
            await websocket.send(json.dumps({"type": "ping"}))
            response = await websocket.recv()
            pong = json.loads(response)
            assert pong["type"] == "pong"

    async def test_websocket_connection_timeout(self, test_config):
        """Test WebSocket connection timeout behavior."""
        # Non-existent host
        uri = f"ws://192.0.2.1:{test_config['api_port']}/ws"
        
        with pytest.raises(asyncio.TimeoutError):
            async with websockets.connect(uri, close_timeout=1, open_timeout=2):
                pass

    async def test_multiple_concurrent_websocket_connections(self, backend_server, test_config):
        """Test multiple concurrent WebSocket connections."""
        uri = f"ws://{test_config['api_host']}:{test_config['api_port']}/ws"
        
        # Create multiple connections
        websockets_list = []
        for i in range(5):
            ws = await websockets.connect(uri)
            websockets_list.append(ws)
            
        # All should receive connection message
        for ws in websockets_list:
            message = await ws.recv()
            data = json.loads(message)
            assert data["type"] == "connect"
            
        # Clean up
        for ws in websockets_list:
            await ws.close()

    async def test_websocket_message_ordering(self, backend_server, test_config):
        """Test that WebSocket messages maintain order."""
        uri = f"ws://{test_config['api_host']}:{test_config['api_port']}/ws"
        
        async with websockets.connect(uri) as websocket:
            await websocket.recv()  # Skip connect message
            
            # Send multiple pings
            for i in range(10):
                await websocket.send(json.dumps({"type": "ping", "id": i}))
                
            # Should receive pongs in order
            for i in range(10):
                response = await asyncio.wait_for(websocket.recv(), timeout=2)
                pong = json.loads(response)
                assert pong["type"] == "pong"

    async def test_websocket_binary_message_handling(self, backend_server, test_config):
        """Test WebSocket handling of binary messages."""
        uri = f"ws://{test_config['api_host']}:{test_config['api_port']}/ws"
        
        async with websockets.connect(uri) as websocket:
            await websocket.recv()  # Skip connect message
            
            # Send binary data (should be ignored or handled gracefully)
            await websocket.send(b"binary data")
            
            # Connection should still work
            await websocket.send(json.dumps({"type": "ping"}))
            response = await asyncio.wait_for(websocket.recv(), timeout=2)
            pong = json.loads(response)
            assert pong["type"] == "pong"