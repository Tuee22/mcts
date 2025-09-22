"""
Async wrapper for Corridors MCTS using asyncio and thread pools.

This module provides async-first interface to MCTS operations,
allowing proper integration with FastAPI and other async frameworks.
"""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum, auto
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
    NamedTuple,
)
from types import TracebackType
import functools

from pydantic import BaseModel, Field, field_validator
from corridors import _corridors_mcts

# Type variables for decorator typing
T = TypeVar("T")
P = ParamSpec("P")


class OperationStatus(Enum):
    """Enum for MCTS operation status with functional pattern matching."""

    IDLE = auto()
    RUNNING = auto()
    CANCELLED = auto()
    COMPLETED = auto()
    FAILED = auto()


class OperationState(NamedTuple):
    """Immutable operation state record."""

    status: OperationStatus
    operation_name: Optional[str]
    start_time: Optional[float]
    end_time: Optional[float]

    @classmethod
    def idle(cls) -> "OperationState":
        """Create idle state."""
        return cls(OperationStatus.IDLE, None, None, None)

    @classmethod
    def running(cls, operation_name: str, start_time: float) -> "OperationState":
        """Create running state."""
        return cls(OperationStatus.RUNNING, operation_name, start_time, None)

    def complete(self, end_time: float) -> "OperationState":
        """Create completed state from current state."""
        return self._replace(status=OperationStatus.COMPLETED, end_time=end_time)

    def cancel(self, end_time: float) -> "OperationState":
        """Create cancelled state from current state."""
        return self._replace(status=OperationStatus.CANCELLED, end_time=end_time)

    def fail(self, end_time: float) -> "OperationState":
        """Create failed state from current state."""
        return self._replace(status=OperationStatus.FAILED, end_time=end_time)

    @property
    def is_active(self) -> bool:
        """Check if operation is currently active."""
        return self.status == OperationStatus.RUNNING

    @property
    def elapsed_time(self) -> Optional[float]:
        """Calculate elapsed time for active operations."""
        return (
            time.time() - self.start_time
            if self.start_time and self.status == OperationStatus.RUNNING
            else None
        )


class MCTSConfig(BaseModel):
    """Pydantic model for MCTS configuration validation."""

    c: float = sqrt(0.025)
    seed: int = 42
    min_simulations: int = 100
    max_simulations: int = 10000
    sim_increment: int = 50
    use_rollout: bool = True
    eval_children: bool = False
    use_puct: bool = False
    use_probs: bool = False
    decide_using_visits: bool = True
    max_workers: int = 1

    @field_validator("c")
    @classmethod
    def validate_c(cls, v: float) -> float:
        """Ensure c > 0."""
        if v <= 0:
            raise ValueError("c must be greater than 0")
        return v

    @field_validator(
        "seed", "min_simulations", "max_simulations", "sim_increment", "max_workers"
    )
    @classmethod
    def validate_positive_int(cls, v: int) -> int:
        """Ensure positive integers."""
        if v < 1:
            raise ValueError("Value must be >= 1")
        return v

    @field_validator("max_workers")
    @classmethod
    def validate_max_workers(cls, v: int) -> int:
        """Ensure max_workers is between 1 and 4."""
        if not 1 <= v <= 4:
            raise ValueError("max_workers must be between 1 and 4")
        return v

    @field_validator("max_simulations")
    @classmethod
    def validate_max_simulations(cls, v: int) -> int:
        """Ensure max_simulations is reasonable (simplified validation)."""
        if v < 100:
            raise ValueError("max_simulations must be >= 100")
        return v


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
    Async wrapper for Corridors MCTS operations with functional state management.

    This class provides thread-safe async access to MCTS simulations,
    allowing cancellation and proper resource management using immutable patterns.
    """

    def __init__(
        self,
        config: MCTSConfig,
    ) -> None:
        # Store validated configuration
        self._config = config

        # Create C++ instance with validated configuration
        self._impl: MCTSProtocol = _corridors_mcts._corridors_mcts(
            self._config.c,
            self._config.seed,
            self._config.use_rollout,
            self._config.eval_children,
            self._config.use_puct,
            self._config.use_probs,
            self._config.decide_using_visits,
        )

        # Thread pool for async operations
        self._executor = ThreadPoolExecutor(max_workers=self._config.max_workers)

        # Cancellation support (immutable)
        self._cancel_flag = threading.Event()
        self._current_task: Optional[
            Union[asyncio.Task[int], asyncio.Future[int]]
        ] = None

        # General async lock for internal coordination
        self._lock = asyncio.Lock()
        self._closed = False

        # Immutable operation state management
        self._operation_state = OperationState.idle()
        self._operation_lock = asyncio.Lock()

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
        Acquire exclusive operation lock with fail-fast semantics using immutable state.

        Raises ConcurrencyViolationError if another operation is in progress.
        """
        async with self._operation_lock:
            # Check current state using pattern matching
            current_state = self._operation_state

            match current_state.status:
                case OperationStatus.RUNNING:
                    elapsed = current_state.elapsed_time or 0
                    raise ConcurrencyViolationError(
                        f"RACE CONDITION DETECTED: '{operation_name}' blocked by "
                        f"'{current_state.operation_name}' running for {elapsed:.3f}s"
                    )
                case OperationStatus.IDLE | OperationStatus.COMPLETED | OperationStatus.CANCELLED | OperationStatus.FAILED:
                    # Atomically transition to running state
                    self._operation_state = OperationState.running(
                        operation_name, time.time()
                    )
                case _:
                    raise ConcurrencyViolationError(
                        f"Invalid operation state: {current_state.status}"
                    )

    async def _release_operation_lock(self) -> None:
        """Release exclusive operation lock by transitioning to idle state."""
        current_time = time.time()

        # Create new idle state (functional transition)
        match self._operation_state.status:
            case OperationStatus.RUNNING:
                self._operation_state = self._operation_state.complete(current_time)
            case _:
                # Already released or in error state, transition to idle
                self._operation_state = OperationState.idle()

    def _run_simulations_batch(self, n: int, batch_size: int = 100) -> int:
        """Functional simulation runner that processes in batches."""
        simulations_completed = 0

        while simulations_completed < n and not self._cancel_flag.is_set():
            current_batch = min(batch_size, n - simulations_completed)
            try:
                self._impl.run_simulations(current_batch)
                simulations_completed += current_batch
            except Exception:
                break

        return simulations_completed

    async def _run_simulations_with_timeout(
        self, n: int, timeout: Optional[float]
    ) -> int:
        """Functional simulation runner with timeout and cancellation."""
        # Execute with timeout handling
        loop = asyncio.get_event_loop()
        task = loop.run_in_executor(
            self._executor, lambda: self._run_simulations_batch(n)
        )

        try:
            return await asyncio.wait_for(task, timeout) if timeout else await task
        except asyncio.TimeoutError:
            # Functional cancellation - set flag and wait for graceful completion
            self._cancel_flag.set()
            try:
                return await asyncio.wait_for(task, timeout=1.0)
            except asyncio.TimeoutError:
                return 0
        except asyncio.CancelledError:
            self._cancel_flag.set()
            raise

    async def run_simulations_async(
        self, n: int, timeout: Optional[float] = None
    ) -> int:
        """
        Run MCTS simulations asynchronously with functional timeout and cancellation.

        Returns the actual number of simulations completed.
        """
        await self._acquire_operation_lock("run_simulations")

        # Early validation using guard clauses
        if self._closed:
            await self._release_operation_lock()
            raise RuntimeError("AsyncCorridorsMCTS has been closed")

        if n <= 0:
            await self._release_operation_lock()
            return 0

        try:
            async with self._lock:
                # Cancel any existing task functionally
                current_task = self._current_task
                if current_task and not current_task.done():
                    self._cancel_flag.set()
                    await asyncio.gather(current_task, return_exceptions=True)

                # Reset cancellation state
                self._cancel_flag.clear()

                # Run simulations using functional approach
                self._current_task = asyncio.create_task(
                    self._run_simulations_with_timeout(n, timeout)
                )

                try:
                    return await self._current_task
                finally:
                    self._current_task = None

        finally:
            await self._release_operation_lock()

    async def ensure_sims_async(
        self, target_sims: int, timeout: Optional[float] = None
    ) -> int:
        """
        Ensure a minimum number of simulations using functional composition.

        Returns the total simulation count after completion.
        """
        current_sims: int = await self.get_visit_count_async()

        # Use ternary operator instead of if statement
        needed_sims = max(0, target_sims - current_sims)

        # Short-circuit if no simulations needed
        return (
            current_sims
            if needed_sims == 0
            else current_sims + await self.run_simulations_async(needed_sims, timeout)
        )

    async def make_move_async(self, action: str, flip: bool = False) -> None:
        """Make a move asynchronously using functional composition."""
        await self._acquire_operation_lock("make_move")

        # Guard clause for closed state
        if self._closed:
            await self._release_operation_lock()
            raise RuntimeError("AsyncCorridorsMCTS has been closed")

        try:
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
        """Get sorted actions asynchronously using functional composition."""
        await self._acquire_operation_lock("get_sorted_actions")

        # Guard clause for closed state
        if self._closed:
            await self._release_operation_lock()
            raise RuntimeError("AsyncCorridorsMCTS has been closed")

        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self._executor, lambda: self._impl.get_sorted_actions(flip)
            )
        finally:
            await self._release_operation_lock()

    async def choose_best_action_async(self, epsilon: float = 0.0) -> str:
        """Choose best action asynchronously using functional composition."""
        await self._acquire_operation_lock("choose_best_action")

        # Guard clause for closed state
        if self._closed:
            await self._release_operation_lock()
            raise RuntimeError("AsyncCorridorsMCTS has been closed")

        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self._executor, lambda: self._impl.choose_best_action(epsilon)
            )
        finally:
            await self._release_operation_lock()

    async def get_evaluation_async(self) -> Optional[float]:
        """Get evaluation asynchronously using functional composition."""
        await self._acquire_operation_lock("get_evaluation")

        # Guard clause for closed state
        if self._closed:
            await self._release_operation_lock()
            raise RuntimeError("AsyncCorridorsMCTS has been closed")

        try:
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

    async def _cancel_current_task(self) -> None:
        """Functionally cancel current task if exists."""
        current_task = self._current_task
        if current_task and not current_task.done():
            self._cancel_flag.set()
            await asyncio.gather(current_task, return_exceptions=True)

    async def reset_async(self) -> None:
        """Reset to initial state asynchronously using functional composition."""
        await self._acquire_operation_lock("reset")

        # Guard clause for closed state
        if self._closed:
            await self._release_operation_lock()
            raise RuntimeError("AsyncCorridorsMCTS has been closed")

        try:
            async with self._lock:
                # Cancel any running simulations functionally
                await self._cancel_current_task()

                # Reset state functionally
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
        """Clean up resources using functional composition."""
        # Guard clause - already closed
        if self._closed:
            return

        # Mark as closed atomically
        self._closed = True
        self.cancel_simulations()

        # Wait for any running tasks to complete functionally
        current_task = self._current_task
        if current_task and not current_task.done():
            await asyncio.gather(
                asyncio.wait_for(current_task, timeout=2.0), return_exceptions=True
            )

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
        config: MCTSConfig,
    ) -> AsyncCorridorsMCTS:
        """Get existing instance or create new one with atomic registry operations."""
        async with self._registry_lock:
            if game_id not in self._instances:
                # Create new instance with config
                self._instances[game_id] = AsyncCorridorsMCTS(config)

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
