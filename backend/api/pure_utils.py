"""
Functional utility functions to replace imperative loops and mutations.

All functions in this module are pure and use functional programming patterns.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, TypeVar, Union, Tuple
from datetime import datetime, timezone

# Type variables for generic functions
T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


def validate_websocket_data(
    raw_data: object,
) -> Dict[str, Union[str, int, float, bool, Dict[str, object]]]:
    """
    Validate and transform WebSocket message data functionally.

    Replaces the imperative loop in server.py with functional operations.
    """
    # Ensure we have a dict-like object
    if not (hasattr(raw_data, "items") and callable(getattr(raw_data, "items"))):
        return {"error": "Invalid message format"}

    # Transform all key-value pairs functionally
    return dict(
        map(
            lambda item: (_sanitize_key(item[0]), _sanitize_value(item[1])),
            filter(
                lambda item: item[1] is not None,
                raw_data.items(),
            ),
        )
    )


def _sanitize_key(key: object) -> str:
    """Convert any key to string."""
    return str(key)


def _sanitize_value(value: object) -> Union[str, int, float, bool]:
    """Convert value to acceptable WebSocket type."""
    return (
        value
        if isinstance(value, (str, int, float, bool))
        else "null"
        if value is None
        else str(value)
    )


def find_first_match(items: List[T], predicate: Callable[[T], bool]) -> Optional[T]:
    """
    Find first item matching predicate, returning None if not found.

    Functional replacement for for-loop searches.
    """
    matches = filter(predicate, items)
    return next(matches, None)


def safe_get(
    dictionary: Dict[K, V], key: K, default: Optional[V] = None
) -> Optional[V]:
    """
    Safely get value from dictionary without mutation.

    More explicit than dict.get for type safety.
    """
    return dictionary.get(key, default)


def count_where(items: List[T], predicate: Callable[[T], bool]) -> int:
    """
    Count items matching predicate.

    Functional replacement for counting loops.
    """
    return sum(1 for item in items if predicate(item))


# ==================== Game Cleanup Utilities ====================


def partition_by_age(
    items: Dict[str, T],
    get_timestamp: Callable[[T], datetime],
    now: datetime,
    max_age_seconds: int,
) -> Tuple[List[str], List[str]]:
    """
    Partition items into active and inactive based on age.

    Pure function that separates items by whether they exceed the max age.
    Returns (active_ids, inactive_ids).
    """

    def is_inactive(item: T) -> bool:
        return (now - get_timestamp(item)).total_seconds() > max_age_seconds

    inactive = [k for k, v in items.items() if is_inactive(v)]
    active = [k for k in items.keys() if k not in inactive]

    return active, inactive


def filter_dict(
    dictionary: Dict[K, V], predicate: Callable[[K, V], bool]
) -> Dict[K, V]:
    """
    Create new dict with only items matching predicate.

    Pure function for functional dictionary filtering.
    """
    return {k: v for k, v in dictionary.items() if predicate(k, v)}


def calculate_age_seconds(game: T, get_timestamp: Callable[[T], datetime]) -> float:
    """
    Calculate age of an item in seconds.

    Pure function for age calculation.
    """
    now = datetime.now(timezone.utc)
    return (now - get_timestamp(game)).total_seconds()


def categorize_age(age_seconds: float) -> str:
    """
    Categorize age into human-readable buckets.

    Pure function for age categorization using functional patterns.
    """
    return (
        "under_1_min"
        if age_seconds < 60
        else "1_to_5_min"
        if age_seconds < 300
        else "5_to_30_min"
        if age_seconds < 1800
        else "over_30_min"
    )


def get_last_activity_timestamp(game: object) -> datetime:
    """
    Extract last activity timestamp from a game object.

    Uses fallback chain for backward compatibility.
    """
    # Use functional approach with ternary operators for fallback chain
    last_activity = getattr(game, "last_activity", None)
    return (
        last_activity
        if isinstance(last_activity, datetime)
        else (
            created_at
            if isinstance(created_at := getattr(game, "created_at", None), datetime)
            else datetime.now(timezone.utc)
        )
    )
