#!/usr/bin/env python3
"""Simple test to verify evaluation fix."""

try:
    from python.corridors.corridors_mcts import Corridors_MCTS
except ImportError:
    print("Could not import Corridors_MCTS")
    exit(1)

# Test the exact problematic case
mcts = Corridors_MCTS(c=1.0, seed=789, min_simulations=50, max_simulations=100, sim_increment=10, use_rollout=True, decide_using_visits=True)

print("Before any moves:", mcts.get_evaluation())

mcts.ensure_sims(50)
actions = mcts.get_sorted_actions(flip=True)

# Find a wall move that should trigger the issue
wall_moves = [a for a in actions if a[2].startswith("V(") or a[2].startswith("H(")]
if wall_moves:
    wall_move = wall_moves[0][2]
    print(f"Making wall move: {wall_move}")
    mcts.make_move(wall_move, flip=True)
    
    eval_after = mcts.get_evaluation() 
    actions_after = len(mcts.get_sorted_actions(flip=False))
    
    print(f"Evaluation after move: {eval_after} (type: {type(eval_after)})")
    print(f"Actions after move: {actions_after}")
    
    # The fix should make this return None instead of ±1.0
    if eval_after is None:
        print("✅ FIX WORKING: Evaluation correctly returned None")
    elif eval_after == -1.0 or eval_after == 1.0:
        print("❌ FIX NOT WORKING: Still returning ±1.0")
    else:
        print(f"? UNEXPECTED: Evaluation is {eval_after}")
else:
    print("No wall moves available")