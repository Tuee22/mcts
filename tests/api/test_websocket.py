"""
Tests for WebSocket functionality.
"""
import pytest
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import WebSocket
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

# Fixtures are imported automatically from conftest.py
from api.websocket_manager import WebSocketManager
from api.models import MoveResponse, GameResponse, Move, GameStatus, PlayerType


# MCTS mock fixture for websocket tests
@pytest.fixture(autouse=True)
def mock_mcts():
    """Mock MCTS for websocket tests."""
    mock_mcts = MagicMock()
    mock_mcts.get_sorted_actions.return_value = [
        (100, 0.8, "*(4,1)"),
        (50, 0.6, "*(3,0)")
    ]
    mock_mcts.choose_best_action.return_value = "*(4,1)"
    mock_mcts.get_evaluation.return_value = None
    mock_mcts.display.return_value = "Test Board Display"
    mock_mcts.ensure_sims.return_value = None
    mock_mcts.make_move.return_value = None
    mock_mcts.get_legal_moves.return_value = ["*(4,1)", "*(3,0)", "H(4,0)"]
    
    with patch('api.game_manager.Corridors_MCTS', return_value=mock_mcts):
        yield mock_mcts


@pytest.mark.asyncio
class TestWebSocketManager:
    """Test WebSocketManager functionality."""
    
    async def test_connect(self, ws_manager: WebSocketManager):
        """Test WebSocket connection."""
        mock_ws = AsyncMock(spec=WebSocket)
        game_id = "test-game"
        
        await ws_manager.connect(mock_ws, game_id)
        
        # Check connection was registered
        assert game_id in ws_manager.active_connections
        assert mock_ws in ws_manager.active_connections[game_id]
        assert ws_manager.connection_games[mock_ws] == game_id
        
        # Check accept was called
        mock_ws.accept.assert_called_once()
    
    async def test_disconnect(self, ws_manager: WebSocketManager):
        """Test WebSocket disconnection."""
        mock_ws = AsyncMock(spec=WebSocket)
        game_id = "test-game"
        
        # Connect first
        await ws_manager.connect(mock_ws, game_id)
        
        # Then disconnect
        await ws_manager.disconnect(mock_ws, game_id)
        
        # Check connection was removed
        if game_id in ws_manager.active_connections:
            assert mock_ws not in ws_manager.active_connections[game_id]
        assert mock_ws not in ws_manager.connection_games
    
    async def test_broadcast_move(self, ws_manager: WebSocketManager):
        """Test broadcasting a move."""
        # Setup mock connections
        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)
        game_id = "test-game"
        
        await ws_manager.connect(mock_ws1, game_id)
        await ws_manager.connect(mock_ws2, game_id)
        
        # Reset call counts after connection messages
        mock_ws1.send_json.reset_mock()
        mock_ws2.send_json.reset_mock()
        
        # Create move response
        move = Move(
            player_id="player1",
            action="*(4,1)",
            move_number=1
        )
        
        move_response = MoveResponse(
            success=True,
            game_id=game_id,
            move=move,
            game_status=GameStatus.IN_PROGRESS,
            next_turn=2,
            next_player_type=PlayerType.HUMAN
        )
        
        # Broadcast move
        await ws_manager.broadcast_move(game_id, move_response)
        
        # Check both connections received the move message
        mock_ws1.send_json.assert_called_once()
        mock_ws2.send_json.assert_called_once()
        
        # Verify message content
        sent_data = mock_ws1.send_json.call_args[0][0]
        assert sent_data["type"] == "move"
        assert sent_data["data"]["move"]["action"] == "*(4,1)"
    
    async def test_broadcast_game_ended(self, ws_manager: WebSocketManager):
        """Test broadcasting game end."""
        mock_ws = AsyncMock(spec=WebSocket)
        game_id = "test-game"
        
        await ws_manager.connect(mock_ws, game_id)
        
        # Broadcast game end
        await ws_manager.broadcast_game_ended(game_id, "checkmate", winner=1)
        
        # Check message was sent
        mock_ws.send_json.assert_called_once()
        sent_data = mock_ws.send_json.call_args[0][0]
        assert sent_data["type"] == "game_ended"
        assert sent_data["data"]["reason"] == "checkmate"
        assert sent_data["data"]["winner"] == 1
    
    async def test_broadcast_with_dead_connection(self, ws_manager: WebSocketManager):
        """Test broadcasting with a dead connection."""
        mock_ws_good = AsyncMock(spec=WebSocket)
        mock_ws_bad = AsyncMock(spec=WebSocket)
        mock_ws_bad.send_json.side_effect = Exception("Connection closed")
        game_id = "test-game"
        
        await ws_manager.connect(mock_ws_good, game_id)
        await ws_manager.connect(mock_ws_bad, game_id)
        
        # Broadcast message
        await ws_manager.broadcast_game_created(game_id)
        
        # Good connection should receive message
        mock_ws_good.send_json.assert_called()
        
        # Bad connection should be removed
        assert mock_ws_bad not in ws_manager.active_connections.get(game_id, set())
    
    async def test_get_connection_count(self, ws_manager: WebSocketManager):
        """Test getting connection counts."""
        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)
        mock_ws3 = AsyncMock(spec=WebSocket)
        
        await ws_manager.connect(mock_ws1, "game1")
        await ws_manager.connect(mock_ws2, "game1")
        await ws_manager.connect(mock_ws3, "game2")
        
        # Total connections
        assert ws_manager.get_connection_count() == 3
        
        # Per-game connections
        assert ws_manager.get_game_connection_count("game1") == 2
        assert ws_manager.get_game_connection_count("game2") == 1
        assert ws_manager.get_game_connection_count("nonexistent") == 0
    
    async def test_disconnect_all(self, ws_manager: WebSocketManager):
        """Test disconnecting all connections."""
        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)
        
        await ws_manager.connect(mock_ws1, "game1")
        await ws_manager.connect(mock_ws2, "game2")
        
        # Disconnect all
        await ws_manager.disconnect_all()
        
        # Check all connections closed
        mock_ws1.close.assert_called_once()
        mock_ws2.close.assert_called_once()
        
        # Check data structures cleared
        assert len(ws_manager.active_connections) == 0
        assert len(ws_manager.connection_games) == 0


class TestWebSocketEndpoint:
    """Test WebSocket endpoint integration."""
    
    def test_websocket_connection(self, test_client: TestClient, pvp_game_request):
        """Test WebSocket connection to game."""
        # MCTS is mocked via autouse fixture above
        
        # Create a game first
        response = test_client.post("/games", json=pvp_game_request.dict())
        game_id = response.json()["game_id"]
        
        # Connect via WebSocket
        with test_client.websocket_connect(f"/games/{game_id}/ws") as websocket:
            # Should receive initial game state
            data = websocket.receive_json()
            assert data["type"] == "game_state"
            assert data["data"]["game_id"] == game_id
            
            # Send ping
            websocket.send_json({"type": "ping"})
            
            # Receive pong
            data = websocket.receive_json()
            assert data["type"] == "pong"
    
    def test_websocket_invalid_game(self, test_client: TestClient):
        """Test WebSocket connection to invalid game."""
        with pytest.raises(Exception):
            with test_client.websocket_connect("/games/invalid-game/ws") as websocket:
                pass  # Should fail to connect
    
    def test_websocket_move_via_ws(self, test_client: TestClient, pvp_game_request):
        """Test making a move via WebSocket."""
        # MCTS is mocked via autouse fixture above
        
        # Create a game
        response = test_client.post("/games", json=pvp_game_request.dict())
        game_data = response.json()
        game_id = game_data["game_id"]
        player1_id = game_data["player1"]["id"]
        
        with test_client.websocket_connect(f"/games/{game_id}/ws") as websocket:
            # Receive initial state
            websocket.receive_json()
            
            # Send move via WebSocket
            websocket.send_json({
                "type": "move",
                "player_id": player1_id,
                "action": "*(4,1)"
            })
            
            # Should receive move broadcast
            data = websocket.receive_json()
            assert data["type"] == "move"
            assert data["data"]["move"]["action"] == "*(4,1)"
    
    def test_websocket_receive_updates(self, test_client: TestClient, pvp_game_request):
        """Test receiving updates from other clients."""
        # MCTS is mocked via autouse fixture above
        
        # Create a game
        response = test_client.post("/games", json=pvp_game_request.dict())
        game_data = response.json()
        game_id = game_data["game_id"]
        player1_id = game_data["player1"]["id"]
        
        # Connect via WebSocket
        with test_client.websocket_connect(f"/games/{game_id}/ws") as websocket:
            # Receive initial state
            websocket.receive_json()
            
            # Make a move via REST API
            move_response = test_client.post(
                f"/games/{game_id}/moves",
                json={
                    "player_id": player1_id,
                    "action": "*(4,1)"
                }
            )
            assert move_response.status_code == 200
            
            # Should receive move via WebSocket
            data = websocket.receive_json()
            assert data["type"] == "move"
            assert data["data"]["move"]["action"] == "*(4,1)"


@pytest.mark.asyncio
class TestWebSocketConcurrency:
    """Test WebSocket concurrent operations."""
    
    async def test_concurrent_connections(self, ws_manager: WebSocketManager):
        """Test multiple concurrent connections."""
        mock_websockets = [AsyncMock(spec=WebSocket) for _ in range(10)]
        game_id = "test-game"
        
        # Connect all concurrently
        tasks = [
            ws_manager.connect(ws, game_id) 
            for ws in mock_websockets
        ]
        await asyncio.gather(*tasks)
        
        # Check all connected
        assert len(ws_manager.active_connections[game_id]) == 10
    
    async def test_concurrent_broadcasts(self, ws_manager: WebSocketManager):
        """Test concurrent broadcasts."""
        mock_websockets = [AsyncMock(spec=WebSocket) for _ in range(5)]
        games = ["game1", "game2", "game3"]
        
        # Connect websockets to different games
        for i, ws in enumerate(mock_websockets):
            await ws_manager.connect(ws, games[i % len(games)])
        
        # Broadcast to all games concurrently
        tasks = [
            ws_manager.broadcast_game_created(game_id)
            for game_id in games
        ]
        await asyncio.gather(*tasks)
        
        # All websockets should have received messages
        for ws in mock_websockets:
            ws.send_json.assert_called()
    
    async def test_disconnect_during_broadcast(self, ws_manager: WebSocketManager):
        """Test disconnection during broadcast."""
        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)
        game_id = "test-game"
        
        await ws_manager.connect(mock_ws1, game_id)
        await ws_manager.connect(mock_ws2, game_id)
        
        # Simulate disconnect during broadcast
        async def delayed_disconnect():
            await asyncio.sleep(0.01)
            await ws_manager.disconnect(mock_ws2, game_id)
        
        # Start disconnect and broadcast concurrently
        await asyncio.gather(
            delayed_disconnect(),
            ws_manager.broadcast_game_created(game_id)
        )
        
        # Should handle gracefully
        assert mock_ws1 in ws_manager.active_connections.get(game_id, set())
        assert mock_ws2 not in ws_manager.active_connections.get(game_id, set())