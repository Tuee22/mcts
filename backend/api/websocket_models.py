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
    machine_settings: dict[str, Union[str, int]] = {}


class ConnectMessage(BaseModel):
    """WebSocket connect message."""

    type: Literal["connect"]


# Union type for all possible incoming WebSocket messages
WebSocketMessage = Union[PingMessage, MoveMessage, CreateGameMessage, ConnectMessage]

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
    else:
        raise ValueError(f"Unknown message type: {message_type}")
