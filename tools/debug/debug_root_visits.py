#!/usr/bin/env python3
"""Debug the root node vs child visits issue."""

try:
    from python.corridors.corridors_mcts import Corridors_MCTS
except ImportError:
    print("Could not import Corridors_MCTS")
    exit(1)

# Unfortunately, I don't have a direct way to get root visits from Python bindings
# But I can infer the issue from the pattern

mcts = Corridors_MCTS(
    c=1.2, seed=666, min_simulations=200, max_simulations=1000, sim_increment=50
)

simulation_targets = [200, 400]

for target in simulation_targets:
    print(f"\n=== TARGET: {target} ===")
    mcts.ensure_sims(target)
    
    actions = mcts.get_sorted_actions(flip=True)
    total_child_visits = sum(a[0] for a in actions)
    
    print(f"Target simulations: {target}")  
    print(f"Total child visits: {total_child_visits}")
    print(f"Difference: {target - total_child_visits}")
    
    # The pattern shows:
    # Target 200 -> child visits 200 (difference 0)
    # Target 400 -> child visits 399 (difference 1) 
    # Target 600 -> child visits 599 (difference 1)
    # etc.
    
    # This suggests that the first ensure_sims(200) works correctly,
    # but subsequent calls have an off-by-one error in the simulation counting.

print("""
DIAGNOSIS:
The issue appears to be that:
1. ensure_sims(200) correctly gives 200 child visits
2. ensure_sims(400) only adds 199 more visits instead of 200

This is likely because:
- The ensure_sims logic calculates needed_sims = target - current_visits
- But there's a race condition or off-by-one in the threaded simulation loop
- OR the root node consumes one visit that's not distributed to children in subsequent runs

SOLUTION:
The fix should be in the ensure_sims implementation or worker thread logic.
""")