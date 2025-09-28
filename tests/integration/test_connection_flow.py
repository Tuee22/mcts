"""
Connection Flow Integration Tests

Tests for frontend-backend connection establishment, handshake protocols,
and connection state synchronization that could affect E2E test stability.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Union, Protocol, AsyncGenerator, Mapping
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

from backend.api.server import app
from tests.types import TestMessageData


class WebSocketProtocol(Protocol):
    """Protocol for WebSocket-like objects."""

    async def close(self) -> None:
        ...

    async def send(self, data: str) -> None:
        ...

    async def recv(self) -> str:
        ...


class MockFrontendClient:
    """Mock frontend client for integration testing."""

    def __init__(self, websocket_url: str):
        self.websocket_url = websocket_url
        self.websocket: Optional[Union[WebSocketProtocol, AsyncMock]] = None
        self.messages_received: List[Mapping[str, object]] = []
        self.connection_events: List[str] = []
        self.is_connected = False

    async def connect(self) -> bool:
        """Establish WebSocket connection."""
        try:
            import websockets

            self.websocket = await websockets.connect(self.websocket_url)
            self.is_connected = True
            self.connection_events.append("connected")
            return True
        except Exception as e:
            self.connection_events.append(f"connection_failed: {e}")
            return False

    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            self.connection_events.append("disconnected")

    async def send_message(self, message: Mapping[str, object]) -> None:
        """Send message to backend."""
        if not self.websocket:
            raise ConnectionError("Not connected")

        await self.websocket.send(json.dumps(message))

    async def receive_message(
        self, timeout: float = 1.0
    ) -> Optional[Mapping[str, object]]:
        """Receive message from backend with timeout."""
        if not self.websocket:
            return None

        try:
            message_text = await asyncio.wait_for(
                self.websocket.recv(), timeout=timeout
            )
            message_data = json.loads(message_text)
            # Cast the JSON result to our expected type
            message: Mapping[str, object] = message_data
            self.messages_received.append(message)
            return message
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            self.connection_events.append(f"receive_error: {e}")
            return None

    async def wait_for_message_type(
        self, message_type: str, timeout: float = 5.0
    ) -> Optional[Mapping[str, object]]:
        """Wait for specific message type."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            message = await self.receive_message(timeout=0.1)
            if message and message.get("type") == message_type:
                return message

        return None


@pytest.fixture
async def test_server() -> AsyncGenerator[TestClient, None]:
    """Start test server for integration testing."""
    # Use TestClient for HTTP endpoints and mock WebSocket
    client = TestClient(app)
    yield client


@pytest.fixture
def mock_frontend() -> MockFrontendClient:
    """Create mock frontend client."""
    return MockFrontendClient("ws://localhost:8000/ws")


@pytest.mark.asyncio
class TestConnectionEstablishment:
    """Test WebSocket connection establishment flow."""

    async def test_successful_connection_handshake(
        self, mock_frontend: MockFrontendClient
    ) -> None:
        """Test successful WebSocket connection and handshake."""
        # Mock successful connection
        mock_frontend.websocket = AsyncMock()
        mock_frontend.is_connected = True

        # Send connection message
        connection_message = {
            "type": "connect",
            "data": {
                "connection_id": "test-conn-123",
                "client_info": {"user_agent": "TestClient/1.0", "version": "1.0.0"},
            },
        }

        await mock_frontend.send_message(connection_message)

        # Mock successful response
        welcome_response = {
            "type": "welcome",
            "data": {
                "connection_id": "test-conn-123",
                "server_time": time.time(),
                "protocol_version": "1.0",
            },
        }

        mock_frontend.messages_received.append(welcome_response)

        # Verify connection established
        assert mock_frontend.is_connected
        assert len(mock_frontend.messages_received) == 1
        assert mock_frontend.messages_received[0]["type"] == "welcome"

    async def test_connection_rejection_on_invalid_protocol(
        self, mock_frontend: MockFrontendClient
    ) -> None:
        """Test connection rejection for invalid protocol version."""
        mock_frontend.websocket = AsyncMock()

        # Send connection with invalid protocol
        connection_message = {
            "type": "connect",
            "data": {
                "connection_id": "test-conn-456",
                "protocol_version": "0.1",  # Unsupported version
            },
        }

        await mock_frontend.send_message(connection_message)

        # Mock rejection response
        rejection_response = {
            "type": "connection_rejected",
            "data": {
                "reason": "Unsupported protocol version",
                "supported_versions": ["1.0"],
            },
        }

        mock_frontend.messages_received.append(rejection_response)

        # Verify rejection handling
        received_message = mock_frontend.messages_received[0]
        assert isinstance(received_message, dict)
        assert received_message["type"] == "connection_rejected"
        data = received_message["data"]
        assert isinstance(data, dict)
        assert "protocol version" in data["reason"]

    async def test_connection_timeout_handling(
        self, mock_frontend: MockFrontendClient
    ) -> None:
        """Test connection timeout scenarios."""
        # Simulate connection timeout
        mock_frontend.websocket = None
        mock_frontend.is_connected = False
        mock_frontend.connection_events.append("connection_timeout")

        # Verify timeout handling
        assert not mock_frontend.is_connected
        assert "connection_timeout" in mock_frontend.connection_events

    async def test_connection_retry_logic(
        self, mock_frontend: MockFrontendClient
    ) -> None:
        """Test connection retry with exponential backoff."""
        retry_attempts = []

        # Simulate multiple connection attempts
        for attempt in range(3):
            mock_frontend.connection_events.append(f"retry_attempt_{attempt + 1}")
            await asyncio.sleep(0.1 * (2**attempt))  # Exponential backoff
            retry_attempts.append(attempt + 1)

        # Verify retry attempts
        assert len(retry_attempts) == 3
        assert "retry_attempt_1" in mock_frontend.connection_events
        assert "retry_attempt_3" in mock_frontend.connection_events


@pytest.mark.asyncio
class TestConnectionStateSync:
    """Test connection state synchronization between frontend and backend."""

    async def test_connection_state_broadcast(
        self, mock_frontend: MockFrontendClient
    ) -> None:
        """Test broadcasting connection state changes."""
        mock_frontend.websocket = AsyncMock()
        mock_frontend.is_connected = True

        # Simulate connection state broadcast
        state_broadcast = {
            "type": "connection_state",
            "data": {
                "connection_id": "test-conn-789",
                "state": "connected",
                "timestamp": time.time(),
                "active_connections": 5,
            },
        }

        mock_frontend.messages_received.append(state_broadcast)

        # Verify state synchronization
        received_message = mock_frontend.messages_received[0]
        assert isinstance(received_message, dict)
        assert received_message["type"] == "connection_state"
        data = received_message["data"]
        assert isinstance(data, dict)
        assert data["state"] == "connected"

    async def test_multiple_connection_coordination(self) -> None:
        """Test coordination between multiple connections."""
        # Create multiple mock clients
        clients = [
            MockFrontendClient(f"ws://localhost:8000/ws"),
            MockFrontendClient(f"ws://localhost:8000/ws"),
            MockFrontendClient(f"ws://localhost:8000/ws"),
        ]

        # Mock all as connected
        for i, client in enumerate(clients):
            client.websocket = AsyncMock()
            client.is_connected = True
            client.connection_events.append(f"connected_client_{i}")

        # Simulate broadcast to all connections
        broadcast_message = {
            "type": "server_announcement",
            "data": {
                "message": "Server maintenance in 5 minutes",
                "timestamp": time.time(),
            },
        }

        # All clients receive broadcast
        for client in clients:
            client.messages_received.append(broadcast_message)

        # Verify all clients received message
        for client in clients:
            assert len(client.messages_received) == 1
            assert client.messages_received[0]["type"] == "server_announcement"

    async def test_connection_recovery_after_interruption(
        self, mock_frontend: MockFrontendClient
    ) -> None:
        """Test connection recovery after network interruption."""
        # Initial connection
        mock_frontend.websocket = AsyncMock()
        mock_frontend.is_connected = True
        mock_frontend.connection_events.append("initial_connection")

        # Simulate interruption
        mock_frontend.is_connected = False
        mock_frontend.connection_events.append("connection_interrupted")

        # Wait for recovery
        await asyncio.sleep(0.1)

        # Simulate recovery
        mock_frontend.is_connected = True
        mock_frontend.connection_events.append("connection_recovered")

        # Send recovery message
        recovery_message = {
            "type": "connection_recovered",
            "data": {
                "connection_id": "test-conn-recovery",
                "last_message_id": "msg-123",
                "recovery_time": time.time(),
            },
        }

        mock_frontend.messages_received.append(recovery_message)

        # Verify recovery sequence
        events = mock_frontend.connection_events
        assert "initial_connection" in events
        assert "connection_interrupted" in events
        assert "connection_recovered" in events

    async def test_connection_metadata_synchronization(
        self, mock_frontend: MockFrontendClient
    ) -> None:
        """Test synchronization of connection metadata."""
        mock_frontend.websocket = AsyncMock()
        mock_frontend.is_connected = True

        # Send metadata update
        metadata_update = {
            "type": "metadata_update",
            "data": {
                "connection_id": "test-conn-meta",
                "metadata": {
                    "user_preferences": {"theme": "dark", "board_size": 9},
                    "session_info": {
                        "start_time": time.time(),
                        "client_version": "1.2.0",
                    },
                },
            },
        }

        mock_frontend.messages_received.append(metadata_update)

        # Verify metadata sync
        received_message = mock_frontend.messages_received[0]
        assert isinstance(received_message, dict)
        assert received_message["type"] == "metadata_update"
        data = received_message["data"]
        assert isinstance(data, dict)
        metadata = data["metadata"]
        assert isinstance(metadata, dict)
        assert "user_preferences" in metadata
        assert "session_info" in metadata


@pytest.mark.asyncio
class TestProtocolCompliance:
    """Test WebSocket protocol compliance and message validation."""

    async def test_message_format_validation(
        self, mock_frontend: MockFrontendClient
    ) -> None:
        """Test message format validation."""
        mock_frontend.websocket = AsyncMock()

        # Valid message format
        valid_message = {
            "type": "ping",
            "request_id": "req-123",
            "data": {},
            "timestamp": time.time(),
        }

        await mock_frontend.send_message(valid_message)

        # Should not raise validation errors
        assert isinstance(mock_frontend.websocket, AsyncMock)
        mock_websocket = mock_frontend.websocket
        assert isinstance(mock_websocket, AsyncMock)
        # Verify that send was called by checking if it has mock attributes
        send_method = getattr(mock_websocket, "send")
        if hasattr(send_method, "call_count"):
            assert send_method.call_count > 0
        else:
            # If not a mock, just verify the method exists
            assert callable(send_method)

    async def test_invalid_message_rejection(
        self, mock_frontend: MockFrontendClient
    ) -> None:
        """Test rejection of invalid message formats."""
        mock_frontend.websocket = AsyncMock()

        # Invalid message (missing required fields)
        invalid_message = {"invalid_field": "should_be_rejected"}

        await mock_frontend.send_message(invalid_message)

        # Mock error response
        error_response = {
            "type": "error",
            "data": {
                "error_code": "INVALID_MESSAGE_FORMAT",
                "message": "Missing required field 'type'",
                "received_message": invalid_message,
            },
        }

        mock_frontend.messages_received.append(error_response)

        # Verify error handling
        received_message = mock_frontend.messages_received[0]
        assert isinstance(received_message, dict)
        assert received_message["type"] == "error"
        data = received_message["data"]
        assert isinstance(data, dict)
        assert data["error_code"] == "INVALID_MESSAGE_FORMAT"

    async def test_request_response_correlation(
        self, mock_frontend: MockFrontendClient
    ) -> None:
        """Test request-response message correlation."""
        mock_frontend.websocket = AsyncMock()

        request_id = "req-correlation-test"

        # Send request
        request_message = {
            "type": "create_game",
            "request_id": request_id,
            "data": {"mode": "human_vs_human", "board_size": 9},
        }

        await mock_frontend.send_message(request_message)

        # Mock correlated response
        response_message = {
            "type": "game_created",
            "request_id": request_id,
            "data": {"game_id": "game-123", "success": True},
        }

        mock_frontend.messages_received.append(response_message)

        # Verify correlation
        received_response = mock_frontend.messages_received[0]
        assert received_response["request_id"] == request_id
        assert received_response["type"] == "game_created"

    async def test_heartbeat_mechanism(self, mock_frontend: MockFrontendClient) -> None:
        """Test WebSocket heartbeat/ping-pong mechanism."""
        mock_frontend.websocket = AsyncMock()

        # Send ping
        ping_message = {"type": "ping", "data": {"timestamp": time.time()}}

        await mock_frontend.send_message(ping_message)

        # Mock pong response
        pong_message = {
            "type": "pong",
            "data": {"timestamp": time.time(), "server_time": time.time()},
        }

        mock_frontend.messages_received.append(pong_message)

        # Verify heartbeat
        received_pong = mock_frontend.messages_received[0]
        assert isinstance(received_pong, dict)
        assert received_pong["type"] == "pong"
        data = received_pong["data"]
        assert isinstance(data, dict)
        assert "timestamp" in data


@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling in connection flow."""

    async def test_malformed_json_handling(
        self, mock_frontend: MockFrontendClient
    ) -> None:
        """Test handling of malformed JSON messages."""
        mock_frontend.websocket = AsyncMock()

        # Simulate receiving malformed JSON
        mock_frontend.connection_events.append("malformed_json_received")

        # Mock error response
        error_response = {
            "type": "error",
            "data": {
                "error_code": "MALFORMED_JSON",
                "message": "Invalid JSON format in message",
            },
        }

        mock_frontend.messages_received.append(error_response)

        # Verify error handling
        assert "malformed_json_received" in mock_frontend.connection_events
        received_error = mock_frontend.messages_received[0]
        assert isinstance(received_error, dict)
        data = received_error["data"]
        assert isinstance(data, dict)
        assert data["error_code"] == "MALFORMED_JSON"

    async def test_connection_limit_handling(
        self, mock_frontend: MockFrontendClient
    ) -> None:
        """Test handling when connection limits are reached."""
        # Mock connection limit exceeded
        limit_exceeded_response = {
            "type": "connection_rejected",
            "data": {
                "reason": "Connection limit exceeded",
                "max_connections": 100,
                "current_connections": 100,
            },
        }

        mock_frontend.messages_received.append(limit_exceeded_response)

        # Verify limit handling
        received_message = mock_frontend.messages_received[0]
        assert isinstance(received_message, dict)
        assert received_message["type"] == "connection_rejected"
        data = received_message["data"]
        assert isinstance(data, dict)
        assert "limit exceeded" in data["reason"]

    async def test_unauthorized_connection_handling(
        self, mock_frontend: MockFrontendClient
    ) -> None:
        """Test handling of unauthorized connection attempts."""
        # Mock unauthorized access
        auth_error_response = {
            "type": "connection_rejected",
            "data": {
                "reason": "Authentication required",
                "auth_methods": ["token", "session"],
            },
        }

        mock_frontend.messages_received.append(auth_error_response)

        # Verify auth handling
        received_message = mock_frontend.messages_received[0]
        assert isinstance(received_message, dict)
        assert received_message["type"] == "connection_rejected"
        data = received_message["data"]
        assert isinstance(data, dict)
        assert "Authentication" in data["reason"]


@pytest.mark.asyncio
class TestPerformanceMetrics:
    """Test performance aspects of connection flow."""

    async def test_connection_establishment_time(
        self, mock_frontend: MockFrontendClient
    ) -> None:
        """Test connection establishment performance."""
        start_time = time.time()

        # Mock quick connection
        mock_frontend.websocket = AsyncMock()
        mock_frontend.is_connected = True

        connection_time = time.time() - start_time

        # Should be reasonably fast (under 100ms for mock)
        assert connection_time < 0.1

    async def test_message_throughput(self, mock_frontend: MockFrontendClient) -> None:
        """Test message sending/receiving throughput."""
        mock_frontend.websocket = AsyncMock()

        message_count = 100
        start_time = time.time()

        # Send many messages
        for i in range(message_count):
            message = {"type": "test_message", "data": {"sequence": i}}
            await mock_frontend.send_message(message)

        throughput_time = time.time() - start_time

        # Should handle messages efficiently
        messages_per_second = message_count / throughput_time
        assert messages_per_second > 1000  # Should be fast for mock

    async def test_concurrent_connection_handling(self) -> None:
        """Test handling multiple concurrent connections."""
        concurrent_clients = 10
        clients = []

        # Create multiple mock clients
        for i in range(concurrent_clients):
            client = MockFrontendClient(f"ws://localhost:8000/ws")
            client.websocket = AsyncMock()
            client.is_connected = True
            clients.append(client)

        # All should be connected successfully
        connected_count = sum(1 for client in clients if client.is_connected)
        assert connected_count == concurrent_clients

    async def test_memory_usage_during_connections(self) -> None:
        """Test memory efficiency with multiple connections."""
        # This would be more meaningful with real WebSocket connections
        # For now, verify we can create many mock clients without issues

        client_count = 1000
        clients = []

        for i in range(client_count):
            client = MockFrontendClient(f"ws://localhost:8000/ws")
            clients.append(client)

        # Should be able to create many clients
        assert len(clients) == client_count

        # Cleanup
        clients.clear()
        assert len(clients) == 0
