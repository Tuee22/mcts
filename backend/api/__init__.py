"""
Corridors Game API

A FastAPI-based REST API for the Corridors board game with MCTS AI support.
"""

from .game_manager import GameManager
from .models import (
    GameCreateRequest,
    GameMode,
    GameResponse,
    GameStatus,
    MoveRequest,
    MoveResponse,
    PlayerType,
)
from .server import app
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
