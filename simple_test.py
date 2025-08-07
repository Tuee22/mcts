#!/usr/bin/env python3
"""Simple test of the evaluation fix."""

try:
    from python.corridors.corridors_mcts import Corridors_MCTS
except ImportError:
    print("Could not import Corridors_MCTS")
    exit(1)

mcts = Corridors_MCTS(
    c=2.0, seed=789, min_simulations=150, max_simulations=300, sim_increment=30,
    use_rollout=True, decide_using_visits=True
)

print("Initial evaluation:", mcts.get_evaluation())
mcts.ensure_sims(150)
actions = mcts.get_sorted_actions(flip=True)
print("Making move:", actions[0][2])
mcts.make_move(actions[0][2], flip=True)
print("Evaluation after move:", mcts.get_evaluation())
print("Actions available:", len(mcts.get_sorted_actions(flip=False)))