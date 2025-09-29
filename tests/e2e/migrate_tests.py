#!/usr/bin/env python3
"""
Automated migration script for e2e tests from async_playwright() to page fixture.

This script transforms tests to use the generic page fixture that runs on all browsers.
"""

import ast
import re
import shutil
import sys
from pathlib import Path
from typing import List, Tuple


class TestMigrator:
    """Migrates e2e tests from async_playwright() to page fixture."""

    def __init__(self, test_file_path: Path):
        self.test_file_path = test_file_path
        self.original_content = ""
        self.migrated_content = ""

    def backup_original(self) -> None:
        """Create backup of original file."""
        backup_path = self.test_file_path.with_suffix(".py.backup")
        shutil.copy2(self.test_file_path, backup_path)
        print(f"✅ Created backup: {backup_path}")

    def read_file(self) -> None:
        """Read the original test file."""
        with open(self.test_file_path, "r", encoding="utf-8") as f:
            self.original_content = f.read()

    def fix_imports(self) -> str:
        """Fix import statements."""
        content = self.original_content

        # Remove async_playwright import, add Page if not present
        if "async_playwright" in content:
            if "from playwright.async_api import Page" in content:
                # Page already imported, just remove async_playwright
                content = re.sub(r", async_playwright", "", content)
                content = re.sub(r"async_playwright, ", "", content)
                content = re.sub(
                    r"from playwright\.async_api import async_playwright", "", content
                )
            else:
                # Replace async_playwright with Page
                content = re.sub(
                    r"from playwright\.async_api import ([^,\n]*), async_playwright",
                    r"from playwright.async_api import \1, Page",
                    content,
                )
                content = re.sub(
                    r"from playwright\.async_api import async_playwright, ([^\n]*)",
                    r"from playwright.async_api import Page, \1",
                    content,
                )
                content = re.sub(
                    r"from playwright\.async_api import async_playwright",
                    r"from playwright.async_api import Page",
                    content,
                )

        return content

    def migrate_function_signatures(self, content: str) -> str:
        """Migrate function signatures to include page parameter."""
        # Pattern for function signatures without page parameter
        patterns = [
            # Class methods
            (
                r"async def (test_[^(]+)\(self, e2e_urls: Dict\[str, str\]\)",
                r"async def \1(self, page: Page, e2e_urls: Dict[str, str])",
            ),
            # Standalone functions
            (
                r"async def (test_[^(]+)\(e2e_urls: Dict\[str, str\]\)",
                r"async def \1(page: Page, e2e_urls: Dict[str, str])",
            ),
        ]

        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)

        return content

    def remove_playwright_blocks(self, content: str) -> str:
        """Remove async_playwright blocks and browser management."""
        # Remove async with async_playwright() blocks
        content = re.sub(r"\s*async with async_playwright\(\) as p:\s*\n", "", content)

        # Remove browser launch lines
        browser_launch_patterns = [
            r"\s*browser = await p\.chromium\.launch\([^)]*\)\s*\n",
            r"\s*browser = await p\.firefox\.launch\([^)]*\)\)\s*\n",
            r"\s*browser = await p\.webkit\.launch\([^)]*\)\)\s*\n",
        ]

        for pattern in browser_launch_patterns:
            content = re.sub(pattern, "", content)

        # Remove context creation
        content = re.sub(
            r"\s*context = await browser\.new_context\([^)]*\)\s*\n", "", content
        )

        # Remove page creation
        content = re.sub(r"\s*page = await context\.new_page\(\)\s*\n", "", content)

        # Remove try blocks (but keep the content)
        content = re.sub(r"\s*try:\s*\n", "", content)

        # Remove finally blocks and browser cleanup
        finally_pattern = r"\s*finally:\s*\n(?:\s*await [^.]*\.close\(\)\s*\n)*"
        content = re.sub(finally_pattern, "", content)

        return content

    def fix_indentation(self, content: str) -> str:
        """Fix indentation after removing nested blocks."""
        lines = content.split("\n")
        fixed_lines = []
        in_test_function = False
        dedent_amount = 0

        for line in lines:
            # Check if we're entering a test function
            if re.match(r"\s*async def test_", line):
                in_test_function = True
                dedent_amount = 0
                fixed_lines.append(line)
                continue

            # Check if we're leaving a test function
            if in_test_function and line.strip() and not line.startswith(" "):
                in_test_function = False
                dedent_amount = 0

            if in_test_function:
                # Detect if line was over-indented due to removed blocks
                if line.strip() and line.startswith("        "):  # 8+ spaces
                    # Find the actual indentation we need
                    if (
                        "await page." in line
                        or "connection_text" in line
                        or "print(" in line
                    ):
                        # These should be at 8 spaces (inside method)
                        stripped = line.lstrip()
                        line = "        " + stripped
                elif line.strip() and line.startswith("    "):
                    # Keep 4-space indentation as is
                    pass

            fixed_lines.append(line)

        return "\n".join(fixed_lines)

    def migrate_file(self) -> bool:
        """Perform the full migration."""
        try:
            print(f"🔄 Migrating {self.test_file_path}")

            self.backup_original()
            self.read_file()

            # Apply transformations
            content = self.fix_imports()
            content = self.migrate_function_signatures(content)
            content = self.remove_playwright_blocks(content)
            content = self.fix_indentation(content)

            self.migrated_content = content

            # Write migrated content
            with open(self.test_file_path, "w", encoding="utf-8") as f:
                f.write(self.migrated_content)

            print(f"✅ Migration completed: {self.test_file_path}")
            return True

        except Exception as e:
            print(f"❌ Migration failed for {self.test_file_path}: {e}")
            return False

    def validate_syntax(self) -> bool:
        """Validate the migrated file syntax."""
        try:
            with open(self.test_file_path, "r", encoding="utf-8") as f:
                content = f.read()
            ast.parse(content)
            print(f"✅ Syntax validation passed: {self.test_file_path}")
            return True
        except SyntaxError as e:
            print(f"❌ Syntax validation failed for {self.test_file_path}: {e}")
            return False


def migrate_test_files(file_paths: List[Path]) -> None:
    """Migrate multiple test files."""
    results = []

    for file_path in file_paths:
        if not file_path.exists():
            print(f"⚠️  File not found: {file_path}")
            continue

        migrator = TestMigrator(file_path)
        success = migrator.migrate_file()

        if success:
            syntax_ok = migrator.validate_syntax()
        else:
            syntax_ok = False

        results.append((file_path, success, syntax_ok))

    # Summary
    print("\n📊 Migration Summary:")
    print("-" * 50)
    for file_path, migrated, syntax_ok in results:
        status = "✅" if migrated and syntax_ok else "❌"
        print(f"{status} {file_path.name}")

    total_files = len(results)
    successful = sum(1 for _, migrated, syntax_ok in results if migrated and syntax_ok)
    print(f"\n📈 Results: {successful}/{total_files} files successfully migrated")


if __name__ == "__main__":
    # Files to migrate (in order of complexity)
    test_files = [
        "test_connection_scenarios.py",
        "test_network_failures.py",
        "test_new_game_disconnection_bug.py",
        "test_race_conditions.py",
        "test_page_refresh_scenarios.py",
        "test_browser_navigation.py",
        "test_game_creation_disconnection_bug.py",
        "test_complete_gameplay.py",
    ]

    base_path = Path(__file__).parent
    file_paths = [base_path / filename for filename in test_files]

    if len(sys.argv) > 1:
        # Migrate specific file
        target_file = base_path / sys.argv[1]
        if target_file.exists():
            migrate_test_files([target_file])
        else:
            print(f"File not found: {target_file}")
    else:
        # Migrate all files
        migrate_test_files(file_paths)
