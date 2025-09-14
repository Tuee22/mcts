"""Pydantic models for WebSocket message validation."""

from typing import Dict, Literal, Union

from pydantic import BaseModel, Field


class PingMessage(BaseModel):
    """WebSocket ping message."""

    type: Literal["ping"]


class PongMessage(BaseModel):
    """WebSocket pong message."""

    type: Literal["pong"]


class MoveMessage(BaseModel):
    """WebSocket move message."""

    type: Literal["move"]
    game_id: str
    player_id: str
    action: str


class CreateGameMessage(BaseModel):
    """WebSocket create game message."""

    type: Literal["create_game"]
    player1_type: str
    player2_type: str
    player1_name: str
    player2_name: str
    settings: Dict[str, Union[str, int, Dict[str, Union[str, int]]]] = {}
    board_size: int = 9

    # Keep backward compatibility
    machine_settings: Dict[str, Union[str, int]] = {}


class ConnectMessage(BaseModel):
    """WebSocket connect message."""

    type: Literal["connect"]


class JoinGameMessage(BaseModel):
    """WebSocket join game message."""

    type: Literal["join_game"]
    game_id: str


class GetAIMoveMessage(BaseModel):
    """WebSocket get AI move message."""

    type: Literal["get_ai_move"]
    game_id: str


# Union type for all possible incoming WebSocket messages
WebSocketMessage = Union[
    PingMessage,
    MoveMessage,
    CreateGameMessage,
    ConnectMessage,
    JoinGameMessage,
    GetAIMoveMessage,
]

# Union type for all possible outgoing WebSocket messages
WebSocketResponse = Union[PongMessage, ConnectMessage]


def parse_websocket_message(data: Dict[str, object]) -> WebSocketMessage:
    """Parse a WebSocket message using the appropriate model based on type."""
    message_type = data.get("type")

    if message_type == "ping":
        return PingMessage.model_validate(data)
    elif message_type == "move":
        return MoveMessage.model_validate(data)
    elif message_type == "create_game":
        return CreateGameMessage.model_validate(data)
    elif message_type == "connect":
        return ConnectMessage.model_validate(data)
    elif message_type == "join_game":
        return JoinGameMessage.model_validate(data)
    elif message_type == "get_ai_move":
        return GetAIMoveMessage.model_validate(data)
    else:
        raise ValueError(f"Unknown message type: {message_type}")
