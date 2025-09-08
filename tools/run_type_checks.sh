#!/bin/bash
# Run all type checking tools via Poetry

set -e  # Exit on any error

echo "Running mypy type checker..."
poetry run typecheck

echo -e "\nRunning custom type safety checker..."
poetry run check-type-safety


echo -e "\n✅ All type checks passed!"