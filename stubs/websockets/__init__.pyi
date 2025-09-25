"""Type stubs for websockets library."""

from typing import (
    AsyncContextManager,
    Awaitable,
    Generator,
    Iterator,
    TypeVar,
    Optional,
    Dict,
)

from .client import WebSocketClientProtocol, ConnectionClosed

Self = TypeVar("Self", bound="Connect")

class Connect:
    def __await__(self) -> Generator[object, object, WebSocketClientProtocol]: ...
    async def __aenter__(self) -> WebSocketClientProtocol: ...
    async def __aexit__(
        self, exc_type: object, exc_val: object, exc_tb: object
    ) -> None: ...

def connect(
    uri: str,
    *,
    timeout: Optional[float] = None,
    extra_headers: Optional[Dict[str, str]] = None,
    **kwargs: object,
) -> Connect: ...

# Export common exceptions
__all__ = ["connect", "WebSocketClientProtocol", "ConnectionClosed"]
