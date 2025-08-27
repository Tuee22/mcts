"""
Advanced WebSocket manager tests to cover remaining uncovered lines.
"""

import asyncio
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocket

from backend.api.models import (
    GameResponse,
    GameSession,
    MoveResponse,
    Player,
    PlayerType,
)
from backend.api.types import OutgoingWebSocketMessage, WebSocketProtocol
from backend.api.websocket_manager import WebSocketManager
from tests.pytest_marks import websocket


class MockWebSocket:
    """Mock WebSocket for testing that implements the WebSocket interface."""

    def __init__(self) -> None:
        self._accept_mock = MagicMock()
        self._send_text_mock = MagicMock()
        self._send_json_mock = MagicMock()
        self._close_mock = MagicMock()
        self._receive_text_mock = MagicMock(return_value="")
        self._receive_json_mock = MagicMock(return_value={})

    # Implement protocol methods
    async def accept(self) -> None:
        """Mock accept method."""
        self._accept_mock()

    async def close(self, code: int = 1000) -> None:
        """Mock close method."""
        self._close_mock(code)

    async def send_text(self, data: str) -> None:
        """Mock send_text method."""
        self._send_text_mock(data)

    async def send_json(self, data: object) -> None:
        """Mock send_json method."""
        self._send_json_mock(data)

    async def receive_text(self) -> str:
        """Mock receive_text method."""
        result = self._receive_text_mock()
        return str(result) if result is not None else ""

    async def receive_json(self) -> object:
        """Mock receive_json method."""
        return self._receive_json_mock()

    # Expose mock objects for assertions
    @property
    def mock_accept(self) -> MagicMock:
        return self._accept_mock

    @property
    def mock_send_text(self) -> MagicMock:
        return self._send_text_mock

    @property
    def mock_send_json(self) -> MagicMock:
        return self._send_json_mock

    @property
    def mock_close(self) -> MagicMock:
        return self._close_mock

    @property
    def mock_receive_text(self) -> MagicMock:
        return self._receive_text_mock

    @property
    def mock_receive_json(self) -> MagicMock:
        return self._receive_json_mock


def create_mock_websocket() -> MockWebSocket:
    """Create a properly typed mock WebSocket."""
    return MockWebSocket()


@pytest.mark.asyncio
class TestWebSocketManagerConnections:
    """Test WebSocket connection management."""

    async def test_connect_and_register_properly(
        self, ws_manager: WebSocketManager
    ) -> None:
        """Test proper connection and registration."""
        websocket = create_mock_websocket()

        await ws_manager.connect(websocket, "game1")

        # Verify websocket was accepted
        websocket.mock_accept.assert_called_once()

        # Verify connection was registered
        assert "game1" in ws_manager.active_connections
        assert websocket in ws_manager.active_connections["game1"]
        assert ws_manager.connection_games[websocket] == "game1"

    async def test_connect_with_notification_broadcast(
        self, ws_manager: WebSocketManager
    ) -> None:
        """Test that connect broadcasts notification to other clients."""
        # Connect first client
        websocket1 = create_mock_websocket()

        await ws_manager.connect(websocket1, "game1")

        # Connect second client
        websocket2 = create_mock_websocket()

        await ws_manager.connect(websocket2, "game1")

        # First client should have received notification about second client connecting
        assert websocket1.mock_send_json.call_count >= 1

        # Check that notification message was sent
        calls = websocket1.mock_send_json.call_args_list
        notification_sent = any(
            isinstance(call[0][0], dict)
            and call[0][0].get("type") == "player_connected"
            for call in calls
        )
        assert notification_sent

    async def test_disconnect_with_notification(
        self, ws_manager: WebSocketManager
    ) -> None:
        """Test disconnect sends notification to remaining clients."""
        # Connect two clients
        websocket1 = create_mock_websocket()
        websocket2 = create_mock_websocket()

        await ws_manager.connect(websocket1, "game1")
        await ws_manager.connect(websocket2, "game1")

        # Reset call count after connections
        websocket1.mock_send_json.reset_mock()
        websocket2.mock_send_json.reset_mock()

        # Disconnect first client
        await ws_manager.disconnect(websocket1, "game1")

        # Second client should receive disconnect notification
        assert websocket2.mock_send_json.call_count >= 1

        # Verify websocket1 is removed but websocket2 remains
        assert websocket1 not in ws_manager.active_connections["game1"]
        assert websocket2 in ws_manager.active_connections["game1"]

    async def test_disconnect_removes_empty_game(
        self, ws_manager: WebSocketManager
    ) -> None:
        """Test that empty games are removed after all clients disconnect."""
        websocket = create_mock_websocket()

        await ws_manager.connect(websocket, "game1")
        assert "game1" in ws_manager.active_connections

        await ws_manager.disconnect(websocket, "game1")

        # Game should be removed when no clients remain
        assert "game1" not in ws_manager.active_connections
        assert websocket not in ws_manager.connection_games


@pytest.mark.asyncio
class TestWebSocketManagerBroadcasting:
    """Test WebSocket broadcasting functionality."""

    async def test_broadcast_move_detailed(self, ws_manager: WebSocketManager) -> None:
        """Test detailed move broadcasting."""
        # Set up connections
        websockets = []
        for i in range(2):
            ws = create_mock_websocket()
            await ws_manager.connect(ws, "game1")
            websockets.append(ws)

        # Create mock move response - manually create to avoid mock typing issues
        from datetime import datetime

        from backend.api.models import Move

        player = Player(id="p1", name="Player1", type=PlayerType.HUMAN, is_hero=True)
        mock_move = Move(
            player_id="p1",
            action="*(4,1)",
            move_number=1,
            evaluation=0.5,
            timestamp=datetime.now(),
        )
        move_response = MoveResponse(
            success=True,
            game_id="game1",
            move=mock_move,
            game_status="in_progress",
            next_turn=2,
            next_player_type=PlayerType.HUMAN,
            board_display="board_string",
            winner=None,
        )

        await ws_manager.broadcast_move("game1", move_response)

        # All connected clients should receive the move
        for ws in websockets:
            ws.mock_send_json.assert_called()

            # Verify the message structure
            call_args = ws.mock_send_json.call_args
            assert call_args is not None
            message = call_args[0][0]
            assert isinstance(message, dict)
            assert message["type"] == "move"
            assert isinstance(message["data"], dict)
            assert message["data"]["game_id"] == "game1"
            move_data = message["data"]["move"]
            assert isinstance(move_data, dict)
            assert move_data["action"] == "*(4,1)"

    async def test_broadcast_game_state(self, ws_manager: WebSocketManager) -> None:
        """Test game state broadcasting."""
        websocket = create_mock_websocket()

        await ws_manager.connect(websocket, "game1")

        # Create real game response to avoid mock typing issues
        from datetime import datetime

        player1 = Player(
            id="player1", name="Player1", type=PlayerType.HUMAN, is_hero=True
        )
        player2 = Player(
            id="player2", name="Player2", type=PlayerType.HUMAN, is_hero=False
        )
        game_response = GameResponse(
            game_id="game1",
            status="in_progress",
            mode="pvp",
            player1=player1,
            player2=player2,
            current_turn=1,
            move_count=0,
            board_display=None,
            winner=None,
            created_at=datetime.now(),
        )

        await ws_manager.broadcast_game_state("game1", game_response)

        websocket.mock_send_json.assert_called()
        call_args = websocket.mock_send_json.call_args
        assert call_args is not None
        message = call_args[0][0]
        assert isinstance(message, dict)
        assert message["type"] == "game_state"
        assert isinstance(message["data"], dict)
        assert message["data"]["game_id"] == "game1"

    async def test_broadcast_game_created_to_all(
        self, ws_manager: WebSocketManager
    ) -> None:
        """Test game creation broadcast to all connections."""
        # Connect to different games
        websockets = []
        for i in range(3):
            ws = create_mock_websocket()
            await ws_manager.connect(ws, f"game{i}")
            websockets.append(ws)

        await ws_manager.broadcast_game_created("new_game")

        # All connections should receive the broadcast
        for ws in websockets:
            ws.mock_send_json.assert_called()
            call_args = ws.mock_send_json.call_args
            assert call_args is not None
            message = call_args[0][0]
            assert isinstance(message, dict)
            assert message["type"] == "game_created"
            assert isinstance(message["data"], dict)
            assert message["data"]["game_id"] == "new_game"

    async def test_broadcast_game_ended(self, ws_manager: WebSocketManager) -> None:
        """Test game end broadcasting."""
        websocket = create_mock_websocket()

        await ws_manager.connect(websocket, "game1")

        await ws_manager.broadcast_game_ended("game1", "resignation", winner=1)

        websocket.mock_send_json.assert_called()
        call_args = websocket.mock_send_json.call_args
        assert call_args is not None
        message = call_args[0][0]
        assert isinstance(message, dict)
        assert message["type"] == "game_ended"
        assert isinstance(message["data"], dict)
        assert message["data"]["game_id"] == "game1"
        assert message["data"]["game_status"] == "resignation"
        assert message["data"]["winner"] == 1


@pytest.mark.asyncio
class TestWebSocketManagerErrorHandling:
    """Test WebSocket error handling and edge cases."""

    async def test_send_json_safe_with_exception(
        self, ws_manager: WebSocketManager
    ) -> None:
        """Test _send_json_safe handles exceptions properly."""
        websocket = MockWebSocket()
        websocket._send_json_mock.side_effect = Exception("Send failed")

        dead_connections: List[WebSocketProtocol] = []

        # Create proper message format - data must match OutgoingWebSocketMessage type
        message: OutgoingWebSocketMessage = {
            "type": "test",
            "data": {"test": "message"},
        }

        # This should handle the exception gracefully
        await ws_manager._send_json_safe(websocket, message, dead_connections)

        # Websocket should be added to dead connections
        assert websocket in dead_connections

    async def test_send_json_safe_success(self, ws_manager: WebSocketManager) -> None:
        """Test _send_json_safe with successful send."""
        websocket = create_mock_websocket()

        dead_connections: List[WebSocketProtocol] = []

        # Create proper message format - data must match OutgoingWebSocketMessage type
        message: OutgoingWebSocketMessage = {
            "type": "test",
            "data": {"test": "message"},
        }

        await ws_manager._send_json_safe(websocket, message, dead_connections)

        # Should send successfully without adding to dead connections
        websocket.mock_send_json.assert_called_once_with(message)
        assert websocket not in dead_connections

    async def test_broadcast_to_game_cleans_dead_connections(
        self, ws_manager: WebSocketManager
    ) -> None:
        """Test that _broadcast_to_game cleans up dead connections."""
        # Connect working and failing websockets
        working_ws = create_mock_websocket()

        failing_ws = MockWebSocket()
        failing_ws._send_json_mock.side_effect = Exception("Send failed")

        await ws_manager.connect(working_ws, "game1")
        await ws_manager.connect(failing_ws, "game1")

        # Both should be connected initially
        assert len(ws_manager.active_connections["game1"]) == 2

        # Broadcast message - create proper format
        message: OutgoingWebSocketMessage = {
            "type": "test",
            "data": {"test": "message"},
        }
        await ws_manager._broadcast_to_game("game1", message)

        # Working websocket should still be connected
        assert working_ws in ws_manager.active_connections["game1"]

        # Failing websocket should be removed
        assert failing_ws not in ws_manager.active_connections.get("game1", set())

    async def test_broadcast_to_all_with_mixed_connections(
        self, ws_manager: WebSocketManager
    ) -> None:
        """Test _broadcast_to_all with connections across multiple games."""
        # Set up connections in different games
        websockets = []
        for i in range(3):
            ws = create_mock_websocket()
            await ws_manager.connect(ws, f"game{i}")
            websockets.append(ws)

        # Add one more connection to game0
        extra_ws = create_mock_websocket()
        await ws_manager.connect(extra_ws, "game0")
        websockets.append(extra_ws)

        # Create proper message format
        broadcast_message: OutgoingWebSocketMessage = {
            "type": "broadcast",
            "data": {"broadcast": "message"},
        }
        await ws_manager._broadcast_to_all(broadcast_message)

        # All connections should receive the message
        for ws in websockets:
            ws.mock_send_json.assert_called_with(broadcast_message)

    async def test_send_to_player_broadcasts_to_game(
        self, ws_manager: WebSocketManager
    ) -> None:
        """Test send_to_player falls back to broadcasting to game."""
        websocket = create_mock_websocket()

        await ws_manager.connect(websocket, "game1")

        # Create proper message format
        message: OutgoingWebSocketMessage = {
            "type": "pong",
            "data": {"message": "pong"},
        }
        await ws_manager.send_to_player("game1", "player1", message)

        # Should have sent message via broadcast
        websocket.mock_send_json.assert_called()


@pytest.mark.asyncio
class TestWebSocketManagerDisconnectAll:
    """Test disconnect_all functionality."""

    async def test_disconnect_all_comprehensive(
        self, ws_manager: WebSocketManager
    ) -> None:
        """Test comprehensive disconnect_all functionality."""
        # Set up multiple connections across different games
        websockets = []
        for i in range(3):
            for j in range(2):  # 2 connections per game
                ws = create_mock_websocket()
                ws._close_mock = MagicMock()
                await ws_manager.connect(ws, f"game{i}")
                websockets.append(ws)

        # Should have 3 games with 2 connections each
        assert len(ws_manager.active_connections) == 3
        total_connections = sum(
            len(conns) for conns in ws_manager.active_connections.values()
        )
        assert total_connections == 6

        await ws_manager.disconnect_all()

        # All connections should be cleared
        assert len(ws_manager.active_connections) == 0
        assert len(ws_manager.connection_games) == 0

        # All websockets should have been closed
        for ws in websockets:
            ws.mock_close.assert_called_once()

    async def test_disconnect_all_handles_close_exceptions(
        self, ws_manager: WebSocketManager
    ) -> None:
        """Test disconnect_all handles WebSocket close exceptions."""
        # Set up connections with different close behaviors
        working_ws = create_mock_websocket()
        working_ws._close_mock = MagicMock()

        failing_ws = create_mock_websocket()
        failing_ws._close_mock = MagicMock(side_effect=Exception("Close failed"))

        await ws_manager.connect(working_ws, "game1")
        await ws_manager.connect(failing_ws, "game1")

        # Should not raise exception despite failing close
        await ws_manager.disconnect_all()

        # Both should have been attempted to close
        working_ws.mock_close.assert_called_once()
        failing_ws.mock_close.assert_called_once()

        # All connections should still be cleared
        assert len(ws_manager.active_connections) == 0
        assert len(ws_manager.connection_games) == 0

    async def test_get_connection_count(self, ws_manager: WebSocketManager) -> None:
        """Test getting total connection count."""
        # Initially should be 0
        assert ws_manager.get_connection_count() == 0

        # Add some connections
        for i in range(5):
            ws = create_mock_websocket()
            await ws_manager.connect(ws, f"game{i % 2}")  # 2 games

        # Should count all connections
        assert ws_manager.get_connection_count() == 5

        # Disconnect some
        await ws_manager.disconnect_all()
        assert ws_manager.get_connection_count() == 0
