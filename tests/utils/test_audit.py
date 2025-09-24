#!/usr/bin/env python3
"""Test audit utility to detect potential silent failures in the test suite."""

import ast
import os
import sys
from pathlib import Path
from typing import List, Tuple


class TestAuditor(ast.NodeVisitor):
    """AST visitor to audit test files for silent failure patterns."""

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.issues: List[Tuple[int, str]] = []

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        """Check for bare except clauses or overly broad exception handling."""
        if node.type is None:
            # Bare except:
            self.issues.append(
                (node.lineno, "Bare 'except:' clause - could silence errors")
            )
        elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
            # except Exception:
            self.issues.append(
                (
                    node.lineno,
                    "Generic 'except Exception:' - should catch specific exceptions",
                )
            )

        # Check for empty except blocks that just pass
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            self.issues.append(
                (
                    node.lineno,
                    "Empty except block with only 'pass' - may silence errors",
                )
            )

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Check for pytest skip/xfail patterns that might hide issues."""
        if isinstance(node.func, ast.Attribute):
            # Check for pytest.mark.skip or similar
            if (
                isinstance(node.func.value, ast.Attribute)
                and isinstance(node.func.value.value, ast.Name)
                and node.func.value.value.id == "pytest"
                and node.func.value.attr == "mark"
                and node.func.attr in ["skip", "skipif", "xfail"]
            ):
                reason = "No reason provided"
                if node.args and isinstance(node.args[0], ast.Constant):
                    reason = str(node.args[0].value)
                elif node.keywords:
                    for kw in node.keywords:
                        if kw.arg == "reason" and isinstance(kw.value, ast.Constant):
                            reason = str(kw.value.value)

                self.issues.append(
                    (node.lineno, f"Test marked as {node.func.attr}: {reason}")
                )

        self.generic_visit(node)


def audit_file(filepath: Path) -> List[Tuple[int, str]]:
    """Audit a single Python file for silent failure patterns."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(filepath))
        auditor = TestAuditor(str(filepath))
        auditor.visit(tree)
        return auditor.issues

    except (SyntaxError, UnicodeDecodeError) as e:
        return [(0, f"Could not parse file: {e}")]


def audit_directory(directory: Path, pattern: str = "test_*.py") -> None:
    """Audit all test files in a directory."""
    print(f"🔍 Auditing test files in {directory}")
    print(f"📋 Looking for pattern: {pattern}")
    print("=" * 60)

    total_files = 0
    total_issues = 0

    # Find all test files
    test_files = list(directory.rglob(pattern))
    if not test_files:
        print(f"⚠️  No test files found matching pattern '{pattern}' in {directory}")
        return

    for filepath in sorted(test_files):
        relative_path = filepath.relative_to(directory)
        issues = audit_file(filepath)

        if issues:
            print(f"\n📁 {relative_path}")
            for line_no, message in issues:
                if line_no > 0:
                    print(f"  🔴 Line {line_no}: {message}")
                else:
                    print(f"  🔴 {message}")
            total_issues += len(issues)

        total_files += 1

    print("\n" + "=" * 60)
    if total_issues > 0:
        print(f"❌ Found {total_issues} potential issues in {total_files} files")
        sys.exit(1)
    else:
        print(f"✅ No silent failure patterns detected in {total_files} files")


def main() -> None:
    """Main audit function."""
    if len(sys.argv) > 1:
        test_dir = Path(sys.argv[1])
    else:
        # Default to tests directory relative to this script
        test_dir = Path(__file__).parent.parent

    if not test_dir.exists():
        print(f"❌ Directory {test_dir} does not exist")
        sys.exit(1)

    print("🛡️  Test Suite Audit - Silent Failure Detection")
    print(f"🎯 Target directory: {test_dir.absolute()}")

    # Audit Python test files
    audit_directory(test_dir, "test_*.py")

    # Also check conftest.py files
    conftest_files = list(test_dir.rglob("conftest.py"))
    if conftest_files:
        print(f"\n🔍 Auditing {len(conftest_files)} conftest.py files")
        print("=" * 60)
        for filepath in sorted(conftest_files):
            relative_path = filepath.relative_to(test_dir)
            issues = audit_file(filepath)
            if issues:
                print(f"\n📁 {relative_path}")
                for line_no, message in issues:
                    if line_no > 0:
                        print(f"  🔴 Line {line_no}: {message}")
                    else:
                        print(f"  🔴 {message}")


if __name__ == "__main__":
    main()
