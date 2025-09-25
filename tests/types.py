"""
Type Definitions for Test Code.

Test-specific type definitions to ensure proper typing in test files.
"""

from typing import Dict, List, Optional, Callable, Protocol, TypedDict, Union, Mapping
from unittest.mock import AsyncMock, MagicMock


# Mock and test data types
class MockWebSocketData(TypedDict, total=False):
    """Mock WebSocket connection data."""

    url: str
    connected: bool
    messages_sent: List[Dict[str, object]]
    messages_received: List[Dict[str, object]]
    connection_events: List[str]
    error_events: List[str]


class MockGameStateData(TypedDict):
    """Mock game state for testing."""

    game_id: str
    board_size: int
    current_player: int
    players: List[Dict[str, Union[str, int]]]
    board: List[List[int]]
    walls: List[Dict[str, Union[int, str]]]
    walls_remaining: List[int]
    legal_moves: List[str]
    move_history: List[Dict[str, Union[str, int, float]]]
    winner: Optional[int]
    status: str


class MockPlayerData(TypedDict):
    """Mock player data for testing."""

    id: str
    name: str
    type: str
    position: Dict[str, int]
    active: bool


class TestGameSettings(TypedDict):
    """Test game settings data."""

    mode: str
    board_size: int
    ai_difficulty: Optional[str]
    ai_time_limit: Optional[int]
    player1_name: Optional[str]
    player2_name: Optional[str]


class TestMessageData(TypedDict, total=False):
    """Test message structure."""

    type: str
    data: Mapping[str, object]
    request_id: Optional[str]
    timestamp: float
    connection_id: Optional[str]


class TestConnectionData(TypedDict):
    """Test connection information."""

    connection_id: str
    user_id: str
    connected: bool
    message_count: int
    error_count: int
    last_ping: Optional[float]
    games: List[str]


class TestEventData(TypedDict):
    """Test event verification data."""

    event_type: str
    expected: bool
    actual: bool
    timestamp: float
    metadata: Dict[str, object]


# State management test types
class StateManagerTestData(TypedDict):
    """State manager test data structure."""

    frontend_state: Dict[str, object]
    backend_state: Dict[str, object]
    sync_events: List[Dict[str, object]]
    conflicts: List[Dict[str, object]]
    snapshots: List[Dict[str, object]]


class ConflictTestData(TypedDict):
    """Conflict detection test data."""

    key: str
    frontend_value: object
    backend_value: object
    expected_conflict: bool
    resolution_strategy: str


class SyncTestData(TypedDict):
    """Synchronization test data."""

    initial_state: Dict[str, object]
    updates: List[Dict[str, object]]
    expected_final_state: Dict[str, object]
    expected_events: List[str]


# Performance test types
class LoadTestData(TypedDict):
    """Load testing data structure."""

    concurrent_connections: int
    messages_per_connection: int
    message_size_bytes: int
    duration_seconds: float
    success_rate: float
    error_rate: float
    average_latency_ms: float


class BenchmarkData(TypedDict):
    """Benchmark test data."""

    operation: str
    iterations: int
    total_time_ms: float
    average_time_ms: float
    min_time_ms: float
    max_time_ms: float
    success_count: int
    error_count: int


# Mock type protocols
class MockWebSocketProtocol(Protocol):
    """Protocol for mock WebSocket objects."""

    async def accept(self) -> None:
        ...

    async def close(self, code: int = 1000) -> None:
        ...

    async def send_text(self, data: str) -> None:
        ...

    async def send_json(self, data: object) -> None:
        ...

    async def receive_text(self) -> str:
        ...

    async def receive_json(self) -> object:
        ...


class MockGameManagerProtocol(Protocol):
    """Protocol for mock game manager objects."""

    async def create_game(self, settings: TestGameSettings) -> str:
        ...

    async def get_game(self, game_id: str) -> Optional[MockGameStateData]:
        ...

    async def make_move(self, game_id: str, player_id: str, move: str) -> bool:
        ...

    async def join_game(self, game_id: str, player_id: str) -> bool:
        ...


class MockConnectionManagerProtocol(Protocol):
    """Protocol for mock connection manager objects."""

    async def connect(
        self, websocket: MockWebSocketProtocol, user_id: Optional[str] = None
    ) -> str:
        ...

    async def disconnect(self, connection_id: str, code: int = 1000) -> None:
        ...

    async def send_message(self, connection_id: str, message: TestMessageData) -> bool:
        ...

    def get_connection_count(self) -> int:
        ...


# Test fixture types
TestFixtureFunc = Callable[
    [], Union[object, MockWebSocketProtocol, MockGameManagerProtocol]
]
AsyncTestFixtureFunc = Callable[
    [], Union[object, MockWebSocketProtocol, MockGameManagerProtocol]
]

# Mock factory types
MockFactory = Callable[[Optional[Dict[str, object]]], MagicMock]
AsyncMockFactory = Callable[[Optional[Dict[str, object]]], AsyncMock]


# Test assertion types
class AssertionData(TypedDict):
    """Test assertion data structure."""

    description: str
    expected: object
    actual: object
    passed: bool
    error_message: Optional[str]


class TestResultData(TypedDict):
    """Test execution result data."""

    test_name: str
    status: str  # "passed", "failed", "skipped", "error"
    duration_ms: float
    assertions: List[AssertionData]
    error_message: Optional[str]
    warnings: List[str]


# Integration test types
class IntegrationTestConfig(TypedDict):
    """Integration test configuration."""

    server_url: str
    timeout_seconds: int
    retry_attempts: int
    test_data_dir: str
    cleanup_after_test: bool


class E2ETestData(TypedDict):
    """End-to-end test data."""

    scenario: str
    steps: List[Dict[str, object]]
    expected_results: List[Dict[str, object]]
    setup_data: Optional[Dict[str, object]]
    cleanup_data: Optional[Dict[str, object]]


# Error simulation types
class ErrorSimulationData(TypedDict):
    """Error simulation configuration."""

    error_type: str
    error_message: str
    error_code: Optional[int]
    should_retry: bool
    recovery_expected: bool
    timeout_ms: Optional[int]


class NetworkSimulationData(TypedDict):
    """Network condition simulation."""

    latency_ms: int
    packet_loss_percent: float
    bandwidth_kbps: int
    connection_drops: int
    recovery_time_ms: int
