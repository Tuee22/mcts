"""Functional types and enums for build management."""

from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Generic, TypeVar, Union

T = TypeVar("T")
E = TypeVar("E")


class Architecture(Enum):
    """System architecture types."""

    AMD64 = "amd64"
    ARM64 = "arm64"

    @property
    def file_patterns(self) -> list[str]:
        """File command patterns for architecture detection."""
        return (
            ["x86-64", "x86_64"]
            if self == Architecture.AMD64
            else ["ARM aarch64", "aarch64"]
        )


class BuildResult(Enum):
    """Build operation results."""

    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"


class InstallStrategy(Enum):
    """NPM installation strategies."""

    CI_INSTALL = "ci"
    FRESH_INSTALL = "install"


@dataclass(frozen=True)
class BuildStatus:
    """Immutable build status tracking."""

    playwright: bool = False
    frontend: bool = False
    backend: bool = False

    def with_playwright(self, success: bool) -> "BuildStatus":
        """Return new status with playwright result."""
        return replace(self, playwright=success)

    def with_frontend(self, success: bool) -> "BuildStatus":
        """Return new status with frontend result."""
        return replace(self, frontend=success)

    def with_backend(self, success: bool) -> "BuildStatus":
        """Return new status with backend result."""
        return replace(self, backend=success)

    @property
    def can_start_server(self) -> bool:
        """Check if minimum requirements met for server startup."""
        return self.backend

    @property
    def summary(self) -> dict[str, str]:
        """Human-readable status summary."""
        return {
            component: "✅" if success else "❌"
            for component, success in [
                ("playwright", self.playwright),
                ("frontend", self.frontend),
                ("backend", self.backend),
            ]
        }


@dataclass(frozen=True)
class Result(Generic[T, E]):
    """Functional result type for error handling."""

    value: Union[T, E]
    is_success: bool

    @classmethod
    def success(cls, value: T) -> "Result[T, E]":
        """Create success result."""
        return cls(value=value, is_success=True)

    @classmethod
    def failure(cls, error: E) -> "Result[T, E]":
        """Create failure result."""
        return cls(value=error, is_success=False)

    def map(self, func: Callable[[T], T]) -> "Result[T, E]":
        """Apply function if success, otherwise return error."""
        if self.is_success:
            return Result.success(func(self.value))  # type: ignore
        else:
            return Result.failure(self.value)  # type: ignore

    def flat_map(self, func: Callable[[T], "Result[T, E]"]) -> "Result[T, E]":
        """Apply function returning Result if success."""
        if self.is_success:
            return func(self.value)  # type: ignore
        else:
            return Result.failure(self.value)  # type: ignore


@dataclass(frozen=True)
class BuildConfig:
    """Build configuration parameters."""

    app_root: Path
    timeout: int = 300
    clean_cache: bool = True

    @property
    def frontend_dir(self) -> Path:
        """Frontend directory path."""
        return self.app_root / "frontend"

    @property
    def backend_core_dir(self) -> Path:
        """Backend core directory path."""
        return self.app_root / "backend" / "core"

    @property
    def corridors_dir(self) -> Path:
        """Corridors Python module directory."""
        return self.app_root / "backend" / "python" / "corridors"


@dataclass(frozen=True)
class ValidationResult:
    """Validation operation result."""

    is_valid: bool
    reason: str

    @classmethod
    def valid(cls, reason: str = "Validation passed") -> "ValidationResult":
        """Create valid result."""
        return cls(is_valid=True, reason=reason)

    @classmethod
    def invalid(cls, reason: str) -> "ValidationResult":
        """Create invalid result."""
        return cls(is_valid=False, reason=reason)
