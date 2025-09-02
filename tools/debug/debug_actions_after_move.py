#!/usr/bin/env python3
"""Debug the actions available after problematic moves."""

try:
    from corridors.corridors_mcts import Corridors_MCTS
except ImportError:
    print("Could not import Corridors_MCTS")
    exit(1)

mcts = Corridors_MCTS(
    c=2.0,
    seed=789,
    min_simulations=150,
    max_simulations=300,
    use_rollout=True,
    decide_using_visits=True,
)

print("=== INITIAL STATE ===")
mcts.ensure_sims(150)
initial_actions = mcts.get_sorted_actions(flip=True)
print(f"Initial actions available: {len(initial_actions)}")
print(f"Initial evaluation: {mcts.get_evaluation()}")

# Make first move
best_action = initial_actions[0][2]
print(f"\nMaking move: {best_action} with flip=True")
mcts.make_move(best_action, flip=True)

print(f"\n=== AFTER FIRST MOVE ===")
print(f"Evaluation: {mcts.get_evaluation()}")

# Check actions from both perspectives
actions_flip_false = mcts.get_sorted_actions(flip=False)
actions_flip_true = mcts.get_sorted_actions(flip=True)

print(f"Actions with flip=False: {len(actions_flip_false)}")
print(f"Actions with flip=True: {len(actions_flip_true)}")

if actions_flip_false:
    print("First 5 actions (flip=False):")
    for i, action in enumerate(actions_flip_false[:5]):
        print(f"  {i}: visits={action[0]}, equity={action[1]}, action='{action[2]}'")

if actions_flip_true:
    print("First 5 actions (flip=True):")
    for i, action in enumerate(actions_flip_true[:5]):
        print(f"  {i}: visits={action[0]}, equity={action[1]}, action='{action[2]}'")

# The issue might be that we're calling get_sorted_actions(false) in the C++ code
# but the Python test might be calling it with a different flip value

# Let me also check what happens if we make a second move
if actions_flip_false:
    second_action = actions_flip_false[0][2]
    print(f"\nMaking second move: {second_action} with flip=False")
    mcts.make_move(second_action, flip=False)

    print(f"Evaluation after second move: {mcts.get_evaluation()}")
    third_actions = mcts.get_sorted_actions(flip=True)
    print(f"Actions after second move: {len(third_actions)}")

# The core issue might be that even though actions are available from the MCTS tree,
# the underlying get_equity() is returning ±1.0 for non-terminal positions due to
# flipped board states in the tree structure
