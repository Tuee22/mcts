"""Type definitions for the API module."""
from typing import Protocol, Optional, List, Tuple, Dict, Union, Literal
from typing_extensions import TypedDict


class CorridorsMCTSProtocol(Protocol):
    """Protocol for Corridors_MCTS interface."""
    
    def make_move(self, action: str, flip: bool = False) -> None: ...
    def get_legal_moves(self, flip: bool = False) -> List[str]: ...
    def get_sorted_actions(self, flip: bool = False) -> List[Tuple[int, float, str]]: ...
    def choose_best_action(self, epsilon: float = 0.0) -> str: ...
    def ensure_sims(self, num_sims: int) -> None: ...
    def get_evaluation(self) -> Optional[float]: ...
    def display(self, flip: bool = False) -> str: ...
    def reset(self) -> None: ...
    def is_terminal(self) -> bool: ...
    def get_winner(self) -> Optional[int]: ...
    def get_best_move(self) -> str: ...
    def get_action_stats(self) -> Dict[str, Dict[str, float]]: ...


class GameState(TypedDict):
    """Type for game state dictionary."""
    board: str
    legal_moves: List[str]
    evaluation: Optional[float]
    is_terminal: bool
    winner: Optional[int]
    current_player: int
    move_history: List[str]


class MoveStats(TypedDict):
    """Type for move statistics."""
    visits: float
    win_rate: float
    action: str


class GameConfig(TypedDict, total=False):
    """Configuration for a game."""
    c: float
    seed: int
    min_simulations: int
    max_simulations: int
    sim_increment: int
    use_rollout: bool
    eval_children: bool
    use_puct: bool
    use_probs: bool
    decide_using_visits: bool


class WebSocketMessage(TypedDict):
    """WebSocket message structure."""
    type: Literal["move", "reset", "get_state", "get_stats", "error"]
    data: Optional[Dict[str, Union[str, int, float, List[str], Dict[str, float]]]]


class GameSession(TypedDict):
    """Game session information."""
    game_id: str
    player_id: str
    game_state: GameState
    config: GameConfig


# WebSocket message types
class MoveData(TypedDict):
    """Data for a move."""
    player_id: str
    action: str
    move_number: int
    evaluation: Optional[float]
    timestamp: str


class MoveMessageData(TypedDict):
    """Data for move message."""
    game_id: str
    move: MoveData
    game_status: str
    next_turn: int
    board_display: Optional[str]  # Can be None
    winner: Optional[int]


class GameStateData(TypedDict):
    """Data for game state message."""
    game_id: str
    board_display: Optional[str]  # Can be None
    legal_moves: List[str]
    status: str  # From game_response.status
    player1_id: str
    player2_id: str
    current_turn: int
    winner: Optional[int]
    created_at: str


class GameEndedData(TypedDict):
    """Data for game ended message."""
    game_id: str
    winner: Optional[int]
    game_status: str


class GameCreatedData(TypedDict):
    """Data for game created message."""
    game_id: str


class OutgoingWebSocketMessage(TypedDict):
    """Base outgoing WebSocket message."""
    type: str
    data: Union[MoveMessageData, GameStateData, GameEndedData, GameCreatedData, Dict[str, Union[str, int, bool, List[str], Optional[int]]]]


class PlayerConnectedMessage(OutgoingWebSocketMessage):
    """Player connected message."""
    pass


class PlayerDisconnectedMessage(OutgoingWebSocketMessage):
    """Player disconnected message."""
    pass


class GameStateMessage(OutgoingWebSocketMessage):
    """Game state message."""
    pass


class MoveBroadcastMessage(OutgoingWebSocketMessage):
    """Move broadcast message."""
    pass


class GameEndedMessage(OutgoingWebSocketMessage):
    """Game ended message."""
    pass


class GameCreatedMessage(OutgoingWebSocketMessage):
    """Game created message."""
    pass