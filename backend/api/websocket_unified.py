"""
Unified WebSocket message system for Corridors game API.

This module consolidates all WebSocket communication into a single endpoint
with message-based routing and proper request/response correlation.
"""

import asyncio
import json
import logging
import uuid
from typing import Annotated, Dict, List, Optional, Set, Union, TypedDict
from datetime import datetime
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# TypedDict classes for message data payloads
class PingData(TypedDict, total=False):
    """Data for ping messages."""

    pass


class JoinGameData(TypedDict):
    """Data for join game messages."""

    game_id: str


class LeaveGameData(TypedDict):
    """Data for leave game messages."""

    game_id: str


class CreateGameData(TypedDict, total=False):
    """Data for create game messages."""

    player1_name: Optional[str]
    player2_name: Optional[str]
    settings: Optional[Dict[str, Union[str, int, float, bool]]]


class MakeMoveData(TypedDict):
    """Data for make move messages."""

    game_id: str
    action: str


class GetLegalMovesData(TypedDict):
    """Data for get legal moves messages."""

    game_id: str


class GetBoardStateData(TypedDict):
    """Data for get board state messages."""

    game_id: str


class ConnectData(TypedDict):
    """Data for connect messages."""

    connection_id: str


class PlayerJoinedData(TypedDict):
    """Data for player joined notifications."""

    game_id: str
    connection_id: str
    user_id: Optional[str]
    player_count: int


class PlayerLeftData(TypedDict):
    """Data for player left notifications."""

    game_id: str
    connection_id: str
    user_id: Optional[str]
    player_count: int


class ErrorData(TypedDict):
    """Data for error messages."""

    message: str


# Union type for all possible message data types
MessageData = Union[
    PingData,
    JoinGameData,
    LeaveGameData,
    CreateGameData,
    MakeMoveData,
    GetLegalMovesData,
    GetBoardStateData,
    ConnectData,
    PlayerJoinedData,
    PlayerLeftData,
    ErrorData,
    Dict[str, Union[str, int, float, bool]],  # Generic fallback
    str,  # Allow string data for ping messages
    int,  # Allow numeric data
    float,  # Allow float data
    bool,  # Allow boolean data
    None,  # Allow None data
]


class MessageType(str, Enum):
    """WebSocket message types."""

    # Connection management
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    PING = "ping"
    PONG = "pong"

    # Game management
    CREATE_GAME = "create_game"
    JOIN_GAME = "join_game"
    LEAVE_GAME = "leave_game"
    LIST_GAMES = "list_games"

    # Game actions
    MAKE_MOVE = "make_move"
    GET_LEGAL_MOVES = "get_legal_moves"
    GET_BOARD_STATE = "get_board_state"
    GET_ANALYSIS = "get_analysis"
    GET_HINT = "get_hint"

    # Notifications
    GAME_CREATED = "game_created"
    GAME_UPDATED = "game_updated"
    GAME_ENDED = "game_ended"
    MOVE_MADE = "move_made"
    PLAYER_JOINED = "player_joined"
    PLAYER_LEFT = "player_left"
    ERROR = "error"


class WSMessage(BaseModel):
    """Unified WebSocket message format."""

    id: Annotated[Union[str, int], Field(default_factory=lambda: str(uuid.uuid4()))]
    type: MessageType
    data: Annotated[MessageData, Field(default_factory=dict)]
    error: Optional[str] = None
    timestamp: Annotated[datetime, Field(default_factory=datetime.utcnow)]

    class Config:
        use_enum_values = True


class WSResponse(BaseModel):
    """WebSocket response message."""

    id: Union[str, int]  # Correlates with request ID
    type: MessageType
    data: Annotated[MessageData, Field(default_factory=dict)]
    success: bool = True
    error: Optional[str] = None
    timestamp: Annotated[datetime, Field(default_factory=datetime.utcnow)]

    class Config:
        use_enum_values = True


class ConnectionInfo(BaseModel):
    """Information about a WebSocket connection."""

    connection_id: str
    websocket: WebSocket
    user_id: Optional[str] = None
    game_ids: Annotated[Set[str], Field(default_factory=set)]
    connected_at: Annotated[datetime, Field(default_factory=datetime.utcnow)]
    last_ping: Optional[datetime] = None

    model_config = {"arbitrary_types_allowed": True}


class UnifiedWebSocketManager:
    """
    Unified WebSocket manager that handles all game-related WebSocket communication.

    Features:
    - Single endpoint for all WebSocket communication
    - Message-based routing
    - Request/response correlation
    - Room-based game isolation
    - Connection state management
    - Automatic ping/pong heartbeat
    """

    def __init__(self) -> None:
        # Connection management
        self.connections: Dict[str, ConnectionInfo] = {}
        self.game_rooms: Dict[str, Set[str]] = {}  # game_id -> connection_ids
        self.pending_responses: Dict[str, asyncio.Event] = {}
        self.response_data: Dict[str, WSResponse] = {}

        # Heartbeat management
        self.heartbeat_task: Optional[asyncio.Task[None]] = None
        self.heartbeat_interval = 30  # seconds

        self._lock = asyncio.Lock()

    async def start_heartbeat(self) -> None:
        """Start the heartbeat task."""
        if self.heartbeat_task is None:
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def stop_heartbeat(self) -> None:
        """Stop the heartbeat task."""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
            self.heartbeat_task = None

    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None) -> str:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()

        connection_id = str(uuid.uuid4())

        async with self._lock:
            connection_info = ConnectionInfo(
                connection_id=connection_id, websocket=websocket, user_id=user_id
            )
            self.connections[connection_id] = connection_info

        logger.info(f"WebSocket connected: {connection_id} (user: {user_id})")

        # Send connection confirmation
        await self._send_to_connection(
            connection_id,
            WSResponse(
                id=str(uuid.uuid4()),
                type=MessageType.CONNECT,
                data={"connection_id": connection_id},
            ),
        )

        # Start heartbeat if not already running
        await self.start_heartbeat()

        return connection_id

    async def disconnect(self, connection_id: str) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            connection_info = self.connections.pop(connection_id, None)
            if not connection_info:
                return

            # Leave all game rooms
            for game_id in connection_info.game_ids.copy():
                await self._leave_game_room(connection_id, game_id)

        logger.info(f"WebSocket disconnected: {connection_id}")

    async def join_game_room(self, connection_id: str, game_id: str) -> None:
        """Add connection to a game room."""
        async with self._lock:
            connection_info = self.connections.get(connection_id)
            if not connection_info:
                return

            if game_id not in self.game_rooms:
                self.game_rooms[game_id] = set()

            self.game_rooms[game_id].add(connection_id)
            connection_info.game_ids.add(game_id)

        # Notify other players in the room
        await self.broadcast_to_game(
            game_id,
            WSMessage(
                type=MessageType.PLAYER_JOINED,
                data={
                    "game_id": game_id,
                    "connection_id": connection_id,
                    "user_id": connection_info.user_id,
                    "player_count": len(self.game_rooms[game_id]),
                },
            ),
            exclude_connection=connection_id,
        )

        logger.info(f"Connection {connection_id} joined game {game_id}")

    async def _leave_game_room(self, connection_id: str, game_id: str) -> None:
        """Remove connection from a game room (internal method)."""
        if game_id in self.game_rooms:
            self.game_rooms[game_id].discard(connection_id)
            if not self.game_rooms[game_id]:
                del self.game_rooms[game_id]

        connection_info = self.connections.get(connection_id)
        if connection_info:
            connection_info.game_ids.discard(game_id)

            # Notify other players in the room
            if game_id in self.game_rooms:
                await self.broadcast_to_game(
                    game_id,
                    WSMessage(
                        type=MessageType.PLAYER_LEFT,
                        data={
                            "game_id": game_id,
                            "connection_id": connection_id,
                            "user_id": connection_info.user_id,
                            "player_count": len(self.game_rooms.get(game_id, set())),
                        },
                    ),
                )

        logger.info(f"Connection {connection_id} left game {game_id}")

    async def leave_game_room(self, connection_id: str, game_id: str) -> None:
        """Remove connection from a game room (public method)."""
        async with self._lock:
            await self._leave_game_room(connection_id, game_id)

    async def handle_message(
        self, connection_id: str, message_data: Dict[str, Union[str, int, float, bool]]
    ) -> Optional[WSResponse]:
        """
        Handle incoming WebSocket message.
        Returns a response if this is a request-response type message.
        """
        try:
            message = WSMessage.model_validate(message_data)
            logger.debug(f"Received message from {connection_id}: {message.type}")

            # Handle different message types
            if message.type == MessageType.PING:
                return await self._handle_ping(connection_id, message)
            elif message.type == MessageType.JOIN_GAME:
                return await self._handle_join_game(connection_id, message)
            elif message.type == MessageType.LEAVE_GAME:
                return await self._handle_leave_game(connection_id, message)
            elif message.type == MessageType.MAKE_MOVE:
                return await self._handle_make_move(connection_id, message)
            elif message.type == MessageType.GET_LEGAL_MOVES:
                return await self._handle_get_legal_moves(connection_id, message)
            elif message.type == MessageType.GET_BOARD_STATE:
                return await self._handle_get_board_state(connection_id, message)
            elif message.type == MessageType.CREATE_GAME:
                return await self._handle_create_game(connection_id, message)
            elif message.type == MessageType.LIST_GAMES:
                return await self._handle_list_games(connection_id, message)
            else:
                return WSResponse(
                    id=message.id,
                    type=MessageType.ERROR,
                    success=False,
                    error=f"Unsupported message type: {message.type}",
                )

        except Exception as e:
            logger.error(f"Error handling message from {connection_id}: {e}")
            return WSResponse(
                id=message_data.get("id", str(uuid.uuid4())),
                type=MessageType.ERROR,
                success=False,
                error=str(e),
            )

    async def _handle_ping(self, connection_id: str, message: WSMessage) -> WSResponse:
        """Handle ping message."""
        async with self._lock:
            connection_info = self.connections.get(connection_id)
            if connection_info:
                connection_info.last_ping = datetime.utcnow()

        # Echo back any data sent in the ping message
        response_data: Dict[str, Union[str, int, float, bool]] = {
            "timestamp": datetime.utcnow().isoformat()
        }

        # Include any data from the original ping message
        if message.data:
            # Handle large messages by limiting echoed data size
            if isinstance(message.data, dict):
                for key, value in message.data.items():
                    if key != "timestamp":  # Don't override our timestamp
                        # Limit large string values to prevent memory issues
                        if isinstance(value, str) and len(value) > 10000:
                            response_data[key] = value[:1000] + "...[truncated]"
                        else:
                            response_data[key] = value
            else:
                response_data["echo"] = message.data

        return WSResponse(
            id=message.id,
            type=MessageType.PONG,
            data=response_data,
        )

    async def _handle_join_game(
        self, connection_id: str, message: WSMessage
    ) -> WSResponse:
        """Handle join game message."""
        if not isinstance(message.data, dict):
            return WSResponse(
                id=message.id,
                type=MessageType.ERROR,
                success=False,
                error="Invalid message data format",
            )

        game_id = message.data.get("game_id")
        if not game_id or not isinstance(game_id, str):
            return WSResponse(
                id=message.id,
                type=MessageType.ERROR,
                success=False,
                error="game_id is required",
            )

        await self.join_game_room(connection_id, game_id)

        return WSResponse(
            id=message.id,
            type=MessageType.JOIN_GAME,
            data={"game_id": game_id, "success": True},
        )

    async def _handle_leave_game(
        self, connection_id: str, message: WSMessage
    ) -> WSResponse:
        """Handle leave game message."""
        if not isinstance(message.data, dict):
            return WSResponse(
                id=message.id,
                type=MessageType.ERROR,
                success=False,
                error="Invalid message data format",
            )

        game_id = message.data.get("game_id")
        if not game_id or not isinstance(game_id, str):
            return WSResponse(
                id=message.id,
                type=MessageType.ERROR,
                success=False,
                error="game_id is required",
            )

        await self.leave_game_room(connection_id, game_id)

        return WSResponse(
            id=message.id,
            type=MessageType.LEAVE_GAME,
            data={"game_id": game_id, "success": True},
        )

    # Placeholder handlers for game-specific messages
    # These will need to be connected to the GameManager

    async def _handle_make_move(
        self, connection_id: str, message: WSMessage
    ) -> WSResponse:
        """Handle make move message."""
        # TODO: Connect to GameManager
        return WSResponse(
            id=message.id,
            type=MessageType.ERROR,
            success=False,
            error="Not implemented yet",
        )

    async def _handle_get_legal_moves(
        self, connection_id: str, message: WSMessage
    ) -> WSResponse:
        """Handle get legal moves message."""
        # TODO: Connect to GameManager
        return WSResponse(
            id=message.id,
            type=MessageType.ERROR,
            success=False,
            error="Not implemented yet",
        )

    async def _handle_get_board_state(
        self, connection_id: str, message: WSMessage
    ) -> WSResponse:
        """Handle get board state message."""
        # TODO: Connect to GameManager
        return WSResponse(
            id=message.id,
            type=MessageType.ERROR,
            success=False,
            error="Not implemented yet",
        )

    async def _handle_create_game(
        self, connection_id: str, message: WSMessage
    ) -> WSResponse:
        """Handle create game message."""
        # TODO: Connect to GameManager
        return WSResponse(
            id=message.id,
            type=MessageType.ERROR,
            success=False,
            error="Not implemented yet",
        )

    async def _handle_list_games(
        self, connection_id: str, message: WSMessage
    ) -> WSResponse:
        """Handle list games message."""
        # TODO: Connect to GameManager
        return WSResponse(
            id=message.id,
            type=MessageType.ERROR,
            success=False,
            error="Not implemented yet",
        )

    async def broadcast_to_game(
        self, game_id: str, message: WSMessage, exclude_connection: Optional[str] = None
    ) -> None:
        """Broadcast a message to all connections in a game room."""
        connection_ids = self.game_rooms.get(game_id, set()).copy()

        if exclude_connection:
            connection_ids.discard(exclude_connection)

        for connection_id in connection_ids:
            await self._send_to_connection(connection_id, message)

    async def broadcast_to_all(self, message: WSMessage) -> None:
        """Broadcast a message to all connections."""
        connection_ids = list(self.connections.keys())

        for connection_id in connection_ids:
            await self._send_to_connection(connection_id, message)

    async def _send_to_connection(
        self, connection_id: str, message: Union[WSMessage, WSResponse]
    ) -> None:
        """Send a message to a specific connection."""
        connection_info = self.connections.get(connection_id)
        if not connection_info:
            return

        try:
            message_json = json.dumps(message.model_dump(), default=str)
            await connection_info.websocket.send_text(message_json)
        except Exception as e:
            logger.error(f"Failed to send message to {connection_id}: {e}")
            # Connection might be dead, remove it
            await self.disconnect(connection_id)

    async def _heartbeat_loop(self) -> None:
        """Heartbeat loop to maintain connections."""
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)

                # Send ping to all connections
                ping_message = WSMessage(type=MessageType.PING)
                await self.broadcast_to_all(ping_message)

                # Check for stale connections
                now = datetime.utcnow()
                stale_connections = []

                async with self._lock:
                    for connection_id, connection_info in self.connections.items():
                        if connection_info.last_ping:
                            time_since_ping = (
                                now - connection_info.last_ping
                            ).total_seconds()
                            if (
                                time_since_ping > self.heartbeat_interval * 3
                            ):  # 3x interval threshold
                                stale_connections.append(connection_id)

                # Disconnect stale connections
                for connection_id in stale_connections:
                    logger.warning(f"Disconnecting stale connection: {connection_id}")
                    await self.disconnect(connection_id)

        except asyncio.CancelledError:
            logger.info("Heartbeat loop cancelled")

    async def get_connection_count(self) -> int:
        """Get the total number of active connections."""
        return len(self.connections)

    async def get_game_connection_count(self, game_id: str) -> int:
        """Get the number of connections in a specific game."""
        return len(self.game_rooms.get(game_id, set()))

    async def cleanup(self) -> None:
        """Clean up all connections and stop background tasks."""
        await self.stop_heartbeat()

        # Disconnect all connections
        connection_ids = list(self.connections.keys())
        for connection_id in connection_ids:
            await self.disconnect(connection_id)

        self.connections.clear()
        self.game_rooms.clear()


# Global instance
unified_ws_manager = UnifiedWebSocketManager()
