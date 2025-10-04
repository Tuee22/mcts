"""Type stubs for argparse."""

from typing import List, Optional, Sequence, TypeVar, overload

_T = TypeVar("_T")

class Namespace:
    def __init__(self, **kwargs: object) -> None: ...
    def __getattr__(self, name: str) -> object: ...
    def __setattr__(self, name: str, value: object) -> None: ...
    # Specific attributes for backend_build.py usage
    command: Optional[str]
    debug: bool
    profile: bool
    sanitize: bool
    test: bool

class _SubParsersAction:
    def add_parser(
        self, name: str, *, help: Optional[str] = None, **kwargs: object
    ) -> ArgumentParser: ...

class ArgumentParser:
    def __init__(
        self,
        description: Optional[str] = None,
        prog: Optional[str] = None,
        **kwargs: object,
    ) -> None: ...
    @overload
    def add_argument(
        self,
        *args: str,
        action: str = "store",
        choices: Optional[Sequence[object]] = None,
        default: object = None,
        help: Optional[str] = None,
        type: Optional[object] = None,
        **kwargs: object,
    ) -> object: ...
    @overload
    def add_argument(
        self,
        *args: str,
        action: str,
        help: Optional[str] = None,
        **kwargs: object,
    ) -> object: ...
    def add_subparsers(
        self,
        *,
        dest: Optional[str] = None,
        help: Optional[str] = None,
        **kwargs: object,
    ) -> _SubParsersAction: ...
    def parse_args(self, args: Optional[List[str]] = None) -> Namespace: ...
