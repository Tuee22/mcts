#!/usr/bin/env python3
"""Debug by checking what board.is_terminal() returns."""

try:
    from corridors.corridors_mcts import Corridors_MCTS
except ImportError:
    print("Could not import Corridors_MCTS")
    exit(1)

# I need to create a debug version that exposes the board's is_terminal method to Python
# For now, let me trace what's happening by looking at the evaluation logic more carefully

mcts = Corridors_MCTS(
    c=2.0,
    seed=789,
    min_simulations=150,
    max_simulations=300,
    sim_increment=30,
    use_rollout=True,
    decide_using_visits=True,
)

print("=== BEFORE MOVE ===")
print("Initial evaluation:", mcts.get_evaluation())  # Should be None
print()

mcts.ensure_sims(150)
print("Making wall move V(7,1) with flip=True")
mcts.make_move("V(7,1)", flip=True)

print("\n=== AFTER WALL MOVE ===")
eval_result = mcts.get_evaluation()
print("Evaluation:", eval_result, type(eval_result))
actions = mcts.get_sorted_actions(flip=False)
print("Actions available:", len(actions))

# The fact that there are 127 actions but evaluation is -1.0 means either:
# 1. The board.is_terminal() is incorrectly returning true when it shouldn't
# 2. The get_terminal_eval() is being called inappropriately
# 3. There's a logic error in the modified get_evaluation() method

# Let's test if the issue happens immediately after a wall placement
print("\n=== TESTING SECOND MOVE ===")
if actions:
    next_move = actions[0][2]  # Get the best move for villain
    print(f"Making villain move {next_move} with flip=False")
    mcts.make_move(next_move, flip=False)

    eval_after_second = mcts.get_evaluation()
    print("Evaluation after second move:", eval_after_second)
    actions_after_second = mcts.get_sorted_actions(flip=True)
    print("Actions after second move:", len(actions_after_second))

# Maybe the problem is that placing a wall is being interpreted as winning the game?
# The wall V(7,1) is placed near one of the end zones, maybe that's confusing the terminal detection

print("\n=== TESTING DIFFERENT WALL POSITIONS ===")
for wall_pos in ["V(4,4)", "H(4,4)", "V(1,1)", "H(1,1)"]:
    mcts_test = Corridors_MCTS(
        c=1.0,
        seed=789,
        min_simulations=50,
        max_simulations=100,
        sim_increment=10,
        use_rollout=True,
        decide_using_visits=True,
    )

    mcts_test.ensure_sims(50)
    actions_before = mcts_test.get_sorted_actions(flip=True)

    # Check if this wall position is legal
    legal_moves = [a[2] for a in actions_before]
    if wall_pos in legal_moves:
        print(f"Testing wall position {wall_pos}:")
        mcts_test.make_move(wall_pos, flip=True)
        eval_result = mcts_test.get_evaluation()
        actions_after = len(mcts_test.get_sorted_actions(flip=False))
        print(f"  Evaluation: {eval_result}, Actions: {actions_after}")
    else:
        print(f"Wall position {wall_pos} not legal")
