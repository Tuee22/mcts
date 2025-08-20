"""Type stubs for argparse."""

from typing import Dict, List, Optional, Union

class Namespace:
    def __init__(self, **kwargs: object) -> None: ...
    def __getattr__(self, name: str) -> object: ...
    def __setattr__(self, name: str, value: object) -> None: ...

class ArgumentParser:
    def __init__(self, description: Optional[str] = None, **kwargs: object) -> None: ...
    def add_argument(
        self,
        *args: str,
        choices: Optional[List[object]] = None,
        default: object = None,
        help: Optional[str] = None,
        action: Optional[str] = None,
        type: Optional[object] = None,
        **kwargs: object,
    ) -> object: ...
    def parse_args(self, args: Optional[List[str]] = None) -> Namespace: ...
