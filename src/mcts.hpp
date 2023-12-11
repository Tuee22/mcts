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
    uct_node();
    uct_node(G && input, uct_node * _parent = NULL);
    uct_node(const G & input);

    // not copyable, but movable
    uct_node(const uct_node & source) noexcept = delete;
    uct_node& operator=(const uct_node & source) noexcept = delete;
    uct_node(uct_node && source) noexcept = default;
    uct_node & operator=(uct_node && source) noexcept = default;
    virtual ~uct_node() noexcept = default;
    void set_state(const G & input, uct_node_ptr & output);


    void orphan();
    void emplace_back(G && input);
    const G & get_state() const;


    bool simulate(const size_t simulations, Rand & rand, const double c);
    void select(uct_node_ptr & leaf, const double c) const;
    void expand();
    double evaluate(Rand & rand) const;
    void backprop(const double eval);
    std::string display(const bool flip);
    uct_node_ptr choose_best_action(Rand & rand, const double epsilon=0);
    uct_node_ptr make_move(const size_t choice);
    uct_node_ptr make_move(const std::string & action_text, const bool flip);
    size_t get_visit_count() const;
    // tuple is (visit count, evaluation, move description)
    std::vector<std::tuple<size_t, double, std::string>> get_sorted_actions(const bool flip); // flip==true means we get the move from hero's perspective

private:
    double eval_sum;
    size_t visit_count;

    const G state;
    uct_node * parent;
    std::vector<uct_node_ptr> children;

    void Set_Null();        
};
}

template <typename G>
mcts::uct_node<G>::uct_node()
{
    Set_Null();
}

template <typename G>
void mcts::uct_node<G>::set_state(const G & input, uct_node_ptr & output)
{
    // if we're setting the same session, do nothing
    if (input==state) return;

    // if it matches a child, return the child
    for(size_t i=0;i<children.size();++i)
    {
        if (input==children[i]->get_state())
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
mcts::uct_node<G>::uct_node(G && input, mcts::uct_node<G> * _parent) : state(std::move(input))
{
    Set_Null();
    parent = _parent;
}

template <typename G>
mcts::uct_node<G>::uct_node(const G & input) : state(input)
{
    Set_Null();
}

template <typename G>
void mcts::uct_node<G>::emplace_back(G && input)
{
    children.emplace_back(uct_node_ptr(new uct_node<G>(std::move(input),this)));
}

template <typename G>
const G & mcts::uct_node<G>::get_state() const
{
    return state;
}

// returns false if no simulations possible
template <typename G>
bool mcts::uct_node<G>::simulate(const size_t simulations, Rand & rand, const double c)
{
    if (children.size()==0) expand();
    if (children.size()==0) return false;

    uct_node_ptr leaf;
    for(size_t i=0;i<simulations;++i)
    {
        // select node
        select(leaf,c);

        double eval;
        // only expand/simulate if no non-terminal evaluation is
        // available.
        if (!leaf->state.check_non_terminal_eval(eval))
        {
            // if there has already been at lest one simulation for this node,
            // expand and select one of the new leaves
            if (leaf->visit_count>0)
            {
                leaf->expand();
                leaf->select(leaf,c);
            }

            // evaluate
            eval = leaf->evaluate(rand);
        }

        // backup
        leaf->backprop(eval);
    }
    return true;
}

template <typename G>
void mcts::uct_node<G>::select(uct_node_ptr & leaf, const double c) const
{
    const uct_node * curr_node_ptr = this;

    while(curr_node_ptr->children.size()>0)
    {
        double log_visit_count = std::log((double)curr_node_ptr->visit_count);
        double max_uct = std::numeric_limits<double>::min();
        size_t best_action=0;
        double curr_uct=0;
        for (size_t i=0;i<curr_node_ptr->children.size();++i)
        {
            // select the first node we encounter that has a visit_count of 0 (it needs a simulation performed)
            if (curr_node_ptr->children[i]->visit_count==0)
            {
                best_action = i;
                break;
            }
            // standard uct formula, see e.g. https://en.wikipedia.org/wiki/Monte_Carlo_tree_search
            // for a theoretical explanation. the negative sign on the first term
            // accounts for the fact that evaluations in the child nodes
            // are from villain's perspective, ergo a sign flip is needed
            // to get them from hero's.
            curr_uct =
                -curr_node_ptr->children[i]->eval_sum / (double)curr_node_ptr->children[i]->visit_count // equity (exploitation)
                + c * sqrt(log_visit_count / (double)curr_node_ptr->children[i]->visit_count); // exploration term
            if (curr_uct > max_uct)
            {
                max_uct = curr_uct;
                best_action = i;
            }
        }

        // get the node we're choosing
        leaf = curr_node_ptr->children[best_action];
        curr_node_ptr = leaf.get();
    }    
}

// chooses an action based on epsilon-greedy policy
template <typename G>
typename mcts::uct_node<G>::uct_node_ptr mcts::uct_node<G>::choose_best_action(Rand & rand, const double epsilon)
{
    if(epsilon <0 || epsilon>1)
        throw std::string("Error: improper use of choose_best_action. Check arguments.");

    if (children.size()==0)
        throw std::string("Error: no legal moves!");

    size_t choice=0;
    double eval;
    if (state.check_non_terminal_eval(eval))
    {
        // if it's possible to get a (heuristic), non-terminal
        // evaluation for this state, we will make our move decision
        // according to that criteria rather than uct.
        // this basically signifies that we're now in the territory
        // of domain-specific knowledge and no longer need the tree
        int min_non_terminal_rank = std::numeric_limits<int>::min();
        for (size_t i=0;i<children.size();++i)
        {
            int curr_rank = children[i]->state.get_non_terminal_rank();
            if (curr_rank > min_non_terminal_rank)
            {
                min_non_terminal_rank = curr_rank;
                choice=i;
            }
        }
    }
    else
    {
        std::uniform_real_distribution<double> unif(0.0,1.0); // call unif(rand)
        bool greedy=true;
        if (epsilon > 0 && unif(rand) < epsilon) greedy=false;

        if(greedy)
        {
            // randomly choose between ties (helps avoid infinite loops)
            std::vector<size_t> choices_queue;
            size_t max_visit_count=0;
            for (size_t i=0;i<children.size();++i)
            {
                if (children[i]->visit_count > max_visit_count)
                {
                    choices_queue.clear();
                    max_visit_count = children[i]->visit_count;
                }
                if (children[i]->visit_count >= max_visit_count) // NB: this is always true when the above if is true
                {
                    choices_queue.push_back(i);
                }
            }

            // randomly select a value from choices_queue
            if (choices_queue.size()>0)
                choice = choices_queue[(size_t)(unif(rand) * (double)choices_queue.size())];
            else
                choice = choices_queue[0];
        }
        else
        {
            choice = unif(rand) * (double)children.size();
        }
    }

    return make_move(choice);
}

template <typename G>
typename mcts::uct_node<G>::uct_node_ptr mcts::uct_node<G>::make_move(const size_t choice)
{
    if (choice>=children.size())
        throw std::string("Error: invalid move chosen.");
    children[choice]->orphan(); // so that backprop stops when it reaches the top (see while loop condition in backprop())
    return children[choice];
}

template <typename G>
typename mcts::uct_node<G>::uct_node_ptr mcts::uct_node<G>::make_move(const std::string & action_text, const bool flip)
{
    for (size_t i=0;i<children.size();++i)
        if(children[i]->state.get_action_text(flip)==action_text)
            return make_move(i);

    throw std::string("Illegial move.");
}

template <typename G>
size_t mcts::uct_node<G>::get_visit_count() const
{
    return visit_count;
}

template <typename G>
double mcts::uct_node<G>::evaluate(Rand & rand) const
{
    return rollout<G>()(state,rand);
}

// releases smart pointer reference to the parent
// (stopping backprop at this node, allowing parent
// to be safely deleted)
template <typename G>
void mcts::uct_node<G>::orphan()
{
    parent = NULL;
}

template <typename G>
void mcts::uct_node<G>::expand()
{
    children.clear();
    state.get_legal_moves(*this);
    children.shrink_to_fit();
}

template <typename G>
void mcts::uct_node<G>::Set_Null()
{
    parent = NULL;
    eval_sum = 0;
    visit_count = 0;
}

// performs the "backup" phase of the MCTS search
template <typename G>
void mcts::uct_node<G>::backprop(const double eval)
{
    uct_node * curr_node_ptr = this;
    bool initial_heros_turn = true;
    while(curr_node_ptr)
    {
        curr_node_ptr->eval_sum+=(initial_heros_turn?1.0:-1.0) * eval;
        curr_node_ptr->visit_count++;
        curr_node_ptr=curr_node_ptr->parent;
        initial_heros_turn = !initial_heros_turn;
    }
}

// Returns a vector of sorted actions, from best to worst. each action is represented by a tuple of
// (visit_count, equity, action_text).
template <typename G>
std::vector<std::tuple<size_t, double, std::string>> mcts::uct_node<G>::get_sorted_actions(const bool flip)
{
    // ensure we've populated legal moves for this state
    if (children.size()==0) expand();

    std::vector<std::tuple<double, double, size_t, std::string>> moves;
    std::for_each(children.cbegin(),children.cend(),[&](const uct_node_ptr & _child)
    {
        // primary sort criteria is equity.
        // secondary sort criteria is non_terminal_rank, which acts
        // as a meaningful tie-breaker to prevent potentially infinite cycles
        // in an effectively "won" game

        double equity = std::numeric_limits<double>::min();
        if ((double)_child->visit_count)
            equity = -_child->eval_sum / (double)_child->visit_count;

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
        std::string eq(boost::lexical_cast<std::string>(std::get<1>(mv)));
        eq.resize(6);
        res += eq;

        res += " ";
        res += std::get<2>(mv);
        res += "\n";
    });

    res += "\n";

    return std::move(res);
}

// performs naive (completely random) rollout
template <typename G>
double mcts::rollout<G>::operator()(const G & input, Rand & rand) const
{
    std::uniform_real_distribution<double> unif(0.0,1.0); // call unif(rand)
    std::vector<G> actions;
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

        actions.clear();
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
} // namespace mcts