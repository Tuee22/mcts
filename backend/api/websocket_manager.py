import asyncio
import json
import logging
from typing import Dict, List, Optional, Set, Union

from fastapi import WebSocket

from backend.api.api_types import (
    GameCreatedData,
    GameCreatedMessage,
    GameEndedData,
    GameEndedMessage,
    GameStateData,
    GameStateMessage,
    MoveBroadcastMessage,
    MoveData,
    MoveMessageData,
    OutgoingWebSocketMessage,
    PlayerConnectedMessage,
    PlayerDisconnectedMessage,
    WebSocketProtocol,
)
from backend.api.models import GameResponse, MoveResponse

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocketProtocol connections for real-time game updates."""

    def __init__(self) -> None:
        # game_id -> set of WebSocketProtocol connections
        self.active_connections: Dict[str, Set[WebSocketProtocol]] = {}
        # WebSocketProtocol -> game_id mapping
        self.connection_games: Dict[WebSocketProtocol, str] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocketProtocol, game_id: str) -> None:
        """Accept and register a new WebSocketProtocol connection."""
        await websocket.accept()

        async with self._lock:
            if game_id not in self.active_connections:
                self.active_connections[game_id] = set()

            self.active_connections[game_id].add(websocket)
            self.connection_games[websocket] = game_id

            logger.info(f"WebSocketProtocol connected to game {game_id}")

            # Notify other clients
            message: PlayerConnectedMessage = {
                "type": "player_connected",
                "data": {
                    "game_id": game_id,
                    "connection_count": len(self.active_connections[game_id]),
                },
            }
            await self._broadcast_to_game(
                game_id,
                message,
                exclude=websocket,
            )

    async def disconnect(self, websocket: WebSocketProtocol, game_id: str) -> None:
        """Remove a WebSocketProtocol connection."""
        async with self._lock:
            if game_id in self.active_connections:
                self.active_connections[game_id].discard(websocket)

                if not self.active_connections[game_id]:
                    del self.active_connections[game_id]

            if websocket in self.connection_games:
                del self.connection_games[websocket]

            logger.info(f"WebSocketProtocol disconnected from game {game_id}")

            # Notify remaining clients
            if game_id in self.active_connections:
                message: PlayerDisconnectedMessage = {
                    "type": "player_disconnected",
                    "data": {
                        "game_id": game_id,
                        "connection_count": len(self.active_connections[game_id]),
                    },
                }
                await self._broadcast_to_game(game_id, message)

    async def broadcast_move(self, game_id: str, move_response: MoveResponse) -> None:
        """Broadcast a move to all connected clients for a game."""
        move_data: MoveData = {
            "player_id": move_response.move.player_id,
            "action": move_response.move.action,
            "move_number": move_response.move.move_number,
            "evaluation": move_response.move.evaluation,
            "timestamp": move_response.move.timestamp.isoformat(),
        }

        message_data: MoveMessageData = {
            "game_id": game_id,
            "move": move_data,
            "game_status": move_response.game_status,
            "next_turn": move_response.next_turn,
            "board_display": move_response.board_display,
            "winner": move_response.winner,
        }

        message: MoveBroadcastMessage = {
            "type": "move",
            "data": message_data,
        }

        await self._broadcast_to_game(game_id, message)

    async def broadcast_game_state(
        self, game_id: str, game_response: GameResponse
    ) -> None:
        """Broadcast updated game state to all connected clients."""
        game_data: GameStateData = {
            "game_id": game_response.game_id,
            "status": game_response.status,
            "player1_id": game_response.player1.id,
            "player2_id": game_response.player2.id,
            "current_turn": game_response.current_turn,
            "winner": game_response.winner,
            "board_display": game_response.board_display,
            "legal_moves": [],  # GameResponse doesn't have legal_moves
            "created_at": game_response.created_at.isoformat(),
        }

        message: GameStateMessage = {"type": "game_state", "data": game_data}

        await self._broadcast_to_game(game_id, message)

    async def broadcast_game_created(self, game_id: str) -> None:
        """Broadcast that a new game has been created."""
        game_created_data: GameCreatedData = {"game_id": game_id}
        message: GameCreatedMessage = {
            "type": "game_created",
            "data": game_created_data,
        }

        # Broadcast to all connections (for lobby updates)
        await self._broadcast_to_all(message)

    async def broadcast_game_ended(
        self, game_id: str, reason: str, winner: Optional[int] = None
    ) -> None:
        """Broadcast that a game has ended."""
        game_ended_data: GameEndedData = {
            "game_id": game_id,
            "winner": winner,
            "game_status": reason,
        }

        message: GameEndedMessage = {
            "type": "game_ended",
            "data": game_ended_data,
        }

        await self._broadcast_to_game(game_id, message)

    async def send_to_player(
        self, game_id: str, player_id: str, message: OutgoingWebSocketMessage
    ) -> None:
        """Send a message to a specific player (if connected)."""
        # This would require tracking player_id -> WebSocketProtocol mapping
        # For now, broadcast to all in game
        await self._broadcast_to_game(game_id, message)

    async def broadcast_to_game(
        self,
        game_id: str,
        message: OutgoingWebSocketMessage,
        exclude: Optional[WebSocketProtocol] = None,
    ) -> None:
        """Public interface to broadcast a message to all connections for a specific game."""
        await self._broadcast_to_game(game_id, message, exclude)

    async def _broadcast_to_game(
        self,
        game_id: str,
        message: OutgoingWebSocketMessage,
        exclude: Optional[WebSocketProtocol] = None,
    ) -> None:
        """Broadcast a message to all connections for a specific game."""
        if game_id not in self.active_connections:
            return

        # Create tasks for all sends using functional approach
        dead_connections: List[WebSocketProtocol] = []
        connections_to_send = [
            conn for conn in self.active_connections[game_id] if conn != exclude
        ]
        tasks = [
            self._send_json_safe(conn, message, dead_connections)
            for conn in connections_to_send
        ]

        # Send all messages concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Clean up dead connections using functional approach
        await asyncio.gather(
            *[self.disconnect(conn, game_id) for conn in dead_connections],
            return_exceptions=True,
        )

    async def _broadcast_to_all(self, message: OutgoingWebSocketMessage) -> None:
        """Broadcast a message to all connected clients."""
        # Use functional approach to gather all connections
        all_connections = set().union(*self.active_connections.values())

        # Create tasks using list comprehension
        dead_connections: List[WebSocketProtocol] = []
        tasks = [
            self._send_json_safe(conn, message, dead_connections)
            for conn in all_connections
        ]

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Clean up dead connections using functional approach
        cleanup_tasks = [
            self.disconnect(conn, self.connection_games[conn])
            for conn in dead_connections
            if conn in self.connection_games
        ]
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

    async def _send_json_safe(
        self,
        websocket: WebSocketProtocol,
        message: OutgoingWebSocketMessage,
        dead_connections: List[WebSocketProtocol],
    ) -> None:
        """Safely send JSON message to a WebSocketProtocol."""
        try:
            # Check if connection is still active before sending
            # FastAPI WebSocket states: 0=DISCONNECTED, 1=CONNECTING, 2=CONNECTED, 3=DISCONNECTING
            if hasattr(websocket, "client_state") and websocket.client_state != 2:
                logger.debug(
                    f"WebSocket not connected (state: {websocket.client_state}), skipping send"
                )
                dead_connections.append(websocket)
                return

            # Convert TypedDict to dict for WebSocketProtocol API compatibility
            message_dict = dict(message)
            await websocket.send_json(message_dict)
        except Exception as e:
            logger.warning(f"Failed to send message to WebSocketProtocol: {e}")
            dead_connections.append(websocket)

    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return sum(len(conns) for conns in self.active_connections.values())

    def get_game_connection_count(self, game_id: str) -> int:
        """Get number of connections for a specific game."""
        return len(self.active_connections.get(game_id, set()))

    async def disconnect_all(self) -> None:
        """Disconnect all WebSocketProtocol connections (for shutdown)."""
        # Use functional approach to flatten connections
        all_connections = [
            conn
            for connections in self.active_connections.values()
            for conn in connections
        ]

        # Process disconnections using functional approach
        async def close_connection_safe(conn: WebSocketProtocol) -> None:
            try:
                await conn.close()
            except Exception as e:
                logger.error(f"Error closing WebSocketProtocol: {e}")

        # Close all connections concurrently
        if all_connections:
            await asyncio.gather(
                *[close_connection_safe(conn) for conn in all_connections],
                return_exceptions=True,
            )

        self.active_connections.clear()
        self.connection_games.clear()
