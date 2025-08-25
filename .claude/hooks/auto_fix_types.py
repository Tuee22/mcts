#!/usr/bin/env python3
"""
Auto-fix common type errors in Python files.

This script attempts to automatically fix common mypy errors:
- Missing type annotations on functions
- Missing return type annotations
- Import statements for common types
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


def get_mypy_errors() -> List[Dict[str, str]]:
    """Run mypy and parse errors."""
    result = subprocess.run(
        ["mypy", "--strict", ".", "--no-error-summary"],
        capture_output=True,
        text=True,
    )

    errors = []
    for line in result.stdout.splitlines():
        # Parse mypy error format: file.py:line: error: message [error-code]
        match = re.match(r"^(.+?):(\d+):\s*error:\s*(.+?)\s*\[(.+?)\]", line)
        if match:
            errors.append(
                {
                    "file": match.group(1),
                    "line": int(match.group(2)),
                    "message": match.group(3),
                    "code": match.group(4),
                }
            )

    return errors


def fix_missing_type_annotation(file_path: Path, line_num: int) -> bool:
    """Fix missing type annotation on function."""
    try:
        lines = file_path.read_text().splitlines()
        if line_num > len(lines):
            return False

        line_idx = line_num - 1
        line = lines[line_idx]

        # Simple heuristic: if it's a def without annotation, add -> None
        if re.match(r"^\s*def\s+\w+\s*\([^)]*\)\s*:", line):
            # Check if it already has a return type
            if " -> " not in line:
                # Add -> None before the colon
                lines[line_idx] = re.sub(r"(\))\s*:", r"\1 -> None:", line)
                file_path.write_text("\n".join(lines) + "\n")
                return True

    except Exception as e:
        print(f"Error fixing {file_path}:{line_num}: {e}")

    return False


def fix_missing_return_annotation(file_path: Path, line_num: int) -> bool:
    """Fix missing return type annotation."""
    # For now, same as missing type annotation
    return fix_missing_type_annotation(file_path, line_num)


def add_typing_imports(file_path: Path) -> bool:
    """Add common typing imports if needed."""
    try:
        content = file_path.read_text()
        lines = content.splitlines()

        # Check if we need typing imports
        needs_typing = False
        if re.search(r"\bList\[", content) and "from typing import" not in content:
            needs_typing = True
        if re.search(r"\bDict\[", content) and "from typing import" not in content:
            needs_typing = True
        if re.search(r"\bOptional\[", content) and "from typing import" not in content:
            needs_typing = True

        if needs_typing:
            # Find where to insert import (after other imports or at top)
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    insert_idx = i + 1
                elif line.strip() and not line.startswith("#"):
                    break

            # Add typing import
            lines.insert(insert_idx, "from typing import Any, Dict, List, Optional")
            file_path.write_text("\n".join(lines) + "\n")
            return True

    except Exception as e:
        print(f"Error adding imports to {file_path}: {e}")

    return False


def main() -> int:
    """Main auto-fix function."""
    print("🔧 Running automatic type error fixes...")

    errors = get_mypy_errors()
    if not errors:
        print("✅ No type errors found")
        return 0

    print(f"Found {len(errors)} type errors to fix")

    fixed_count = 0
    files_modified: Set[str] = set()

    for error in errors:
        file_path = Path(error["file"])

        # Skip virtual environment and third-party files
        if "venv/" in str(file_path) or "site-packages/" in str(file_path):
            continue

        # Handle specific error codes
        if error["code"] == "no-untyped-def":
            if fix_missing_type_annotation(file_path, error["line"]):
                fixed_count += 1
                files_modified.add(str(file_path))

        elif (
            error["code"] == "no-untyped-def"
            and "return type annotation" in error["message"]
        ):
            if fix_missing_return_annotation(file_path, error["line"]):
                fixed_count += 1
                files_modified.add(str(file_path))

    # Add typing imports where needed
    for file_str in files_modified:
        add_typing_imports(Path(file_str))

    print(f"✅ Fixed {fixed_count} errors in {len(files_modified)} files")

    # Run mypy again to check if all errors are fixed
    final_errors = get_mypy_errors()
    remaining = len([e for e in final_errors if "venv/" not in e["file"]])

    if remaining == 0:
        print("✅ All fixable type errors resolved")
        return 0
    else:
        print(f"⚠️  {remaining} type errors remain (may need manual fixes)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
