#!/usr/bin/env python3
"""Debug the terminal detection issue."""

try:
    from python.corridors.corridors_mcts import Corridors_MCTS
except ImportError:
    print("Could not import Corridors_MCTS")
    exit(1)

# Create a simple debugging wrapper to call C++ board methods directly
# Let me see what's happening with the terminal detection

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
print("Initial evaluation:", mcts.get_evaluation())
print()

mcts.ensure_sims(150)
actions = mcts.get_sorted_actions(flip=True)

print("Making move V(7,1) with flip=True")
mcts.make_move("V(7,1)", flip=True)

# Check if this is actually a terminal state
print("=== POST-MOVE STATE ===")
print("Number of actions available:", len(mcts.get_sorted_actions(flip=False)))
print("Evaluation (should be None for non-terminal):", mcts.get_evaluation())

# This suggests the C++ is detecting this as terminal when it shouldn't be
# Let's check with a simpler move to see if it's specific to wall placement

print("\n=== TESTING WITH A FRESH INSTANCE ===")
mcts2 = Corridors_MCTS(
    c=2.0,
    seed=789,
    min_simulations=150,
    max_simulations=300,
    sim_increment=30,
    use_rollout=True,
    decide_using_visits=True,
)

print("Initial evaluation of fresh instance:", mcts2.get_evaluation())
mcts2.ensure_sims(150)
actions2 = mcts2.get_sorted_actions(flip=True)

# Find a positional move instead of a wall move
positional_moves = [action for action in actions2 if action[2].startswith("*(")]
print(f"Found {len(positional_moves)} positional moves")

if positional_moves:
    print(f"Making positional move {positional_moves[0][2]} with flip=True")
    mcts2.make_move(positional_moves[0][2], flip=True)
    
    print("Actions available after positional move:", len(mcts2.get_sorted_actions(flip=False)))
    print("Evaluation after positional move:", mcts2.get_evaluation())
else:
    print("No positional moves found!")

print("\n=== ACTION ANALYSIS ===")
for i, action in enumerate(actions[:10]):
    print(f"Action {i}: visits={action[0]}, equity={action[1]}, move={action[2]}")

print("\n=== TESTING ANOTHER WALL MOVE ===")
mcts3 = Corridors_MCTS(
    c=2.0,
    seed=789,
    min_simulations=150,
    max_simulations=300,
    sim_increment=30,
    use_rollout=True,
    decide_using_visits=True,
)
mcts3.ensure_sims(150)

# Find a different wall move  
actions3 = mcts3.get_sorted_actions(flip=True)
wall_moves = [action for action in actions3 if action[2].startswith("V(") or action[2].startswith("H(")]
if len(wall_moves) > 1:
    second_wall = wall_moves[1][2]
    print(f"Making second wall move {second_wall} with flip=True")
    mcts3.make_move(second_wall, flip=True)
    
    print("Actions available after second wall move:", len(mcts3.get_sorted_actions(flip=False)))
    print("Evaluation after second wall move:", mcts3.get_evaluation())