#!/usr/bin/env python3
"""Audit script that logs hook triggers to test_hook_trigger.txt by reading stdin JSON"""

import json
import sys
from datetime import datetime
from pathlib import Path


def main():
    """Read hook event from stdin JSON and log to audit file"""
    try:
        # Detect event type from command line or environment
        event_type = "Post-Tool-Use"  # Default
        if len(sys.argv) > 1:
            event_type = sys.argv[1]

        # Read JSON from stdin
        stdin_data = sys.stdin.read()
        tool_name = "Unknown"
        file_summary = "no payload"

        if stdin_data:
            try:
                # Parse JSON payload
                event_data = json.loads(stdin_data)

                # Extract tool information
                tool_name = event_data.get("tool", {}).get("name", "Unknown")
                tool_params = event_data.get("tool", {}).get("parameters", {})

                # Extract file path(s) based on tool type
                if tool_name in ["Edit", "Write"]:
                    file_path = tool_params.get("file_path", "Unknown")
                    file_summary = (
                        str(Path(file_path).name)
                        if file_path != "Unknown"
                        else "Unknown"
                    )
                elif tool_name == "MultiEdit":
                    file_path = tool_params.get("file_path", "Unknown")
                    edits = tool_params.get("edits", [])
                    if file_path != "Unknown":
                        file_summary = (
                            f"{Path(file_path).name} ({len(edits)} edits)"
                            if edits
                            else str(Path(file_path).name)
                        )
                    else:
                        file_summary = "Unknown"
                elif tool_name == "Task":
                    file_summary = "sub-agent task"
                else:
                    # Fallback description
                    file_summary = f"params: {json.dumps(tool_params)[:30]}..."
            except json.JSONDecodeError:
                file_summary = "json parse error"

        # Create timestamp in ISO-8601 local time
        timestamp = datetime.now().isoformat()

        # Create audit line
        audit_line = f"{timestamp} | Event: {event_type} | Tool: {tool_name} | Files: {file_summary}"

        # Ensure audit file exists with header
        audit_file = Path.cwd() / "test_hook_trigger.txt"
        if not audit_file.exists():
            with open(audit_file, "w") as f:
                f.write(
                    "# Hook Audit Log - ISO-8601 Timestamp | Event Type | Tool Name | File Summary\n"
                )

        # Append audit line
        with open(audit_file, "a") as f:
            f.write(audit_line + "\n")

        # Print confirmation to stdout (minimal)
        print(f"Hook audit: {event_type} | {tool_name}")

        return 0

    except Exception as e:
        # Try to write minimal log even on error
        try:
            audit_file = Path.cwd() / "test_hook_trigger.txt"
            with open(audit_file, "a") as f:
                f.write(
                    f"{datetime.now().isoformat()} | Event: ERROR | Tool: Unknown | Files: {str(e)[:30]}\n"
                )
        except:
            pass
        print(f"Hook audit error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
