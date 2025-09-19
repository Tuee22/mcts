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
from typing import (
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Protocol,
    Union,
    Callable,
    TypeVar,
    Awaitable,
    ParamSpec,
)
from types import TracebackType
import functools

from corridors import _corridors_mcts

# Type variables for decorator typing
T = TypeVar("T")
P = ParamSpec("P")


class ConcurrencyViolationError(Exception):
    """
    Raised when concurrent access to C++ MCTS instance is detected.

    This exception indicates a race condition that could corrupt game state
    or cause undefined behavior in the C++ MCTS engine.
    """

    pass


# Note: Removed atomic_mcts_operation decorator to simplify typing
# The locking logic is now implemented directly in each async method


class MCTSLockProtocol(Protocol):
    """Protocol for objects that have MCTS operation locking methods."""

    async def _acquire_operation_lock(self, operation_name: str) -> None:
        ...

    async def _release_operation_lock(self) -> None:
        ...


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
        min_simulations: int = 100,
        max_simulations: int = 10000,
        sim_increment: int = 50,
        use_rollout: bool = True,
        eval_children: bool = False,
        use_puct: bool = False,
        use_probs: bool = False,
        decide_using_visits: bool = True,
        max_workers: int = 1,
    ) -> None:
        # Create C++ instance with correct pybind11 signature
        self._impl: MCTSProtocol = _corridors_mcts._corridors_mcts(
            c,
            seed,
            use_rollout,
            eval_children,
            use_puct,
            use_probs,
            decide_using_visits,
        )

        # Store simulation parameters separately
        self.min_simulations = min_simulations
        self.max_simulations = max_simulations
        self.sim_increment = sim_increment

        # Thread pool for async operations
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

        # Cancellation support
        self._cancel_flag = threading.Event()
        self._current_task: Optional[
            Union[asyncio.Task[int], asyncio.Future[int]]
        ] = None

        # General async lock for internal coordination
        self._lock = asyncio.Lock()
        self._closed = False

        # Race condition protection
        self._operation_in_progress = False
        self._operation_lock = asyncio.Lock()
        self._current_operation: Optional[str] = None
        self._operation_start_time: Optional[float] = None

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

    async def _acquire_operation_lock(self, operation_name: str) -> None:
        """
        Acquire exclusive operation lock with fail-fast semantics.

        Raises ConcurrencyViolationError if another operation is in progress.
        """
        # Acquire lock and check atomically
        async with self._operation_lock:
            if self._operation_in_progress:
                elapsed = time.time() - (self._operation_start_time or 0)
                raise ConcurrencyViolationError(
                    f"RACE CONDITION DETECTED: '{operation_name}' blocked by "
                    f"'{self._current_operation}' running for {elapsed:.3f}s"
                )

            # Atomically mark operation as in progress
            self._operation_in_progress = True
            self._current_operation = operation_name
            self._operation_start_time = time.time()

    async def _release_operation_lock(self) -> None:
        """Release exclusive operation lock."""
        self._operation_in_progress = False
        self._current_operation = None
        self._operation_start_time = None

    async def run_simulations_async(
        self, n: int, timeout: Optional[float] = None
    ) -> int:
        """
        Run MCTS simulations asynchronously with optional timeout and cancellation.

        Returns the actual number of simulations completed.
        """
        await self._acquire_operation_lock("run_simulations")
        try:
            if self._closed:
                raise RuntimeError("AsyncCorridorsMCTS has been closed")

            if n <= 0:
                return 0
        except Exception:
            await self._release_operation_lock()
            raise

        try:
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
        finally:
            await self._release_operation_lock()

    async def ensure_sims_async(
        self, target_sims: int, timeout: Optional[float] = None
    ) -> int:
        """
        Ensure a minimum number of simulations, running additional ones if needed.

        Returns the total simulation count after completion.
        """
        current_sims: int = await self.get_visit_count_async()

        if current_sims >= target_sims:
            return current_sims

        needed_sims = target_sims - current_sims
        completed_sims: int = await self.run_simulations_async(needed_sims, timeout)

        return current_sims + completed_sims

    async def make_move_async(self, action: str, flip: bool = False) -> None:
        """Make a move asynchronously."""
        await self._acquire_operation_lock("make_move")
        try:
            if self._closed:
                raise RuntimeError("AsyncCorridorsMCTS has been closed")

            async with self._lock:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    self._executor, lambda: self._impl.make_move(action, flip)
                )
        finally:
            await self._release_operation_lock()

    async def get_sorted_actions_async(
        self, flip: bool = False
    ) -> List[Tuple[int, float, str]]:
        """Get sorted actions asynchronously."""
        await self._acquire_operation_lock("get_sorted_actions")
        try:
            if self._closed:
                raise RuntimeError("AsyncCorridorsMCTS has been closed")

            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self._executor, lambda: self._impl.get_sorted_actions(flip)
            )
        finally:
            await self._release_operation_lock()

    async def choose_best_action_async(self, epsilon: float = 0.0) -> str:
        """Choose best action asynchronously."""
        await self._acquire_operation_lock("choose_best_action")
        try:
            if self._closed:
                raise RuntimeError("AsyncCorridorsMCTS has been closed")

            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self._executor, lambda: self._impl.choose_best_action(epsilon)
            )
        finally:
            await self._release_operation_lock()

    async def get_evaluation_async(self) -> Optional[float]:
        """Get evaluation asynchronously."""
        await self._acquire_operation_lock("get_evaluation")
        try:
            if self._closed:
                raise RuntimeError("AsyncCorridorsMCTS has been closed")

            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self._executor, self._impl.get_evaluation)
        finally:
            await self._release_operation_lock()

    async def get_visit_count_async(self) -> int:
        """Get visit count asynchronously."""
        await self._acquire_operation_lock("get_visit_count")
        try:
            if self._closed:
                raise RuntimeError("AsyncCorridorsMCTS has been closed")

            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self._executor, self._impl.get_visit_count
            )
        finally:
            await self._release_operation_lock()

    async def display_async(self, flip: bool = False) -> str:
        """Get board display asynchronously."""
        await self._acquire_operation_lock("display")
        try:
            if self._closed:
                raise RuntimeError("AsyncCorridorsMCTS has been closed")

            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self._executor, lambda: self._impl.display(flip)
            )
        finally:
            await self._release_operation_lock()

    async def is_terminal_async(self) -> bool:
        """Check if position is terminal asynchronously."""
        await self._acquire_operation_lock("is_terminal")
        try:
            if self._closed:
                raise RuntimeError("AsyncCorridorsMCTS has been closed")

            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self._executor, self._impl.is_terminal)
        finally:
            await self._release_operation_lock()

    async def reset_async(self) -> None:
        """Reset to initial state asynchronously."""
        await self._acquire_operation_lock("reset")
        try:
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
        finally:
            await self._release_operation_lock()

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
    with proper cleanup and resource management. Thread-safe
    with per-instance locks to prevent race conditions.
    """

    def __init__(self) -> None:
        self._instances: Dict[str, AsyncCorridorsMCTS] = {}
        self._registry_lock = asyncio.Lock()  # Protects registry dict operations
        self._instance_locks: Dict[str, asyncio.Lock] = {}  # Per-instance API locks

    async def get_with_lock(
        self, game_id: str
    ) -> Tuple[AsyncCorridorsMCTS, asyncio.Lock]:
        """
        Get instance with its dedicated lock for atomic operations.

        Returns tuple of (mcts_instance, lock) for atomic API operations.
        Raises ValueError if game_id not found.
        """
        async with self._registry_lock:
            if game_id not in self._instances:
                raise ValueError(f"Game {game_id} not found in registry")

            # Ensure per-instance lock exists
            if game_id not in self._instance_locks:
                self._instance_locks[game_id] = asyncio.Lock()

            return self._instances[game_id], self._instance_locks[game_id]

    async def get_or_create(
        self,
        game_id: str,
        c: float = sqrt(0.025),
        seed: int = 42,
        min_simulations: int = 100,
        max_simulations: int = 10000,
        sim_increment: int = 50,
        use_rollout: bool = True,
        eval_children: bool = False,
        use_puct: bool = False,
        use_probs: bool = False,
        decide_using_visits: bool = True,
    ) -> AsyncCorridorsMCTS:
        """Get existing instance or create new one with atomic registry operations."""
        async with self._registry_lock:
            if game_id not in self._instances:
                # Create new instance with corrected constructor signature
                self._instances[game_id] = AsyncCorridorsMCTS(
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

                # Create corresponding API lock
                self._instance_locks[game_id] = asyncio.Lock()

            return self._instances[game_id]

    async def get(self, game_id: str) -> Optional[AsyncCorridorsMCTS]:
        """Get existing instance."""
        async with self._registry_lock:
            return self._instances.get(game_id)

    async def remove(self, game_id: str) -> None:
        """Remove and cleanup instance with atomic operations."""
        async with self._registry_lock:
            instance = self._instances.pop(game_id, None)
            # Also cleanup the per-instance lock
            self._instance_locks.pop(game_id, None)

            if instance:
                await instance.cleanup()

    async def cleanup_all(self) -> None:
        """Cleanup all instances with atomic operations."""
        async with self._registry_lock:
            cleanup_tasks = [
                instance.cleanup() for instance in self._instances.values()
            ]

            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)

            self._instances.clear()
            self._instance_locks.clear()

    async def list_games(self) -> List[str]:
        """List all game IDs with active instances."""
        async with self._registry_lock:
            return list(self._instances.keys())

    @property
    def instance_count(self) -> int:
        """Get the number of active instances."""
        return len(self._instances)
