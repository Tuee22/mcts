"""Backend C++ build management for JIT compilation."""

import logging
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from backend.utils.types import (
    Architecture,
    BuildConfig,
    BuildResult,
    Result,
    ValidationResult,
)

logger = logging.getLogger(__name__)


def detect_architecture() -> Architecture:
    """Detect system architecture using pattern matching."""
    machine = platform.machine().lower()
    return (
        Architecture.AMD64
        if machine in ["x86_64", "amd64"]
        else (
            Architecture.ARM64
            if machine in ["aarch64", "arm64"]
            else Architecture.AMD64
        )  # default
    )


def get_so_architecture(so_path: Path) -> Optional[Architecture]:
    """Detect architecture of existing .so file using file command."""
    if not so_path.exists():
        return None

    try:
        result = subprocess.run(
            ["file", "-L", str(so_path)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = (result.stdout or "").lower()

        return (
            Architecture.AMD64
            if any(pattern in output for pattern in ["x86-64", "x86_64"])
            else (
                Architecture.ARM64
                if any(pattern in output for pattern in ["arm aarch64", "aarch64"])
                else None
            )
        )
    except (
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
        FileNotFoundError,
    ):
        return None


def check_build_needed(config: BuildConfig, arch: Architecture) -> ValidationResult:
    """Check if C++ backend needs rebuilding."""
    so_name = "_corridors_mcts.so"
    so_path = config.corridors_dir / so_name
    arch_so_path = config.corridors_dir / f"{so_name[:-3]}_{arch.value}.so"

    return (
        ValidationResult.invalid(f"Missing {so_name}")
        if not so_path.exists()
        else (
            ValidationResult.invalid(
                f"Architecture mismatch: found {get_so_architecture(so_path)}, need {arch}"
            )
            if (so_arch := get_so_architecture(so_path)) and so_arch != arch
            else (
                ValidationResult.valid(f"Can link from {arch_so_path.name}")
                if arch_so_path.exists() and not so_path.exists()
                else ValidationResult.valid("Build is up to date")
            )
        )
    )


def run_scons_command(config: BuildConfig, args: list[str]) -> Result[str, str]:
    """Run scons build command functionally."""
    cmd = ["scons"] + (args or [])
    logger.info(f"Running: {' '.join(cmd)} in {config.backend_core_dir}")

    try:
        result = subprocess.run(
            cmd,
            cwd=str(config.backend_core_dir),
            capture_output=True,
            text=True,
            timeout=config.timeout,
        )

        return (
            Result.success("SCons build successful")
            if result.returncode == 0
            else Result.failure(
                f"SCons build failed: {str(result.stderr) if result.stderr else 'Unknown error'}"
            )
        )
    except subprocess.TimeoutExpired:
        return Result.failure(f"SCons build timed out after {config.timeout} seconds")
    except Exception as e:
        return Result.failure(f"SCons build error: {e}")


def create_architecture_link(
    config: BuildConfig, arch: Architecture
) -> Result[str, str]:
    """Create symlink from architecture-specific .so to main .so."""
    so_name = "_corridors_mcts.so"
    so_path = config.corridors_dir / so_name
    arch_so_path = config.corridors_dir / f"{so_name[:-3]}_{arch.value}.so"

    if not arch_so_path.exists():
        return Result.failure(f"Architecture-specific file not found: {arch_so_path}")

    try:
        # Remove existing symlink/file if present
        (so_path.unlink() if so_path.exists() or so_path.is_symlink() else None)

        # Create relative symlink
        os.chdir(config.corridors_dir)
        os.symlink(arch_so_path.name, so_name)
        return Result.success(f"Created symlink: {so_name} -> {arch_so_path.name}")
    except Exception as e:
        return Result.failure(f"Failed to create symlink: {e}")


def validate_backend_module(config: BuildConfig) -> Result[str, str]:
    """Validate that the built .so file is loadable."""
    try:
        sys.path.insert(0, str(config.corridors_dir.parent))
        from corridors import corridors_mcts  # noqa: F401

        return Result.success("C++ module loads successfully")
    except ImportError as e:
        return Result.failure(f"Failed to import C++ module: {e}")


class BackendBuilder:
    """Manages C++ backend builds with functional architecture awareness."""

    def __init__(self, config: BuildConfig):
        self.config = config
        self.arch = detect_architecture()

    def build(self) -> bool:
        """Build C++ backend if needed using functional pipeline."""
        logger.info(f"🔍 Checking C++ backend for architecture: {self.arch.value}")

        validation = check_build_needed(self.config, self.arch)
        logger.info(f"Build check: {validation.reason}")

        # Early return for valid builds
        if validation.is_valid:
            so_name = "_corridors_mcts.so"
            arch_so_path = (
                self.config.corridors_dir / f"{so_name[:-3]}_{self.arch.value}.so"
            )
            so_path = self.config.corridors_dir / so_name

            # Try linking if needed
            if arch_so_path.exists() and not so_path.exists():
                logger.info(
                    f"🔗 Linking architecture-specific .so file for {self.arch.value}"
                )
                result = create_architecture_link(self.config, self.arch)
                if result.is_success:
                    logger.info(result.value)
                    return True
                else:
                    logger.error(result.value)
                    return False

            logger.info("✅ C++ backend already built and compatible")
            return True

        # Build pipeline
        logger.info(
            f"🔧 Building C++ backend for {self.arch.value} ({validation.reason})"
        )

        # Clean existing incompatible file
        so_path = self.config.corridors_dir / "_corridors_mcts.so"
        (so_path.unlink() if so_path.exists() else None)
        if so_path.exists():
            logger.info("🗑️  Removed incompatible .so file")

        # Build steps using functional pipeline
        clean_result = run_scons_command(self.config, ["-c", "-Q"])
        if not clean_result.is_success:
            logger.error(f"Failed to clean: {clean_result.value}")
            return False

        build_result = run_scons_command(self.config, ["-Q"])
        if not build_result.is_success:
            logger.error(f"❌ {build_result.value}")
            return False

        # Create architecture-specific copy
        if so_path.exists():
            arch_so_path = (
                self.config.corridors_dir / f"_corridors_mcts_{self.arch.value}.so"
            )
            try:
                shutil.copy2(so_path, arch_so_path)
                logger.info(
                    f"📦 Created architecture-specific copy: {arch_so_path.name}"
                )
            except Exception as e:
                logger.warning(f"Could not create architecture copy: {e}")

        logger.info(f"✅ C++ backend build complete for {self.arch.value}")
        return True

    def validate(self) -> bool:
        """Validate that the built .so file is loadable."""
        result = validate_backend_module(self.config)
        if result.is_success:
            logger.info(f"✅ {result.value}")
            return True
        else:
            logger.error(f"❌ {result.value}")
            return False
