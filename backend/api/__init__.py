"""
Corridors Game API

A FastAPI-based REST API for the Corridors board game with MCTS AI support.
"""

from .server import app
from .models import (
    GameCreateRequest,
    GameResponse,
    MoveRequest,
    MoveResponse,
    PlayerType,
    GameStatus,
    GameMode,
)
from .game_manager import GameManager
from .websocket_manager import WebSocketManager

__version__ = "1.0.0"

__all__ = [
    "app",
    "GameManager",
    "WebSocketManager",
    "GameCreateRequest",
    "GameResponse",
    "MoveRequest",
    "MoveResponse",
    "PlayerType",
    "GameStatus",
    "GameMode",
]
