"""
Advanced WebSocket manager tests to cover remaining uncovered lines.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import WebSocket
from tests.pytest_marks import asyncio, websocket

from backend.api.websocket_manager import WebSocketManager
from backend.api.models import (
    MoveResponse,
    GameResponse,
    Player,
    PlayerType,
    GameSession,
)


@asyncio
class TestWebSocketManagerConnections:
    """Test WebSocket connection management."""

    async def test_connect_and_register_properly(
        self, ws_manager: WebSocketManager
    ) -> None:
        """Test proper connection and registration."""
        websocket = MagicMock()
        websocket.accept = AsyncMock()

        await ws_manager.connect(websocket, "game1")

        # Verify websocket was accepted
        websocket.accept.assert_called_once()

        # Verify connection was registered
        assert "game1" in ws_manager.active_connections
        assert websocket in ws_manager.active_connections["game1"]
        assert ws_manager.connection_games[websocket] == "game1"

    async def test_connect_with_notification_broadcast(
        self, ws_manager: WebSocketManager
    ) -> None:
        """Test that connect broadcasts notification to other clients."""
        # Connect first client
        websocket1 = MagicMock()
        websocket1.accept = AsyncMock()
        websocket1.send_json = AsyncMock()

        await ws_manager.connect(websocket1, "game1")

        # Connect second client
        websocket2 = MagicMock()
        websocket2.accept = AsyncMock()
        websocket2.send_json = AsyncMock()

        await ws_manager.connect(websocket2, "game1")

        # First client should have received notification about second client connecting
        assert websocket1.send_json.call_count >= 1

        # Check that notification message was sent
        calls = websocket1.send_json.call_args_list
        notification_sent = any(
            call[0][0].get("type") == "player_connected" for call in calls
        )
        assert notification_sent

    async def test_disconnect_with_notification(
        self, ws_manager: WebSocketManager
    ) -> None:
        """Test disconnect sends notification to remaining clients."""
        # Connect two clients
        websocket1 = MagicMock()
        websocket1.accept = AsyncMock()
        websocket1.send_json = AsyncMock()

        websocket2 = MagicMock()
        websocket2.accept = AsyncMock()
        websocket2.send_json = AsyncMock()

        await ws_manager.connect(websocket1, "game1")
        await ws_manager.connect(websocket2, "game1")

        # Reset call count after connections
        websocket1.send_json.reset_mock()
        websocket2.send_json.reset_mock()

        # Disconnect first client
        await ws_manager.disconnect(websocket1, "game1")

        # Second client should receive disconnect notification
        assert websocket2.send_json.call_count >= 1

        # Verify websocket1 is removed but websocket2 remains
        assert websocket1 not in ws_manager.active_connections["game1"]
        assert websocket2 in ws_manager.active_connections["game1"]

    async def test_disconnect_removes_empty_game(
        self, ws_manager: WebSocketManager
    ) -> None:
        """Test that empty games are removed after all clients disconnect."""
        websocket = MagicMock()
        websocket.accept = AsyncMock()

        await ws_manager.connect(websocket, "game1")
        assert "game1" in ws_manager.active_connections

        await ws_manager.disconnect(websocket, "game1")

        # Game should be removed when no clients remain
        assert "game1" not in ws_manager.active_connections
        assert websocket not in ws_manager.connection_games


@asyncio
class TestWebSocketManagerBroadcasting:
    """Test WebSocket broadcasting functionality."""

    async def test_broadcast_move_detailed(self, ws_manager: WebSocketManager) -> None:
        """Test detailed move broadcasting."""
        # Set up connections
        websockets = []
        for i in range(2):
            ws = MagicMock()
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            await ws_manager.connect(ws, "game1")
            websockets.append(ws)

        # Create mock move response
        player = Player(id="p1", name="Player1", type=PlayerType.HUMAN, is_hero=True)
        move_response = MagicMock(spec=MoveResponse)

        # Mock the move object
        mock_move = MagicMock()
        mock_move.player_id = "p1"
        mock_move.action = "*(4,1)"
        mock_move.move_number = 1
        mock_move.evaluation = 0.5
        mock_move.timestamp = MagicMock()
        mock_move.timestamp.isoformat.return_value = "2023-01-01T00:00:00"

        move_response.move = mock_move
        move_response.game_status = "in_progress"
        move_response.next_turn = 2
        move_response.board_display = "board_string"
        move_response.winner = None

        await ws_manager.broadcast_move("game1", move_response)

        # All connected clients should receive the move
        for ws in websockets:
            ws.send_json.assert_called()

            # Verify the message structure
            call_args = ws.send_json.call_args[0][0]
            assert call_args["type"] == "move"
            assert call_args["data"]["game_id"] == "game1"
            assert call_args["data"]["move"]["action"] == "*(4,1)"

    async def test_broadcast_game_state(self, ws_manager: WebSocketManager) -> None:
        """Test game state broadcasting."""
        websocket = MagicMock()
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()

        await ws_manager.connect(websocket, "game1")

        # Create mock game response
        game_response = MagicMock(spec=GameResponse)
        game_response.dict.return_value = {"game_id": "game1", "status": "in_progress"}

        await ws_manager.broadcast_game_state("game1", game_response)

        websocket.send_json.assert_called()
        call_args = websocket.send_json.call_args[0][0]
        assert call_args["type"] == "game_state"
        assert call_args["data"]["game_id"] == "game1"

    async def test_broadcast_game_created_to_all(
        self, ws_manager: WebSocketManager
    ) -> None:
        """Test game creation broadcast to all connections."""
        # Connect to different games
        websockets = []
        for i in range(3):
            ws = MagicMock()
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            await ws_manager.connect(ws, f"game{i}")
            websockets.append(ws)

        await ws_manager.broadcast_game_created("new_game")

        # All connections should receive the broadcast
        for ws in websockets:
            ws.send_json.assert_called()
            call_args = ws.send_json.call_args[0][0]
            assert call_args["type"] == "game_created"
            assert call_args["data"]["game_id"] == "new_game"

    async def test_broadcast_game_ended(self, ws_manager: WebSocketManager) -> None:
        """Test game end broadcasting."""
        websocket = MagicMock()
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()

        await ws_manager.connect(websocket, "game1")

        await ws_manager.broadcast_game_ended("game1", "resignation", winner=1)

        websocket.send_json.assert_called()
        call_args = websocket.send_json.call_args[0][0]
        assert call_args["type"] == "game_ended"
        assert call_args["data"]["game_id"] == "game1"
        assert call_args["data"]["reason"] == "resignation"
        assert call_args["data"]["winner"] == 1


@asyncio
class TestWebSocketManagerErrorHandling:
    """Test WebSocket error handling and edge cases."""

    async def test_send_json_safe_with_exception(
        self, ws_manager: WebSocketManager
    ) -> None:
        """Test _send_json_safe handles exceptions properly."""
        websocket = MagicMock()
        websocket.send_json = AsyncMock(side_effect=Exception("Send failed"))

        dead_connections: list[WebSocket] = []

        # This should handle the exception gracefully
        await ws_manager._send_json_safe(
            websocket, {"test": "message"}, dead_connections
        )

        # Websocket should be added to dead connections
        assert websocket in dead_connections

    async def test_send_json_safe_success(self, ws_manager: WebSocketManager) -> None:
        """Test _send_json_safe with successful send."""
        websocket = MagicMock()
        websocket.send_json = AsyncMock()

        dead_connections: list[WebSocket] = []

        await ws_manager._send_json_safe(
            websocket, {"test": "message"}, dead_connections
        )

        # Should send successfully without adding to dead connections
        websocket.send_json.assert_called_once_with({"test": "message"})
        assert websocket not in dead_connections

    async def test_broadcast_to_game_cleans_dead_connections(
        self, ws_manager: WebSocketManager
    ) -> None:
        """Test that _broadcast_to_game cleans up dead connections."""
        # Connect working and failing websockets
        working_ws = MagicMock()
        working_ws.accept = AsyncMock()
        working_ws.send_json = AsyncMock()

        failing_ws = MagicMock()
        failing_ws.accept = AsyncMock()
        failing_ws.send_json = AsyncMock(side_effect=Exception("Send failed"))

        await ws_manager.connect(working_ws, "game1")
        await ws_manager.connect(failing_ws, "game1")

        # Both should be connected initially
        assert len(ws_manager.active_connections["game1"]) == 2

        # Broadcast message
        await ws_manager._broadcast_to_game("game1", {"test": "message"})

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
            ws = MagicMock()
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            await ws_manager.connect(ws, f"game{i}")
            websockets.append(ws)

        # Add one more connection to game0
        extra_ws = MagicMock()
        extra_ws.accept = AsyncMock()
        extra_ws.send_json = AsyncMock()
        await ws_manager.connect(extra_ws, "game0")
        websockets.append(extra_ws)

        await ws_manager._broadcast_to_all({"broadcast": "message"})

        # All connections should receive the message
        for ws in websockets:
            ws.send_json.assert_called_with({"broadcast": "message"})

    async def test_send_to_player_broadcasts_to_game(
        self, ws_manager: WebSocketManager
    ) -> None:
        """Test send_to_player falls back to broadcasting to game."""
        websocket = MagicMock()
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()

        await ws_manager.connect(websocket, "game1")

        await ws_manager.send_to_player("game1", "player1", {"type": "pong"})

        # Should have sent message via broadcast
        websocket.send_json.assert_called()


@asyncio
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
                ws = MagicMock()
                ws.accept = AsyncMock()
                ws.close = AsyncMock()
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
            ws.close.assert_called_once()

    async def test_disconnect_all_handles_close_exceptions(
        self, ws_manager: WebSocketManager
    ) -> None:
        """Test disconnect_all handles WebSocket close exceptions."""
        # Set up connections with different close behaviors
        working_ws = MagicMock()
        working_ws.accept = AsyncMock()
        working_ws.close = AsyncMock()

        failing_ws = MagicMock()
        failing_ws.accept = AsyncMock()
        failing_ws.close = AsyncMock(side_effect=Exception("Close failed"))

        await ws_manager.connect(working_ws, "game1")
        await ws_manager.connect(failing_ws, "game1")

        # Should not raise exception despite failing close
        await ws_manager.disconnect_all()

        # Both should have been attempted to close
        working_ws.close.assert_called_once()
        failing_ws.close.assert_called_once()

        # All connections should still be cleared
        assert len(ws_manager.active_connections) == 0
        assert len(ws_manager.connection_games) == 0

    async def test_get_connection_count(self, ws_manager: WebSocketManager) -> None:
        """Test getting total connection count."""
        # Initially should be 0
        assert ws_manager.get_connection_count() == 0

        # Add some connections
        for i in range(5):
            ws = MagicMock()
            ws.accept = AsyncMock()
            await ws_manager.connect(ws, f"game{i % 2}")  # 2 games

        # Should count all connections
        assert ws_manager.get_connection_count() == 5

        # Disconnect some
        await ws_manager.disconnect_all()
        assert ws_manager.get_connection_count() == 0
