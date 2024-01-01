#pragma once
#include <random>
#include <vector>
#include <memory>
#include <limits>
#include "boost/lexical_cast.hpp"
#include <algorithm>

// test code
//#define PRINT_OUTPUT
//#define LOG_MOVES
#ifdef PRINT_OUTPUT
#include "conio.h"
#include <iostream>
#endif

#define MAX_ROLLOUT_ITERS 10000

namespace mcts {
typedef std::mt19937_64 Rand; 
typedef uint_fast64_t Seed;

template <typename G>
struct rollout
{
    double operator()(const G & input, Rand & rand) const;
};

template <typename G>
class uct_node
{
    typedef std::shared_ptr<uct_node<G>> uct_node_ptr;
public:
    uct_node() noexcept;
    uct_node(G && input, uct_node * _parent = NULL) noexcept;
    uct_node(const G & input) noexcept;

    // not copyable, but movable
    uct_node(const uct_node & source) noexcept = delete;
    uct_node& operator=(const uct_node & source) noexcept = delete;
    uct_node(uct_node && source) noexcept = default;
    uct_node & operator=(uct_node && source) noexcept = default;
    virtual ~uct_node() noexcept = default;

    // adds a child (should only be called from G)
    void emplace_back(G && input);

    // gameplay actions (for end user)
    void set_state(const G & input, uct_node_ptr & output);
    const G & get_state() const;
    void simulate(
        const size_t simulations,
        Rand & rand,
        const double c,
        const bool use_rollout,
        const bool eval_children,
        const bool use_puct,
        const bool use_probs
    );
    uct_node_ptr choose_best_action(Rand & rand, const double epsilon, const bool decide_using_visits);
    std::string display(const bool flip);
    uct_node_ptr make_move(const size_t choice);
    uct_node_ptr make_move(const std::string & action_text, const bool flip);
    std::vector<std::tuple<size_t, double, std::string>> get_sorted_actions(const bool flip); // flip==true means we get the move from hero's perspective
    bool is_evaluated() const;
    size_t get_visit_count() const;
    double get_equity() const;
    bool check_non_terminal_eval() const;

protected:
    void orphan();
    void select(uct_node_ptr & leaf, const double c, Rand & rand, const bool use_puct, const bool use_probs);
    std::vector<uct_node_ptr> & get_children();
    void eval(Rand & rand, const bool use_rollout, const bool eval_children);
    double rollout(Rand & rand) const;
    void backprop();
        // tuple is (visit count, evaluation, move description)

private:
    double Q_sum; // sum of all backprop'd equity values
    double eval_Q; // stored evaluation from rollout / handmade eval function / NN
    size_t visit_count; // number of backprops which have contributed to Q_sum (eval_Q always being the first)
    bool all_children_evaluated; // flag indicating that all children have an eval_Q populated

    const G state;
    uct_node * parent;
    std::vector<uct_node_ptr> children;
    std::vector<double> eval_probs;

    void Set_Null();        
};
}

template <typename G>
mcts::uct_node<G>::uct_node() noexcept : state()
{
    Set_Null();
}

template <typename G>
mcts::uct_node<G>::uct_node(G && input, mcts::uct_node<G> * _parent) noexcept : state(std::move(input))
{
    Set_Null();
    parent = _parent;
}

template <typename G>
mcts::uct_node<G>::uct_node(const G & input) noexcept : state(input)
{
    Set_Null();
}

template <typename G>
void mcts::uct_node<G>::emplace_back(G && input)
{
    children.emplace_back(uct_node_ptr(new uct_node<G>(std::move(input),this)));
}

template <typename G>
void mcts::uct_node<G>::set_state(const G & input, uct_node_ptr & output)
{
    // if we're setting the same session, do nothing
    if (input==state) return;

    // if it matches a child, return the child
    std::vector<uct_node_ptr> & _children = get_children();
    for(size_t i=0;i<_children.size();++i)
    {
        if (input==_children[i]->get_state())
        {
            output = make_move(i);
            return;
        }
    }

    // test code
    throw std::string("Unable to find state in child node.");

    // otherwise assign a new mcts instance initialized with input to the shared_ptr
    output.reset(new uct_node(input));
}

template <typename G>
const G & mcts::uct_node<G>::get_state() const
{
    return state;
}

// returns false if no simulations possible
template <typename G>
void mcts::uct_node<G>::simulate(
    const size_t simulations,
    Rand & rand,
    const double c, 
    const bool use_rollout,
    const bool eval_children,
    const bool use_puct,
    const bool use_probs)
{
    std::vector<uct_node_ptr> & _children = get_children();
    if (_children.size()==0 || state.is_terminal())
        throw std::string("Error: cannot simulate from a terminal state");

    // evaluate top node if it hasn't been evaluated
    if (!is_evaluated())
        eval(rand,use_rollout,eval_children);

    for(size_t i=0;i<simulations;++i)
    {
        uct_node_ptr leaf;

        // select node
        select(leaf, c, rand, use_puct, use_probs);

        // evaluate the node (and children if applicable)
        if (!leaf->is_evaluated())
            leaf->eval(rand, use_rollout, eval_children);
        else
            // test code
            if (!leaf->get_state().is_terminal() && !leaf->check_non_terminal_eval())
                throw std::string("Error: we have selected a node that is already evaluated, and is not terminal or nte");

        // backprop
        leaf->backprop();
    }
}

// chooses an action to take from current board position based on epsilon-greedy policy
template <typename G>
typename mcts::uct_node<G>::uct_node_ptr mcts::uct_node<G>::choose_best_action(
    Rand & rand,
    const double epsilon,
    const bool decide_using_visits // false means we decide using equity
    )
{
    if(epsilon <0 || epsilon>1)
        throw std::string("Error: improper use of choose_best_action. Check arguments.");

    std::vector<uct_node_ptr> _children = get_children();
    size_t num_legal_moves = _children.size();

    if (num_legal_moves==0)
        throw std::string("Error: no legal moves!");

    std::uniform_real_distribution<double> unif(0.0,1.0); // call unif(rand)
    size_t choice=std::numeric_limits<size_t>::max();

    // determine if there are any winning moves
    std::vector<size_t> winning_moves;
    for (size_t i=0;i<num_legal_moves;++i)
    {
        if (_children[i]->get_state().is_terminal() && _children[i]->get_equity()<0) // we use < because child equity is from villain's perspective, signifying a win for hero
            winning_moves.push_back(i);
    }
    
    if (winning_moves.size()>0)
    {
        // if there are multiple winning moves, choose one randomly
        if (winning_moves.size()>1)
            choice=winning_moves[(size_t)(unif(rand)+(double)winning_moves.size())];
        else
            choice=winning_moves[0];
    }
    else if (check_non_terminal_eval())
    {
        // evaluation for this state, we will make our move decision
        // if it's possible to get a (heuristic), non-terminal
        // according to that criteria rather than uct.
        // this basically signifies that we're now in the territory
        // of domain-specific knowledge and no longer need the tree
        int min_non_terminal_rank = std::numeric_limits<int>::max();
        for (size_t i=0;i<num_legal_moves;++i)
        {
            int curr_rank = _children[i]->state.get_non_terminal_rank(); // minimize this because get_non_terminal_rank returns rank from villain's perspective (ie high is good for villain)
            if (curr_rank < min_non_terminal_rank)
            {
                min_non_terminal_rank = curr_rank;
                choice=i;
            }
        }
    }
    else
    {
        bool greedy = !(epsilon > 0 && unif(rand) < epsilon);

        if(greedy)
        {
            // randomly choose between ties (helps avoid infinite loops)
            std::vector<size_t> choices_queue;
            if (decide_using_visits)
            {
                size_t max_visit_count=0;
                for (size_t i=0;i<num_legal_moves;++i)
                {
                    size_t curr_visit_count = _children[i]->visit_count; // no negation needed (as with equity below) because visit count always looks from parent node's perspective
                    if (curr_visit_count >= max_visit_count)
                    {
                        if (curr_visit_count > max_visit_count)
                        {
                            choices_queue.clear();
                            max_visit_count = curr_visit_count;
                        }
                        choices_queue.push_back(i);
                    }
                }
            }
            else 
            {
                // decide using equity
                double max_Q = std::numeric_limits<double>::lowest();
                for (size_t i=0;i<num_legal_moves;++i)
                {
                    double curr_Q = -_children[i]->get_equity(); // negative because equity is from villain's perspective
                    if (curr_Q >= max_Q)
                    {
                        if (curr_Q > max_Q)
                        {
                            choices_queue.clear();
                            curr_Q = max_Q;
                        }
                        choices_queue.push_back(i);
                    }
                }
            }

            // randomly select a value from choices_queue
            if (choices_queue.size()>1)
                choice = choices_queue[(size_t)(unif(rand) * (double)choices_queue.size())];
            else
                choice = choices_queue[0];
        }
        else
        {
            choice = (size_t)(unif(rand) * (double)num_legal_moves);
        }
    }

    if (choice==std::numeric_limits<size_t>::max())
        throw std::string("Error: unable to find a choice");

    // test code
    uct_node_ptr ret = make_move(choice);
    if (ret->get_children().size()==0 && !ret->get_state().is_terminal())
        throw std::string("Error: position is not marked as terminal, but there are no children");
    return ret;

    return make_move(choice);
}

// don't really need this anymore-- much more elegant
// to do this in Python
template <typename G>
std::string mcts::uct_node<G>::display(const bool flip)
{
    auto moves = get_sorted_actions(flip);    

    // display
    std::string res;

    res += "Total Visits: ";
    res += boost::lexical_cast<std::string>(visit_count);
    res += "\n";

    size_t wall_placements = 0;
    std::for_each(moves.cbegin(), moves.cend(), [&](const auto &mv)
    {
        res += "Visit Count: ";
        res += boost::lexical_cast<std::string>(std::get<0>(mv));

        res += " Equity: ";
        double equity=std::get<1>(mv);
        std::string eq(
            equity > std::numeric_limits<double>::lowest()
            ? boost::lexical_cast<std::string>(equity)
            : "NA"
        );
        eq.resize(6);
        res += eq;

        res += " ";
        res += std::get<2>(mv);
        res += "\n";
    });

    res += "\n";

    return std::move(res);
}

template <typename G>
typename mcts::uct_node<G>::uct_node_ptr mcts::uct_node<G>::make_move(const size_t choice)
{
    std::vector<uct_node_ptr> & _children = get_children();
    if (choice>=_children.size())
        throw std::string("Error: invalid move chosen.");
    _children[choice]->orphan(); // so that backprop stops when it reaches the top (see while loop condition in backprop())
    return _children[choice];
}

template <typename G>
typename mcts::uct_node<G>::uct_node_ptr mcts::uct_node<G>::make_move(const std::string & action_text, const bool flip)
{
    std::vector<uct_node_ptr> & _children = get_children();
    for (size_t i=0;i<_children.size();++i)
        if(_children[i]->state.get_action_text(flip)==action_text)
            return make_move(i);

    throw std::string("Illegial move.");
}

// Returns a vector of sorted actions, from best to worst. each action is represented by a tuple of
// (visit_count, equity, action_text).
template <typename G>
std::vector<std::tuple<size_t, double, std::string>> mcts::uct_node<G>::get_sorted_actions(const bool flip)
{
    std::vector<uct_node_ptr> & _children = get_children();

    std::vector<std::tuple<double, double, size_t, std::string>> moves;
    std::for_each(_children.cbegin(),_children.cend(),[&](const uct_node_ptr & _child)
    {
        // primary sort criteria is equity.
        // secondary sort criteria is non_terminal_rank, which acts
        // as a meaningful tie-breaker to prevent potentially infinite cycles
        // in an effectively "won" game

        double equity = _child->is_evaluated()
            ? -_child->get_equity()
            : std::numeric_limits<double>::lowest();

        moves.emplace_back(
            std::make_tuple(
                equity,
                (double)_child->state.get_non_terminal_rank(),
                _child->visit_count,
                _child->state.get_action_text(flip)
            )
        );
    });

    // sort it in descending order
    std::sort(moves.rbegin(), moves.rend());

    // assemble output (don't want all the above fields, and the display order can change
    // from the sorting order)
    std::vector<std::tuple<size_t, double, std::string>> moves_display;
    std::for_each(moves.cbegin(), moves.cend(),[&](const auto & move)
    {
        moves_display.emplace_back(
            std::make_tuple(
                std::get<2>(move),
                std::get<0>(move),
                std::get<3>(move)
            )
        );
    });

    return std::move(moves_display);
}

template <typename G>
bool mcts::uct_node<G>::is_evaluated() const
{
    return eval_Q > std::numeric_limits<double>::lowest();
}

template <typename G>
size_t mcts::uct_node<G>::get_visit_count() const
{
    return visit_count;
}

template <typename G>
double mcts::uct_node<G>::get_equity() const
{
    if (!is_evaluated())
        throw std::string("Error: cannot get equity without evaluation");

    // test code
    double equity = visit_count > 0
        ? Q_sum / (double)visit_count
        : eval_Q;

    if (equity < -1 || equity > 1)
        throw std::string(
            "Q_sum is " 
            + boost::lexical_cast<std::string>(Q_sum) + "\n"
            + "and visit count is "
            + boost::lexical_cast<std::string>(double(visit_count)) + "\n"
            + "and eval_Q is "
            + boost::lexical_cast<std::string>(eval_Q) + "\n"
        );
    return equity;

    return visit_count > 0
        ? Q_sum / (double)visit_count
        : eval_Q;
}

template <typename G>
bool mcts::uct_node<G>::check_non_terminal_eval() const
{
    double _;
    return state.check_non_terminal_eval(_);
}

// releases pointer reference to the parent
// (stopping backprop at this node, allowing parent
// to be safely deleted)
template <typename G>
void mcts::uct_node<G>::orphan()
{
    parent = NULL;
}

template <typename G>
void mcts::uct_node<G>::select(
    uct_node_ptr & leaf, 
    const double c, 
    Rand & rand, 
    const bool use_puct, // false means use traditional UCT formula
    const bool use_probs
    )
{
    uct_node * curr_node_ptr = this;

    size_t while_loop_iteration=0; // test code
    do
    {
        size_t best_action=std::numeric_limits<size_t>::max();
        const std::vector<uct_node_ptr> & curr_children = curr_node_ptr->get_children();
        if (curr_children.size()==0)
            throw std::string("Error: select encountered empty child vector, this shouldn't happen. Check continuation condition");
        // make a vector of any unexplored children, and select one randomly if there are any
        if (!curr_node_ptr->all_children_evaluated)
        {
            std::vector<size_t> unexplored_children;
            for (size_t i=0;i<curr_children.size();++i)
            {
                // construct vector of unexplored children -- must choose one randomly
                if (!curr_children[i]->is_evaluated())
                    unexplored_children.push_back(i);
            }
            if (unexplored_children.size()>0)
            {
                // if not all children are explored, choose an unexplored node randomly
                if (unexplored_children.size()>1)
                {
                    std::uniform_real_distribution<double> unif(0.0,1.0);
                    best_action=unexplored_children[(size_t)(unif(rand) * (double)unexplored_children.size())];
                }
                else
                    best_action=unexplored_children[0];
            }
            else
                curr_node_ptr->all_children_evaluated=true;            
        }

        if (curr_node_ptr->all_children_evaluated)
        {
            double max_uct = std::numeric_limits<double>::lowest();
            std::vector<size_t> best_actions;
            for (size_t i=0;i<curr_children.size();++i)
            {
                // standard uct formula, see e.g. https://en.wikipedia.org/wiki/Monte_Carlo_tree_search
                // for a theoretical explanation. the negative sign on the first term
                // accounts for the fact that evaluations in the child nodes
                // are from villain's perspective, ergo a sign flip is needed
                // to get them from hero's.
                double Q = -curr_children[i]->get_equity();
                double N = (double)curr_node_ptr->visit_count-1.0; // -1 because we want to count total simulations after parent move (traditional UCT); or total visit count to all actions from base state (PUCT)
                double n = (double)curr_children[i]->visit_count;
                double U;
                
                if (use_puct)
                    // AlphaZero style PUCT formula
                    U = sqrt(N) / (1.0+n);
                else
                    // standard UCT formula
                    U = sqrt(std::log(N) / std::max(n,1.0));

                if (use_probs)
                    U *= curr_node_ptr->eval_probs[i];

                double curr_uct = Q + c * U;

                if (curr_uct >= max_uct)
                {
                    if (curr_uct > max_uct)
                    {
                        // reset if we have set a new high
                        best_actions.clear();
                        max_uct = curr_uct;
                    }
                    best_actions.push_back(i);
                }
            }
        
            size_t num_best_actions=best_actions.size();
            if (num_best_actions>1)
            {
                // if there were ties for best action, choose that action randomly
                std::uniform_real_distribution<double> unif(0.0,1.0);
                best_action=best_actions[(size_t)(unif(rand) * (double)num_best_actions)];
            }
            else
                best_action=best_actions[0];

            if (best_action==std::numeric_limits<size_t>::max())
                throw std::string("Error: failed to select node");
        }
        // test code

        if (best_action<0 || best_action >= curr_children.size())
            throw std::string(
                "error: bounds violation on curr_children. best_action="
                + boost::lexical_cast<std::string>(best_action)
                + " when curr_children.size()=="
                + boost::lexical_cast<std::string>(curr_children.size())
                + " with while_loop_iteration=="
                + boost::lexical_cast<std::string>(while_loop_iteration)
            );

        if (!curr_children[best_action].get())
            throw std::string("error: null pointer!");

        // get the node we're choosing
        leaf = curr_children[best_action];
        curr_node_ptr = leaf.get();

    }
    while (
        // continue search if this node is evaluated (otherwise must stop and eval)
        curr_node_ptr->is_evaluated()
        // and if this position is not terminal (or it has no children)
        && !curr_node_ptr->get_state().is_terminal()
        // and check that there isn't a non-terminal eval
        && !curr_node_ptr->check_non_terminal_eval()
    );    
}

template <typename G>
std::vector<typename mcts::uct_node<G>::uct_node_ptr> & mcts::uct_node<G>::get_children()
{
    // nb: get_children can be thought of memoization for a child of a lazy evaluated
    // (which itself is a lazy tree)
    if (children.size()==0)
    {
        state.get_legal_moves(*this);
        children.shrink_to_fit();
    }
    return children;
}
 
template <typename G>
void mcts::uct_node<G>::eval(
    Rand & rand,
    const bool use_rollout,
    const bool eval_children)
{
    if (!is_evaluated())
    {
        // check if game is over
        double non_terminal_eval;
        bool truncate=false;
        if (state.is_terminal())
        {
            eval_Q=state.get_terminal_eval();
            truncate=true;
        }
        // check if a non-terminal exact eval is available
        else if (state.check_non_terminal_eval(non_terminal_eval))
        {
            eval_Q=non_terminal_eval;
            truncate=true;
        }
        else if (use_rollout)
            // use random rollout
            eval_Q=rollout(rand);
        else {
            // use bespoke evaluation function (which may or may not provide action probs)
            const std::vector<uct_node_ptr> & _children = get_children();
            state.eval(_children,eval_Q,eval_probs);
            // test code
            assert (eval_probs.size()==0 || eval_probs.size()==_children.size());
        }

        eval_probs.shrink_to_fit(); // want to shrink regardless of whether it has content

        if (eval_children && !truncate)
        {
            const std::vector<uct_node_ptr> & _children = get_children();
            for (size_t i=0;i<_children.size();++i)
                _children[i]->eval(rand,use_rollout,false);
            all_children_evaluated=true;
        }

        return;
    }

    throw std::string("Error: calling eval when already evaluated");
}

template <typename G>
double mcts::uct_node<G>::rollout(Rand & rand) const
{
    return mcts::rollout<G>()(state,rand);
}

// performs the "backup" phase of the MCTS search
template <typename G>
void mcts::uct_node<G>::backprop()
{
    // test code
    if (!is_evaluated())
        throw std::string("Error: cannot backprop without an evaluation");
    if (visit_count>0 && !get_state().is_terminal() && !check_non_terminal_eval())
        throw std::string("Error: cannot backprop from a node with visits that is not terminal");

    uct_node * curr_node_ptr = this;
    bool initial_heros_turn = true;
    while(curr_node_ptr)
    {
        curr_node_ptr->Q_sum+=(initial_heros_turn?1.0:-1.0) * eval_Q;
        curr_node_ptr->visit_count++;
        curr_node_ptr=curr_node_ptr->parent;
        initial_heros_turn = !initial_heros_turn;
    }
}

template <typename G>
void mcts::uct_node<G>::Set_Null()
{
    Q_sum = 0;
    eval_Q = std::numeric_limits<double>::lowest();
    visit_count = 0;
    all_children_evaluated = false;
    parent = NULL;
}

// performs naive (completely random) rollout
template <typename G>
double mcts::rollout<G>::operator()(const G & input, Rand & rand) const
{
    std::uniform_real_distribution<double> unif(0.0,1.0); // call unif(rand)
    bool initial_heros_turn = true;

    #ifdef LOG_MOVES
        std::vector<G> moves;
        moves.push_back(input);
    #endif

    G curr_move(input);
    for (size_t i=0;i<MAX_ROLLOUT_ITERS;++i)
    {   
        // if the episode is done, return valuation (from the perspective of active
        // agent from initial move)
        if (curr_move.is_terminal())
        {
            #ifdef PRINT_OUTPUT
                double eval = curr_move.get_terminal_eval();
                if (initial_heros_turn && eval>0
                    || !initial_heros_turn && eval<0)
                    std::cout << "Initial hero wins!" << std::endl;
                else if(initial_heros_turn && eval<0
                    || !initial_heros_turn && eval >0)
                    std::cout << "Initial villain wins!" << std::endl;
                else
                    throw std::string("wtf");
                std::cout << "Raw eval: " << eval << " modified eval: " << ((initial_heros_turn?1.0:-1.0) * curr_move.get_terminal_eval()) << std::endl;
            #endif
            return (initial_heros_turn?1.0:-1.0) * curr_move.get_terminal_eval();
        }

        double eval;
        if (curr_move.check_non_terminal_eval(eval))
            return (initial_heros_turn?1.0:-1.0) * eval;

        std::vector<G> actions;
        curr_move.get_legal_moves(actions);

        size_t random_index = unif(rand) * actions.size();
        curr_move = std::move(actions[random_index]);

        #ifdef LOG_MOVES
            moves.push_back(curr_move);
        #endif

        // flip whose turn it is
        initial_heros_turn = !initial_heros_turn;

        // test code
        #ifdef PRINT_OUTPUT
        std::cout << "i: " << i << std::endl;
        G curr_move_flipped(curr_move, !initial_heros_turn);
        std::cout << curr_move_flipped.display();
        getch();
        #endif
    }

    #ifdef LOG_MOVES
        throw moves;
    #else
        // becuse we hit max moves without returning
        throw std::string("Error: mcts::rollout MAX_ITERATIONS reached without end of episode.");
    #endif
}
