#!/usr/bin/env python3
"""
Custom type safety checker for the MCTS project.
Ensures no usage of Any, cast, or type ignore comments.
"""

import ast
import re
import sys
from pathlib import Path
from typing import List, Set, Tuple


class TypeSafetyChecker(ast.NodeVisitor):
    """AST visitor to check for forbidden type constructs."""

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.errors: List[Tuple[int, int, str]] = []
        self.imported_names: Set[str] = set()

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check for imports of Any or cast from typing."""
        if node.module and "typing" in node.module:
            for alias in node.names:
                name = alias.name
                if name == "Any":
                    self.errors.append(
                        (
                            node.lineno,
                            node.col_offset,
                            "TYP001: Import of 'Any' is forbidden",
                        )
                    )
                elif name == "cast":
                    self.errors.append(
                        (
                            node.lineno,
                            node.col_offset,
                            "TYP002: Import of 'cast' is forbidden",
                        )
                    )
                # Track imported names for later checks
                self.imported_names.add(alias.asname or name)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """Check for usage of Any or cast if imported."""
        if isinstance(node.ctx, ast.Load):
            if node.id == "Any" and "Any" in self.imported_names:
                self.errors.append(
                    (
                        node.lineno,
                        node.col_offset,
                        "TYP001: Use of 'Any' type is forbidden",
                    )
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Check for cast() calls."""
        if isinstance(node.func, ast.Name) and node.func.id == "cast":
            self.errors.append(
                (
                    node.lineno,
                    node.col_offset,
                    "TYP002: Use of 'cast' function is forbidden",
                )
            )
        self.generic_visit(node)


def check_type_ignore_comments(
    content: str, filename: str
) -> List[Tuple[int, int, str]]:
    """Check for type ignore comments in the file."""
    errors = []
    lines = content.splitlines()

    for line_num, line in enumerate(lines, 1):
        if re.search(r"type:\s*ignore", line):
            # Find the column where the comment starts
            match = re.search(r"type:\s*ignore", line)
            if match:
                col = match.start()
                errors.append(
                    (line_num, col, "TYP003: Use of 'type ignore' comment is forbidden")
                )

    return errors


def check_file(filepath: Path) -> List[Tuple[str, int, int, str]]:
    """Check a single Python file for type safety violations."""
    try:
        content = filepath.read_text()

        # Parse the AST
        tree = ast.parse(content, str(filepath))

        # Check AST for Any and cast usage
        checker = TypeSafetyChecker(str(filepath))
        checker.visit(tree)

        # Check for type ignore comments
        comment_errors = check_type_ignore_comments(content, str(filepath))

        # Combine all errors
        all_errors = []
        for line, col, msg in checker.errors + comment_errors:
            all_errors.append((str(filepath), line, col, msg))

        return all_errors

    except Exception as e:
        print(f"Error checking {filepath}: {e}", file=sys.stderr)
        return []


def main() -> int:
    """Main entry point for the type safety checker."""
    # Get all Python files in the project
    root_path = Path(__file__).parent.parent
    python_files: List[Path] = []

    # Define directories to check
    check_dirs = ["backend", "tests", "tools"]

    for dir_name in check_dirs:
        dir_path = root_path / dir_name
        if dir_path.exists():
            python_files.extend(dir_path.rglob("*.py"))

    # Check each file
    all_errors: List[Tuple[str, int, int, str]] = []
    for filepath in python_files:
        # Skip stubs directory
        if "stubs" in filepath.parts:
            continue

        errors = check_file(filepath)
        all_errors.extend(errors)

    # Report errors
    if all_errors:
        print(f"\nFound {len(all_errors)} type safety violation(s):\n")
        for file_str, line, col, msg in sorted(all_errors):
            print(f"{file_str}:{line}:{col}: {msg}")
        return 1
    else:
        print("✅ No type safety violations found!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
