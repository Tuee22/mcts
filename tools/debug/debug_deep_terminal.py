#!/usr/bin/env python3
"""Deep debug of the terminal evaluation issue."""

try:
    from corridors.corridors_mcts import Corridors_MCTS
except ImportError:
    print("Could not import Corridors_MCTS")
    exit(1)

# Let's debug exactly what happens when we make the problematic wall move
mcts = Corridors_MCTS(
    c=2.0,
    seed=789,
    min_simulations=150,
    max_simulations=300,
    sim_increment=30,
    use_rollout=True,
    decide_using_visits=True,
)

print("=== ANALYZING THE PROBLEMATIC SEQUENCE ===")

print("\n1. INITIAL STATE:")
print("Evaluation:", mcts.get_evaluation())
mcts.ensure_sims(150)

print("\n2. GET ACTIONS (flip=True for Hero's turn):")
actions = mcts.get_sorted_actions(flip=True)
print(f"Actions available: {len(actions)}")
print("Top 3 actions:")
for i, action in enumerate(actions[:3]):
    print(f"  {i}: visits={action[0]}, equity={action[1]}, action='{action[2]}'")

print(f"\n3. MAKING MOVE: {actions[0][2]} with flip=True")
mcts.make_move(actions[0][2], flip=True)

print("\n4. AFTER MOVE STATE:")
print("Raw get_evaluation():", mcts.get_evaluation())

# Let's try different flip values for actions to see if that reveals the issue
print("\n5. CHECKING ACTIONS FROM DIFFERENT PERSPECTIVES:")
actions_flip_false = mcts.get_sorted_actions(flip=False)
actions_flip_true = mcts.get_sorted_actions(flip=True)

print(f"Actions with flip=False: {len(actions_flip_false)}")
print(f"Actions with flip=True: {len(actions_flip_true)}")

print("\n6. DISPLAY CURRENT BOARD:")
display = mcts.display(flip=False)
print(display)

# The key insight is that in the test, the condition is:
# if evaluation is not None and abs(evaluation) >= 1.0:
# So if get_evaluation() returns -1.0, it triggers termination

print("\n7. TESTING DIFFERENT WALL POSITIONS:")
# Test if it's specific to certain wall positions
test_walls = ["V(4,4)", "H(4,4)", "V(1,1)", "H(1,1)"]

for wall_pos in test_walls:
    test_mcts = Corridors_MCTS(
        c=1.0,
        seed=789,
        min_simulations=50,
        max_simulations=100,
        sim_increment=10,
        use_rollout=True,
        decide_using_visits=True,
    )
    test_mcts.ensure_sims(50)

    test_actions = test_mcts.get_sorted_actions(flip=True)
    legal_moves = [a[2] for a in test_actions]

    if wall_pos in legal_moves:
        print(f"\nTesting {wall_pos}:")
        test_mcts.make_move(wall_pos, flip=True)
        eval_result = test_mcts.get_evaluation()
        actions_after = len(test_mcts.get_sorted_actions(flip=False))
        print(f"  Evaluation: {eval_result}, Actions: {actions_after}")
    else:
        print(f"\n{wall_pos} not legal")

print("\n=== HYPOTHESIS ===")
print(
    """
The issue seems to be that certain wall placements, when combined with flip=True,
create board states where the MCTS tree evaluation logic incorrectly returns ±1.0.

This could be because:
1. The board flip logic in wall generation creates genuinely terminal states
2. The get_equity() method is returning high confidence values that aren't actually terminal
3. There's a bug in how flipped wall moves are stored in the MCTS tree

Next steps: Need to dig into the actual C++ board state after these moves.
"""
)
