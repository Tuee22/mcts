"""
State Synchronization Integration Tests

Tests for frontend-backend state consistency, recovery mechanisms,
and conflict resolution that could affect E2E test reliability.
"""

import asyncio
import copy
import json
import time
import uuid
from typing import Dict, List, Optional, Union, Mapping
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.types import (
    StateManagerTestData,
    ConflictTestData,
    SyncTestData,
    TestEventData,
)


def get_list_from_state(state_dict: Dict[str, object], key: str) -> List[object]:
    """Helper to safely get a list from state dict."""
    value = state_dict[key]
    if isinstance(value, list):
        return value
    raise TypeError(f"Expected list for key '{key}', got {type(value)}")


def get_dict_from_state(state_dict: Dict[str, object], key: str) -> Dict[str, object]:
    """Helper to safely get a dict from state dict."""
    value = state_dict[key]
    if isinstance(value, dict):
        return value
    raise TypeError(f"Expected dict for key '{key}', got {type(value)}")


class MockStateManager:
    """Mock state manager for testing synchronization."""

    def __init__(self) -> None:
        self.frontend_state: Dict[str, object] = {}
        self.backend_state: Dict[str, object] = {}
        self.sync_events: List[Dict[str, object]] = []
        self.conflicts: List[Dict[str, object]] = []
        self.snapshots: List[Dict[str, object]] = []

    def update_frontend_state(self, updates: Mapping[str, object]) -> None:
        """Update frontend state."""
        self.frontend_state.update(updates)
        self.sync_events.append(
            {
                "source": "frontend",
                "type": "state_update",
                "updates": updates,
                "timestamp": time.time(),
            }
        )

    def update_backend_state(self, updates: Mapping[str, object]) -> None:
        """Update backend state."""
        self.backend_state.update(updates)
        self.sync_events.append(
            {
                "source": "backend",
                "type": "state_update",
                "updates": updates,
                "timestamp": time.time(),
            }
        )

    def create_snapshot(self, source: str) -> str:
        """Create state snapshot."""
        snapshot_id = str(uuid.uuid4())
        state_copy = copy.deepcopy(
            self.frontend_state if source == "frontend" else self.backend_state
        )

        snapshot = {
            "snapshot_id": snapshot_id,
            "source": source,
            "state": state_copy,
            "timestamp": time.time(),
        }

        self.snapshots.append(snapshot)
        return snapshot_id

    def detect_conflicts(self) -> List[Dict[str, object]]:
        """Detect state conflicts between frontend and backend."""
        conflicts = []

        for key in set(self.frontend_state.keys()) | set(self.backend_state.keys()):
            frontend_value = self.frontend_state.get(key)
            backend_value = self.backend_state.get(key)

            if frontend_value != backend_value:
                conflict = {
                    "key": key,
                    "frontend_value": frontend_value,
                    "backend_value": backend_value,
                    "timestamp": time.time(),
                }
                conflicts.append(conflict)

        self.conflicts.extend(conflicts)
        return conflicts

    def resolve_conflict(self, key: str, resolution_strategy: str) -> object:
        """Resolve state conflict using specified strategy."""
        if resolution_strategy == "backend_wins":
            resolved_value = self.backend_state.get(key)
            self.frontend_state[key] = resolved_value
        elif resolution_strategy == "frontend_wins":
            resolved_value = self.frontend_state.get(key)
            self.backend_state[key] = resolved_value
        elif resolution_strategy == "latest_timestamp":
            # In real implementation, would use timestamps
            resolved_value = self.backend_state.get(key)  # Default to backend
            self.frontend_state[key] = resolved_value
        else:
            raise ValueError(f"Unknown resolution strategy: {resolution_strategy}")

        self.sync_events.append(
            {
                "source": "resolver",
                "type": "conflict_resolved",
                "key": key,
                "strategy": resolution_strategy,
                "resolved_value": resolved_value,
                "timestamp": time.time(),
            }
        )

        return resolved_value

    def is_synchronized(self) -> bool:
        """Check if frontend and backend states are synchronized."""
        return self.frontend_state == self.backend_state


@pytest.fixture
def state_manager() -> MockStateManager:
    """Create state manager for testing."""
    return MockStateManager()


@pytest.mark.asyncio
class TestBasicStateSynchronization:
    """Test basic state synchronization between frontend and backend."""

    async def test_initial_state_sync(self, state_manager: MockStateManager) -> None:
        """Test initial state synchronization."""
        # Backend initializes game state
        initial_state = {
            "game_id": "sync-test-game",
            "board_size": 9,
            "current_player": 0,
            "players": [{"x": 4, "y": 8}, {"x": 4, "y": 0}],
            "walls": [],
            "walls_remaining": [10, 10],
            "move_history": [],
        }

        state_manager.update_backend_state(initial_state)

        # Simulate sync to frontend
        state_manager.update_frontend_state(copy.deepcopy(initial_state))

        # Should be synchronized
        assert state_manager.is_synchronized()
        assert state_manager.frontend_state["game_id"] == "sync-test-game"
        assert state_manager.backend_state["game_id"] == "sync-test-game"

    async def test_move_state_propagation(
        self, state_manager: MockStateManager
    ) -> None:
        """Test move state propagation from frontend to backend."""
        # Initialize synchronized state
        initial_state = {
            "current_player": 0,
            "players": [{"x": 4, "y": 8}, {"x": 4, "y": 0}],
            "move_history": [],
        }

        state_manager.update_frontend_state(initial_state)
        state_manager.update_backend_state(copy.deepcopy(initial_state))

        # Frontend makes move
        move_updates = {
            "current_player": 1,
            "players": [{"x": 4, "y": 7}, {"x": 4, "y": 0}],  # Player 0 moved up
            "move_history": ["move_up"],
        }

        state_manager.update_frontend_state(move_updates)

        # Backend processes and confirms move
        state_manager.update_backend_state(move_updates)

        # Should be synchronized after move
        assert state_manager.is_synchronized()
        assert state_manager.frontend_state["current_player"] == 1
        assert (
            len(get_list_from_state(state_manager.frontend_state, "move_history")) == 1
        )

    async def test_backend_state_broadcast(
        self, state_manager: MockStateManager
    ) -> None:
        """Test backend broadcasting state changes to frontend."""
        # Initialize state
        initial_state = {
            "game_id": "broadcast-test",
            "walls": [],
            "walls_remaining": [10, 10],
        }

        state_manager.update_backend_state(initial_state)

        # Backend processes wall placement
        wall_updates = {
            "walls": [{"x": 3, "y": 4, "orientation": "horizontal"}],
            "walls_remaining": [9, 10],
        }

        state_manager.update_backend_state(wall_updates)

        # Simulate broadcast to frontend
        current_backend_state = copy.deepcopy(state_manager.backend_state)
        state_manager.frontend_state = current_backend_state

        # Should be synchronized
        assert state_manager.is_synchronized()
        assert len(get_list_from_state(state_manager.frontend_state, "walls")) == 1
        walls_remaining = get_list_from_state(
            state_manager.frontend_state, "walls_remaining"
        )
        assert walls_remaining[0] == 9


@pytest.mark.asyncio
class TestConflictDetectionAndResolution:
    """Test detection and resolution of state conflicts."""

    async def test_conflict_detection(self, state_manager: MockStateManager) -> None:
        """Test detection of state conflicts."""
        # Set up conflicting states
        state_manager.update_frontend_state(
            {"current_player": 0, "last_move": "move_up"}
        )

        state_manager.update_backend_state(
            {"current_player": 1, "last_move": "move_down"}
        )

        # Detect conflicts
        conflicts = state_manager.detect_conflicts()

        # Should detect conflicts
        assert len(conflicts) == 2
        conflict_keys = [conflict["key"] for conflict in conflicts]
        assert "current_player" in conflict_keys
        assert "last_move" in conflict_keys

    async def test_backend_wins_resolution(
        self, state_manager: MockStateManager
    ) -> None:
        """Test conflict resolution with backend wins strategy."""
        # Set up conflict
        state_manager.update_frontend_state({"score": 100})
        state_manager.update_backend_state({"score": 150})

        # Resolve with backend wins
        conflicts = state_manager.detect_conflicts()
        assert len(conflicts) == 1

        resolved_value = state_manager.resolve_conflict("score", "backend_wins")

        # Backend value should win
        assert resolved_value == 150
        assert state_manager.is_synchronized()
        assert state_manager.frontend_state["score"] == 150

    async def test_frontend_wins_resolution(
        self, state_manager: MockStateManager
    ) -> None:
        """Test conflict resolution with frontend wins strategy."""
        # Set up conflict
        state_manager.update_frontend_state({"user_preference": "dark_theme"})
        state_manager.update_backend_state({"user_preference": "light_theme"})

        # Resolve with frontend wins
        conflicts = state_manager.detect_conflicts()
        resolved_value = state_manager.resolve_conflict(
            "user_preference", "frontend_wins"
        )

        # Frontend value should win
        assert resolved_value == "dark_theme"
        assert state_manager.is_synchronized()
        assert state_manager.backend_state["user_preference"] == "dark_theme"

    async def test_latest_timestamp_resolution(
        self, state_manager: MockStateManager
    ) -> None:
        """Test conflict resolution with latest timestamp strategy."""
        # Set up conflict
        state_manager.update_frontend_state({"game_status": "paused"})
        await asyncio.sleep(0.01)  # Small delay
        state_manager.update_backend_state({"game_status": "active"})

        # Resolve with latest timestamp (backend is newer)
        conflicts = state_manager.detect_conflicts()
        resolved_value = state_manager.resolve_conflict(
            "game_status", "latest_timestamp"
        )

        # Later value should win (backend in this mock)
        assert resolved_value == "active"
        assert state_manager.is_synchronized()

    async def test_multiple_conflict_resolution(
        self, state_manager: MockStateManager
    ) -> None:
        """Test resolution of multiple simultaneous conflicts."""
        # Set up multiple conflicts
        state_manager.update_frontend_state(
            {"player_name": "Alice", "turn_timer": 30, "ui_theme": "dark"}
        )

        state_manager.update_backend_state(
            {
                "player_name": "Bob",
                "turn_timer": 45,
                "ui_theme": "dark",  # No conflict here
            }
        )

        # Resolve conflicts
        conflicts = state_manager.detect_conflicts()
        assert len(conflicts) == 2  # player_name and turn_timer

        for conflict in conflicts:
            if conflict["key"] == "player_name":
                state_manager.resolve_conflict("player_name", "frontend_wins")
            elif conflict["key"] == "turn_timer":
                state_manager.resolve_conflict("turn_timer", "backend_wins")

        # Should be synchronized after resolution
        assert state_manager.is_synchronized()
        assert state_manager.backend_state["player_name"] == "Alice"  # Frontend won
        assert state_manager.frontend_state["turn_timer"] == 45  # Backend won


@pytest.mark.asyncio
class TestStateSnapshots:
    """Test state snapshot functionality for recovery."""

    async def test_snapshot_creation(self, state_manager: MockStateManager) -> None:
        """Test creating state snapshots."""
        # Set up state
        test_state = {"game_id": "snapshot-test", "current_player": 1, "move_count": 15}

        state_manager.update_frontend_state(test_state)

        # Create snapshot
        snapshot_id = state_manager.create_snapshot("frontend")

        # Verify snapshot
        assert len(state_manager.snapshots) == 1
        snapshot = state_manager.snapshots[0]
        assert snapshot["snapshot_id"] == snapshot_id
        assert snapshot["source"] == "frontend"
        snapshot_state = get_dict_from_state(snapshot, "state")
        assert snapshot_state["game_id"] == "snapshot-test"

    async def test_snapshot_recovery(self, state_manager: MockStateManager) -> None:
        """Test state recovery from snapshot."""
        # Initial state
        initial_state = {"game_phase": "midgame", "moves_made": 10}

        state_manager.update_backend_state(initial_state)
        snapshot_id = state_manager.create_snapshot("backend")

        # State gets corrupted
        state_manager.update_backend_state(
            {"game_phase": "corrupted", "moves_made": -1}
        )

        # Recover from snapshot
        recovery_snapshot = next(
            snap
            for snap in state_manager.snapshots
            if snap["snapshot_id"] == snapshot_id
        )

        snapshot_state = recovery_snapshot["state"]
        if isinstance(snapshot_state, dict):
            state_manager.backend_state = copy.deepcopy(snapshot_state)
        else:
            raise TypeError(
                f"Expected dict for snapshot state, got {type(snapshot_state)}"
            )

        # Should be recovered
        assert state_manager.backend_state["game_phase"] == "midgame"
        assert state_manager.backend_state["moves_made"] == 10

    async def test_periodic_snapshots(self, state_manager: MockStateManager) -> None:
        """Test periodic snapshot creation."""
        # Simulate multiple state changes with snapshots
        for i in range(5):
            state_updates = {"turn_number": i, "last_action": f"action_{i}"}

            state_manager.update_backend_state(state_updates)

            # Create snapshot every 2 turns
            if i % 2 == 0:
                state_manager.create_snapshot("backend")

        # Should have 3 snapshots (turns 0, 2, 4)
        assert len(state_manager.snapshots) == 3
        snapshot_0_state = get_dict_from_state(state_manager.snapshots[0], "state")
        snapshot_1_state = get_dict_from_state(state_manager.snapshots[1], "state")
        snapshot_2_state = get_dict_from_state(state_manager.snapshots[2], "state")
        assert snapshot_0_state["turn_number"] == 0
        assert snapshot_1_state["turn_number"] == 2
        assert snapshot_2_state["turn_number"] == 4


@pytest.mark.asyncio
class TestNetworkInterruptionHandling:
    """Test state synchronization during network interruptions."""

    async def test_state_queue_during_disconnect(
        self, state_manager: MockStateManager
    ) -> None:
        """Test state change queuing during network disconnection."""
        # Initial synchronized state
        initial_state = {"connection_status": "connected", "pending_moves": []}
        state_manager.update_frontend_state(initial_state)
        state_manager.update_backend_state(copy.deepcopy(initial_state))

        # Simulate network interruption
        state_manager.update_frontend_state({"connection_status": "disconnected"})

        # Frontend continues to make changes while disconnected
        queued_changes = [
            {"pending_moves": ["move_1"]},
            {"pending_moves": ["move_1", "move_2"]},
            {"pending_moves": ["move_1", "move_2", "move_3"]},
        ]

        for change in queued_changes:
            state_manager.update_frontend_state(change)

        # Reconnection occurs
        state_manager.update_frontend_state({"connection_status": "connected"})

        # Apply queued changes to backend
        for change in queued_changes:
            state_manager.update_backend_state(change)

        # Should be synchronized after reconnection
        final_moves = get_list_from_state(state_manager.frontend_state, "pending_moves")
        assert state_manager.is_synchronized()
        assert len(final_moves) == 3

    async def test_partial_sync_recovery(self, state_manager: MockStateManager) -> None:
        """Test recovery from partial synchronization failure."""
        # Start with synchronized state
        initial_state = {
            "field_a": "value_a",
            "field_b": "value_b",
            "field_c": "value_c",
        }

        state_manager.update_frontend_state(initial_state)
        state_manager.update_backend_state(copy.deepcopy(initial_state))

        # Partial update fails (only some fields sync)
        update = {
            "field_a": "new_value_a",
            "field_b": "new_value_b",
            "field_c": "new_value_c",
        }

        state_manager.update_frontend_state(update)

        # Only partial update reaches backend
        partial_update = {
            "field_a": "new_value_a",
            # field_b and field_c missing due to network issue
        }

        state_manager.update_backend_state(partial_update)

        # Detect partial sync failure
        conflicts = state_manager.detect_conflicts()
        assert len(conflicts) == 2  # field_b and field_c

        # Recover by re-syncing missing fields
        missing_fields = {"field_b": "new_value_b", "field_c": "new_value_c"}

        state_manager.update_backend_state(missing_fields)

        # Should be synchronized after recovery
        assert state_manager.is_synchronized()

    async def test_state_reconciliation_after_reconnect(
        self, state_manager: MockStateManager
    ) -> None:
        """Test state reconciliation after reconnection."""
        # Both frontend and backend change state while disconnected
        base_state = {"version": 1, "data": "base"}

        state_manager.update_frontend_state(base_state)
        state_manager.update_backend_state(copy.deepcopy(base_state))

        # Simulate disconnection - both sides change independently
        state_manager.update_frontend_state(
            {"version": 2, "data": "frontend_changes", "frontend_only": "frontend_data"}
        )

        state_manager.update_backend_state(
            {"version": 2, "data": "backend_changes", "backend_only": "backend_data"}
        )

        # Reconnection triggers reconciliation
        conflicts = state_manager.detect_conflicts()
        assert len(conflicts) >= 2  # data field conflict + unique fields

        # Reconcile by merging changes
        merged_state = {
            "version": 2,
            "data": "merged_changes",  # Manual merge resolution
            "frontend_only": "frontend_data",
            "backend_only": "backend_data",
        }

        state_manager.frontend_state = merged_state
        state_manager.backend_state = copy.deepcopy(merged_state)

        # Should be reconciled
        assert state_manager.is_synchronized()


@pytest.mark.asyncio
class TestRealTimeStateSynchronization:
    """Test real-time state synchronization scenarios."""

    async def test_rapid_state_updates(self, state_manager: MockStateManager) -> None:
        """Test handling of rapid state updates."""
        # Initialize state
        state_manager.update_backend_state({"counter": 0})
        state_manager.update_frontend_state({"counter": 0})

        # Rapid updates
        for i in range(1, 11):
            # Backend updates
            state_manager.update_backend_state({"counter": i})

            # Small delay to simulate network latency
            await asyncio.sleep(0.001)

            # Frontend receives update
            state_manager.update_frontend_state({"counter": i})

        # Should handle rapid updates correctly
        assert state_manager.is_synchronized()
        assert state_manager.frontend_state["counter"] == 10

    async def test_concurrent_field_updates(
        self, state_manager: MockStateManager
    ) -> None:
        """Test concurrent updates to different fields."""
        # Initialize with multiple fields
        initial_state = {"player_1_score": 0, "player_2_score": 0, "game_timer": 300}

        state_manager.update_frontend_state(initial_state)
        state_manager.update_backend_state(copy.deepcopy(initial_state))

        # Concurrent updates to different fields
        async def update_scores() -> None:
            state_manager.update_backend_state({"player_1_score": 10})
            await asyncio.sleep(0.01)
            state_manager.update_frontend_state({"player_1_score": 10})

        async def update_timer() -> None:
            state_manager.update_backend_state({"game_timer": 295})
            await asyncio.sleep(0.01)
            state_manager.update_frontend_state({"game_timer": 295})

        # Run concurrent updates
        await asyncio.gather(update_scores(), update_timer())

        # Should handle concurrent updates
        assert state_manager.frontend_state["player_1_score"] == 10
        assert state_manager.frontend_state["game_timer"] == 295
        assert state_manager.is_synchronized()

    async def test_event_ordering_preservation(
        self, state_manager: MockStateManager
    ) -> None:
        """Test preservation of event ordering in state updates."""
        # Initialize state
        state_manager.update_backend_state({"move_sequence": []})

        # Sequence of moves that must be preserved in order
        moves = ["move_1", "move_2", "move_3", "move_4", "move_5"]

        for move in moves:
            current_sequence = state_manager.backend_state.get("move_sequence", [])
            if isinstance(current_sequence, list):
                updated_sequence = current_sequence + [move]
            else:
                updated_sequence = [move]
            state_manager.update_backend_state({"move_sequence": updated_sequence})

        # Frontend should receive moves in correct order
        state_manager.update_frontend_state(
            {"move_sequence": state_manager.backend_state["move_sequence"]}
        )

        # Verify ordering
        assert state_manager.frontend_state["move_sequence"] == moves
        assert state_manager.is_synchronized()


@pytest.mark.asyncio
class TestPerformanceAndScalability:
    """Test performance aspects of state synchronization."""

    async def test_large_state_synchronization(
        self, state_manager: MockStateManager
    ) -> None:
        """Test synchronization of large state objects."""
        # Create large state
        large_state = {
            "board_cells": [
                [{"state": "empty"} for _ in range(100)] for _ in range(100)
            ],
            "game_history": [f"move_{i}" for i in range(1000)],
            "player_stats": {f"player_{i}": {"score": i} for i in range(50)},
        }

        start_time = time.time()

        state_manager.update_backend_state(large_state)
        state_manager.update_frontend_state(copy.deepcopy(large_state))

        sync_time = time.time() - start_time

        # Should handle large states efficiently
        assert state_manager.is_synchronized()
        assert sync_time < 1.0  # Should complete within 1 second for mock

    async def test_high_frequency_updates(
        self, state_manager: MockStateManager
    ) -> None:
        """Test high-frequency state updates."""
        # Initialize state
        state_manager.update_backend_state({"high_freq_counter": 0})

        update_count = 100
        start_time = time.time()

        # High-frequency updates
        for i in range(1, update_count + 1):
            state_manager.update_backend_state({"high_freq_counter": i})
            if i % 10 == 0:  # Sync every 10 updates
                state_manager.update_frontend_state({"high_freq_counter": i})

        total_time = time.time() - start_time

        # Should handle high frequency efficiently
        updates_per_second = update_count / total_time
        assert updates_per_second > 1000  # Should be fast for mock

    async def test_memory_efficiency(self, state_manager: MockStateManager) -> None:
        """Test memory efficiency of state management."""
        # Create and cleanup many state versions
        for version in range(100):
            state = {
                "version": version,
                "temp_data": f"data_{version}" * 100,  # Some bulk data
            }

            state_manager.update_backend_state(state)

            # Simulate cleanup of old data
            if version > 10:
                # Keep only recent state
                state_manager.backend_state = {"version": version}

        # Should maintain reasonable memory usage
        final_state = state_manager.backend_state
        assert final_state["version"] == 99
        assert "temp_data" not in final_state  # Old data cleaned up
