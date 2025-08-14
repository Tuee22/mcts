#!/usr/bin/env python3
"""Debug by testing moves without any flip logic."""

try:
    from python.corridors.corridors_mcts import Corridors_MCTS
except ImportError:
    print("Could not import Corridors_MCTS")
    exit(1)

# Test the same sequence as the failing test but WITHOUT flip logic
mcts = Corridors_MCTS(
    c=2.0,
    seed=789,
    min_simulations=150,
    max_simulations=300,
    sim_increment=30,
    use_rollout=True,
    decide_using_visits=True,
)

print("=== TESTING WITHOUT FLIP ===")
print("Initial evaluation:", mcts.get_evaluation())

move_sequence = []
max_moves = 10

for move_num in range(max_moves):
    mcts.ensure_sims(150)

    # Get actions WITHOUT flip (always False)
    actions = mcts.get_sorted_actions(flip=False)

    if not actions:
        print(f"No actions available at move {move_num}")
        break

    best_action = actions[0]
    move_sequence.append(
        {
            "move": move_num,
            "action": best_action[2],
            "visits": best_action[0],
            "equity": best_action[1],
            "total_actions": len(actions),
        }
    )

    print(
        f"Move {move_num}: {best_action[2]} (visits: {best_action[0]}, equity: {best_action[1]})"
    )

    # Make move WITHOUT flip (always False)
    mcts.make_move(best_action[2], flip=False)

    # Check terminal state
    evaluation = mcts.get_evaluation()
    print(f"  Evaluation after move: {evaluation}")

    if evaluation is not None and abs(evaluation) >= 1.0:
        print(f"  TERMINAL: evaluation {evaluation}")
        break

print(f"\nGame lasted {len(move_sequence)} moves without flip logic")

print("\n" + "=" * 60)
print("\n=== TESTING WITH ALTERNATING FLIP (original logic) ===")

# Reset and test with the original flip logic from the failing test
mcts2 = Corridors_MCTS(
    c=2.0,
    seed=789,
    min_simulations=150,
    max_simulations=300,
    sim_increment=30,
    use_rollout=True,
    decide_using_visits=True,
)

move_sequence2 = []

for move_num in range(max_moves):
    mcts2.ensure_sims(150)

    # Original flip logic from failing test: flip=(move_num % 2 == 0)
    flip_value = move_num % 2 == 0
    actions = mcts2.get_sorted_actions(flip=flip_value)

    if not actions:
        print(f"No actions available at move {move_num}")
        break

    best_action = actions[0]
    move_sequence2.append(
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

    # Make move with same flip logic
    mcts2.make_move(best_action[2], flip=flip_value)

    # Check terminal state
    evaluation = mcts2.get_evaluation()
    print(f"  Evaluation after move: {evaluation}")

    if evaluation is not None and abs(evaluation) >= 1.0:
        print(f"  TERMINAL: evaluation {evaluation}")
        break

print(f"\nGame lasted {len(move_sequence2)} moves with alternating flip logic")

print("\n" + "=" * 60)
print("\n=== TESTING WITH CONSISTENT FLIP=TRUE ===")

# Test with flip always True
mcts3 = Corridors_MCTS(
    c=2.0,
    seed=789,
    min_simulations=150,
    max_simulations=300,
    sim_increment=30,
    use_rollout=True,
    decide_using_visits=True,
)

move_sequence3 = []

for move_num in range(max_moves):
    mcts3.ensure_sims(150)

    actions = mcts3.get_sorted_actions(flip=True)

    if not actions:
        print(f"No actions available at move {move_num}")
        break

    best_action = actions[0]
    move_sequence3.append(
        {
            "move": move_num,
            "action": best_action[2],
            "visits": best_action[0],
            "equity": best_action[1],
        }
    )

    print(
        f"Move {move_num}: {best_action[2]} (visits: {best_action[0]}, equity: {best_action[1]})"
    )

    # Make move with flip=True
    mcts3.make_move(best_action[2], flip=True)

    # Check terminal state
    evaluation = mcts3.get_evaluation()
    print(f"  Evaluation after move: {evaluation}")

    if evaluation is not None and abs(evaluation) >= 1.0:
        print(f"  TERMINAL: evaluation {evaluation}")
        break

print(f"\nGame lasted {len(move_sequence3)} moves with consistent flip=True")
