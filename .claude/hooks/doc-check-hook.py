#!/usr/bin/env python3
"""
Documentation consistency check wrapper.

Runs lightweight documentation checking only when relevant files are changed.
This prevents unnecessary overhead on general code edits.

Executes the doc-checker.py script inside the Docker container via Poetry.
"""

import json
import os
import sys
import subprocess
from pathlib import Path


def should_check_docs(tool_call_data: dict) -> bool:
    """
    Determine if documentation consistency checking is needed based on the files being edited.

    Check docs when:
    - Documentation files (.md, .rst, .txt) are changed
    - Public interface files (API modules, __init__.py) are changed
    - Configuration files that affect project structure are changed
    """
    try:
        file_path = tool_call_data.get("parameters", {}).get("file_path", "")

        if not file_path:
            return False

        path = Path(file_path)

        # Check for documentation files
        doc_extensions = {".md", ".rst", ".txt"}
        if path.suffix.lower() in doc_extensions:
            return True

        # Check for important project files
        important_files = {
            "README.md",
            "CLAUDE.md",
            "pyproject.toml",
            "setup.py",
            "requirements.txt",
            "Dockerfile",
            "docker-compose.yaml",
            ".gitignore",
            ".dockerignore",
        }
        if path.name in important_files:
            return True

        # Check for public interface files
        if path.name == "__init__.py" or path.name.endswith("_api.py"):
            return True

        # Check for changes in main project structure
        path_parts = path.parts
        if len(path_parts) > 0:
            # Changes in top-level directories that may affect docs
            top_level_dirs = {
                "backend",
                "frontend",
                "docker",
                "tests",
                "tools",
                "scripts",
            }
            if len(path_parts) >= 2 and path_parts[0] in top_level_dirs:
                return True

        return False

    except Exception:
        # If we can't determine, err on the side of not checking
        return False


def read_tool_call():
    """Read tool call data from stdin or environment."""
    try:
        # Try stdin first (Claude CLI provides on stdin)
        if not sys.stdin.isatty():
            input_data = sys.stdin.read().strip()
            if input_data:
                return json.loads(input_data)
    except:
        pass

    # Fall back to environment variable
    try:
        tool_call_json = os.environ.get("TOOL_CALL", "{}")
        return json.loads(tool_call_json)
    except:
        return {}


def get_docker_compose_dir():
    """Get the docker compose directory from CLAUDE_PROJECT_DIR."""
    project_root = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
    docker_dir = project_root / "docker"

    if docker_dir.exists():
        return docker_dir
    return None


def main() -> int:
    """Check if docs consistency check should run and execute if needed."""
    try:
        # Get the tool call data
        tool_call_data = read_tool_call()

        if not should_check_docs(tool_call_data):
            # Skip silently for non-documentation changes
            return 0

        # Get docker compose directory
        docker_dir = get_docker_compose_dir()

        if docker_dir:
            # Run documentation check inside container via Poetry
            cmd = [
                "docker",
                "compose",
                "exec",
                "-T",
                "mcts",
                "poetry",
                "run",
                "python",
                "/app/.claude/hooks/doc-checker.py",
            ]

            result = subprocess.run(
                cmd, cwd=docker_dir, capture_output=True, text=True, timeout=30
            )
        else:
            # Fall back to local execution if Docker not available
            # This allows the hook to work in environments without Docker
            checker_path = Path(__file__).parent / "doc-checker.py"
            result = subprocess.run(
                ["python", str(checker_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )

        # Only print output if there are issues
        if result.returncode != 0:
            print("📚 Documentation consistency check found issues:")
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)

        return result.returncode

    except subprocess.TimeoutExpired:
        print("Documentation check timed out", file=sys.stderr)
        return 0  # Don't block on timeout
    except Exception as e:
        print(f"Documentation check wrapper error: {e}", file=sys.stderr)
        return 0  # Don't block on wrapper errors


if __name__ == "__main__":
    sys.exit(main())
