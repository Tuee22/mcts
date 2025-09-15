"""
Async wrapper for Corridors MCTS using asyncio and thread pools.

This module provides async-first interface to MCTS operations,
allowing proper integration with FastAPI and other async frameworks.
"""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from math import sqrt
from typing import Dict, List, Optional, Tuple, Type, Protocol, Union
from types import TracebackType

from corridors import _corridors_mcts as _ext_module


class MCTSProtocol(Protocol):
    """Protocol defining the interface for MCTS implementations."""

    def run_simulations(self, n: int) -> None:
        ...

    def make_move(self, action: str, flip: bool = False) -> None:
        ...

    def get_sorted_actions(self, flip: bool = False) -> List[Tuple[int, float, str]]:
        ...

    def choose_best_action(self, epsilon: float = 0.0) -> str:
        ...

    def get_evaluation(self) -> Optional[float]:
        ...

    def get_visit_count(self) -> int:
        ...

    def display(self, flip: bool = False) -> str:
        ...

    def reset_to_initial_state(self) -> None:
        ...

    def is_terminal(self) -> bool:
        ...


class AsyncCorridorsMCTS:
    """
    Async wrapper for Corridors MCTS operations.

    This class provides thread-safe async access to MCTS simulations,
    allowing cancellation and proper resource management.
    """

    def __init__(
        self,
        c: float = sqrt(0.025),
        seed: int = 42,
        use_rollout: bool = True,
        eval_children: bool = False,
        use_puct: bool = False,
        use_probs: bool = False,
        decide_using_visits: bool = True,
        max_workers: int = 1,
    ) -> None:
        self._impl: MCTSProtocol = _ext_module._corridors_mcts(
            c,
            seed,
            use_rollout,
            eval_children,
            use_puct,
            use_probs,
            decide_using_visits,
        )

        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._cancel_flag = threading.Event()
        self._current_task: Optional[
            Union[asyncio.Task[int], asyncio.Future[int]]
        ] = None
        self._lock = asyncio.Lock()
        self._closed = False

    async def __aenter__(self) -> "AsyncCorridorsMCTS":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Async context manager exit."""
        await self.cleanup()

    async def run_simulations_async(
        self, n: int, timeout: Optional[float] = None
    ) -> int:
        """
        Run MCTS simulations asynchronously with optional timeout and cancellation.

        Returns the actual number of simulations completed.
        """
        if self._closed:
            raise RuntimeError("AsyncCorridorsMCTS has been closed")

        if n <= 0:
            return 0

        async with self._lock:
            # Cancel any existing simulation task
            if self._current_task and not self._current_task.done():
                self._cancel_flag.set()
                try:
                    await asyncio.wait_for(self._current_task, timeout=1.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    pass

            # Reset cancellation flag
            self._cancel_flag.clear()

            # Create simulation function with cancellation support
            def _run_with_cancellation() -> int:
                simulations_completed = 0
                batch_size = min(100, n)  # Process in batches to check cancellation

                while simulations_completed < n:
                    if self._cancel_flag.is_set():
                        break

                    current_batch = min(batch_size, n - simulations_completed)
                    try:
                        self._impl.run_simulations(current_batch)
                        simulations_completed += current_batch
                    except Exception:
                        # If simulation fails, stop processing
                        break

                return simulations_completed

            # Run simulations in executor
            loop = asyncio.get_event_loop()
            current_future = loop.run_in_executor(
                self._executor, _run_with_cancellation
            )
            self._current_task = current_future

            try:
                if timeout:
                    simulations_done = await asyncio.wait_for(
                        current_future, timeout=timeout
                    )
                else:
                    simulations_done = await current_future

                return simulations_done

            except asyncio.TimeoutError:
                # Cancel the simulation
                self._cancel_flag.set()
                # Wait briefly for cancellation to take effect
                try:
                    simulations_done = await asyncio.wait_for(
                        current_future, timeout=1.0
                    )
                    return simulations_done
                except asyncio.TimeoutError:
                    return 0  # Couldn't even cancel cleanly

            except asyncio.CancelledError:
                self._cancel_flag.set()
                raise

            finally:
                self._current_task = None

    async def ensure_sims_async(
        self, target_sims: int, timeout: Optional[float] = None
    ) -> int:
        """
        Ensure a minimum number of simulations, running additional ones if needed.

        Returns the total simulation count after completion.
        """
        current_sims = await self.get_visit_count_async()

        if current_sims >= target_sims:
            return current_sims

        needed_sims = target_sims - current_sims
        completed_sims = await self.run_simulations_async(needed_sims, timeout)

        return current_sims + completed_sims

    async def make_move_async(self, action: str, flip: bool = False) -> None:
        """Make a move asynchronously."""
        if self._closed:
            raise RuntimeError("AsyncCorridorsMCTS has been closed")

        async with self._lock:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._executor, lambda: self._impl.make_move(action, flip)
            )

    async def get_sorted_actions_async(
        self, flip: bool = False
    ) -> List[Tuple[int, float, str]]:
        """Get sorted actions asynchronously."""
        if self._closed:
            raise RuntimeError("AsyncCorridorsMCTS has been closed")

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, lambda: self._impl.get_sorted_actions(flip)
        )

    async def choose_best_action_async(self, epsilon: float = 0.0) -> str:
        """Choose best action asynchronously."""
        if self._closed:
            raise RuntimeError("AsyncCorridorsMCTS has been closed")

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, lambda: self._impl.choose_best_action(epsilon)
        )

    async def get_evaluation_async(self) -> Optional[float]:
        """Get evaluation asynchronously."""
        if self._closed:
            raise RuntimeError("AsyncCorridorsMCTS has been closed")

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self._impl.get_evaluation)

    async def get_visit_count_async(self) -> int:
        """Get visit count asynchronously."""
        if self._closed:
            raise RuntimeError("AsyncCorridorsMCTS has been closed")

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self._impl.get_visit_count)

    async def display_async(self, flip: bool = False) -> str:
        """Get board display asynchronously."""
        if self._closed:
            raise RuntimeError("AsyncCorridorsMCTS has been closed")

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, lambda: self._impl.display(flip)
        )

    async def is_terminal_async(self) -> bool:
        """Check if position is terminal asynchronously."""
        if self._closed:
            raise RuntimeError("AsyncCorridorsMCTS has been closed")

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self._impl.is_terminal)

    async def reset_async(self) -> None:
        """Reset to initial state asynchronously."""
        if self._closed:
            raise RuntimeError("AsyncCorridorsMCTS has been closed")

        async with self._lock:
            # Cancel any running simulations
            if self._current_task and not self._current_task.done():
                self._cancel_flag.set()
                try:
                    await asyncio.wait_for(self._current_task, timeout=1.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    pass

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._executor, self._impl.reset_to_initial_state
            )

    def cancel_simulations(self) -> None:
        """Cancel any currently running simulations."""
        self._cancel_flag.set()
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._closed:
            return

        self._closed = True
        self.cancel_simulations()

        # Wait for any running tasks to complete
        if self._current_task and not self._current_task.done():
            try:
                await asyncio.wait_for(self._current_task, timeout=2.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass

        # Shutdown executor
        self._executor.shutdown(wait=True)

    @property
    def is_closed(self) -> bool:
        """Check if the instance has been closed."""
        return self._closed


class MCTSRegistry:
    """
    Registry for managing MCTS instances by game ID.

    Provides centralized management of async MCTS instances
    with proper cleanup and resource management.
    """

    def __init__(self) -> None:
        self._instances: Dict[str, AsyncCorridorsMCTS] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(
        self,
        game_id: str,
        c: float = sqrt(0.025),
        seed: int = 42,
        use_rollout: bool = True,
        eval_children: bool = False,
        use_puct: bool = False,
        use_probs: bool = False,
        decide_using_visits: bool = True,
    ) -> AsyncCorridorsMCTS:
        """Get existing instance or create new one."""
        async with self._lock:
            if game_id not in self._instances:
                self._instances[game_id] = AsyncCorridorsMCTS(
                    c=c,
                    seed=seed,
                    use_rollout=use_rollout,
                    eval_children=eval_children,
                    use_puct=use_puct,
                    use_probs=use_probs,
                    decide_using_visits=decide_using_visits,
                )

            return self._instances[game_id]

    async def get(self, game_id: str) -> Optional[AsyncCorridorsMCTS]:
        """Get existing instance."""
        async with self._lock:
            return self._instances.get(game_id)

    async def remove(self, game_id: str) -> None:
        """Remove and cleanup instance."""
        async with self._lock:
            instance = self._instances.pop(game_id, None)
            if instance:
                await instance.cleanup()

    async def cleanup_all(self) -> None:
        """Cleanup all instances."""
        async with self._lock:
            cleanup_tasks = [
                instance.cleanup() for instance in self._instances.values()
            ]

            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)

            self._instances.clear()

    async def list_games(self) -> List[str]:
        """List all game IDs with active instances."""
        async with self._lock:
            return list(self._instances.keys())

    @property
    def instance_count(self) -> int:
        """Get the number of active instances."""
        return len(self._instances)
