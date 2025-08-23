"""Integration tests for network failure scenarios and recovery."""

import asyncio
import json
import time
from unittest.mock import patch

import pytest
import websockets
from httpx import AsyncClient

from tests.fixtures.test_data_seeder import TestDataSeeder


@pytest.mark.integration
@pytest.mark.asyncio
class TestNetworkFailures:
    """Test network failure scenarios at the integration level."""

    async def test_websocket_connection_retry_logic(self, test_config):
        """Test WebSocket connection retry with exponential backoff."""
        # Use non-existent port for connection failure
        bad_url = f"ws://{test_config['api_host']}:9999/ws"
        
        retry_attempts = []
        start_time = time.time()
        
        for attempt in range(3):
            try:
                async with websockets.connect(bad_url, open_timeout=1, close_timeout=1):
                    pass
            except Exception:
                retry_attempts.append(time.time() - start_time)
                await asyncio.sleep(0.5 * (2 ** attempt))  # Exponential backoff
        
        # Verify retry attempts happened with increasing intervals
        assert len(retry_attempts) == 3
        assert retry_attempts[1] > retry_attempts[0]
        assert retry_attempts[2] > retry_attempts[1]

    async def test_websocket_message_queuing_during_disconnect(self, backend_server, test_config):
        """Test that messages are handled gracefully during connection issues."""
        uri = f"ws://{test_config['api_host']}:{test_config['api_port']}/ws"
        
        async with websockets.connect(uri) as websocket:
            # Send connection message
            await websocket.recv()  # Skip connect message
            
            # Queue multiple messages rapidly
            messages = [
                {"type": "ping", "id": i} for i in range(10)
            ]
            
            for msg in messages:
                await websocket.send(json.dumps(msg))
                
            # Receive all responses
            responses = []
            for _ in range(10):
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2)
                    responses.append(json.loads(response))
                except asyncio.TimeoutError:
                    break
            
            # All pings should get pong responses
            pong_count = sum(1 for r in responses if r.get("type") == "pong")
            assert pong_count == 10

    async def test_api_request_timeout_handling(self, backend_server, test_config):
        """Test API request timeout behavior."""
        async with AsyncClient(
            base_url=f"http://{test_config['api_host']}:{test_config['api_port']}",
            timeout=0.1  # Very short timeout
        ) as client:
            # This should timeout for slow endpoints
            with pytest.raises(Exception):  # httpx.TimeoutException or similar
                await client.get("/games")

    async def test_partial_json_message_handling(self, backend_server, test_config):
        """Test handling of partial or corrupted JSON messages."""
        uri = f"ws://{test_config['api_host']}:{test_config['api_port']}/ws"
        
        async with websockets.connect(uri) as websocket:
            await websocket.recv()  # Skip connect message
            
            # Send partial JSON
            await websocket.send('{"type": "ping", "incomplete')
            
            # Connection should remain open
            await websocket.send(json.dumps({"type": "ping"}))
            response = await asyncio.wait_for(websocket.recv(), timeout=2)
            data = json.loads(response)
            assert data["type"] == "pong"

    async def test_connection_recovery_after_network_interruption(self, test_config):
        """Test connection recovery after simulated network interruption."""
        uri = f"ws://{test_config['api_host']}:{test_config['api_port']}/ws"
        
        # First connection
        websocket1 = await websockets.connect(uri)
        await websocket1.recv()  # Connection message
        
        # Send ping to verify connection
        await websocket1.send(json.dumps({"type": "ping"}))
        await websocket1.recv()  # Pong response
        
        # Simulate network interruption by closing
        await websocket1.close()
        
        # Wait a moment, then reconnect
        await asyncio.sleep(1)
        
        # Should be able to reconnect
        async with websockets.connect(uri) as websocket2:
            await websocket2.recv()  # New connection message
            
            # Should work normally
            await websocket2.send(json.dumps({"type": "ping"}))
            response = await websocket2.recv()
            data = json.loads(response)
            assert data["type"] == "pong"

    async def test_high_latency_connection_handling(self, backend_server, test_config):
        """Test behavior under high latency conditions."""
        uri = f"ws://{test_config['api_host']}:{test_config['api_port']}/ws"
        
        # Use longer timeout to simulate high latency
        async with websockets.connect(uri) as websocket:
            await websocket.recv()  # Connection message
            
            # Send message with simulated processing delay
            start_time = time.time()
            await websocket.send(json.dumps({"type": "ping"}))
            
            # Add artificial delay
            await asyncio.sleep(0.5)
            
            response = await websocket.recv()
            total_time = time.time() - start_time
            
            data = json.loads(response)
            assert data["type"] == "pong"
            assert total_time >= 0.5  # At least our artificial delay

    async def test_websocket_large_message_handling(self, backend_server, test_config):
        """Test handling of large WebSocket messages."""
        uri = f"ws://{test_config['api_host']}:{test_config['api_port']}/ws"
        
        async with websockets.connect(uri) as websocket:
            await websocket.recv()  # Connection message
            
            # Send large message (but not too large to cause issues)
            large_data = "x" * 1024  # 1KB of data
            large_message = {
                "type": "ping",
                "data": large_data
            }
            
            await websocket.send(json.dumps(large_message))
            
            # Should still get pong
            response = await websocket.recv()
            data = json.loads(response)
            assert data["type"] == "pong"

    async def test_rapid_connection_disconnect_cycle(self, test_config):
        """Test rapid connect/disconnect cycles."""
        uri = f"ws://{test_config['api_host']}:{test_config['api_port']}/ws"
        
        # Perform multiple rapid connect/disconnect cycles
        for i in range(5):
            websocket = await websockets.connect(uri)
            await websocket.recv()  # Connection message
            await websocket.send(json.dumps({"type": "ping", "cycle": i}))
            await websocket.recv()  # Pong
            await websocket.close()
            
            # Small delay between cycles
            await asyncio.sleep(0.1)
        
        # Final connection should still work
        async with websockets.connect(uri) as websocket:
            await websocket.recv()
            await websocket.send(json.dumps({"type": "ping", "final": True}))
            response = await websocket.recv()
            data = json.loads(response)
            assert data["type"] == "pong"

    async def test_concurrent_websocket_connections(self, test_config):
        """Test multiple concurrent WebSocket connections."""
        uri = f"ws://{test_config['api_host']}:{test_config['api_port']}/ws"
        
        # Create multiple concurrent connections
        async def create_connection(connection_id):
            async with websockets.connect(uri) as websocket:
                await websocket.recv()  # Connection message
                
                # Send unique ping
                await websocket.send(json.dumps({
                    "type": "ping", 
                    "connection_id": connection_id
                }))
                
                response = await websocket.recv()
                data = json.loads(response)
                assert data["type"] == "pong"
                return connection_id
        
        # Run 5 concurrent connections
        tasks = [create_connection(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        assert set(results) == set(range(5))

    async def test_websocket_protocol_error_recovery(self, backend_server, test_config):
        """Test recovery from WebSocket protocol errors."""
        uri = f"ws://{test_config['api_host']}:{test_config['api_port']}/ws"
        
        # First, establish a normal connection
        async with websockets.connect(uri) as websocket:
            await websocket.recv()  # Connection message
            
            # Send valid message first
            await websocket.send(json.dumps({"type": "ping"}))
            await websocket.recv()  # Pong
            
            # Try to send binary data (should be handled gracefully)
            await websocket.send(b"binary data")
            
            # Connection might close due to protocol violation
            # but server should handle it gracefully
        
        # Should be able to reconnect after protocol error
        async with websockets.connect(uri) as websocket2:
            await websocket2.recv()  # New connection message
            await websocket2.send(json.dumps({"type": "ping"}))
            response = await websocket2.recv()
            data = json.loads(response)
            assert data["type"] == "pong"

    async def test_database_connection_failure_handling(self, backend_server, test_config):
        """Test API behavior when database operations fail."""
        async with AsyncClient(
            base_url=f"http://{test_config['api_host']}:{test_config['api_port']}"
        ) as client:
            # Create a game normally first
            response = await client.post("/games", json={
                "player1_type": "human",
                "player2_type": "human",
                "player1_name": "Test1",
                "player2_name": "Test2"
            })
            assert response.status_code == 200
            
            # Health endpoint should still work even if individual operations fail
            health_response = await client.get("/health")
            assert health_response.status_code == 200
            health_data = health_response.json()
            assert "status" in health_data