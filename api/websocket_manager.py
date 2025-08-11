import asyncio
import logging
from typing import Dict, List, Set
from fastapi import WebSocket
import json

from .models import MoveResponse, GameResponse, WebSocketMessage
from typing import Optional

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time game updates."""
    
    def __init__(self):
        # game_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # WebSocket -> game_id mapping
        self.connection_games: Dict[WebSocket, str] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, game_id: str):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        
        async with self._lock:
            if game_id not in self.active_connections:
                self.active_connections[game_id] = set()
            
            self.active_connections[game_id].add(websocket)
            self.connection_games[websocket] = game_id
            
            logger.info(f"WebSocket connected to game {game_id}")
            
            # Notify other clients
            await self._broadcast_to_game(
                game_id,
                {
                    "type": "player_connected",
                    "data": {
                        "game_id": game_id,
                        "connection_count": len(self.active_connections[game_id])
                    }
                },
                exclude=websocket
            )
    
    async def disconnect(self, websocket: WebSocket, game_id: str):
        """Remove a WebSocket connection."""
        async with self._lock:
            if game_id in self.active_connections:
                self.active_connections[game_id].discard(websocket)
                
                if not self.active_connections[game_id]:
                    del self.active_connections[game_id]
            
            if websocket in self.connection_games:
                del self.connection_games[websocket]
            
            logger.info(f"WebSocket disconnected from game {game_id}")
            
            # Notify remaining clients
            if game_id in self.active_connections:
                await self._broadcast_to_game(
                    game_id,
                    {
                        "type": "player_disconnected",
                        "data": {
                            "game_id": game_id,
                            "connection_count": len(self.active_connections[game_id])
                        }
                    }
                )
    
    async def broadcast_move(self, game_id: str, move_response: MoveResponse):
        """Broadcast a move to all connected clients for a game."""
        message = {
            "type": "move",
            "data": {
                "game_id": game_id,
                "move": {
                    "player_id": move_response.move.player_id,
                    "action": move_response.move.action,
                    "move_number": move_response.move.move_number,
                    "evaluation": move_response.move.evaluation,
                    "timestamp": move_response.move.timestamp.isoformat()
                },
                "game_status": move_response.game_status,
                "next_turn": move_response.next_turn,
                "board_display": move_response.board_display,
                "winner": move_response.winner
            }
        }
        
        await self._broadcast_to_game(game_id, message)
    
    async def broadcast_game_state(self, game_id: str, game_response: GameResponse):
        """Broadcast updated game state to all connected clients."""
        message = {
            "type": "game_state",
            "data": game_response.dict()
        }
        
        await self._broadcast_to_game(game_id, message)
    
    async def broadcast_game_created(self, game_id: str):
        """Broadcast that a new game has been created."""
        message = {
            "type": "game_created",
            "data": {"game_id": game_id}
        }
        
        # Broadcast to all connections (for lobby updates)
        await self._broadcast_to_all(message)
    
    async def broadcast_game_ended(
        self,
        game_id: str,
        reason: str,
        winner: Optional[int] = None
    ):
        """Broadcast that a game has ended."""
        message = {
            "type": "game_ended",
            "data": {
                "game_id": game_id,
                "reason": reason,
                "winner": winner
            }
        }
        
        await self._broadcast_to_game(game_id, message)
    
    async def send_to_player(
        self,
        game_id: str,
        player_id: str,
        message: Dict
    ):
        """Send a message to a specific player (if connected)."""
        # This would require tracking player_id -> WebSocket mapping
        # For now, broadcast to all in game
        await self._broadcast_to_game(game_id, message)
    
    async def _broadcast_to_game(
        self,
        game_id: str,
        message: Dict,
        exclude: Optional[WebSocket] = None
    ):
        """Broadcast a message to all connections for a specific game."""
        if game_id not in self.active_connections:
            return
        
        # Create tasks for all sends
        tasks = []
        dead_connections = []
        
        for connection in self.active_connections[game_id]:
            if connection != exclude:
                tasks.append(self._send_json_safe(connection, message, dead_connections))
        
        # Send all messages concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Clean up dead connections
        for conn in dead_connections:
            await self.disconnect(conn, game_id)
    
    async def _broadcast_to_all(self, message: Dict):
        """Broadcast a message to all connected clients."""
        all_connections = set()
        for connections in self.active_connections.values():
            all_connections.update(connections)
        
        tasks = []
        dead_connections = []
        
        for connection in all_connections:
            tasks.append(self._send_json_safe(connection, message, dead_connections))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Clean up dead connections
        for conn in dead_connections:
            if conn in self.connection_games:
                game_id = self.connection_games[conn]
                await self.disconnect(conn, game_id)
    
    async def _send_json_safe(
        self,
        websocket: WebSocket,
        message: Dict,
        dead_connections: List[WebSocket]
    ):
        """Safely send JSON message to a WebSocket."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send message to WebSocket: {e}")
            dead_connections.append(websocket)
    
    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return sum(len(conns) for conns in self.active_connections.values())
    
    def get_game_connection_count(self, game_id: str) -> int:
        """Get number of connections for a specific game."""
        return len(self.active_connections.get(game_id, set()))
    
    async def disconnect_all(self):
        """Disconnect all WebSocket connections (for shutdown)."""
        all_connections = []
        for connections in self.active_connections.values():
            all_connections.extend(connections)
        
        for conn in all_connections:
            try:
                await conn.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
        
        self.active_connections.clear()
        self.connection_games.clear()