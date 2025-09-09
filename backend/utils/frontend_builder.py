"""Frontend React build management for JIT compilation."""

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from backend.utils.types import (
    Architecture,
    BuildConfig,
    InstallStrategy,
    Result,
    ValidationResult,
)

logger = logging.getLogger(__name__)


def detect_node_npm_availability() -> Result[tuple[str, str], str]:
    """Check Node.js and npm availability functionally."""
    try:
        node_result = subprocess.run(
            ["node", "--version"], capture_output=True, text=True, timeout=5
        )
        npm_result = subprocess.run(
            ["npm", "--version"], capture_output=True, text=True, timeout=5
        )

        return (
            Result.success(
                (
                    str(node_result.stdout).strip() if node_result.stdout else "",
                    str(npm_result.stdout).strip() if npm_result.stdout else "",
                )
            )
            if node_result.returncode == 0 and npm_result.returncode == 0
            else Result.failure("Node.js or npm not available")
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return Result.failure(f"Failed to check Node/npm: {e}")


def validate_frontend_build(config: BuildConfig) -> ValidationResult:
    """Validate frontend build status functionally."""
    build_dir = config.frontend_dir / "build"
    node_modules = config.frontend_dir / "node_modules"
    package_json = config.frontend_dir / "package.json"

    # Use functional validation chain
    validations = [
        (build_dir.exists(), "Build directory missing"),
        (
            any(build_dir.iterdir()) if build_dir.exists() else False,
            "Build directory empty",
        ),
        ((build_dir / "index.html").exists(), "Missing index.html in build"),
        (node_modules.exists(), "node_modules missing"),
        (package_json.exists(), "package.json missing"),
    ]

    failed = next((reason for valid, reason in validations if not valid), None)
    return (
        ValidationResult.invalid(failed)
        if failed
        else ValidationResult.valid("Build is up to date")
    )


def clean_npm_cache(config: BuildConfig) -> Result[str, str]:
    """Clean npm cache functionally."""
    try:
        subprocess.run(
            ["npm", "cache", "clean", "--force"],
            cwd=str(config.frontend_dir),
            capture_output=True,
            timeout=30,
        )
        return Result.success("npm cache cleaned")
    except Exception as e:
        return Result.failure(f"Failed to clean npm cache: {e}")


def handle_arm64_quirks(config: BuildConfig, arch: Architecture) -> None:
    """Handle ARM64-specific npm issues functionally."""
    if arch == Architecture.ARM64:
        package_lock = config.frontend_dir / "package-lock.json"
        if package_lock.exists():
            package_lock.unlink()
            logger.info("🔧 ARM64: Removed package-lock.json for fresh install")


def determine_install_strategy(
    config: BuildConfig, arch: Architecture
) -> InstallStrategy:
    """Determine npm install strategy based on conditions."""
    package_lock = config.frontend_dir / "package-lock.json"
    return (
        InstallStrategy.CI_INSTALL
        if package_lock.exists() and arch == Architecture.AMD64
        else InstallStrategy.FRESH_INSTALL
    )


def run_npm_command(
    config: BuildConfig,
    command: list[str],
    env_override: Optional[dict[str, str]] = None,
) -> Result[str, str]:
    """Run npm command functionally."""
    try:
        env = {**os.environ, **(env_override or {})}
        result = subprocess.run(
            command,
            cwd=str(config.frontend_dir),
            capture_output=True,
            text=True,
            env=env,
            timeout=config.timeout,
        )

        return (
            Result.success(f"{' '.join(command)} succeeded")
            if result.returncode == 0
            else Result.failure(
                f"{' '.join(command)} failed: {str(result.stderr) if result.stderr else 'Unknown error'}"
            )
        )
    except subprocess.TimeoutExpired:
        return Result.failure(
            f"{' '.join(command)} timed out after {config.timeout} seconds"
        )
    except Exception as e:
        return Result.failure(f"{' '.join(command)} error: {e}")


def validate_frontend_artifacts(config: BuildConfig) -> Result[str, str]:
    """Validate frontend build artifacts functionally."""
    build_dir = config.frontend_dir / "build"
    required_paths = [build_dir / "index.html", build_dir / "static"]

    # Check all required files exist
    missing = [path for path in required_paths if not path.exists()]
    if missing:
        return Result.failure(f"Missing required files: {[str(p) for p in missing]}")

    # Check static directory has content
    static_dir = build_dir / "static"
    return (
        Result.failure("Static directory is empty")
        if not any(static_dir.iterdir())
        else Result.success("Frontend build validated successfully")
    )


class FrontendBuilder:
    """Manages frontend React/npm builds with functional operations."""

    def __init__(self, config: BuildConfig):
        self.config = config
        self.arch = (
            Architecture.AMD64
            if os.uname().machine.lower() in ["x86_64", "amd64"]
            else (
                Architecture.ARM64
                if os.uname().machine.lower() in ["aarch64", "arm64"]
                else Architecture.AMD64
            )
        )

    def build(self) -> bool:
        """Build frontend using functional pipeline."""
        logger.info("🚀 Checking frontend build status")

        # Check Node/npm availability first
        node_check = detect_node_npm_availability()
        if not node_check.is_success:
            logger.error(f"❌ {node_check.value}")
            return False

        if isinstance(node_check.value, tuple) and len(node_check.value) == 2:
            node_version, npm_version = node_check.value
        else:
            logger.error(f"❌ Unexpected node check result: {node_check.value}")
            return False
        logger.info(f"Node: {node_version}, npm: {npm_version}")

        # Validate current build status
        validation = validate_frontend_build(self.config)
        logger.info(f"Build check: {validation.reason}")

        if validation.is_valid:
            logger.info("✅ Frontend already built")
            return True

        logger.info(f"📦 Building frontend ({validation.reason})")

        # Preparation pipeline
        clean_result = clean_npm_cache(self.config)
        if clean_result.is_success:
            logger.info("🧹 npm cache cleaned")
        else:
            logger.warning(clean_result.value)

        # Handle architecture-specific quirks
        handle_arm64_quirks(self.config, self.arch)

        # Remove corrupted build directory
        build_dir = self.config.frontend_dir / "build"
        if build_dir.exists() and not (build_dir / "index.html").exists():
            try:
                shutil.rmtree(build_dir)
                logger.info("🗑️  Removed corrupted build directory")
            except Exception as e:
                logger.warning(f"Could not remove build directory: {e}")

        # Install dependencies using strategy pattern
        strategy = determine_install_strategy(self.config, self.arch)
        install_command = (
            ["npm", "ci"]
            if strategy == InstallStrategy.CI_INSTALL
            else ["npm", "install"]
        )

        logger.info(f"📦 Running {' '.join(install_command)}")
        install_result = run_npm_command(self.config, install_command)
        if not install_result.is_success:
            logger.error(f"❌ {install_result.value}")
            return False
        logger.info(f"✅ {install_result.value}")

        # Build frontend
        logger.info("🔨 Running npm build")
        build_result = run_npm_command(
            self.config, ["npm", "run", "build"], {"CI": "false"}
        )
        if not build_result.is_success:
            logger.error(f"❌ {build_result.value}")
            return False
        logger.info("✅ Frontend build complete")

        return True

    def validate(self) -> bool:
        """Validate frontend build artifacts."""
        result = validate_frontend_artifacts(self.config)
        if result.is_success:
            logger.info(f"✅ {result.value}")
            return True
        else:
            logger.error(f"❌ {result.value}")
            return False
