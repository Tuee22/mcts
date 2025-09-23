#!/usr/bin/env python
"""
Documentation consistency checker for MCTS project.

Verifies that documentation files (.gitignore, .dockerignore, README.md, etc.)
are up-to-date with the current codebase structure and recent changes.
"""

# Test comment to trigger hook - testing workaround

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, NamedTuple, Optional, Set, Tuple


class CheckResult(NamedTuple):
    """Result of a documentation check."""

    errors: List[str]
    warnings: List[str]


def read_file_safe(file_path: Path) -> Optional[str]:
    """Safely read file content, returning None if file doesn't exist."""
    try:
        return file_path.read_text() if file_path.exists() else None
    except (IOError, OSError):
        return None


def get_git_changed_files(
    repo_root: Path, commit_range: str = "HEAD~5..HEAD"
) -> List[str]:
    """Get list of changed files from git, empty list on failure."""
    try:
        # Check if git is available
        git_check = subprocess.run(
            ["which", "git"], capture_output=True, text=True, timeout=1
        )
        if git_check.returncode != 0:
            # Git not available, skip this check
            return []

        result = subprocess.run(
            ["git", "diff", "--name-only", commit_range],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return [f for f in result.stdout.strip().split("\n") if f]
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        # Git not available or command failed, skip gracefully
        return []


def check_gitignore(repo_root: Path) -> CheckResult:
    """Check .gitignore for missing patterns."""
    gitignore_path = repo_root / ".gitignore"
    content = read_file_safe(gitignore_path)

    if content is None:
        return CheckResult(errors=[".gitignore file is missing"], warnings=[])

    expected_patterns = {
        "__pycache__",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".Python",
        "*.egg-info",
        "dist/",
        "build/",
        ".pytest_cache",
        ".mypy_cache",
        ".coverage",
        "htmlcov/",
        ".vscode/",
        ".idea/",
        "*.swp",
        "*.swo",
        "*~",
        ".DS_Store",
        "Thumbs.db",
        ".claude/logs/",
        "*.log",
    }

    missing = [p for p in expected_patterns if p not in content]
    warning = (
        f".gitignore may be missing patterns: {', '.join(sorted(missing))}"
        if missing
        else None
    )

    return CheckResult(errors=[], warnings=[warning] if warning else [])


def check_dockerignore(repo_root: Path) -> CheckResult:
    """Check .dockerignore for consistency with Docker setup."""
    dockerignore_path = repo_root / ".dockerignore"
    docker_dir = repo_root / "docker"
    content = read_file_safe(dockerignore_path)

    if docker_dir.exists() and content is None:
        return CheckResult(
            errors=[],
            warnings=[
                ".dockerignore file is missing (recommended for Docker projects)"
            ],
        )

    if content is None:
        return CheckResult(errors=[], warnings=[])

    expected_patterns = {
        ".git",
        ".gitignore",
        ".claude/",
        "*.log",
        "__pycache__",
        "*.pyc",
        ".pytest_cache",
        ".mypy_cache",
        ".coverage",
        "htmlcov/",
    }

    missing = [p for p in expected_patterns if p not in content]
    warning = (
        f".dockerignore may be missing patterns: {', '.join(sorted(missing))}"
        if missing
        else None
    )

    return CheckResult(errors=[], warnings=[warning] if warning else [])


def extract_code_blocks(content: str) -> List[str]:
    """Extract shell code blocks from markdown content."""
    return re.findall(r"```(?:bash|sh|shell)?\n(.*?)\n```", content, re.DOTALL)


def extract_file_references(line: str) -> List[str]:
    """Extract file references from a command line."""
    return re.findall(r"(?:python|pytest|./|bash)\s+([^\s]+\.(?:py|sh))", line)


def check_readme_commands(repo_root: Path) -> CheckResult:
    """Verify that commands in README.md are valid."""
    readme_path = repo_root / "README.md"
    content = read_file_safe(readme_path)

    if content is None:
        return CheckResult(errors=["README.md file is missing"], warnings=[])

    code_blocks = extract_code_blocks(content)
    command_lines = [
        line.strip()
        for block in code_blocks
        for line in block.strip().split("\n")
        if line.strip() and not line.strip().startswith("#")
    ]

    # Check for references to deleted scripts
    script_errors = [
        f"README.md references non-existent scripts/ directory: {line}"
        for line in command_lines
        if "scripts/" in line and not (repo_root / "scripts").exists()
    ]

    # Check for file references
    file_warnings = [
        f"README.md references possibly missing file: {ref}"
        for line in command_lines
        for ref in extract_file_references(line)
        if not ref.startswith(("/", "$"))
        and "*" not in ref
        and not (repo_root / ref).exists()
    ]

    return CheckResult(errors=script_errors, warnings=file_warnings)


def extract_relative_links(content: str) -> List[Tuple[str, str]]:
    """Extract relative markdown links from content."""
    return [
        (text, path)
        for text, path in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
        if not path.startswith(("http://", "https://", "#"))
    ]


def check_documentation_files(repo_root: Path) -> CheckResult:
    """Check that documentation references are valid."""
    doc_files = list(repo_root.rglob("*.md"))

    warnings = [
        f"{doc_file.relative_to(repo_root)} has broken link: [{text}]({path})"
        for doc_file in doc_files
        if (content := read_file_safe(doc_file)) is not None
        for text, path in extract_relative_links(content)
        if "*" not in path and not (doc_file.parent / path).resolve().exists()
    ]

    return CheckResult(errors=[], warnings=warnings)


def check_claude_md(repo_root: Path) -> CheckResult:
    """Check CLAUDE.md for accuracy."""
    claude_md_path = repo_root / "CLAUDE.md"
    compose_path = repo_root / "docker" / "docker-compose.yaml"

    claude_content = read_file_safe(claude_md_path)
    compose_content = read_file_safe(compose_path)

    if claude_content is None or compose_content is None:
        return CheckResult(errors=[], warnings=[])

    has_mcts_dev_ref = "docker compose exec mcts-dev" in claude_content
    has_mcts_service = "mcts:" in compose_content
    has_mcts_dev_service = "mcts-dev:" in compose_content

    error = (
        "CLAUDE.md references 'mcts-dev' service but docker-compose.yaml uses 'mcts'"
        if has_mcts_dev_ref and has_mcts_service and not has_mcts_dev_service
        else None
    )

    return CheckResult(errors=[error] if error else [], warnings=[])


def check_recent_changes(repo_root: Path) -> CheckResult:
    """Check if recent changes require documentation updates."""
    changed_files = get_git_changed_files(repo_root)

    code_dirs = {
        Path(f).parent
        for f in changed_files
        if f.endswith((".py", ".cpp", ".hpp", ".h"))
        and f.startswith("backend/")
        and "README" not in f
    }

    warnings = [
        f"New code in {code_dir} but no README.md found"
        for code_dir in code_dirs
        if not (repo_root / code_dir / "README.md").exists()
    ]

    return CheckResult(errors=[], warnings=warnings)


def find_repo_root() -> Optional[Path]:
    """Find repository root by looking for .git directory."""
    current = Path.cwd()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return None


def merge_results(results: List[CheckResult]) -> CheckResult:
    """Merge multiple check results into one."""
    all_errors = [error for result in results for error in result.errors]
    all_warnings = [warning for result in results for warning in result.warnings]
    return CheckResult(errors=all_errors, warnings=all_warnings)


def run_all_checks(repo_root: Path) -> CheckResult:
    """Run all documentation checks and return combined results."""
    checks = [
        check_gitignore,
        check_dockerignore,
        check_readme_commands,
        check_documentation_files,
        check_claude_md,
        check_recent_changes,
    ]

    results = [check(repo_root) for check in checks]
    return merge_results(results)


def print_results(errors: List[str], warnings: List[str]) -> int:
    """Print check results and return appropriate exit code."""
    if errors:
        print("❌ Documentation Check FAILED\n")
        print("ERRORS:")
        for error in errors:
            print(f"  • {error}")
        print("\n📋 Run agent: @doc-consistency-checker")
        print("🔧 Or fix documentation manually")
        return 1

    if warnings:
        print("⚠️  Documentation Check PASSED with warnings\n")
        print("WARNINGS:")
        for warning in warnings:
            print(f"  • {warning}")
        print("\nConsider addressing these issues to improve documentation quality.")
        return 0

    print("✅ Documentation Check PASSED")
    return 0


def main() -> int:
    """Main entry point."""
    repo_root = find_repo_root()
    if repo_root is None:
        print("❌ Could not find repository root")
        return 1

    result = run_all_checks(repo_root)
    return print_results(result.errors, result.warnings)


if __name__ == "__main__":
    sys.exit(main())
