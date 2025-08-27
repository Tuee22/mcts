"""Pydantic models for API response validation in tests."""

from typing import Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response model."""

    status: Literal["healthy"]
    active_games: int
    connected_clients: int


class ErrorResponse(BaseModel):
    """Error response model."""

    detail: str


class PlayerInfo(BaseModel):
    """Player information model."""

    id: str
    name: str
    type: str


class GameResponse(BaseModel):
    """Game response model."""

    game_id: str
    status: str
    player1: PlayerInfo
    player2: PlayerInfo
    current_turn: int
    winner: Optional[int] = None
    move_count: Optional[int] = None
    created_at: Optional[str] = None


class GameListData(BaseModel):
    """Game list response data."""

    games: List[GameResponse]
    total: int


class GameListResponse(BaseModel):
    """Game list response wrapper."""

    games: List[GameResponse]
    total: int


class MoveResponseData(BaseModel):
    """Move response data."""

    game_id: str
    player_id: str
    action: str
    valid: bool
    game_over: bool
    winner: Optional[int] = None
    next_player_type: str
    board_state: Optional[str] = None


class BoardStateResponse(BaseModel):
    """Board state response."""

    game_id: str
    board: str
    current_turn: int
    move_count: int


class LegalMovesResponse(BaseModel):
    """Legal moves response."""

    game_id: str
    current_player: int
    legal_moves: List[str]


class WebSocketConnectMessage(BaseModel):
    """WebSocket connect message."""

    type: Literal["connect"]
    message: Optional[str] = None


class WebSocketPongMessage(BaseModel):
    """WebSocket pong message."""

    type: Literal["pong"]


class WebSocketGameStateMessage(BaseModel):
    """WebSocket game state message."""

    type: Literal["game_state"]
    data: Dict[str, Union[str, int, bool]]


class WebSocketGameCreatedMessage(BaseModel):
    """WebSocket game created message."""

    type: Literal["game_created"]
    data: Dict[str, Union[str, int, bool]]


class WebSocketGameEndedMessage(BaseModel):
    """WebSocket game ended message."""

    type: Literal["game_ended"]
    data: Dict[str, Union[str, int, bool]]


# Union type for all possible WebSocket messages in tests
TestWebSocketMessage = Union[
    WebSocketConnectMessage,
    WebSocketPongMessage,
    WebSocketGameStateMessage,
    WebSocketGameCreatedMessage,
    WebSocketGameEndedMessage,
]


def parse_test_websocket_message(data: Dict[str, object]) -> TestWebSocketMessage:
    """Parse a test WebSocket message using the appropriate model based on type."""
    message_type = data.get("type")

    if message_type == "connect":
        return WebSocketConnectMessage.model_validate(data)
    elif message_type == "pong":
        return WebSocketPongMessage.model_validate(data)
    elif message_type == "game_state":
        return WebSocketGameStateMessage.model_validate(data)
    elif message_type == "game_created":
        return WebSocketGameCreatedMessage.model_validate(data)
    elif message_type == "game_ended":
        return WebSocketGameEndedMessage.model_validate(data)
    else:
        raise ValueError(f"Unknown message type: {message_type}")
