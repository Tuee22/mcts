"""Type stubs for websockets library."""

from typing import AsyncContextManager, Awaitable, Generator, Iterator, TypeVar

from .client import WebSocketClientProtocol

Self = TypeVar("Self", bound="Connect")

class Connect:
    def __await__(self) -> Generator[object, object, WebSocketClientProtocol]: ...
    async def __aenter__(self) -> WebSocketClientProtocol: ...
    async def __aexit__(
        self, exc_type: object, exc_val: object, exc_tb: object
    ) -> None: ...

def connect(uri: str, **kwargs: object) -> Connect: ...
