# Tools

Development and debugging tools for the Corridors MCTS project.

## Structure

- `debug/` - Debug scripts for analyzing game states and MCTS behavior

## Debug Scripts

The debug scripts help analyze various aspects of the MCTS algorithm:

- `debug_terminal.py` - Check terminal state detection
- `debug_evaluation.py` - Analyze position evaluation
- `debug_board_state.py` - Examine board representations

## Usage

Run debug scripts from the project root:

```bash
# Debug tools must be run directly (Poetry scripts are disabled due to missing main() functions)
poetry run python tools/debug/debug_terminal.py
poetry run python tools/debug/debug_board_state.py
poetry run python tools/debug/debug_evaluation.py

# Or run inside Docker container:
docker compose exec mcts poetry run python tools/debug/debug_terminal.py
```