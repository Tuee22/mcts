"""Type stubs for _pytest.monkeypatch."""

from typing import Union

class MonkeyPatch:
    def setattr(
        self,
        target: Union[str, object],
        name: Union[str, object],
        value: object = ...,
        raising: bool = True,
    ) -> None: ...
