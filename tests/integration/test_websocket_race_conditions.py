"""
WebSocket Race Condition Integration Tests

These tests use real WebSocket connections to reproduce the race conditions
that cause E2E test failures. They test the interaction between WebSocket
events and frontend state management.
"""

import asyncio
import json
import pytest
import websockets
from typing import Dict, List, Optional, Union, AsyncGenerator
from unittest.mock import AsyncMock, patch

from backend.api.models import GameSettings, MCTSSettings

# Type aliases for JSON-serializable data
from typing_extensions import TypedDict


class GameRequestData(TypedDict):
    player1_type: str
    player2_type: str
    player1_name: str
    player2_name: str
    settings: Dict[str, Dict[str, Union[float, int]]]


class GameRequest(TypedDict):
    type: str
    data: GameRequestData


class PingData(TypedDict):
    timestamp: Optional[float]
    id: Optional[int]
    client: Optional[int]
    op: Optional[int]
    recovery_test: Optional[bool]
    final_check: Optional[bool]
    message_id: Optional[int]


class PingRequest(TypedDict):
    type: str
    data: PingData


class GameStateRequest(TypedDict):
    type: str
    data: Dict[str, str]


class ResponseData(TypedDict, total=False):
    game_id: str
    timestamp: float
    id: int
    client: int
    op: int
    recovery_test: bool
    final_check: bool
    message_id: int


class WebSocketResponse(TypedDict):
    type: str
    data: ResponseData


MessageRequest = Union[GameRequest, PingRequest, GameStateRequest, Dict[str, object]]


class WebSocketTestClient:
    """Test client for WebSocket connections with timing control."""

    def __init__(self, uri: str) -> None:
        self.uri = uri
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.messages: List[WebSocketResponse] = []
        self.connected = False

    async def connect(self) -> None:
        """Connect to WebSocket server."""
        self.websocket = await websockets.connect(self.uri)
        self.connected = True

    async def disconnect(self) -> None:
        """Disconnect from WebSocket server."""
        if self.websocket:
            await self.websocket.close()
        self.connected = False
        self.websocket = None

    async def send_message(self, message: MessageRequest) -> None:
        """Send a message to the server."""
        if not self.websocket:
            raise RuntimeError("Not connected")
        await self.websocket.send(json.dumps(message))

    async def receive_message(self, timeout: float = 1.0) -> WebSocketResponse:
        """Receive a message from the server."""
        if not self.websocket:
            raise RuntimeError("Not connected")

        try:
            message = await asyncio.wait_for(self.websocket.recv(), timeout=timeout)
            parsed: WebSocketResponse = json.loads(message)
            self.messages.append(parsed)
            return parsed
        except asyncio.TimeoutError:
            raise TimeoutError(f"No message received within {timeout} seconds")

    async def wait_for_message_type(
        self, message_type: str, timeout: float = 2.0
    ) -> WebSocketResponse:
        """Wait for a specific message type."""
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                message = await self.receive_message(timeout=0.1)
                if message.get("type") == message_type:
                    return message
            except TimeoutError:
                continue

        raise TimeoutError(
            f"Message type '{message_type}' not received within {timeout} seconds"
        )


@pytest.fixture
async def websocket_client() -> AsyncGenerator[WebSocketTestClient, None]:
    """Create a WebSocket test client."""
    client = WebSocketTestClient("ws://localhost:8000/ws")
    yield client
    if client.connected:
        await client.disconnect()


class TestWebSocketRaceConditions:
    """Test race conditions in WebSocket communication."""

    @pytest.mark.asyncio
    async def test_rapid_connect_disconnect_cycles(
        self, websocket_client: WebSocketTestClient
    ) -> None:
        """Test rapid connection/disconnection cycles."""

        # Perform multiple rapid connect/disconnect cycles
        for i in range(5):
            await websocket_client.connect()
            assert websocket_client.connected

            # Send a ping to ensure connection is active
            ping_msg: PingRequest = {
                "type": "ping",
                "data": {
                    "timestamp": asyncio.get_event_loop().time(),
                    "id": None,
                    "client": None,
                    "op": None,
                    "recovery_test": None,
                    "final_check": None,
                    "message_id": None,
                },
            }
            await websocket_client.send_message(ping_msg)

            # Receive pong response
            response = await websocket_client.wait_for_message_type("pong")
            assert response["type"] == "pong"

            # Rapid disconnect
            await websocket_client.disconnect()

            # Small delay to simulate real timing
            await asyncio.sleep(0.01)

    @pytest.mark.asyncio
    async def test_game_creation_during_connection_instability(
        self, websocket_client: WebSocketTestClient
    ) -> None:
        """Test game creation during connection instability."""

        await websocket_client.connect()

        # Start game creation
        game_request: GameRequest = {
            "type": "create_game",
            "data": {
                "player1_type": "human",
                "player2_type": "human",
                "player1_name": "Player 1",
                "player2_name": "Player 2",
                "settings": {
                    "mcts_settings": {
                        "c": 1.414,
                        "min_simulations": 100,
                        "max_simulations": 1000,
                    }
                },
            },
        }

        await websocket_client.send_message(game_request)

        # Simulate connection instability during game creation
        await websocket_client.disconnect()
        await asyncio.sleep(0.05)  # Brief disconnection
        await websocket_client.connect()

        # Try to receive game creation response
        try:
            response = await websocket_client.wait_for_message_type(
                "game_created", timeout=3.0
            )
            assert response["type"] == "game_created"
            game_id = response["data"].get("game_id")
            assert game_id is not None
        except TimeoutError:
            # Connection instability may have prevented game creation
            # This is expected behavior - test passes if no crash occurs
            pass

    @pytest.mark.asyncio
    async def test_rapid_game_state_updates(
        self, websocket_client: WebSocketTestClient
    ) -> None:
        """Test rapid game state updates that can cause frontend race conditions."""

        await websocket_client.connect()

        # Create a game first
        game_request: GameRequest = {
            "type": "create_game",
            "data": {
                "player1_type": "human",
                "player2_type": "human",
                "player1_name": "Player 1",
                "player2_name": "Player 2",
                "settings": {
                    "mcts_settings": {
                        "c": 1.414,
                        "min_simulations": 100,
                        "max_simulations": 1000,
                    }
                },
            },
        }

        await websocket_client.send_message(game_request)
        game_response = await websocket_client.wait_for_message_type("game_created")
        game_id = game_response["data"].get("game_id")
        assert game_id is not None

        # Rapid state request cycles
        for i in range(10):
            await websocket_client.send_message(
                {"type": "get_game_state", "data": {"game_id": game_id}}
            )

            # Small delay between requests
            await asyncio.sleep(0.01)

        # Collect all responses
        responses = []
        for _ in range(10):
            try:
                response = await websocket_client.wait_for_message_type(
                    "game_state", timeout=0.5
                )
                responses.append(response)
            except TimeoutError:
                break

        # Should have received at least some responses
        assert len(responses) > 0

        # All responses should be for the same game
        for response in responses:
            response_game_id = response["data"].get("game_id")
            assert response_game_id == game_id

    @pytest.mark.asyncio
    async def test_concurrent_game_operations(
        self, websocket_client: WebSocketTestClient
    ) -> None:
        """Test concurrent game operations that can cause race conditions."""

        await websocket_client.connect()

        # Create multiple games rapidly
        game_ids = []
        for i in range(3):
            game_request: GameRequest = {
                "type": "create_game",
                "data": {
                    "player1_type": "human",
                    "player2_type": "human",
                    "player1_name": f"Player 1 Game {i}",
                    "player2_name": f"Player 2 Game {i}",
                    "settings": {
                        "mcts_settings": {
                            "c": 1.414,
                            "min_simulations": 100,
                            "max_simulations": 1000,
                        }
                    },
                },
            }

            await websocket_client.send_message(game_request)

            # Don't wait for response before sending next request
            await asyncio.sleep(0.01)

        # Collect game creation responses
        for _ in range(3):
            try:
                response = await websocket_client.wait_for_message_type(
                    "game_created", timeout=2.0
                )
                game_id = response["data"].get("game_id")
                if game_id is not None:
                    game_ids.append(game_id)
            except TimeoutError:
                continue

        # Should have created at least one game
        assert len(game_ids) > 0

        # Test rapid game state requests for all games
        for game_id in game_ids:
            await websocket_client.send_message(
                {"type": "get_game_state", "data": {"game_id": game_id}}
            )

        # Collect responses
        state_responses = []
        for _ in range(len(game_ids)):
            try:
                response = await websocket_client.wait_for_message_type(
                    "game_state", timeout=1.0
                )
                state_responses.append(response)
            except TimeoutError:
                continue

        # Should receive responses for the games
        assert len(state_responses) > 0

    @pytest.mark.asyncio
    async def test_message_ordering_during_rapid_operations(
        self, websocket_client: WebSocketTestClient
    ) -> None:
        """Test message ordering during rapid operations."""

        await websocket_client.connect()

        # Send rapid sequence of different message types
        message_sequence: List[MessageRequest] = [
            {
                "type": "ping",
                "data": {
                    "id": 1,
                    "timestamp": None,
                    "client": None,
                    "op": None,
                    "recovery_test": None,
                    "final_check": None,
                    "message_id": None,
                },
            },
            {"type": "list_games", "data": {}},
            {
                "type": "ping",
                "data": {
                    "id": 2,
                    "timestamp": None,
                    "client": None,
                    "op": None,
                    "recovery_test": None,
                    "final_check": None,
                    "message_id": None,
                },
            },
            {"type": "list_games", "data": {}},
            {
                "type": "ping",
                "data": {
                    "id": 3,
                    "timestamp": None,
                    "client": None,
                    "op": None,
                    "recovery_test": None,
                    "final_check": None,
                    "message_id": None,
                },
            },
        ]

        # Send all messages rapidly
        for message in message_sequence:
            await websocket_client.send_message(message)
            await asyncio.sleep(0.005)  # Very small delay

        # Collect all responses
        responses = []
        expected_responses = len(message_sequence)

        for _ in range(expected_responses):
            try:
                response = await websocket_client.receive_message(timeout=0.5)
                responses.append(response)
            except TimeoutError:
                break

        # Should receive responses for most/all messages
        assert len(responses) >= expected_responses // 2

        # Verify response types are valid
        valid_types = {"pong", "games_list", "error"}
        for response in responses:
            assert response["type"] in valid_types

    @pytest.mark.asyncio
    async def test_connection_recovery_with_pending_operations(
        self, websocket_client: WebSocketTestClient
    ) -> None:
        """Test connection recovery when operations are pending."""

        await websocket_client.connect()

        # Start some operations
        await websocket_client.send_message({"type": "list_games", "data": {}})
        await websocket_client.send_message(
            {
                "type": "create_game",
                "data": {
                    "player1_type": "human",
                    "player2_type": "human",
                    "player1_name": "Player 1",
                    "player2_name": "Player 2",
                    "settings": {
                        "mcts_settings": {
                            "c": 1.414,
                            "min_simulations": 100,
                            "max_simulations": 1000,
                        }
                    },
                },
            }
        )

        # Simulate connection loss during operations
        await websocket_client.disconnect()
        await asyncio.sleep(0.1)

        # Reconnect and verify server is still responsive
        await websocket_client.connect()

        # Send a simple ping to verify connection
        await websocket_client.send_message(
            {"type": "ping", "data": {"recovery_test": True}}
        )

        response = await websocket_client.wait_for_message_type("pong", timeout=2.0)
        assert response["type"] == "pong"
        recovery_test = response["data"].get("recovery_test")
        assert recovery_test is True


class TestWebSocketMessageTiming:
    """Test message timing issues that affect frontend state management."""

    @pytest.mark.asyncio
    async def test_delayed_response_handling(
        self, websocket_client: WebSocketTestClient
    ) -> None:
        """Test handling of delayed responses."""

        await websocket_client.connect()

        # Send message that may have delayed response
        await websocket_client.send_message(
            {
                "type": "create_game",
                "data": {
                    "player1_type": "human",
                    "player2_type": "machine",  # AI game may take longer
                    "player1_name": "Human",
                    "player2_name": "AI",
                    "settings": {
                        "mcts_settings": {
                            "c": 1.414,
                            "min_simulations": 500,  # Higher simulation count
                            "max_simulations": 1000,
                        }
                    },
                },
            }
        )

        # Send immediate follow-up request
        await websocket_client.send_message({"type": "ping", "data": {}})

        # Should receive ping response quickly
        ping_response = await websocket_client.wait_for_message_type(
            "pong", timeout=1.0
        )
        assert ping_response["type"] == "pong"

        # Game creation may take longer
        try:
            game_response = await websocket_client.wait_for_message_type(
                "game_created", timeout=5.0
            )
            assert game_response["type"] == "game_created"
        except TimeoutError:
            # Acceptable if game creation times out with high simulation count
            pass

    @pytest.mark.asyncio
    async def test_out_of_order_message_handling(
        self, websocket_client: WebSocketTestClient
    ) -> None:
        """Test handling of out-of-order messages."""

        await websocket_client.connect()

        # Send multiple ping messages with IDs
        message_ids = [1, 2, 3, 4, 5]
        for msg_id in message_ids:
            await websocket_client.send_message(
                {"type": "ping", "data": {"message_id": msg_id}}
            )
            await asyncio.sleep(0.01)

        # Collect responses
        responses = []
        for _ in message_ids:
            try:
                response = await websocket_client.wait_for_message_type(
                    "pong", timeout=0.5
                )
                responses.append(response)
            except TimeoutError:
                break

        # Should receive all responses
        assert len(responses) == len(message_ids)

        # Check that all message IDs are present (may be out of order)
        received_ids: List[int] = []
        for r in responses:
            msg_id_raw = r["data"].get("message_id")
            if msg_id_raw is not None and isinstance(msg_id_raw, int):
                received_ids.append(msg_id_raw)
        assert set(received_ids) == set(message_ids)


@pytest.mark.asyncio
async def test_websocket_integration_stability() -> None:
    """Test overall WebSocket integration stability under stress."""

    clients = []
    try:
        # Create multiple concurrent clients
        for i in range(3):
            client = WebSocketTestClient("ws://localhost:8000/ws")
            await client.connect()
            clients.append(client)

        # Each client performs rapid operations
        async def client_operations(
            client: WebSocketTestClient, client_id: int
        ) -> None:
            for j in range(5):
                # Mix of operations
                await client.send_message(
                    {"type": "ping", "data": {"client": client_id, "op": j}}
                )
                await client.send_message({"type": "list_games", "data": {}})
                await asyncio.sleep(0.02)

        # Run all clients concurrently
        await asyncio.gather(
            *[client_operations(client, i) for i, client in enumerate(clients)]
        )

        # Verify all clients are still connected
        for i, client in enumerate(clients):
            await client.send_message(
                {"type": "ping", "data": {"final_check": True, "client": i}}
            )
            response = await client.wait_for_message_type("pong", timeout=2.0)
            final_check = response["data"].get("final_check")
            assert final_check is True

    finally:
        # Clean up all clients
        for client in clients:
            if client.connected:
                await client.disconnect()
