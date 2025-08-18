"""Type stubs for argparse."""
from typing import Optional, List, Union, Dict, Any

class Namespace:
    def __init__(self, **kwargs: Any) -> None: ...
    def __getattr__(self, name: str) -> Any: ...
    def __setattr__(self, name: str, value: Any) -> None: ...

class ArgumentParser:
    def __init__(self, description: Optional[str] = None, **kwargs: Any) -> None: ...
    def add_argument(
        self, 
        *args: str,
        choices: Optional[List[Any]] = None,
        default: Any = None,
        help: Optional[str] = None,
        action: Optional[str] = None,
        type: Optional[Any] = None,
        **kwargs: Any
    ) -> Any: ...
    def parse_args(self, args: Optional[List[str]] = None) -> Namespace: ...