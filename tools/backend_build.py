"""Backend build management for consistent SCons builds."""

import os
import subprocess
import sys
from pathlib import Path


def build(
    debug: bool = False,
    profile: bool = False,
    sanitize: bool = False,
    test: bool = False,
) -> None:
    """Build the C++ backend using SCons with proper target.

    Args:
        debug: Enable debug build with symbols
        profile: Enable profiling build with gprof
        sanitize: Enable AddressSanitizer build
        test: Build test executable instead of shared library
    """
    # Ensure we're in Docker container
    if not os.environ.get("DOCKER_CONTAINER"):
        print("Error: Backend build must run inside Docker container", file=sys.stderr)
        sys.exit(1)

    # Build directory based on environment
    target_dir = Path("/opt/mcts/backend-build")
    target_dir.mkdir(parents=True, exist_ok=True)

    # Change to backend/core directory
    core_dir = Path("/app/backend/core")
    if not core_dir.exists():
        print(f"Error: Backend core directory not found: {core_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Changing to build directory: {core_dir}")
    os.chdir(core_dir)

    # Build SCons command
    if test:
        # For test builds, use default target location
        cmd = ["scons", "test=1"]
    else:
        # For library builds, always use the volume mount target
        cmd = ["scons", f"target={target_dir}/_corridors_mcts"]

    # Add build flags
    if debug:
        cmd.append("debug=1")
    if profile:
        cmd.append("profile=1")
    if sanitize:
        cmd.append("sanitize=1")

    # Execute build
    print(f"Building backend: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        print("Backend build failed", file=sys.stderr)
        sys.exit(result.returncode)

    # Verify build output
    if test:
        test_exe = Path("_corridors_mcts")
        if test_exe.exists():
            print("✅ Backend test executable built successfully")
        else:
            print("Warning: Test executable not found after build")
    else:
        so_file = target_dir / "_corridors_mcts.so"
        if so_file.exists():
            print(f"✅ Backend shared library built successfully: {so_file}")
        else:
            print("Warning: Shared library not found after build")


def clean() -> None:
    """Clean backend build artifacts."""
    print("Cleaning backend build artifacts...")

    # Clean volume mount directory
    target_dir = Path("/opt/mcts/backend-build")
    if target_dir.exists():
        cleaned_files = []
        for file in target_dir.glob("*.so"):
            file.unlink()
            cleaned_files.append(str(file))

        if cleaned_files:
            print(f"Removed: {', '.join(cleaned_files)}")

    # Clean local build directory
    core_dir = Path("/app/backend/core")
    if core_dir.exists():
        os.chdir(core_dir)
        # Remove SCons database
        sconsign_file = Path(".sconsign.dblite")
        if sconsign_file.exists():
            sconsign_file.unlink()
            print("Removed SCons database file")

        # Remove test executable if it exists
        test_exe = Path("_corridors_mcts")
        if test_exe.exists():
            test_exe.unlink()
            print("Removed test executable")

    print("✅ Backend build cleaned")


def rebuild() -> None:
    """Clean and rebuild backend."""
    print("Rebuilding backend (clean + build)...")
    clean()
    build()


def debug() -> None:
    """Build backend in debug mode."""
    print("Building backend in debug mode...")
    build(debug=True)


def profile() -> None:
    """Build backend in profile mode."""
    print("Building backend in profile mode...")
    build(profile=True)


def sanitize() -> None:
    """Build backend with AddressSanitizer."""
    print("Building backend with AddressSanitizer...")
    build(sanitize=True)


def test() -> None:
    """Build backend test executable."""
    print("Building backend test executable...")
    build(test=True)


def main() -> None:
    """Main entry point for command-line usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Backend build management")
    parser.add_argument("--debug", action="store_true", help="Enable debug build")
    parser.add_argument("--profile", action="store_true", help="Enable profile build")
    parser.add_argument(
        "--sanitize", action="store_true", help="Enable sanitizer build"
    )
    parser.add_argument("--test", action="store_true", help="Build test executable")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    subparsers.add_parser("clean", help="Clean build artifacts")
    subparsers.add_parser("rebuild", help="Clean and rebuild")

    args = parser.parse_args()

    if args.command == "clean":
        clean()
    elif args.command == "rebuild":
        rebuild()
    else:
        build(
            debug=args.debug,
            profile=args.profile,
            sanitize=args.sanitize,
            test=args.test,
        )


if __name__ == "__main__":
    main()
