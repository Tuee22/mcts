#!/usr/bin/env python3
"""Debug the actual board state after wall moves."""

try:
    from python.corridors.corridors_mcts import Corridors_MCTS
except ImportError:
    print("Could not import Corridors_MCTS")
    exit(1)


def print_board_analysis(name, mcts):
    print(f"=== {name} ===")
    display = mcts.display(flip=False)
    print("Board state:")
    print(display)

    # Extract positions from display
    lines = display.strip().split("\n")
    hero_pos = villain_pos = None

    for y, line in enumerate(lines):
        if "h" in line.lower():
            x = line.lower().find("h") // 4  # Each column is ~4 chars wide
            hero_pos = (x, len(lines) - 1 - y)  # Flip y coordinate
        if "v" in line.lower():
            x = line.lower().find("v") // 4
            villain_pos = (x, len(lines) - 1 - y)

    print(f"Hero position (estimated): {hero_pos}")
    print(f"Villain position (estimated): {villain_pos}")

    if hero_pos and hero_pos[1] == 8:
        print("*** HERO AT WINNING POSITION (y=8) ***")
    if villain_pos and villain_pos[1] == 0:
        print("*** VILLAIN AT WINNING POSITION (y=0) ***")

    eval_result = mcts.get_evaluation()
    print(f"Evaluation: {eval_result}")

    actions = mcts.get_sorted_actions(flip=False)
    print(f"Actions available: {len(actions)}")
    print()


# Test the problematic sequence
mcts1 = Corridors_MCTS(
    c=2.0,
    seed=789,
    min_simulations=50,
    max_simulations=100,
    sim_increment=10,
    use_rollout=True,
    decide_using_visits=True,
)

print_board_analysis("INITIAL STATE", mcts1)

mcts1.ensure_sims(50)
print("Making wall move V(7,1) with flip=True")
mcts1.make_move("V(7,1)", flip=True)

print_board_analysis("AFTER V(7,1) WITH FLIP=TRUE", mcts1)

# Compare with a positional move
mcts2 = Corridors_MCTS(
    c=2.0,
    seed=789,
    min_simulations=50,
    max_simulations=100,
    sim_increment=10,
    use_rollout=True,
    decide_using_visits=True,
)

mcts2.ensure_sims(50)
print("Making positional move *(3,0) with flip=True")
mcts2.make_move("*(3,0)", flip=True)

print_board_analysis("AFTER *(3,0) WITH FLIP=TRUE", mcts2)

# Test the same wall move WITHOUT flip to see the difference
mcts3 = Corridors_MCTS(
    c=2.0,
    seed=789,
    min_simulations=50,
    max_simulations=100,
    sim_increment=10,
    use_rollout=True,
    decide_using_visits=True,
)

mcts3.ensure_sims(50)
actions = mcts3.get_sorted_actions(flip=False)  # Get actions without flip
wall_actions = [a for a in actions if a[2].startswith("V(")]
if wall_actions:
    wall_move = wall_actions[0][2]
    print(f"Making wall move {wall_move} with flip=False")
    mcts3.make_move(wall_move, flip=False)

    print_board_analysis(f"AFTER {wall_move} WITH FLIP=FALSE", mcts3)
