"""Test models for type-safe JSON parsing."""

from .response_models import (
    HealthResponse,
    ErrorResponse,
    GameResponse,
    TestWebSocketMessage,
    WebSocketConnectMessage,
    WebSocketPongMessage,
    WebSocketGameStateMessage,
    WebSocketGameCreatedMessage,
    WebSocketGameEndedMessage,
    parse_test_websocket_message,
)

__all__ = [
    "HealthResponse",
    "ErrorResponse",
    "GameResponse",
    "TestWebSocketMessage",
    "WebSocketConnectMessage",
    "WebSocketPongMessage",
    "WebSocketGameStateMessage",
    "WebSocketGameCreatedMessage",
    "WebSocketGameEndedMessage",
    "parse_test_websocket_message",
]
