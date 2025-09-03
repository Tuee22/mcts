#!/usr/bin/env python3
"""Debug git commit guard to understand hook environment"""

import json
import os
import sys


def main():
    """Debug hook execution environment."""

    # Log all environment variables related to the hook
    env_vars = {
        "TOOL_CALL": os.environ.get("TOOL_CALL"),
        "CLAUDE_PROJECT_DIR": os.environ.get("CLAUDE_PROJECT_DIR"),
        "PWD": os.environ.get("PWD"),
        "HOME": os.environ.get("HOME"),
    }

    with open("/tmp/git-guard-debug.log", "w") as f:
        f.write(f"Git guard debug - {os.getcwd()}\n")
        for key, value in env_vars.items():
            f.write(f"{key}: {value}\n")
        f.write(f"All args: {sys.argv}\n")
        f.write(
            f"All env vars with CLAUDE: {[k for k in os.environ.keys() if 'CLAUDE' in k.upper()]}\n"
        )

        # Try to parse TOOL_CALL if it exists
        tool_call_json = os.environ.get("TOOL_CALL", "{}")
        try:
            tool_call = json.loads(tool_call_json)
            command = tool_call.get("parameters", {}).get("command", "")
            f.write(f"Parsed command: '{command}'\n")
        except Exception as e:
            f.write(f"Failed to parse TOOL_CALL: {e}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
