"""Main entrypoint for JIT build and server startup."""

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, NoReturn, Optional

from backend.utils.backend_builder import BackendBuilder
from backend.utils.frontend_builder import FrontendBuilder
from backend.utils.types import BuildConfig, BuildStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def check_playwright_installation() -> bool:
    """Check if Playwright browsers are installed functionally."""
    cache_dir = Path.home() / ".cache" / "ms-playwright"
    return cache_dir.exists() and any(cache_dir.iterdir())


def install_playwright_browsers(timeout: int = 300) -> bool:
    """Install Playwright browsers functionally."""
    if check_playwright_installation():
        logger.info("✅ Playwright browsers already installed")
        return True

    logger.info("📥 Installing Playwright browsers...")
    try:
        result = subprocess.run(
            ["playwright", "install"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode == 0:
            logger.info("✅ Playwright browsers installed")
            return True
        else:
            logger.error(
                f"Playwright install failed: {str(result.stderr) if result.stderr else 'Unknown error'}"
            )
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"Playwright install timed out after {timeout} seconds")
        return False
    except Exception as e:
        logger.error(f"Failed to install Playwright browsers: {e}")
        return False


def execute_build_component(
    name: str,
    build_func: Callable[[], bool],
    validate_func: Optional[Callable[[], bool]] = None,
) -> bool:
    """Execute a build component with optional validation."""
    try:
        success = build_func()
        return validate_func() if success and validate_func else success
    except Exception as e:
        logger.error(f"{name} build error: {e}")
        return False


def run_build_pipeline(config: BuildConfig) -> BuildStatus:
    """Run build pipeline functionally."""
    logger.info("🚀 Starting MCTS container setup...")

    # Create builders
    frontend_builder = FrontendBuilder(config)
    backend_builder = BackendBuilder(config)

    # Execute build pipeline using functional composition
    playwright_success = execute_build_component(
        "Playwright", lambda: install_playwright_browsers(config.timeout)
    )

    frontend_success = execute_build_component(
        "Frontend", frontend_builder.build, frontend_builder.validate
    )

    backend_success = execute_build_component(
        "Backend", backend_builder.build, backend_builder.validate
    )

    # Create immutable build status
    status = (
        BuildStatus()
        .with_playwright(playwright_success)
        .with_frontend(frontend_success)
        .with_backend(backend_success)
    )

    # Log build summary functionally
    logger.info("=" * 50)
    logger.info("Build Summary:")
    for name, status_emoji in status.summary.items():
        logger.info(f"  {name.capitalize()}: {status_emoji}")
    logger.info("=" * 50)

    return status


def start_server(config: BuildConfig, status: BuildStatus) -> NoReturn:
    """Start server based on build status."""
    if not status.can_start_server:
        logger.error("❌ Cannot start server: Backend build failed")
        sys.exit(1)

    if not status.frontend:
        logger.warning("⚠️  Frontend build failed - API will work but UI unavailable")

    logger.info("🎯 Starting server on port 8000...")
    os.chdir(config.app_root)

    try:
        os.execvp("poetry", ["poetry", "run", "server"])
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)


class EntryPoint:
    """Main orchestrator for JIT builds and server startup."""

    def __init__(self) -> None:
        self.config = BuildConfig(app_root=Path("/app"))

    def run(self) -> NoReturn:
        """Main entrypoint execution using functional pipeline."""
        try:
            # Run functional build pipeline
            build_status = run_build_pipeline(self.config)

            # Start server
            start_server(self.config, build_status)
        except KeyboardInterrupt:
            logger.info("\n👋 Shutting down gracefully...")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            sys.exit(1)


def main() -> NoReturn:
    """Main entry point for the script."""
    entrypoint = EntryPoint()
    entrypoint.run()


if __name__ == "__main__":
    main()
