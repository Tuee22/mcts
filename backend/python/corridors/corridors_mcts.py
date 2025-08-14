from ._corridors_mcts import _corridors_mcts
from math import sqrt
import numpy as np
import logging
from typing import List, Tuple, Optional, Dict, Union, Any


class Corridors_MCTS(_corridors_mcts):

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
        super().__init__(
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
        return {"type": str(type(self)), "name": getattr(self, "name", "unnamed")}

    def display(self, flip: bool = False) -> str:
        """Provides an ASCII representation of the board from
        heros perspective. Flip will provide the same board
        from villain's perspective."""
        return super().display(flip)

    def make_move(self, action_text: str, flip: bool = False) -> None:
        """Makes a move according to the following action text:
        *(X,Y)  - move hero's token to new coordinate (X,Y)
        H(X,Y)  - place a horizontal wall at intersection (X,Y)
        V(X,Y)  - place a vertical wall at intersection (X,Y)"""
        return super().make_move(action_text, flip)

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
        return super().get_sorted_actions(flip)

    def choose_best_action(self, epsilon: float = 0) -> str:
        """make an epsilon-greedy choice"""
        return super().choose_best_action(epsilon)

    def ensure_sims(self, sims: int) -> None:
        """blocking function that holds until at
        least 'sims' simulations have been performed"""
        return super().ensure_sims(sims)

    def get_evaluation(self) -> Optional[float]:
        """Returns -1, 1, or None, depending on whether
        a non-terminal evaluation is available for this position"""
        eval = super().get_evaluation()
        return eval if eval else None


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
    p1: "Corridors_MCTS",
    p2: Optional["Corridors_MCTS"] = None,
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
    mcts: "Corridors_MCTS",
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
