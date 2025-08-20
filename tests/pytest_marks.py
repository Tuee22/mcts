"""Pytest mark definitions with proper typing."""

import pytest

# Export all the marks we need - mypy will see these as dynamic attributes
python = pytest.mark.python
display = pytest.mark.display
integration = pytest.mark.integration
unit = pytest.mark.unit
cpp = pytest.mark.cpp
board = pytest.mark.board
mcts = pytest.mark.mcts
slow = pytest.mark.slow
performance = pytest.mark.performance
stress = pytest.mark.stress
edge_cases = pytest.mark.edge_cases
asyncio = pytest.mark.asyncio
api = pytest.mark.api
websocket = pytest.mark.websocket
game_manager = pytest.mark.game_manager
models = pytest.mark.models
endpoints = pytest.mark.endpoints
benchmark = pytest.mark.benchmark
parametrize = pytest.mark.parametrize

# Also export the mark registry
mark = pytest.mark
