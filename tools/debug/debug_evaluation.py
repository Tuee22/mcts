#!/usr/bin/env python3
"""Debug the evaluation issue in integration tests."""

try:
    from corridors.corridors_mcts import Corridors_MCTS
except ImportError:
    print("Could not import Corridors_MCTS")
    exit(1)

# Reproduce the exact same setup as the failing test
mcts = Corridors_MCTS(
    c=2.0,
    seed=789,
    min_simulations=150,
    max_simulations=300,
    sim_increment=30,
    use_rollout=True,
    decide_using_visits=True,
)

print("=== INITIAL STATE ===")
print("Display:")
print(mcts.display(flip=False))
print()

print("Initial evaluation:", mcts.get_evaluation())
print()

# Ensure simulations
print("Ensuring 150 simulations...")
mcts.ensure_sims(150)
print()

# Get actions for the first move (Hero turn, move_num % 2 == 0 is True, so flip=True)
print("Getting actions with flip=True (Hero turn)...")
actions = mcts.get_sorted_actions(flip=True)
print(f"Number of actions: {len(actions)}")

if actions:
    best_action = actions[0]
    print(f"Best action: {best_action}")
    print(
        f"Best action details: visits={best_action[0]}, equity={best_action[1]}, action='{best_action[2]}'"
    )

    print("\n=== MAKING MOVE ===")
    print(f"Making move: {best_action[2]} with flip=True")

    # Make the move
    mcts.make_move(best_action[2], flip=True)

    print("\n=== STATE AFTER MOVE ===")
    print("Display after move:")
    print(mcts.display(flip=False))
    print()

    # Check evaluation after move
    evaluation = mcts.get_evaluation()
    print(f"Evaluation after move: {evaluation}")
    print(
        f"Terminal condition check: evaluation is not None = {evaluation is not None}"
    )
    if evaluation is not None:
        print(f"abs(evaluation) = {abs(evaluation)}")
        print(f"abs(evaluation) >= 1.0 = {abs(evaluation) >= 1.0}")

    # If the evaluation is exactly -1.0 or 1.0, let's examine the board state
    if evaluation is not None and abs(evaluation) >= 1.0:
        print(f"TERMINAL: evaluation {evaluation} >= 1.0 (absolute value)")
        print("This explains why the game ends after just one move!")

        # Let's see what actions are available after this move
        print("\n=== CHECKING POST-MOVE STATE ===")
        actions_after = mcts.get_sorted_actions(flip=False)  # Villain's turn
        print(f"Actions available after move: {len(actions_after)}")

        if len(actions_after) == 0:
            print("No actions available - position is terminal")
        else:
            print("Actions still available, so evaluation logic might be incorrect")
            for i, action in enumerate(actions_after[:3]):
                print(f"  Action {i}: {action}")
else:
    print("No actions available initially!")
