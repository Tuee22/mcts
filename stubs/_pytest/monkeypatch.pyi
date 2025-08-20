"""Type stubs for _pytest.monkeypatch."""

from typing import Union, Callable

class MonkeyPatch:
    def setattr(
        self,
        target: Union[str, object],
        name: Union[str, object],
        value: Union[
            str, int, bool, Callable[..., Union[str, int, bool, None]], None
        ] = ...,
        raising: bool = True,
    ) -> None: ...
