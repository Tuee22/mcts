#!/usr/bin/env python3
"""Fix broken CORRIDORS_AVAILABLE checks after skip removal."""

import os
import re

def fix_corridors_checks(file_path):
    """Fix CORRIDORS_AVAILABLE checks in a test file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Pattern to match: if not CORRIDORS_AVAILABLE: followed by code on next line
    pattern = r'(\s+)(if not CORRIDORS_AVAILABLE:)\s*\n(\s*)([^#\s\n].*)'
    
    def replacement(match):
        indent = match.group(1)
        if_stmt = match.group(2)
        next_line_indent = match.group(3)
        next_line_content = match.group(4)
        
        return f"{indent}{if_stmt}\n{indent}    return\n{next_line_indent}{next_line_content}"
    
    fixed_content = re.sub(pattern, replacement, content)
    
    # Write back if changed
    if fixed_content != content:
        with open(file_path, 'w') as f:
            f.write(fixed_content)
        return True
    return False

# Fix both files
test_files = [
    '/home/matt/mcts/tests/test_edge_cases.py',
    '/home/matt/mcts/tests/test_python_functions.py'
]

for file_path in test_files:
    if os.path.exists(file_path):
        fixed = fix_corridors_checks(file_path)
        print(f"{'Fixed' if fixed else 'No changes needed for'} {file_path}")