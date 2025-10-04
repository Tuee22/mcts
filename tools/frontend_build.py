#!/usr/bin/env python
"""
Frontend build management tool using Poetry.

This script ensures all frontend builds go to /opt/mcts/frontend-build/build
and provides validation, cleanup, and serving capabilities.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


class FrontendBuildManager:
    """Manages frontend builds with strict path enforcement."""

    def __init__(self) -> None:
        self.project_root = Path(__file__).parent.parent
        self.frontend_dir = self.project_root / "frontend"
        self.build_target = Path("/opt/mcts/frontend-build")
        self.build_output = self.build_target / "build"
        self.wrong_build_location = self.frontend_dir / "build"

    def validate_environment(self) -> bool:
        """Validate that we're in the correct environment for building."""
        print("🔍 Validating environment...")

        # Check if we're in Docker
        if not os.getenv("DOCKER_CONTAINER"):
            print("❌ This command must be run inside the Docker container")
            print("💡 Run: docker compose exec mcts poetry run frontend-build")
            return False

        # Check if frontend directory exists
        if not self.frontend_dir.exists():
            print(f"❌ Frontend directory not found: {self.frontend_dir}")
            return False

        # Check if build target directory exists
        if not self.build_target.exists():
            print(f"❌ Build target directory not found: {self.build_target}")
            print("💡 This should be created by Docker - check your container setup")
            return False

        # Check for wrong build location
        if self.wrong_build_location.exists():
            print(f"⚠️  Wrong build location detected: {self.wrong_build_location}")
            print("💡 Run 'poetry run frontend-build-clean' to remove it")

        print("✅ Environment validation passed")
        return True

    def run_command(
        self, cmd: List[str], description: str, cwd: Optional[Path] = None
    ) -> bool:
        """Run a command and handle output."""
        print(f"\n{'='*60}")
        print(f"Running: {description}")
        print(f"Command: {' '.join(cmd)}")
        if cwd:
            print(f"Working directory: {cwd}")
        print(f"{'='*60}")

        env = os.environ.copy()
        env["BUILD_PATH"] = str(self.build_output)

        result = subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env)
        success = result.returncode == 0

        if success:
            print(f"\n✅ {description} completed successfully")
        else:
            print(f"\n❌ {description} failed with return code {result.returncode}")

        return success

    def build(self, production: bool = True) -> bool:
        """Build the frontend application."""
        if not self.validate_environment():
            return False

        print(f"🏗️  Building frontend to {self.build_output}")

        # Change to build target directory
        os.chdir(self.build_target)

        # Set environment variables
        env = os.environ.copy()
        env["BUILD_PATH"] = str(self.build_output)
        if production:
            env["CI"] = "false"
            env["GENERATE_SOURCEMAP"] = "false"

        # Run npm build
        success = self.run_command(
            ["npm", "run", "build"],
            f"Frontend build ({'production' if production else 'development'})",
            cwd=self.build_target,
        )

        if success:
            # Validate output
            if (
                self.build_output.exists()
                and (self.build_output / "index.html").exists()
            ):
                print(f"✅ Frontend built successfully to {self.build_output}")
                self._show_build_info()
            else:
                print(f"❌ Build output not found at {self.build_output}")
                return False

        return success

    def check(self) -> bool:
        """Check for incorrect build locations and provide diagnostics."""
        print("🔍 Checking frontend build locations...")

        issues_found = False

        # Check for wrong build location
        if self.wrong_build_location.exists():
            print(f"❌ WRONG build location found: {self.wrong_build_location}")
            print(
                f"💡 This should not exist! Use 'poetry run frontend-build-clean' to remove"
            )
            issues_found = True

        # Check for correct build location
        if self.build_output.exists():
            if (self.build_output / "index.html").exists():
                print(f"✅ Correct build location found: {self.build_output}")
                self._show_build_info()
            else:
                print(f"⚠️  Build directory exists but incomplete: {self.build_output}")
                issues_found = True
        else:
            print(f"ℹ️  No build found at correct location: {self.build_output}")

        # Check backend server configuration
        server_py = self.project_root / "backend" / "api" / "server.py"
        if server_py.exists():
            with open(server_py) as f:
                content = f.read()
                if "/opt/mcts/frontend-build/build" in content:
                    print("✅ Backend server configured to serve from correct location")
                else:
                    print("❌ Backend server not configured for correct build location")
                    issues_found = True

        if not issues_found:
            print("🎉 All frontend build locations are correct!")

        return not issues_found

    def clean(self) -> bool:
        """Clean up incorrect build locations."""
        print("🧹 Cleaning incorrect build locations...")

        cleaned = False

        if self.wrong_build_location.exists():
            print(f"🗑️  Removing wrong build location: {self.wrong_build_location}")
            try:
                shutil.rmtree(self.wrong_build_location)
                print(f"✅ Removed {self.wrong_build_location}")
                cleaned = True
            except Exception as e:
                print(f"❌ Failed to remove {self.wrong_build_location}: {e}")
                return False

        # Clean any other wrong locations
        for wrong_path in [
            self.frontend_dir / "dist",
            self.project_root / "build",
            self.project_root / "dist",
        ]:
            if wrong_path.exists():
                print(f"🗑️  Removing wrong build location: {wrong_path}")
                try:
                    shutil.rmtree(wrong_path)
                    print(f"✅ Removed {wrong_path}")
                    cleaned = True
                except Exception as e:
                    print(f"❌ Failed to remove {wrong_path}: {e}")

        if not cleaned:
            print("✅ No incorrect build locations found")
        else:
            print("🎉 Cleanup completed!")

        return True

    def serve(self, port: int = 3000) -> bool:
        """Serve the built frontend for testing."""
        if not self.build_output.exists():
            print("❌ No build found. Run 'poetry run frontend-build' first")
            return False

        print(f"🚀 Serving frontend from {self.build_output} on port {port}")

        # Use npx serve to serve the built files
        return self.run_command(
            ["npx", "serve", "-s", str(self.build_output), "-p", str(port)],
            f"Serving frontend on port {port}",
        )

    def _show_build_info(self) -> None:
        """Show information about the current build."""
        if not self.build_output.exists():
            return

        try:
            # Get build size
            total_size = 0
            file_count = 0
            for file_path in self.build_output.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_count += 1

            print(f"📊 Build info:")
            print(f"   Location: {self.build_output}")
            print(f"   Files: {file_count}")
            print(f"   Size: {total_size / 1024 / 1024:.1f} MB")

            # Check for key files
            key_files = ["index.html", "static/js", "static/css"]
            for key_file in key_files:
                file_path = self.build_output / key_file
                if file_path.exists():
                    print(f"   ✅ {key_file}")
                else:
                    print(f"   ❌ {key_file}")

        except Exception:
            pass  # Don't fail on info display errors


def build() -> None:
    """Main entry point for frontend build."""
    parser = argparse.ArgumentParser(description="Build frontend application")
    parser.add_argument(
        "--dev", action="store_true", help="Development build (with source maps)"
    )
    args = parser.parse_args()

    manager = FrontendBuildManager()
    success = manager.build(production=not args.dev)
    sys.exit(0 if success else 1)


def check() -> None:
    """Main entry point for build location check."""
    manager = FrontendBuildManager()
    success = manager.check()
    sys.exit(0 if success else 1)


def clean() -> None:
    """Main entry point for cleaning incorrect builds."""
    manager = FrontendBuildManager()
    success = manager.clean()
    sys.exit(0 if success else 1)


def serve() -> None:
    """Main entry point for serving built frontend."""
    parser = argparse.ArgumentParser(description="Serve built frontend")
    parser.add_argument(
        "--port", "-p", type=int, default=3000, help="Port to serve on (default: 3000)"
    )
    args = parser.parse_args()

    assert isinstance(args.port, int)
    manager = FrontendBuildManager()
    success = manager.serve(port=args.port)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    # Default to build if run directly
    build()
