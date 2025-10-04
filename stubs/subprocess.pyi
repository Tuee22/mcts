"""Type stubs for subprocess module."""

from typing import IO, Dict, Generic, List, Optional, Sequence, TypeVar, Union, overload

_T = TypeVar("_T", bound=Union[str, bytes])

class CalledProcessError(Exception):
    returncode: int
    cmd: Union[str, Sequence[str]]
    output: Optional[Union[str, bytes]]
    stderr: Optional[Union[str, bytes]]
    stdout: Optional[Union[str, bytes]]

class CompletedProcess(Generic[_T]):
    args: Union[str, Sequence[str]]
    returncode: int
    stdout: Optional[_T]
    stderr: Optional[_T]

    def check_returncode(self) -> None: ...

class Popen(Generic[_T]):
    def __init__(
        self,
        args: Union[str, Sequence[str]],
        bufsize: int = -1,
        executable: Optional[str] = None,
        stdin: Optional[Union[int, IO[str]]] = None,
        stdout: Optional[Union[int, IO[str]]] = None,
        stderr: Optional[Union[int, IO[str]]] = None,
        preexec_fn: Optional[object] = None,
        close_fds: bool = True,
        shell: bool = False,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        universal_newlines: bool = False,
        startupinfo: Optional[object] = None,
        creationflags: int = 0,
        restore_signals: bool = True,
        start_new_session: bool = False,
        pass_fds: Sequence[int] = (),
        text: Optional[bool] = None,
        encoding: Optional[str] = None,
        errors: Optional[str] = None,
    ) -> None: ...
    def communicate(
        self, input: Optional[Union[str, bytes]] = None, timeout: Optional[float] = None
    ) -> tuple[Optional[bytes], Optional[bytes]]: ...
    def wait(self, timeout: Optional[float] = None) -> int: ...
    def poll(self) -> Optional[int]: ...
    def terminate(self) -> None: ...
    def kill(self) -> None: ...

    returncode: Optional[int]
    pid: int

class TimeoutExpired(Exception):
    cmd: Union[str, Sequence[str]]
    timeout: float
    output: Optional[Union[str, bytes]]
    stdout: Optional[Union[str, bytes]]
    stderr: Optional[Union[str, bytes]]

# Overloads for subprocess.run based on text parameter
@overload
def run(
    args: Union[str, Sequence[str]],
    *,
    stdin: Optional[Union[int, IO[str]]] = None,
    input: Optional[str] = None,
    stdout: Optional[Union[int, IO[str]]] = None,
    stderr: Optional[Union[int, IO[str]]] = None,
    capture_output: bool = False,
    shell: bool = False,
    cwd: Optional[str] = None,
    timeout: Optional[float] = None,
    check: bool = False,
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    text: bool = True,
    env: Optional[Dict[str, str]] = None,
    universal_newlines: Optional[bool] = None,
) -> CompletedProcess[str]: ...
@overload
def run(
    args: Union[str, Sequence[str]],
    *,
    stdin: Optional[Union[int, IO[str]]] = None,
    input: Optional[str] = None,
    stdout: Optional[Union[int, IO[str]]] = None,
    stderr: Optional[Union[int, IO[str]]] = None,
    capture_output: bool = False,
    shell: bool = False,
    cwd: Optional[str] = None,
    timeout: Optional[float] = None,
    check: bool = False,
    encoding: str,
    errors: Optional[str] = None,
    text: Optional[bool] = None,
    env: Optional[Dict[str, str]] = None,
    universal_newlines: Optional[bool] = None,
) -> CompletedProcess[str]: ...
@overload
def run(
    args: Union[str, Sequence[str]],
    *,
    stdin: Optional[Union[int, IO[str]]] = None,
    input: Optional[str] = None,
    stdout: Optional[Union[int, IO[str]]] = None,
    stderr: Optional[Union[int, IO[str]]] = None,
    capture_output: bool = False,
    shell: bool = False,
    cwd: Optional[str] = None,
    timeout: Optional[float] = None,
    check: bool = False,
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    text: Optional[bool] = None,
    env: Optional[Dict[str, str]] = None,
    universal_newlines: bool = True,
) -> CompletedProcess[str]: ...
@overload
def run(
    args: Union[str, Sequence[str]],
    *,
    stdin: Optional[Union[int, IO[bytes]]] = None,
    input: Optional[bytes] = None,
    stdout: Optional[Union[int, IO[bytes]]] = None,
    stderr: Optional[Union[int, IO[bytes]]] = None,
    capture_output: bool = False,
    shell: bool = False,
    cwd: Optional[str] = None,
    timeout: Optional[float] = None,
    check: bool = False,
    encoding: None = None,
    errors: Optional[str] = None,
    text: bool = False,
    env: Optional[Dict[str, str]] = None,
    universal_newlines: bool = False,
) -> CompletedProcess[bytes]: ...

# Fallback overload for cases where text parameter is ambiguous
@overload
def run(
    args: Union[str, Sequence[str]],
    *,
    stdin: Optional[Union[int, IO[bytes]]] = None,
    input: Optional[bytes] = None,
    stdout: Optional[Union[int, IO[bytes]]] = None,
    stderr: Optional[Union[int, IO[bytes]]] = None,
    capture_output: bool = False,
    shell: bool = False,
    cwd: Optional[str] = None,
    timeout: Optional[float] = None,
    check: bool = False,
    encoding: None = None,
    errors: Optional[str] = None,
    text: None = None,
    env: Optional[Dict[str, str]] = None,
    universal_newlines: None = None,
) -> CompletedProcess[bytes]: ...

# Constants
PIPE: int
STDOUT: int
DEVNULL: int
