import logging
import sys
from math import sqrt
from typing import Dict, List, Optional, Protocol, Tuple, Type, Union

import numpy as np


# Define a protocol for the C++ extension base class
class MCTSProtocol(Protocol):
    def __init__(
        self,
        c: float,
        seed: int,
        min_simulations: int,
        max_simulations: int,
        sim_increment: int,
        use_rollout: bool,
        eval_children: bool,
        use_puct: bool,
        use_probs: bool,
        decide_using_visits: bool,
    ) -> None:
        ...

    def make_move(self, action: str, flip: bool = False) -> None:
        ...

    def get_sorted_actions(self, flip: bool = False) -> List[Tuple[int, float, str]]:
        ...

    def choose_best_action(self, epsilon: float = 0.0) -> str:
        ...

    def ensure_sims(self, num_sims: int) -> None:
        ...

    def get_evaluation(self) -> Optional[float]:
        ...

    def display(self, flip: bool = False) -> str:
        ...


# Import the C++ extension class
_corridors_mcts: Optional[Type[MCTSProtocol]] = None

def _load_extension():
    """Load the C++ extension with multiple fallback strategies."""
    global _corridors_mcts
    
    if _corridors_mcts is not None:
        return _corridors_mcts
    
    # Strategy 1: Direct import (works when .so is in Python path)
    try:
        import _corridors_mcts as _ext_module
        _corridors_mcts = _ext_module._corridors_mcts
        return _corridors_mcts
    except ImportError:
        pass
    
    # Strategy 2: Check if already loaded in sys.modules
    _module = sys.modules.get("corridors._corridors_mcts") or sys.modules.get("_corridors_mcts")
    if _module is not None:
        try:
            _corridors_mcts = getattr(_module, "_corridors_mcts")
            return _corridors_mcts
        except AttributeError:
            pass
    
    # Strategy 3: Import using importlib to avoid circular imports
    try:
        import importlib.util
        import os
        
        # Find the .so file in our package directory
        package_dir = os.path.dirname(__file__)
        so_files = [f for f in os.listdir(package_dir) if f.startswith('_corridors_mcts') and f.endswith('.so')]
        
        if so_files:
            so_path = os.path.join(package_dir, so_files[0])  # Use first available .so file
            spec = importlib.util.spec_from_file_location("_corridors_mcts", so_path)
            if spec and spec.loader:
                _ext_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(_ext_module)
                _corridors_mcts = _ext_module._corridors_mcts
                return _corridors_mcts
    except Exception:
        pass
    
    raise ImportError("Could not load _corridors_mcts extension")

# Load the extension at module level
_corridors_mcts = _load_extension()


class Corridors_MCTS:
    """
    Class manages state of an MCTS corridors instance.
    The instance runs simulations continuously in a separate
    thread, but is interruptable to take certain actions
    via the API calls below.

    The initializer arguments (with suggesed defaults)
    are the model hyperparemeters:

    c - exploration parameter. Higher values result in wider
        trees, lower values result in deeper trees.

    seed - random seed used for generating rollouts

    min_simulations - game will not provide evaluations
        via get_sorted_actions until at least this many
        simulations have been performed

    max_simulations - simulations will stop once this number
        is reached

    sim_increment - the number of simulations performed on
        each iteration of the event loop. reduce it if the
        API is being too slow.

    use_rollout - evaluate using randomly chosen moves till the
        game ends. False means use corridors::board::eval.

    eval_children - when a leaf is slected, immediately perform
        an evaluation on all children. select from the leaf is then
        done with the benefit of this initial evaluation (ie ranked selection).
        if eval_children==false children will be chosen randomly (unranked selection)
        and ranked selection will occur once each child has an evaluation.

    use_puct - use the alpha-zero style puct formula. false means use traditional uct

    use_probs - means the U term in the selection formula is scaled by the eval probability
        of each action. note that thse probablilites won't be set by use_rollout, and may or
        may not be set by corridors::board::eval. if probs are absent when use_probs==true,
        there will be a runtime exception.

    decide_using_visits - choose_best_action makes greedy choices based on number of visits
        in the tree. False means using equity (which has the potential to be biased towards
        under-explored nodes)
    """

    def __init__(
        self,
        c: float = sqrt(0.025),
        seed: int = 42,
        min_simulations: int = 10000,
        max_simulations: int = 10000,
        use_rollout: bool = True,
        eval_children: bool = False,
        use_puct: bool = False,
        use_probs: bool = False,
        decide_using_visits: bool = True,
    ) -> None:
        # Create the underlying C++ instance through composition
        self._impl: MCTSProtocol = _corridors_mcts(
            c,
            seed,
            min_simulations,
            max_simulations,
            1000,  # sim_increment - deprecated but still required by C++
            use_rollout,
            eval_children,
            use_puct,
            use_probs,
            decide_using_visits,
        )

    def __json__(self) -> Dict[str, str]:
        name_attr: str = getattr(self, "name", "unnamed")
        return {"type": str(type(self)), "name": name_attr}

    def display(self, flip: bool = False) -> str:
        """Provides an ASCII representation of the board from
        heros perspective. Flip will provide the same board
        from villain's perspective."""
        result: str = self._impl.display(flip)
        return result

    def make_move(self, action_text: str, flip: bool = False) -> None:
        """Makes a move according to the following action text:
        *(X,Y)  - move hero's token to new coordinate (X,Y)
        H(X,Y)  - place a horizontal wall at intersection (X,Y)
        V(X,Y)  - place a vertical wall at intersection (X,Y)"""
        self._impl.make_move(action_text, flip)

    def get_sorted_actions(self, flip: bool = True) -> List[Tuple[int, float, str]]:
        """Gets a list of tuples which represent all legal moves.
        List is sorted according to first value. Flip is defaulted
        to true since otherwise we'd be getting action/states from
        villain's perspective.
        Values are:
        0 - visits to state/action pair
        1 - estimated evaluation
        2 - string to describe action (i.e. what you pass to make_move to make that choice)
        """
        result: List[Tuple[int, float, str]] = self._impl.get_sorted_actions(flip)
        return result

    def choose_best_action(self, epsilon: float = 0) -> str:
        """make an epsilon-greedy choice"""
        result: str = self._impl.choose_best_action(epsilon)
        return result

    def ensure_sims(self, sims: int) -> None:
        """blocking function that holds until at
        least 'sims' simulations have been performed"""
        self._impl.ensure_sims(sims)

    def get_evaluation(self) -> Optional[float]:
        """Returns -1, 1, or None, depending on whether
        a non-terminal evaluation is available for this position"""
        eval_result: Optional[float] = self._impl.get_evaluation()
        return eval_result if eval_result else None


def display_sorted_actions(
    sorted_actions: List[Tuple[int, float, str]], list_size: int = 0
) -> str:
    output = ""
    output += f"Total Visits: {sum(a[0] for a in sorted_actions)}\n"
    for a in sorted_actions[: list_size if list_size else len(sorted_actions)]:
        output += f"Visit count: {a[0]} Equity: {a[1]:.4f} Action: {a[2]}\n"
    output += "\n"
    return output


def computer_self_play(
    p1: MCTSProtocol,
    p2: Optional[MCTSProtocol] = None,
    stop_on_eval: bool = False,
) -> None:
    """Pass one or two instances of corridors_mcts to perform self-play.
    p1 acts first"""
    if not p2:
        p2 = p1
    p1_is_hero = True

    sorted_actions = p1.get_sorted_actions(True)
    while len(sorted_actions):
        if p1_is_hero:
            print("Hero's turn")
            hero = p1
            villain = p2
        else:
            print("Villain's turn")
            hero = p2
            villain = p1

        # display the current board state and actions
        print(hero.display(not p1_is_hero))
        print(display_sorted_actions(sorted_actions, 5))

        # make action selection
        best_action = sorted_actions[0][2]

        hero.make_move(best_action, p1_is_hero)
        if hero is not villain:
            # in the 2-tree case, we have to make the same move in each tree
            villain.make_move(best_action, p1_is_hero)

        # stop early
        eval_result = hero.get_evaluation()
        if stop_on_eval and eval_result:
            print(hero.display(p1_is_hero))
            eval_val = eval_result * (-1 if p1_is_hero else 1)
            print("Hero wins!" if eval_val > 0 else "Villain wins!")
            break

        # prepare for next iteration
        sorted_actions = villain.get_sorted_actions(not p1_is_hero)
        hero_sorted_actions = hero.get_sorted_actions(
            p1_is_hero
        )  # we don't use this, we just call (blocking) to ensure min_simulations is met
        if len(sorted_actions) == 0:
            print(hero.display(p1_is_hero))
            print("Hero wins!" if p1_is_hero else "Villain wins!")

        p1_is_hero = not p1_is_hero


def human_computer_play(
    mcts: MCTSProtocol,
    human_plays_first: bool = True,
    hide_humans_moves: bool = True,
) -> None:
    """Pass a single instance of corridors_mcts to perform computer vs human play."""
    humans_turn = human_plays_first
    sorted_actions = mcts.get_sorted_actions(humans_turn)
    while len(sorted_actions):
        print("Your turn" if humans_turn else "Computer's turn")

        # display the current board state and actions
        print(mcts.display(not humans_turn))
        if not hide_humans_moves:
            print(display_sorted_actions(sorted_actions, 5))

        # make action selection
        if humans_turn:
            print("Please enter move:")
            action = input()
            while action not in (a[2] for a in sorted_actions):
                print("Illegal move!")
                action = input()
        else:
            action = sorted_actions[0][2]

        mcts.make_move(action, humans_turn)

        # prepare for next iteration
        sorted_actions = mcts.get_sorted_actions(not humans_turn)
        if len(sorted_actions) == 0:
            print(mcts.display(not humans_turn))
            print("Human wins!" if humans_turn else "Computer wins!")

        humans_turn = not humans_turn


if __name__ == "__main__":
    p1 = Corridors_MCTS(c=sqrt(2), seed=74)
    print(
        "Do you want to play against the computer? No means computer self-play. (y/n)"
    )
    if input() == "y":
        print("Please wait one moment...")
        human_computer_play(p1)
    else:
        p2 = Corridors_MCTS(seed=75)
        p1.ensure_sims(1000)
        p2.ensure_sims(1000)
        computer_self_play(p1, p2, stop_on_eval=True)
