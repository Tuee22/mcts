from typing import TYPE_CHECKING, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from corridors.corridors_mcts import Corridors_MCTS

import uuid
from datetime import datetime
from enum import Enum


class PlayerType(str, Enum):
    """Player type enumeration."""

    HUMAN = "human"
    MACHINE = "machine"


class GameStatus(str, Enum):
    """Game status enumeration."""

    WAITING = "waiting"  # Waiting for players
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class GameMode(str, Enum):
    """Game mode enumeration."""

    PVP = "pvp"  # Player vs Player
    PVM = "pvm"  # Player vs Machine
    MVM = "mvm"  # Machine vs Machine


class MCTSSettings(BaseModel):
    """MCTS algorithm configuration."""

    c: float = 0.158  # Exploration parameter
    min_simulations: int = 10000  # Minimum 100
    max_simulations: int = 10000  # Minimum 100
    use_rollout: bool = True
    eval_children: bool = False
    use_puct: bool = False
    use_probs: bool = False
    decide_using_visits: bool = True
    seed: Optional[int] = None

    @field_validator("min_simulations")
    @classmethod
    def validate_min_simulations(cls, v: int) -> int:
        if v < 100:
            raise ValueError("min_simulations must be >= 100")
        return v

    @field_validator("max_simulations")
    @classmethod
    def validate_max_simulations(cls, v: int) -> int:
        if v < 100:
            raise ValueError("max_simulations must be >= 100")
        return v


class GameSettings(BaseModel):
    """Game configuration settings."""

    time_limit_seconds: Optional[int] = None  # Time limit per player
    mcts_settings: MCTSSettings = MCTSSettings()
    allow_hints: bool = True
    allow_analysis: bool = True
    auto_save: bool = True


class Player(BaseModel):
    """Player information."""

    id: str = str(uuid.uuid4())  # Will be overridden during creation
    name: str
    type: PlayerType
    is_hero: bool  # True for player 1, False for player 2
    walls_remaining: int = 10
    time_remaining: Optional[float] = None

    model_config = ConfigDict(use_enum_values=True)


class Position(BaseModel):
    """Board position."""

    x: int  # Range: 0-8
    y: int  # Range: 0-8

    @field_validator("x", "y")
    @classmethod
    def validate_coordinates(cls, v: int) -> int:
        if v < 0 or v > 8:
            raise ValueError("Coordinates must be in range 0-8")
        return v


class Move(BaseModel):
    """Game move representation."""

    player_id: str
    action: str  # Format: *(X,Y), H(X,Y), or V(X,Y)
    timestamp: datetime = datetime.utcnow()  # Will be overridden during creation
    move_number: int
    time_taken: Optional[float] = None
    evaluation: Optional[float] = None  # AI evaluation after move11
    visits: Optional[int] = None  # MCTS visit count


class BoardState(BaseModel):
    """Current board state."""

    hero_position: Position
    villain_position: Position
    walls: List[
        Dict[str, Union[str, int, bool]]
    ]  # List of wall positions and orientations
    display: Optional[str] = None  # ASCII representation


class GameSession(BaseModel):
    """Complete game session data."""

    game_id: str = str(uuid.uuid4())  # Will be overridden during creation
    status: GameStatus = GameStatus.WAITING
    mode: GameMode
    player1: Player
    player2: Player
    current_turn: Literal[1, 2] = 1
    move_history: List[Move] = []
    board_state: Optional[BoardState] = None
    settings: GameSettings
    created_at: datetime = datetime.utcnow()  # Will be overridden during creation
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    winner: Optional[int] = None  # 1 or 2
    termination_reason: Optional[str] = None
    mcts_instance: Optional["Corridors_MCTS"] = None  # Internal MCTS object

    model_config = ConfigDict(use_enum_values=True, arbitrary_types_allowed=True)

    def is_player(self, player_id: str) -> bool:
        """Check if player_id belongs to this game."""
        return player_id in [self.player1.id, self.player2.id]

    def get_current_player(self) -> Player:
        """Get the current player."""
        return self.player1 if self.current_turn == 1 else self.player2

    def get_player(self, player_id: str) -> Optional[Player]:
        """Get player by ID."""
        if self.player1.id == player_id:
            return self.player1
        elif self.player2.id == player_id:
            return self.player2
        return None


# ==================== API Request/Response Models ====================


class GameCreateRequest(BaseModel):
    """Request to create a new game."""

    player1_type: PlayerType = PlayerType.HUMAN
    player2_type: PlayerType = PlayerType.HUMAN
    player1_name: str = "Player 1"
    player2_name: str = "Player 2"
    player1_id: Optional[str] = None
    player2_id: Optional[str] = None
    settings: Optional[GameSettings] = None

    model_config = ConfigDict(use_enum_values=True)


class GameResponse(BaseModel):
    """Game information response."""

    game_id: str
    status: GameStatus
    mode: GameMode
    player1: Player
    player2: Player
    current_turn: int
    move_count: int
    board_display: Optional[str] = None
    winner: Optional[int] = None
    created_at: datetime
    started_at: Optional[datetime] = None

    model_config = ConfigDict(use_enum_values=True)

    @classmethod
    def from_game_session(cls, session: GameSession) -> "GameResponse":
        """Create response from game session."""
        return cls(
            game_id=session.game_id,
            status=session.status,
            mode=session.mode,
            player1=session.player1,
            player2=session.player2,
            current_turn=session.current_turn,
            move_count=len(session.move_history),
            board_display=session.board_state.display if session.board_state else None,
            winner=session.winner,
            created_at=session.created_at,
            started_at=session.started_at,
        )


class GameListResponse(BaseModel):
    """List of games response."""

    games: List[GameResponse]
    total: int


class MoveRequest(BaseModel):
    """Request to make a move."""

    player_id: str
    action: str  # Format: *(X,Y), H(X,Y), or V(X,Y)


class MoveResponse(BaseModel):
    """Response after making a move."""

    success: bool
    game_id: str
    move: Move
    game_status: GameStatus
    next_turn: int
    next_player_type: PlayerType
    board_display: Optional[str] = None
    winner: Optional[int] = None
    legal_moves: Optional[List[str]] = None

    model_config = ConfigDict(use_enum_values=True)


class AnalysisResult(BaseModel):
    """Position analysis result."""

    evaluation: Optional[float]  # Position evaluation (-1 to 1)
    best_move: str
    sorted_actions: List[Dict[str, Union[str, int, float]]]  # Action, visits, equity
    simulations: int
    depth: int


class WebSocketMessage(BaseModel):
    """WebSocket message format."""

    type: str  # "move", "game_state", "player_joined", "game_ended", etc.
    data: Dict[str, Union[str, int, float, bool, None]]
    timestamp: datetime = datetime.utcnow()  # Will be overridden during creation


class MatchmakingRequest(BaseModel):
    """Matchmaking queue request."""

    player_id: str
    player_name: str
    settings: Optional[GameSettings] = None
    rating: Optional[int] = None


class PlayerStats(BaseModel):
    """Player statistics."""

    player_id: str
    player_name: str
    games_played: int
    wins: int
    losses: int
    draws: int
    win_rate: float
    avg_game_length: float
    rating: int
    rank: Optional[int] = None
