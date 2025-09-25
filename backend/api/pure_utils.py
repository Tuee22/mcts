"""
Functional utility functions to replace imperative loops and mutations.

All functions in this module are pure and use functional programming patterns.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, TypeVar, Union

# Type variables for generic functions
T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


def validate_websocket_data(
    raw_data: object,
) -> Dict[str, Union[str, int, float, bool]]:
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
