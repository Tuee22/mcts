#!/usr/bin/env python3
"""
Setup script to install Playwright browsers.
"""

import subprocess
import sys
from typing import NoReturn


def main() -> NoReturn:
    """Install Playwright browsers."""
    try:
        result = subprocess.run(
            ["playwright", "install"], check=True, capture_output=True, text=True
        )
        print("✅ Playwright browsers installed successfully")
        print(result.stdout)
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install Playwright browsers: {e}")
        stdout_str = e.stdout.decode() if isinstance(e.stdout, bytes) else str(e.stdout)
        stderr_str = e.stderr.decode() if isinstance(e.stderr, bytes) else str(e.stderr)
        print(f"stdout: {stdout_str}")
        print(f"stderr: {stderr_str}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ playwright command not found. Make sure playwright is installed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
