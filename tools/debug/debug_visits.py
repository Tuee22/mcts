#!/usr/bin/env python3
"""Debug the visit counting issue."""

try:
    from python.corridors.corridors_mcts import Corridors_MCTS
except ImportError:
    print("Could not import Corridors_MCTS")
    exit(1)

# Reproduce the exact same setup as the failing test
mcts = Corridors_MCTS(
    c=1.2, seed=666, min_simulations=200, max_simulations=1000, sim_increment=50
)

simulation_targets = [200, 400, 600, 800, 1000]

for target in simulation_targets:
    print(f"\n=== TARGET: {target} ===")
    mcts.ensure_sims(target)

    actions = mcts.get_sorted_actions(flip=True)
    total_visits = sum(a[0] for a in actions)

    print(f"Total visits: {total_visits}")
    print(f"Target: {target}")
    print(f"Difference: {total_visits - target}")
    print(f"Actions count: {len(actions)}")

    if actions:
        print("Top 5 actions:")
        for i, action in enumerate(actions[:5]):
            print(
                f"  {i}: visits={action[0]}, equity={action[1]:.4f}, action='{action[2]}'"
            )

# The issue might be related to how simulations are distributed across child nodes
# or a rounding issue in the ensure_sims implementation
