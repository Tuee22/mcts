"""Type stubs for requests library."""

from typing import Dict, List, Optional, Union, TypeVar

_JsonValue = Union[
    None, bool, int, float, str, List["_JsonValue"], Dict[str, "_JsonValue"]
]

class Response:
    status_code: int
    headers: Dict[str, str]
    text: str
    content: bytes

    def json(self) -> _JsonValue: ...
    def raise_for_status(self) -> None: ...

def get(
    url: str,
    params: Optional[Dict[str, Union[str, int]]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: Optional[float] = None,
    **kwargs: object,
) -> Response: ...
def post(
    url: str,
    data: Optional[Union[str, bytes, Dict[str, object]]] = None,
    json: Optional[object] = None,
    params: Optional[Dict[str, Union[str, int]]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: Optional[float] = None,
    **kwargs: object,
) -> Response: ...
def delete(
    url: str,
    params: Optional[Dict[str, Union[str, int]]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: Optional[float] = None,
    **kwargs: object,
) -> Response: ...
