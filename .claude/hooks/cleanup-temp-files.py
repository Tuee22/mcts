#!/usr/bin/env python
"""
Cleanup hook to remove temporary files from project root.
Runs after any agent completion to prevent accumulation of temp files.
"""

import os
import glob
import sys
from pathlib import Path


def cleanup_temp_files(project_root: str) -> int:
    """Remove temporary files created by agents in project root."""

    # Patterns for temporary files that shouldn't be in project root
    temp_patterns = [
        "*.py",  # Temporary Python scripts
        "*.sh",  # Temporary shell scripts
        "*.txt",  # Temporary text files
        "*.md",  # Temporary markdown (except README.md, CLAUDE.md)
        "analyze_*.py",
        "check_*.py",
        "run_*.py",
        "test_*.py",
        "execute_*.py",
        "project_*.py",
        "direct_*.py",
        "final_*.py",
        "complete_*.py",
        "comprehensive_*.py",
        "systematic_*.py",
        "proactive_*.py",
        "simple_*.py",
        "actual_*.py",
        "examine_*.py",
        "*_execution*.py",
        "*_runner*.py",
        "*_test*.py",
        "*_analysis*.py",
        "command_execution.sh",
        "docker_test_execution.sh",
        "execute_tests.sh",
        "run_check.sh",
        "test_execution.sh",
        "*.log",
    ]

    # Protected files that should NOT be deleted
    protected_files = {
        "README.md",
        "CLAUDE.md",
        "pyproject.toml",
        "pytest.ini",
        ".gitignore",
        ".dockerignore",
    }

    os.chdir(project_root)
    removed_count = 0

    for pattern in temp_patterns:
        for file_path in glob.glob(pattern):
            # Skip directories
            if os.path.isdir(file_path):
                continue

            # Skip protected files
            if file_path in protected_files:
                continue

            # Skip files in subdirectories (only clean root)
            if "/" in file_path:
                continue

            # Additional safety check - don't delete important files
            if file_path.endswith((".md", ".txt")) and not any(
                temp_prefix in file_path
                for temp_prefix in [
                    "temp_",
                    "test_",
                    "execute_",
                    "run_",
                    "check_",
                    "analyze_",
                    "project_",
                    "direct_",
                    "final_",
                    "complete_",
                ]
            ):
                continue

            try:
                os.remove(file_path)
                print(f"Removed temporary file: {file_path}", file=sys.stderr)
                removed_count += 1
            except Exception as e:
                print(f"Failed to remove {file_path}: {e}", file=sys.stderr)

    if removed_count > 0:
        print(
            f"Cleaned up {removed_count} temporary files from project root",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    sys.exit(cleanup_temp_files(project_dir))
