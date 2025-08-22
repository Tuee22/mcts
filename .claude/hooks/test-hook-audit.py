#!/usr/bin/env python3
"""Simple audit script that logs hook triggers to test_hook_trigger.txt"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Get tool information from environment
tool_name = os.environ.get('TOOL_NAME', 'Unknown')
tool_call = os.environ.get('TOOL_CALL', '{}')

# Parse tool call to get file path
try:
    tool_data = json.loads(tool_call)
    params = tool_data.get('parameters', {})
    file_path = params.get('file_path', 'Unknown')
except:
    file_path = 'Unknown'

# Create timestamp
timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Create audit line
audit_line = f"[{timestamp}] Tool: {tool_name} File: {file_path}\n"

# Append to audit file
audit_file = Path.cwd() / "test_hook_trigger.txt"
with open(audit_file, 'a') as f:
    f.write(audit_line)

print(f"Hook fired: {tool_name} on {file_path}")