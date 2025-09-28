"""
Frontend-Backend Integration Tests

Tests the integration between frontend and backend that reproduce E2E race conditions.
These tests simulate frontend behavior while monitoring backend state changes.
"""

import asyncio
import json
import pytest
import httpx
import websockets
from typing import Dict, List, Optional, Tuple, Union, AsyncGenerator
from typing_extensions import TypedDict
from unittest.mock import AsyncMock, patch

from backend.api.models import GameSettings, MCTSSettings


class GameConfig(TypedDict):
    player1_type: str
    player2_type: str
    player1_name: str
    player2_name: str
    settings: Dict[str, Dict[str, Union[float, int]]]


class GameData(TypedDict):
    game_id: str


class GameState(TypedDict):
    game_id: str
    status: str


class Operation(TypedDict):
    operation_type: str
    data: Union[GameData, GameState]


class IntegratedTestSession:
    """Test session combining HTTP API and WebSocket connections."""

    def __init__(self, base_url: str, ws_url: str) -> None:
        self.base_url = base_url
        self.ws_url = ws_url
        self.http_client: Optional[httpx.AsyncClient] = None
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.game_id: Optional[str] = None

    async def start(self) -> None:
        """Start HTTP client and WebSocket connection."""
        self.http_client = httpx.AsyncClient(base_url=self.base_url)
        self.websocket = await websockets.connect(self.ws_url)
        self.connected = True

    async def stop(self) -> None:
        """Stop HTTP client and WebSocket connection."""
        if self.http_client:
            await self.http_client.aclose()
        if self.websocket:
            await self.websocket.close()
        self.connected = False

    async def create_game_via_http(self, game_config: GameConfig) -> GameData:
        """Create game via HTTP API."""
        if not self.http_client:
            raise RuntimeError("HTTP client not started")

        response = await self.http_client.post("/games", json=game_config)
        response.raise_for_status()
        game_data_raw = response.json()
        if not isinstance(game_data_raw, dict) or "game_id" not in game_data_raw:
            raise RuntimeError("Invalid response format")
        game_data: GameData = {"game_id": game_data_raw["game_id"]}
        self.game_id = game_data["game_id"]
        return game_data

    async def create_game_via_websocket(self, game_config: GameConfig) -> GameData:
        """Create game via WebSocket."""
        if not self.websocket:
            raise RuntimeError("WebSocket not connected")

        await self.websocket.send(
            json.dumps({"type": "create_game", "data": game_config})
        )

        # Wait for game creation response
        while True:
            message = await self.websocket.recv()
            data = json.loads(message)
            if data["type"] == "game_created":
                game_id = data["data"]["game_id"]
                self.game_id = game_id
                return {"game_id": game_id}

    async def get_game_state_http(self) -> GameState:
        """Get game state via HTTP API."""
        if not self.http_client or not self.game_id:
            raise RuntimeError("HTTP client not started or no game")

        response = await self.http_client.get(f"/games/{self.game_id}")
        response.raise_for_status()
        state_data = response.json()
        if (
            not isinstance(state_data, dict)
            or "game_id" not in state_data
            or "status" not in state_data
        ):
            raise RuntimeError("Invalid response format")
        return {"game_id": state_data["game_id"], "status": state_data["status"]}

    async def get_game_state_websocket(self) -> GameState:
        """Get game state via WebSocket."""
        if not self.websocket or not self.game_id:
            raise RuntimeError("WebSocket not connected or no game")

        await self.websocket.send(
            json.dumps({"type": "get_game_state", "data": {"game_id": self.game_id}})
        )

        # Wait for game state response
        while True:
            message = await self.websocket.recv()
            data = json.loads(message)
            if data["type"] == "game_state":
                state_data = data["data"]
                return {
                    "game_id": state_data["game_id"],
                    "status": state_data["status"],
                }

    async def simulate_frontend_race_condition(
        self,
    ) -> List[Tuple[str, Union[GameData, GameState]]]:
        """Simulate the race condition that causes E2E failures."""
        # Simulate rapid frontend operations
        operations: List[Tuple[str, Union[GameData, GameState]]] = []

        # 1. Create game via HTTP (frontend settings form)
        game_config: GameConfig = {
            "player1_type": "human",
            "player2_type": "human",
            "player1_name": "Player 1",
            "player2_name": "Player 2",
            "settings": {
                "mcts_settings": {
                    "c": 1.414,
                    "min_simulations": 100,
                    "max_simulations": 1000,
                }
            },
        }

        # Create game
        game_data = await self.create_game_via_http(game_config)
        operations.append(("game_created", game_data))

        # 2. Rapid state requests (frontend updating UI)
        for i in range(5):
            http_state = await self.get_game_state_http()
            operations.append(("http_state", http_state))

            ws_state = await self.get_game_state_websocket()
            operations.append(("ws_state", ws_state))

            await asyncio.sleep(0.01)  # Simulate rapid frontend updates

        return operations


@pytest.fixture
async def integrated_session() -> AsyncGenerator[IntegratedTestSession, None]:
    """Create an integrated test session."""
    session = IntegratedTestSession(
        base_url="http://localhost:8000", ws_url="ws://localhost:8000/ws"
    )
    await session.start()
    yield session
    await session.stop()


@pytest.mark.integration
@pytest.mark.slow
class TestFrontendBackendIntegration:
    """Test integration scenarios that reproduce E2E failures."""

    @pytest.mark.asyncio
    async def test_settings_panel_race_condition(
        self, integrated_session: IntegratedTestSession
    ) -> None:
        """Test the Settings panel race condition that causes E2E failures."""

        # Simulate the specific sequence that causes Settings button to disappear
        operations = await integrated_session.simulate_frontend_race_condition()

        # Verify all operations completed successfully
        assert len(operations) > 0

        # Check game creation
        game_created_op = next(op for op in operations if op[0] == "game_created")
        game_created_data = game_created_op[1]
        assert isinstance(game_created_data, dict) and "game_id" in game_created_data

        # Check state consistency between HTTP and WebSocket
        http_states = [op[1] for op in operations if op[0] == "http_state"]
        ws_states = [op[1] for op in operations if op[0] == "ws_state"]

        assert len(http_states) > 0
        assert len(ws_states) > 0

        # All states should reference the same game
        for state in http_states + ws_states:
            assert state["game_id"] == integrated_session.game_id

    @pytest.mark.asyncio
    async def test_rapid_game_creation_and_state_queries(
        self, integrated_session: IntegratedTestSession
    ) -> None:
        """Test rapid game creation followed by immediate state queries."""

        game_config: GameConfig = {
            "player1_type": "human",
            "player2_type": "human",
            "player1_name": "Player 1",
            "player2_name": "Player 2",
            "settings": {
                "mcts_settings": {
                    "c": 1.414,
                    "min_simulations": 100,
                    "max_simulations": 1000,
                }
            },
        }

        # Create game and immediately start querying state
        game_data = await integrated_session.create_game_via_http(game_config)
        game_id = game_data["game_id"]

        # Rapid state queries (simulates frontend updating UI immediately)
        query_tasks = []
        for i in range(10):
            # Alternate between HTTP and WebSocket queries
            if i % 2 == 0:
                task = integrated_session.get_game_state_http()
            else:
                task = integrated_session.get_game_state_websocket()
            query_tasks.append(task)

        # Execute all queries concurrently
        states = await asyncio.gather(*query_tasks, return_exceptions=True)

        # Most queries should succeed
        successful_states = [s for s in states if isinstance(s, dict)]
        assert len(successful_states) >= len(query_tasks) // 2

        # All successful states should be for the same game
        for state in successful_states:
            assert state["game_id"] == game_id

    @pytest.mark.asyncio
    async def test_connection_instability_during_game_operations(
        self, integrated_session: IntegratedTestSession
    ) -> None:
        """Test connection instability during game operations."""

        # Create game
        game_config: GameConfig = {
            "player1_type": "human",
            "player2_type": "human",
            "player1_name": "Player 1",
            "player2_name": "Player 2",
            "settings": {
                "mcts_settings": {
                    "c": 1.414,
                    "min_simulations": 100,
                    "max_simulations": 1000,
                }
            },
        }

        game_data = await integrated_session.create_game_via_http(game_config)

        # Start WebSocket connection monitoring
        monitoring_task = asyncio.create_task(
            self._monitor_websocket_connection(integrated_session)
        )

        # Simulate connection instability
        await integrated_session.stop()
        await asyncio.sleep(0.1)
        await integrated_session.start()

        # Verify game state is still accessible
        state = await integrated_session.get_game_state_http()
        assert state["game_id"] == game_data["game_id"]

        # Stop monitoring
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass

    async def _monitor_websocket_connection(
        self, session: IntegratedTestSession
    ) -> None:
        """Monitor WebSocket connection for messages."""
        if not session.websocket:
            return

        try:
            while True:
                message = await asyncio.wait_for(session.websocket.recv(), timeout=0.1)
                # Process any incoming messages
                data = json.loads(message)
                # Log message for debugging if needed
        except (asyncio.TimeoutError, websockets.ConnectionClosed):
            pass

    @pytest.mark.asyncio
    async def test_mixed_api_usage_patterns(
        self, integrated_session: IntegratedTestSession
    ) -> None:
        """Test mixed usage of HTTP and WebSocket APIs."""

        # Create game via WebSocket
        game_config: GameConfig = {
            "player1_type": "human",
            "player2_type": "human",
            "player1_name": "WS Player 1",
            "player2_name": "WS Player 2",
            "settings": {
                "mcts_settings": {
                    "c": 1.414,
                    "min_simulations": 100,
                    "max_simulations": 1000,
                }
            },
        }

        game_data = await integrated_session.create_game_via_websocket(game_config)

        # Query state via HTTP
        http_state = await integrated_session.get_game_state_http()
        assert http_state["game_id"] == game_data["game_id"]

        # Query state via WebSocket
        ws_state = await integrated_session.get_game_state_websocket()
        assert ws_state["game_id"] == game_data["game_id"]

        # States should be consistent
        assert http_state["game_id"] == ws_state["game_id"]
        assert http_state["status"] == ws_state["status"]

    @pytest.mark.asyncio
    async def test_rapid_protocol_switching(
        self, integrated_session: IntegratedTestSession
    ) -> None:
        """Test rapid switching between HTTP and WebSocket protocols."""

        game_config: GameConfig = {
            "player1_type": "human",
            "player2_type": "human",
            "player1_name": "Switch Player 1",
            "player2_name": "Switch Player 2",
            "settings": {
                "mcts_settings": {
                    "c": 1.414,
                    "min_simulations": 100,
                    "max_simulations": 1000,
                }
            },
        }

        # Create game via HTTP
        game_data = await integrated_session.create_game_via_http(game_config)

        # Rapid protocol switching for state queries
        for i in range(20):
            if i % 2 == 0:
                state = await integrated_session.get_game_state_http()
            else:
                state = await integrated_session.get_game_state_websocket()

            assert state["game_id"] == game_data["game_id"]
            await asyncio.sleep(0.005)  # Very rapid switching

    @pytest.mark.asyncio
    async def test_concurrent_client_simulation(self) -> None:
        """Test multiple concurrent clients to simulate real frontend load."""

        sessions = []
        try:
            # Create multiple sessions (simulate multiple browser tabs)
            for i in range(3):
                session = IntegratedTestSession(
                    base_url="http://localhost:8000", ws_url="ws://localhost:8000/ws"
                )
                await session.start()
                sessions.append(session)

            # Each session creates a game and performs operations
            async def session_operations(
                session: IntegratedTestSession, session_id: int
            ) -> None:
                game_config: GameConfig = {
                    "player1_type": "human",
                    "player2_type": "human",
                    "player1_name": f"Player 1 Session {session_id}",
                    "player2_name": f"Player 2 Session {session_id}",
                    "settings": {
                        "mcts_settings": {
                            "c": 1.414,
                            "min_simulations": 100,
                            "max_simulations": 1000,
                        }
                    },
                }

                # Create game
                game_data = await session.create_game_via_http(game_config)

                # Perform rapid state queries
                for j in range(5):
                    await session.get_game_state_http()
                    await session.get_game_state_websocket()
                    await asyncio.sleep(0.01)

            # Run all sessions concurrently
            await asyncio.gather(
                *[session_operations(session, i) for i, session in enumerate(sessions)]
            )

        finally:
            # Clean up all sessions
            for session in sessions:
                await session.stop()


@pytest.mark.integration
@pytest.mark.slow
class TestRaceConditionReproduction:
    """Specific tests to reproduce the exact E2E race conditions."""

    @pytest.mark.asyncio
    async def test_settings_button_disappearance_reproduction(
        self, integrated_session: IntegratedTestSession
    ) -> None:
        """Reproduce the exact sequence that causes Settings button to disappear."""

        # Step 1: Start without game (Settings panel should be visible)
        # This simulates frontend initial state

        # Step 2: Create game rapidly (simulates user clicking start)
        game_config: GameConfig = {
            "player1_type": "human",
            "player2_type": "human",
            "player1_name": "Player 1",
            "player2_name": "Player 2",
            "settings": {
                "mcts_settings": {
                    "c": 1.414,
                    "min_simulations": 100,
                    "max_simulations": 1000,
                }
            },
        }

        # Rapid game creation
        game_data = await integrated_session.create_game_via_http(game_config)

        # Step 3: Immediate state queries (frontend updating UI)
        # This can cause gameId to rapidly change from null -> game_id -> null -> game_id
        state_queries = []
        for i in range(10):
            state_queries.append(integrated_session.get_game_state_http())

        states = await asyncio.gather(*state_queries)

        # Step 4: Verify Settings button would be accessible
        # All states should show consistent game_id
        for state in states:
            assert state["game_id"] == game_data["game_id"]
            # In frontend, this means Settings should show as toggle button

    @pytest.mark.asyncio
    async def test_rapid_gameId_transitions(
        self, integrated_session: IntegratedTestSession
    ) -> None:
        """Test rapid gameId transitions that confuse frontend state."""

        # Create and delete games rapidly
        game_configs: List[GameConfig] = [
            {
                "player1_type": "human",
                "player2_type": "human",
                "player1_name": f"Player 1 Game {i}",
                "player2_name": f"Player 2 Game {i}",
                "settings": {
                    "mcts_settings": {
                        "c": 1.414,
                        "min_simulations": 100,
                        "max_simulations": 1000,
                    }
                },
            }
            for i in range(3)
        ]

        created_games = []
        for config in game_configs:
            game_data = await integrated_session.create_game_via_http(config)
            created_games.append(game_data)

            # Immediately query state
            state = await integrated_session.get_game_state_http()
            assert state["game_id"] == game_data["game_id"]

            # Small delay before next game
            await asyncio.sleep(0.01)

        # Verify all games were created successfully
        assert len(created_games) == len(game_configs)
