#!/bin/bash
# Run all type checking tools

set -e  # Exit on any error

echo "Running mypy type checker..."
mypy --strict .

echo -e "\nRunning custom type safety checker..."
python /app/tools/check_type_safety.py

echo -e "\nRunning flake8..."
flake8 .

echo -e "\n✅ All type checks passed!"