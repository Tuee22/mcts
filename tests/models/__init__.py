"""Test models for type-safe JSON parsing."""

from tests.models.response_models import (
    ErrorResponse,
    GameResponse,
    HealthResponse,
    TestWebSocketMessage,
    WebSocketConnectMessage,
    WebSocketGameCreatedMessage,
    WebSocketGameEndedMessage,
    WebSocketGameStateMessage,
    WebSocketPongMessage,
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
