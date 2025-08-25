"""Test runner script for comprehensive test execution."""

import subprocess
import sys
from typing import List, Optional

import click


@click.group()
def cli() -> None:
    """MCTS Test Runner - Execute test suites with proper configuration."""
    pass


def run_pytest(args: List[str], env: Optional[dict[str, str]] = None) -> int:
    """Run pytest with given arguments."""
    cmd = ["pytest"] + args
    result = subprocess.run(cmd, env=env)
    return result.returncode


@cli.command()
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.option("--coverage", is_flag=True, help="Generate coverage report")
def all(verbose: bool, coverage: bool) -> None:
    """Run complete test suite (unit + integration + e2e)."""
    click.echo("Running complete test suite...")

    args = ["tests/"]
    if verbose:
        args.append("-v")
    if coverage:
        args.extend(["--cov=backend", "--cov-report=term", "--cov-report=html"])

    sys.exit(run_pytest(args))


@cli.command()
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.option("--no-slow", is_flag=True, help="Skip slow tests")
def unit(verbose: bool, no_slow: bool) -> None:
    """Run unit tests only."""
    click.echo("Running unit tests...")

    args = ["tests/backend/", "-m", "unit"]
    if no_slow:
        args[-1] = "unit and not slow"
    if verbose:
        args.append("-v")

    sys.exit(run_pytest(args))


@cli.command()
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def integration(verbose: bool) -> None:
    """Run integration tests with real services."""
    click.echo("Running integration tests...")

    args = ["tests/integration/", "-m", "integration"]
    if verbose:
        args.append("-v")

    sys.exit(run_pytest(args))


@cli.command()
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.option("--headed", is_flag=True, help="Run with visible browser")
@click.option("--video", is_flag=True, help="Record videos")
def e2e(verbose: bool, headed: bool, video: bool) -> None:
    """Run end-to-end tests with Playwright."""
    click.echo("Running E2E tests...")

    env: Optional[dict[str, str]] = None
    if headed or video:
        import os

        env = os.environ.copy()
        if headed:
            env["E2E_HEADLESS"] = "false"
        if video:
            env["E2E_VIDEO"] = "on"

    args = ["tests/e2e/", "-m", "e2e"]
    if verbose:
        args.append("-v")

    sys.exit(run_pytest(args, env=env))


@cli.command()
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def quick(verbose: bool) -> None:
    """Run quick tests for development feedback."""
    click.echo("Running quick tests...")

    args = ["tests/backend/", "-m", "unit and not slow"]
    if verbose:
        args.append("-v")

    sys.exit(run_pytest(args))


@cli.command()
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def connection(verbose: bool) -> None:
    """Run connection and network failure tests."""
    click.echo("Running connection tests...")

    args = [
        "tests/integration/test_websocket_connection.py",
        "tests/integration/test_cors_configuration.py",
        "tests/integration/test_network_failures.py",
        "tests/e2e/test_connection_scenarios.py",
        "tests/e2e/test_network_failures.py",
    ]
    if verbose:
        args.append("-v")

    sys.exit(run_pytest(args))


@cli.command()
def websocket() -> None:
    """Run WebSocket-specific tests."""
    click.echo("Running WebSocket tests...")
    sys.exit(run_pytest(["tests/", "-m", "websocket", "-v"]))


@cli.command()
def cors() -> None:
    """Run CORS-specific tests."""
    click.echo("Running CORS tests...")
    sys.exit(run_pytest(["tests/", "-m", "cors", "-v"]))


@cli.command()
def performance() -> None:
    """Run performance and benchmark tests."""
    click.echo("Running performance tests...")
    sys.exit(
        run_pytest(["tests/", "-m", "performance or benchmark", "--benchmark-only"])
    )


@cli.command()
@click.argument("test_path", required=False)
@click.option("-k", "--keyword", help="Run tests matching keyword")
@click.option("-m", "--marker", help="Run tests with specific marker")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.option("-s", "--capture", is_flag=True, help="Don't capture output")
def run(
    test_path: Optional[str],
    keyword: Optional[str],
    marker: Optional[str],
    verbose: bool,
    capture: bool,
) -> None:
    """Run tests with custom options."""
    args = []

    if test_path:
        args.append(test_path)
    else:
        args.append("tests/")

    if keyword:
        args.extend(["-k", keyword])
    if marker:
        args.extend(["-m", marker])
    if verbose:
        args.append("-v")
    if capture:
        args.append("-s")

    sys.exit(run_pytest(args))


def main() -> None:
    """Entry point for test runner."""
    cli()


if __name__ == "__main__":
    main()
