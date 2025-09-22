"""Functional synchronous wrapper for AsyncCorridorsMCTS with context management."""

import asyncio
from typing import List, Optional, Tuple, Dict

from corridors.async_mcts import AsyncCorridorsMCTS, MCTSProtocol, MCTSConfig


class Corridors_MCTS:
    """Functional synchronous wrapper around AsyncCorridorsMCTS with proper resource management."""

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
        """Initialize with validated configuration and managed event loop."""
        # Validate configuration using MCTSConfig from async_mcts
        self._config = MCTSConfig(
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

        # Create async instance with validated config
        self._async_mcts = AsyncCorridorsMCTS(
            c=self._config.c,
            seed=self._config.seed,
            min_simulations=self._config.min_simulations,
            max_simulations=self._config.max_simulations,
            sim_increment=self._config.sim_increment,
            use_rollout=self._config.use_rollout,
            eval_children=self._config.eval_children,
            use_puct=self._config.use_puct,
            use_probs=self._config.use_probs,
            decide_using_visits=self._config.decide_using_visits,
            max_workers=self._config.max_workers,
        )

        # Create dedicated event loop for sync operations
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

    # Use functional composition to convert async methods to sync
    def run_simulations(self, n: int) -> None:
        """Run n MCTS simulations synchronously using functional composition."""
        self._loop.run_until_complete(self._async_mcts.ensure_sims_async(n))

    def ensure_sims(self, n: int) -> None:
        """Alias for run_simulations for compatibility."""
        self.run_simulations(n)

    def make_move(self, action: str, flip: bool = False) -> None:
        """Make a move synchronously using functional composition."""
        self._loop.run_until_complete(self._async_mcts.make_move_async(action, flip))

    def get_sorted_actions(self, flip: bool = False) -> List[Tuple[int, float, str]]:
        """Get sorted actions synchronously using functional composition."""
        return self._loop.run_until_complete(
            self._async_mcts.get_sorted_actions_async(flip)
        )

    def choose_best_action(self, epsilon: float = 0.0) -> str:
        """Choose best action synchronously using functional composition."""
        return self._loop.run_until_complete(
            self._async_mcts.choose_best_action_async(epsilon)
        )

    def get_evaluation(self) -> Optional[float]:
        """Get position evaluation synchronously using functional composition."""
        return self._loop.run_until_complete(self._async_mcts.get_evaluation_async())

    def get_visit_count(self) -> int:
        """Get visit count synchronously using functional composition."""
        return self._loop.run_until_complete(self._async_mcts.get_visit_count_async())

    def display(self, flip: bool = False) -> str:
        """Display board synchronously using functional composition."""
        return self._loop.run_until_complete(self._async_mcts.display_async(flip))

    def reset_to_initial_state(self) -> None:
        """Reset to initial state synchronously using functional composition."""
        self._loop.run_until_complete(self._async_mcts.reset_async())

    def is_terminal(self) -> bool:
        """Check if terminal synchronously using functional composition."""
        return self._loop.run_until_complete(self._async_mcts.is_terminal_async())

    def get_legal_moves(self, flip: bool = False) -> List[str]:
        """Get legal moves synchronously using functional composition."""
        return [action[2] for action in self.get_sorted_actions(flip)]

    def best_action(self) -> str:
        """Get best action synchronously using functional composition."""
        return self.choose_best_action(0.0)

    def __json__(self) -> Dict[str, str]:
        """JSON serialization for compatibility using functional approach."""
        return {"type": "Corridors_MCTS", "name": getattr(self, "name", "unnamed")}


# Export old function names for compatibility
def display_sorted_actions(
    actions: List[Tuple[int, float, str]], list_size: Optional[int] = None
) -> str:
    """Format sorted actions for display using functional composition."""
    # Use slicing and comprehension instead of imperative loops
    limited_actions = actions[:list_size] if list_size is not None else actions
    return "\n".join(
        f"{action}: {visits} visits, {equity:.4f} equity"
        for visits, equity, action in limited_actions
    )


# Stub functions that were removed in async refactor
def computer_self_play(*args: object, **kwargs: object) -> None:
    """Stub function - computer_self_play was removed in async refactor."""
    raise NotImplementedError("computer_self_play was removed in async refactor")


def human_computer_play(*args: object, **kwargs: object) -> None:
    """Stub function - human_computer_play was removed in async refactor."""
    raise NotImplementedError("human_computer_play was removed in async refactor")
