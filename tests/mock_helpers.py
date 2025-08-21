"""Type-safe mock helpers for testing."""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Protocol, Tuple


class CorridorsMCTSInterface(Protocol):
    """Protocol defining the Corridors_MCTS interface."""

    def make_move(self, action: str, flip: bool = False) -> None:
        ...

    def get_legal_moves(self, flip: bool = False) -> List[str]:
        ...

    def get_sorted_actions(self, flip: bool = False) -> List[Tuple[int, float, str]]:
        ...

    def choose_best_action(self, epsilon: float = 0.0) -> str:
        ...

    def ensure_sims(self, num_sims: int) -> None:
        ...

    def get_evaluation(self) -> Optional[float]:
        ...

    def display(self, flip: bool = False) -> str:
        ...

    def reset(self) -> None:
        ...

    def is_terminal(self) -> bool:
        ...

    def get_winner(self) -> Optional[int]:
        ...

    def get_best_move(self) -> str:
        ...

    def get_action_stats(self) -> Dict[str, Dict[str, float]]:
        ...


@dataclass
class MockCorridorsMCTS(CorridorsMCTSInterface):
    """Type-safe mock for Corridors_MCTS that implements the protocol."""

    # Default return values
    legal_moves: List[str] = field(default_factory=list)
    sorted_actions: List[Tuple[int, float, str]] = field(default_factory=list)
    best_action: str = "*(4,1)"
    evaluation: Optional[float] = None
    board_display: str = "Mock board"
    terminal: bool = False
    winner: Optional[int] = None
    best_move: str = "*(4,1)"
    action_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Support for side_effect behavior
    sorted_actions_sequence: List[List[Tuple[int, float, str]]] = field(
        default_factory=list
    )
    sorted_actions_side_effect: Optional[
        Callable[[bool], List[Tuple[int, float, str]]]
    ] = None
    _sorted_actions_call_count: int = field(default=0, init=False)

    # Call tracking
    make_move_calls: List[Tuple[str, bool]] = field(default_factory=list)
    ensure_sims_calls: List[int] = field(default_factory=list)
    reset_calls: int = 0

    def make_move(self, action: str, flip: bool = False) -> None:
        """Record a move."""
        self.make_move_calls.append((action, flip))

    def get_legal_moves(self, flip: bool = False) -> List[str]:
        """Return legal moves."""
        return self.legal_moves

    def get_sorted_actions(self, flip: bool = False) -> List[Tuple[int, float, str]]:
        """Return sorted actions, supporting sequence and side_effect behavior."""
        if self.sorted_actions_side_effect:
            return self.sorted_actions_side_effect(flip)
        elif self.sorted_actions_sequence:
            if self._sorted_actions_call_count < len(self.sorted_actions_sequence):
                result = self.sorted_actions_sequence[self._sorted_actions_call_count]
                self._sorted_actions_call_count += 1
                return result
            else:
                # Return last item if we've run out
                return (
                    self.sorted_actions_sequence[-1]
                    if self.sorted_actions_sequence
                    else []
                )
        return self.sorted_actions

    def choose_best_action(self, epsilon: float = 0.0) -> str:
        """Return best action."""
        return self.best_action

    def ensure_sims(self, num_sims: int) -> None:
        """Record simulation request."""
        self.ensure_sims_calls.append(num_sims)

    def get_evaluation(self) -> Optional[float]:
        """Return evaluation."""
        return self.evaluation

    def display(self, flip: bool = False) -> str:
        """Return board display."""
        return self.board_display

    def reset(self) -> None:
        """Reset the game."""
        self.reset_calls += 1

    def is_terminal(self) -> bool:
        """Check if game is terminal."""
        return self.terminal

    def get_winner(self) -> Optional[int]:
        """Get winner."""
        return self.winner

    def get_best_move(self) -> str:
        """Get best move."""
        return self.best_move

    def get_action_stats(self) -> Dict[str, Dict[str, float]]:
        """Get action statistics."""
        return self.action_stats

    # Helper methods for assertions
    def assert_move_made(self, action: str, flip: bool = False) -> None:
        """Assert a specific move was made."""
        assert (action, flip) in self.make_move_calls

    def assert_called_make_move(self) -> None:
        """Assert make_move was called."""
        assert len(self.make_move_calls) > 0

    def assert_called_ensure_sims(self) -> None:
        """Assert ensure_sims was called."""
        assert len(self.ensure_sims_calls) > 0
