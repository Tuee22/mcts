"""
API test helpers for consistent testing across all test suites.

Provides utilities for testing the new REST API + WebSocket architecture
that was created during the backend refactoring.
"""

import asyncio
import json
from typing import Dict, List, Optional, Callable, Union, TypedDict, Protocol
from unittest.mock import AsyncMock, MagicMock
import httpx

from tests.shared.fixtures_factory import TestFixturesFactory


class MockResponseDict(TypedDict):
    """Mock response dictionary type."""

    response: Dict[str, object]
    status_code: int


class RequestHistoryDict(TypedDict):
    """Request history dictionary type."""

    method: str
    url: str
    kwargs: Dict[str, object]


class MockAPIClient:
    """Mock API client that simulates REST API calls for testing."""

    def __init__(self) -> None:
        self.responses: Dict[str, MockResponseDict] = {}
        self.request_history: List[RequestHistoryDict] = []

    def set_response(
        self, method: str, url: str, response: Dict[str, object], status_code: int = 200
    ) -> None:
        """Set a mock response for a specific endpoint."""
        key = f"{method.upper()} {url}"
        self.responses[key] = {"response": response, "status_code": status_code}

    async def request(
        self, method: str, url: str, **kwargs: object
    ) -> Dict[str, object]:
        """Mock request method that returns predefined responses."""
        key = f"{method.upper()} {url}"
        self.request_history.append({"method": method, "url": url, "kwargs": kwargs})

        if key in self.responses:
            mock_response = self.responses[key]
            if mock_response["status_code"] >= 400:
                raise httpx.HTTPError(f"HTTP {mock_response['status_code']}")
            return mock_response["response"]

        # Default response for unmocked endpoints
        return {"error": f"Unmocked endpoint: {key}"}

    def get_request_history(self) -> List[RequestHistoryDict]:
        """Get history of all requests made."""
        return self.request_history.copy()

    def clear_history(self) -> None:
        """Clear request history."""
        self.request_history.clear()


class MockWebSocketClient:
    """Mock WebSocket client for testing WebSocket functionality."""

    def __init__(self) -> None:
        self.connected = False
        self.messages_sent: List[str] = []
        self.message_handlers: Dict[str, Callable[[Dict[str, object]], None]] = {}
        self.connection_handlers: List[Callable[[str], None]] = []

    def connect(self) -> None:
        """Simulate WebSocket connection."""
        self.connected = True
        for handler in self.connection_handlers:
            handler("connected")

    def disconnect(self) -> None:
        """Simulate WebSocket disconnection."""
        self.connected = False
        for handler in self.connection_handlers:
            handler("disconnected")

    def send(self, message: Union[str, Dict[str, object]]) -> None:
        """Simulate sending a WebSocket message."""
        if not self.connected:
            raise Exception("WebSocket not connected")

        if isinstance(message, dict):
            message = json.dumps(message)

        self.messages_sent.append(message)

        # Simulate message handling if handler is registered
        try:
            message_obj = json.loads(message) if isinstance(message, str) else message
            message_type = message_obj.get("type")
            if message_type in self.message_handlers:
                self.message_handlers[message_type](message_obj)
        except (json.JSONDecodeError, KeyError):
            pass

    def on_message(
        self, message_type: str, handler: Callable[[Dict[str, object]], None]
    ) -> None:
        """Register a handler for a specific message type."""
        self.message_handlers[message_type] = handler

    def on_connection(self, handler: Callable[[str], None]) -> None:
        """Register a handler for connection events."""
        self.connection_handlers.append(handler)

    def simulate_message_received(self, message: Dict[str, object]) -> None:
        """Simulate receiving a message from the server."""
        message_type = message.get("type")
        if isinstance(message_type, str) and message_type in self.message_handlers:
            self.message_handlers[message_type](message)

    def get_sent_messages(self) -> List[str]:
        """Get all messages that were sent."""
        return self.messages_sent.copy()

    def clear_sent_messages(self) -> None:
        """Clear sent message history."""
        self.messages_sent.clear()


class APITestValidator:
    """Validator for API responses and WebSocket messages."""

    @staticmethod
    def validate_game_response(response: Dict[str, object]) -> bool:
        """Validate that a response matches GameResponse schema."""
        required_fields = [
            "game_id",
            "status",
            "player1",
            "player2",
            "current_turn",
            "move_count",
            "board_display",
        ]

        for field in required_fields:
            if field not in response:
                return False

        # Validate nested player objects
        for player_field in ["player1", "player2"]:
            player = response.get(player_field, {})
            if not isinstance(player, dict) or "id" not in player:
                return False

        return True

    @staticmethod
    def validate_move_response(response: Dict[str, object]) -> bool:
        """Validate that a response matches MoveResponse schema."""
        if "move" not in response or "game_state" not in response:
            return False

        move = response["move"]
        if not isinstance(move, dict):
            return False

        required_move_fields = ["player_id", "action", "move_number"]

        for field in required_move_fields:
            if field not in move:
                return False

        game_state = response["game_state"]
        if not isinstance(game_state, dict):
            return False
        return APITestValidator.validate_game_response(dict(game_state))

    @staticmethod
    def validate_websocket_message(
        message: Dict[str, object], expected_type: str
    ) -> bool:
        """Validate WebSocket message format."""
        if message.get("type") != expected_type:
            return False

        # Additional validation based on message type
        if expected_type == "game_state" and "game_state" not in message:
            return False

        return True


class TestScenarioRunner:
    """Helper for running common test scenarios."""

    def __init__(self, api_client: MockAPIClient, ws_client: MockWebSocketClient):
        self.api = api_client
        self.ws = ws_client

    async def run_game_creation_scenario(
        self, game_settings: Dict[str, object], expected_game_id: str = "test-game-123"
    ) -> Dict[str, object]:
        """Run a complete game creation scenario."""
        # Set up expected API response

        game_response = TestFixturesFactory.create_game_response(
            game_id=expected_game_id
        )
        self.api.set_response("POST", "/games", dict(game_response))

        # Connect WebSocket
        self.ws.connect()

        # Create game via REST API
        response = await self.api.request("POST", "/games", json=game_settings)

        # Validate response
        assert APITestValidator.validate_game_response(response)
        assert response["game_id"] == expected_game_id

        return response

    async def run_move_making_scenario(
        self, game_id: str, player_id: str, action: str
    ) -> Dict[str, object]:
        """Run a complete move making scenario."""

        move_response = TestFixturesFactory.create_move_response(
            player_id=player_id, action=action
        )
        self.api.set_response("POST", f"/games/{game_id}/moves", dict(move_response))

        # Make move via REST API
        move_data = {"player_id": player_id, "action": action}
        response = await self.api.request(
            "POST", f"/games/{game_id}/moves", json=move_data
        )

        # Validate response
        assert APITestValidator.validate_move_response(response)

        return response


class TestEnvironmentDict(TypedDict):
    """Test environment dictionary type."""

    api_client: MockAPIClient
    ws_client: MockWebSocketClient
    scenario_runner: TestScenarioRunner
    validator: APITestValidator


class AsyncTestFunc(Protocol):
    """Protocol for async test functions."""

    def __call__(
        self, *args: object, test_env: TestEnvironmentDict, **kwargs: object
    ) -> object:
        ...


class DecoratedTestFunc(Protocol):
    """Protocol for decorated test functions."""

    def __call__(self, *args: object, **kwargs: object) -> object:
        ...


def create_test_environment() -> TestEnvironmentDict:
    """Create a complete test environment with mocked APIs."""
    api_client = MockAPIClient()
    ws_client = MockWebSocketClient()
    scenario_runner = TestScenarioRunner(api_client, ws_client)

    return {
        "api_client": api_client,
        "ws_client": ws_client,
        "scenario_runner": scenario_runner,
        "validator": APITestValidator(),
    }


# Decorators for common test setups
def with_mock_api(func: AsyncTestFunc) -> DecoratedTestFunc:
    """Decorator to provide a mock API client to test functions."""

    async def wrapper(*args: object, **kwargs: object) -> object:
        test_env = create_test_environment()
        return func(*args, test_env=test_env, **kwargs)

    return wrapper


def with_game_setup(
    game_id: str = "test-game",
) -> Callable[[AsyncTestFunc], DecoratedTestFunc]:
    """Decorator to set up a game before running a test."""

    def decorator(func: AsyncTestFunc) -> DecoratedTestFunc:
        async def wrapper(*args: object, **kwargs: object) -> object:
            test_env = create_test_environment()

            # Set up game creation response

            game_response = TestFixturesFactory.create_game_response(game_id=game_id)
            test_env["api_client"].set_response("POST", "/games", dict(game_response))
            test_env["api_client"].set_response(
                "GET", f"/games/{game_id}", dict(game_response)
            )

            # Create the game
            await test_env["scenario_runner"].run_game_creation_scenario({}, game_id)

            return func(*args, test_env=test_env, **kwargs)

        return wrapper

    return decorator
