#!/usr/bin/env python3
"""Audit script that logs hook triggers to test_hook_trigger.txt by reading stdin JSON"""

import sys
import json
from datetime import datetime
from pathlib import Path


def main():
    """Read hook event from stdin JSON and log to audit file"""
    try:
        # Read JSON from stdin
        stdin_data = sys.stdin.read()
        if not stdin_data:
            print("Hook fired: No stdin data provided", file=sys.stderr)
            return 1

        # Parse JSON payload
        event_data = json.loads(stdin_data)

        # Extract tool information
        tool_name = event_data.get("tool", {}).get("name", "Unknown")
        tool_params = event_data.get("tool", {}).get("parameters", {})

        # Extract file path(s) based on tool type
        if tool_name in ["Edit", "Write"]:
            file_path = tool_params.get("file_path", "Unknown")
        elif tool_name == "MultiEdit":
            file_path = tool_params.get("file_path", "Unknown")
            # Could also show edit count
            edits = tool_params.get("edits", [])
            if edits:
                file_path = f"{file_path} ({len(edits)} edits)"
        else:
            # Fallback description
            file_path = f"params: {json.dumps(tool_params)[:50]}..."

        # Create timestamp in ISO-8601 local time
        timestamp = datetime.now().isoformat()

        # Create audit line
        audit_line = f"{timestamp} | Tool: {tool_name} | Path: {file_path}"

        # Ensure audit file exists with header
        audit_file = Path.cwd() / "test_hook_trigger.txt"
        if not audit_file.exists():
            with open(audit_file, "w") as f:
                f.write(
                    "# Hook Audit Log - ISO-8601 Timestamp | Tool Name | File Path or Description\n"
                )

        # Append audit line
        with open(audit_file, "a") as f:
            f.write(audit_line + "\n")

        # Print confirmation to stdout
        print(f"Hook fired: {tool_name} on {file_path}")

        return 0

    except json.JSONDecodeError as e:
        print(f"Hook fired: JSON parse error - {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Hook fired: Error - {e}", file=sys.stderr)
        # Try to write minimal log even on error
        try:
            audit_file = Path.cwd() / "test_hook_trigger.txt"
            with open(audit_file, "a") as f:
                f.write(f"{datetime.now().isoformat()} | ERROR | {str(e)[:50]}\n")
        except:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
