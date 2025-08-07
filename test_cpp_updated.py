#!/usr/bin/env python3
"""Test if C++ changes are taking effect."""

try:
    from python.corridors.corridors_mcts import Corridors_MCTS
except ImportError:
    print("Could not import Corridors_MCTS")
    exit(1)

mcts = Corridors_MCTS(c=1.0, seed=789, min_simulations=50, max_simulations=100, sim_increment=10, use_rollout=True, decide_using_visits=True)

# Test if new method exists and works
try:
    test_result = mcts.test_fix()
    print(f"test_fix() returned: {test_result}")
    if test_result == 42:
        print("✅ C++ changes are taking effect!")
    else:
        print(f"❌ Unexpected test_fix result: {test_result}")
except AttributeError:
    print("❌ test_fix() method not found - C++ changes not taking effect")
except Exception as e:
    print(f"❌ Error calling test_fix(): {e}")

# Test evaluation now
print(f"Initial evaluation: {mcts.get_evaluation()}")

mcts.ensure_sims(50)
actions = mcts.get_sorted_actions(flip=True)
wall_moves = [a for a in actions if a[2].startswith("V(") or a[2].startswith("H(")]

if wall_moves:
    wall_move = wall_moves[0][2]
    print(f"Making wall move: {wall_move}")
    mcts.make_move(wall_move, flip=True)
    
    eval_after = mcts.get_evaluation()
    actions_after = len(mcts.get_sorted_actions(flip=False))
    
    print(f"Evaluation after move: {eval_after}")
    print(f"Actions after move: {actions_after}")
    
    if eval_after is None:
        print("✅ EVALUATION FIX WORKING!")
    else:
        print(f"❌ EVALUATION FIX FAILED: Still got {eval_after}")