"""Synchronous wrapper for AsyncCorridorsMCTS to maintain backward compatibility."""

import asyncio
from typing import List, Optional, Tuple, Dict

from corridors.async_mcts import AsyncCorridorsMCTS, MCTSProtocol


class Corridors_MCTS:
    """Synchronous wrapper around AsyncCorridorsMCTS for backward compatibility."""

    def __init__(
        self,
        c: float = 1.4,
        seed: int = 42,
        min_simulations: int = 100,
        max_simulations: int = 10000,
        sim_increment: int = 50,
        use_rollout: bool = True,
        eval_children: bool = False,
        use_puct: bool = False,
        use_probs: bool = False,
        decide_using_visits: bool = True,
    ) -> None:
        """Initialize with an AsyncCorridorsMCTS instance."""
        self._async_mcts = AsyncCorridorsMCTS(
            c=c,
            seed=seed,
            min_simulations=min_simulations,
            max_simulations=max_simulations,
            sim_increment=sim_increment,
            use_rollout=use_rollout,
            eval_children=eval_children,
            use_puct=use_puct,
            use_probs=use_probs,
            decide_using_visits=decide_using_visits,
        )
        # Create and set event loop
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

    def run_simulations(self, n: int) -> None:
        """Run n MCTS simulations synchronously."""
        result: int = self._loop.run_until_complete(
            self._async_mcts.ensure_sims_async(n)
        )
        # Ignore the returned simulation count for this sync API

    def ensure_sims(self, n: int) -> None:
        """Alias for run_simulations for compatibility."""
        self.run_simulations(n)

    def make_move(self, action: str, flip: bool = False) -> None:
        """Make a move synchronously."""
        self._loop.run_until_complete(self._async_mcts.make_move_async(action, flip))

    def get_sorted_actions(self, flip: bool = False) -> List[Tuple[int, float, str]]:
        """Get sorted actions synchronously."""
        result: List[Tuple[int, float, str]] = self._loop.run_until_complete(
            self._async_mcts.get_sorted_actions_async(flip)
        )
        return result

    def choose_best_action(self, epsilon: float = 0.0) -> str:
        """Choose best action synchronously."""
        result: str = self._loop.run_until_complete(
            self._async_mcts.choose_best_action_async(epsilon)
        )
        return result

    def get_evaluation(self) -> Optional[float]:
        """Get position evaluation synchronously."""
        result: Optional[float] = self._loop.run_until_complete(
            self._async_mcts.get_evaluation_async()
        )
        return result

    def get_visit_count(self) -> int:
        """Get visit count synchronously."""
        result: int = self._loop.run_until_complete(
            self._async_mcts.get_visit_count_async()
        )
        return result

    def display(self, flip: bool = False) -> str:
        """Display board synchronously."""
        result: str = self._loop.run_until_complete(
            self._async_mcts.display_async(flip)
        )
        return result

    def reset_to_initial_state(self) -> None:
        """Reset to initial state synchronously."""
        self._loop.run_until_complete(self._async_mcts.reset_async())

    def is_terminal(self) -> bool:
        """Check if terminal synchronously."""
        result: bool = self._loop.run_until_complete(
            self._async_mcts.is_terminal_async()
        )
        return result

    def get_legal_moves(self, flip: bool = False) -> List[str]:
        """Get legal moves synchronously."""
        actions = self.get_sorted_actions(flip)
        return [action[2] for action in actions]

    def best_action(self) -> str:
        """Get best action synchronously."""
        return self.choose_best_action(0.0)

    def __json__(self) -> Dict[str, str]:
        """JSON serialization for compatibility."""
        return {"type": "Corridors_MCTS", "name": getattr(self, "name", "unnamed")}


# Export old function names for compatibility
def display_sorted_actions(
    actions: List[Tuple[int, float, str]], list_size: Optional[int] = None
) -> str:
    """Format sorted actions for display."""
    if list_size is not None:
        actions = actions[:list_size]
    result = []
    for visits, equity, action in actions:
        result.append(f"{action}: {visits} visits, {equity:.4f} equity")
    return "\n".join(result)


# Stub functions that were removed in async refactor
def computer_self_play(*args: object, **kwargs: object) -> None:
    """Stub function - computer_self_play was removed in async refactor."""
    raise NotImplementedError("computer_self_play was removed in async refactor")


def human_computer_play(*args: object, **kwargs: object) -> None:
    """Stub function - human_computer_play was removed in async refactor."""
    raise NotImplementedError("human_computer_play was removed in async refactor")
