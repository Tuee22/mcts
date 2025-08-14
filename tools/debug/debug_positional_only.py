#!/usr/bin/env python3
"""Debug by forcing positional moves only."""

try:
    from python.corridors.corridors_mcts import Corridors_MCTS
except ImportError:
    print("Could not import Corridors_MCTS")
    exit(1)


def get_positional_actions(mcts, flip):
    """Get only positional actions (moves starting with '*')."""
    all_actions = mcts.get_sorted_actions(flip=flip)
    return [action for action in all_actions if action[2].startswith("*")]


# Test game with positional moves only
mcts = Corridors_MCTS(
    c=2.0,
    seed=789,
    min_simulations=150,
    max_simulations=300,
    sim_increment=30,
    use_rollout=True,
    decide_using_visits=True,
)

print("=== TESTING WITH POSITIONAL MOVES ONLY ===")
print("Initial evaluation:", mcts.get_evaluation())

move_sequence = []
max_moves = 15

for move_num in range(max_moves):
    mcts.ensure_sims(150)

    # Get only positional actions
    flip_value = move_num % 2 == 0
    positional_actions = get_positional_actions(mcts, flip_value)

    if not positional_actions:
        print(f"No positional actions available at move {move_num}")
        # Try all actions as fallback
        all_actions = mcts.get_sorted_actions(flip=flip_value)
        if not all_actions:
            print("No actions available at all!")
            break
        else:
            print(f"Using non-positional action: {all_actions[0][2]}")
            best_action = all_actions[0]
    else:
        best_action = positional_actions[0]

    move_sequence.append(
        {
            "move": move_num,
            "action": best_action[2],
            "visits": best_action[0],
            "equity": best_action[1],
            "flip": flip_value,
        }
    )

    print(
        f"Move {move_num}: {best_action[2]} (flip={flip_value}, visits: {best_action[0]}, equity: {best_action[1]})"
    )

    # Make the move
    mcts.make_move(best_action[2], flip=flip_value)

    # Check terminal state
    evaluation = mcts.get_evaluation()
    print(f"  Evaluation after move: {evaluation}")

    if evaluation is not None and abs(evaluation) >= 1.0:
        print(f"  TERMINAL: evaluation {evaluation}")
        break

print(f"\nGame with positional moves lasted {len(move_sequence)} moves")

# Display final board state
print("\nFinal board state:")
print(mcts.display(flip=False))
