from tests.pytest_marks import (
    python,
    display,
    integration,
    unit,
    parametrize,
    cpp,
    board,
    mcts,
    slow,
    performance,
    stress,
    edge_cases,
    asyncio,
    api,
    websocket,
    game_manager,
    models,
    endpoints,
    benchmark,
)

"""
Tests for API models and validation.
"""
import pytest
from datetime import datetime
from pydantic import ValidationError

from backend.api.models import (
    PlayerType,
    GameStatus,
    GameMode,
    MCTSSettings,
    GameSettings,
    Player,
    Position,
    Move,
    BoardState,
    GameSession,
    GameCreateRequest,
    GameResponse,
    MoveRequest,
    MoveResponse,
    AnalysisResult,
    WebSocketMessage,
    MatchmakingRequest,
    PlayerStats,
)


class TestEnums:
    """Test enum values."""

    def test_player_type_enum(self) -> None:
        """Test PlayerType enum values."""
        assert PlayerType.HUMAN.value == "human"
        assert PlayerType.MACHINE.value == "machine"

    def test_game_status_enum(self) -> None:
        """Test GameStatus enum values."""
        assert GameStatus.WAITING.value == "waiting"
        assert GameStatus.IN_PROGRESS.value == "in_progress"
        assert GameStatus.COMPLETED.value == "completed"
        assert GameStatus.CANCELLED.value == "cancelled"
        assert GameStatus.PAUSED.value == "paused"

    def test_game_mode_enum(self) -> None:
        """Test GameMode enum values."""
        assert GameMode.PVP.value == "pvp"
        assert GameMode.PVM.value == "pvm"
        assert GameMode.MVM.value == "mvm"


class TestMCTSSettings:
    """Test MCTS settings model."""

    def test_default_settings(self) -> None:
        """Test default MCTS settings."""
        settings = MCTSSettings()
        assert settings.c == 0.158
        assert settings.min_simulations == 10000
        assert settings.max_simulations == 10000
        assert settings.use_rollout is True
        assert settings.eval_children is False
        assert settings.use_puct is False
        assert settings.use_probs is False
        assert settings.decide_using_visits is True

    def test_custom_settings(self) -> None:
        """Test custom MCTS settings."""
        settings = MCTSSettings(c=0.5, min_simulations=5000, use_puct=True, seed=42)
        assert settings.c == 0.5
        assert settings.min_simulations == 5000
        assert settings.use_puct is True
        assert settings.seed == 42

    def test_validation(self) -> None:
        """Test MCTS settings validation."""
        # Min simulations must be >= 100
        with pytest.raises(ValidationError):
            MCTSSettings(min_simulations=50)

        # Max simulations must be >= 100
        with pytest.raises(ValidationError):
            MCTSSettings(max_simulations=50)


class TestGameSettings:
    """Test game settings model."""

    def test_default_settings(self) -> None:
        """Test default game settings."""
        settings = GameSettings()
        assert settings.time_limit_seconds is None
        assert settings.allow_hints is True
        assert settings.allow_analysis is True
        assert settings.auto_save is True
        assert isinstance(settings.mcts_settings, MCTSSettings)

    def test_custom_settings(self) -> None:
        """Test custom game settings."""
        mcts = MCTSSettings(c=0.3)
        settings = GameSettings(
            time_limit_seconds=300, mcts_settings=mcts, allow_hints=False
        )
        assert settings.time_limit_seconds == 300
        assert settings.mcts_settings.c == 0.3
        assert settings.allow_hints is False


class TestPlayer:
    """Test Player model."""

    def test_create_player(self) -> None:
        """Test creating a player."""
        player = Player(name="Alice", type=PlayerType.HUMAN, is_hero=True)
        assert player.name == "Alice"
        assert player.type == PlayerType.HUMAN
        assert player.is_hero is True
        assert player.walls_remaining == 10
        assert len(player.id) > 0  # UUID generated

    def test_player_with_custom_id(self) -> None:
        """Test player with custom ID."""
        player = Player(
            id="custom-id", name="Bob", type=PlayerType.MACHINE, is_hero=False
        )
        assert player.id == "custom-id"
        assert player.is_hero is False


class TestPosition:
    """Test Position model."""

    def test_valid_position(self) -> None:
        """Test valid position."""
        pos = Position(x=4, y=4)
        assert pos.x == 4
        assert pos.y == 4

    def test_boundary_positions(self) -> None:
        """Test boundary positions."""
        pos1 = Position(x=0, y=0)
        pos2 = Position(x=8, y=8)
        assert pos1.x == 0
        assert pos2.x == 8

    def test_invalid_position(self) -> None:
        """Test invalid positions."""
        with pytest.raises(ValidationError):
            Position(x=-1, y=4)

        with pytest.raises(ValidationError):
            Position(x=9, y=4)

        with pytest.raises(ValidationError):
            Position(x=4, y=9)


class TestMove:
    """Test Move model."""

    def test_create_move(self) -> None:
        """Test creating a move."""
        move = Move(player_id="player1", action="*(4,1)", move_number=1)
        assert move.player_id == "player1"
        assert move.action == "*(4,1)"
        assert move.move_number == 1
        assert isinstance(move.timestamp, datetime)

    def test_move_with_evaluation(self) -> None:
        """Test move with evaluation data."""
        move = Move(
            player_id="player1",
            action="H(4,4)",
            move_number=5,
            time_taken=2.5,
            evaluation=0.75,
            visits=1000,
        )
        assert move.time_taken == 2.5
        assert move.evaluation == 0.75
        assert move.visits == 1000


class TestGameSession:
    """Test GameSession model."""

    def test_create_game_session(self) -> None:
        """Test creating a game session."""
        player1 = Player(name="Alice", type=PlayerType.HUMAN, is_hero=True)
        player2 = Player(name="Bob", type=PlayerType.HUMAN, is_hero=False)

        session = GameSession(
            mode=GameMode.PVP, player1=player1, player2=player2, settings=GameSettings()
        )

        assert session.mode == GameMode.PVP
        assert session.status == GameStatus.WAITING
        assert session.current_turn == 1
        assert len(session.move_history) == 0
        assert len(session.game_id) > 0

    def test_is_player(self) -> None:
        """Test is_player method."""
        player1 = Player(id="p1", name="Alice", type=PlayerType.HUMAN, is_hero=True)
        player2 = Player(id="p2", name="Bob", type=PlayerType.HUMAN, is_hero=False)

        session = GameSession(
            mode=GameMode.PVP, player1=player1, player2=player2, settings=GameSettings()
        )

        assert session.is_player("p1") is True
        assert session.is_player("p2") is True
        assert session.is_player("p3") is False

    def test_get_current_player(self) -> None:
        """Test get_current_player method."""
        player1 = Player(name="Alice", type=PlayerType.HUMAN, is_hero=True)
        player2 = Player(name="Bob", type=PlayerType.HUMAN, is_hero=False)

        session = GameSession(
            mode=GameMode.PVP, player1=player1, player2=player2, settings=GameSettings()
        )

        # Initially player 1's turn
        current = session.get_current_player()
        assert current.name == "Alice"

        # Switch turn
        session.current_turn = 2
        current = session.get_current_player()
        assert current.name == "Bob"

    def test_get_player(self) -> None:
        """Test get_player method."""
        player1 = Player(id="p1", name="Alice", type=PlayerType.HUMAN, is_hero=True)
        player2 = Player(id="p2", name="Bob", type=PlayerType.HUMAN, is_hero=False)

        session = GameSession(
            mode=GameMode.PVP, player1=player1, player2=player2, settings=GameSettings()
        )

        p1 = session.get_player("p1")
        assert p1 is not None
        assert p1.name == "Alice"

        p2 = session.get_player("p2")
        assert p2 is not None
        assert p2.name == "Bob"

        p3 = session.get_player("p3")
        assert p3 is None


class TestGameCreateRequest:
    """Test GameCreateRequest model."""

    def test_default_request(self) -> None:
        """Test default game creation request."""
        request = GameCreateRequest()
        assert request.player1_type == PlayerType.HUMAN
        assert request.player2_type == PlayerType.HUMAN
        assert request.player1_name == "Player 1"
        assert request.player2_name == "Player 2"

    def test_custom_request(self) -> None:
        """Test custom game creation request."""
        settings = GameSettings(time_limit_seconds=600)
        request = GameCreateRequest(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.MACHINE,
            player1_name="Human",
            player2_name="AI",
            settings=settings,
        )
        assert request.player2_type == PlayerType.MACHINE
        assert request.settings is not None
        assert request.settings.time_limit_seconds == 600


class TestGameResponse:
    """Test GameResponse model."""

    def test_from_game_session(self) -> None:
        """Test creating response from game session."""
        player1 = Player(name="Alice", type=PlayerType.HUMAN, is_hero=True)
        player2 = Player(name="Bob", type=PlayerType.HUMAN, is_hero=False)

        session = GameSession(
            game_id="test-game",
            mode=GameMode.PVP,
            player1=player1,
            player2=player2,
            settings=GameSettings(),
            status=GameStatus.IN_PROGRESS,
        )

        response = GameResponse.from_game_session(session)
        assert response.game_id == "test-game"
        assert response.status == GameStatus.IN_PROGRESS
        assert response.mode == GameMode.PVP
        assert response.move_count == 0


class TestMoveRequest:
    """Test MoveRequest model."""

    def test_move_request(self) -> None:
        """Test move request."""
        request = MoveRequest(player_id="player1", action="*(4,1)")
        assert request.player_id == "player1"
        assert request.action == "*(4,1)"


class TestMoveResponse:
    """Test MoveResponse model."""

    def test_move_response(self) -> None:
        """Test move response."""
        move = Move(player_id="player1", action="*(4,1)", move_number=1)

        response = MoveResponse(
            success=True,
            game_id="test-game",
            move=move,
            game_status=GameStatus.IN_PROGRESS,
            next_turn=2,
            next_player_type=PlayerType.HUMAN,
        )

        assert response.success is True
        assert response.game_id == "test-game"
        assert response.move.action == "*(4,1)"
        assert response.next_turn == 2

    def test_move_response_with_winner(self) -> None:
        """Test move response with winner."""
        move = Move(player_id="player1", action="*(4,8)", move_number=20)

        response = MoveResponse(
            success=True,
            game_id="test-game",
            move=move,
            game_status=GameStatus.COMPLETED,
            next_turn=2,
            next_player_type=PlayerType.HUMAN,
            winner=1,
        )

        assert response.game_status == GameStatus.COMPLETED
        assert response.winner == 1


class TestAnalysisResult:
    """Test AnalysisResult model."""

    def test_analysis_result(self) -> None:
        """Test analysis result."""
        result = AnalysisResult(
            evaluation=0.65,
            best_move="*(4,1)",
            sorted_actions=[
                {"action": "*(4,1)", "visits": 500, "equity": 0.65},
                {"action": "*(3,0)", "visits": 300, "equity": 0.55},
            ],
            simulations=1000,
            depth=10,
        )

        assert result.evaluation == 0.65
        assert result.best_move == "*(4,1)"
        assert len(result.sorted_actions) == 2
        assert result.simulations == 1000


class TestWebSocketMessage:
    """Test WebSocketMessage model."""

    def test_websocket_message(self) -> None:
        """Test WebSocket message."""
        message = WebSocketMessage(
            type="move", data={"action": "*(4,1)", "player": "player1"}
        )

        assert message.type == "move"
        assert message.data["action"] == "*(4,1)"
        assert isinstance(message.timestamp, datetime)


class TestMatchmakingRequest:
    """Test MatchmakingRequest model."""

    def test_matchmaking_request(self) -> None:
        """Test matchmaking request."""
        settings = GameSettings()
        request = MatchmakingRequest(
            player_id="player1", player_name="Alice", settings=settings, rating=1500
        )

        assert request.player_id == "player1"
        assert request.player_name == "Alice"
        assert request.rating == 1500


class TestPlayerStats:
    """Test PlayerStats model."""

    def test_player_stats(self) -> None:
        """Test player statistics."""
        stats = PlayerStats(
            player_id="player1",
            player_name="Alice",
            games_played=100,
            wins=60,
            losses=35,
            draws=5,
            win_rate=0.6,
            avg_game_length=25.5,
            rating=1650,
            rank=42,
        )

        assert stats.games_played == 100
        assert stats.wins == 60
        assert stats.win_rate == 0.6
        assert stats.rating == 1650
        assert stats.rank == 42
