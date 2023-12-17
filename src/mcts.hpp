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

    // gameplay actions (for end user)
    const G & get_state() const;
    bool simulate(const size_t simulations, Rand & rand, const double c);
    uct_node_ptr choose_best_action(Rand & rand, const double epsilon=0, const bool decide_using_visits=true);
    std::string display(const bool flip);
    uct_node_ptr make_move(const size_t choice);
    uct_node_ptr make_move(const std::string & action_text, const bool flip);
    std::vector<std::tuple<size_t, double, std::string>> get_sorted_actions(const bool flip); // flip==true means we get the move from hero's perspective
    bool is_explored()  const;

    // adds a child (should only be called from G)
    void emplace_back(G && input);

protected:

    void orphan();
    void select(uct_node_ptr & leaf, const double c) const;
    std::vector<uct_node_ptr> & get_children();
    void explore(Rand & rand, bool use_rollout);
    double rollout(Rand & rand) const;
    void backprop(const double eval);
    size_t get_visit_count() const;
    // tuple is (visit count, evaluation, move description)

private:
    double Q_sum;
    double eval_Q;
    size_t visit_count;
    bool all_children_explored;

    const G state;
    uct_node * parent;
    std::vector<uct_node_ptr> children;
    std::vector<double> eval_probs;

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
            eval = leaf->explore(rand);
        }

        // backup
        leaf->backprop(eval);
    }
    return true;
}

template <typename G>
void mcts::uct_node<G>::select(
    uct_node_ptr & leaf, 
    const double c, 
    Rand & rand, 
    bool use_puct, // false means use traditional UCT formula
    bool use_probs, 
    ) const
{
    const uct_node * curr_node_ptr = this;

    while(curr_node_ptr->is_explored()) // stop at the first leaf (ie first unexplored node)
    {
        std::vector<uct_node_ptr> & _children = curr_node_ptr->get_children();
        size_t best_action=0;

        // check if all children are explored-- if not, made a vector of them
        if (!all_children_explored)
        {
            std::vector<size_t> unexplored_children;
            for (size_t i=0;i<curr_node_ptr->_children.size();++i)
            {
                // construct vector of unexplored children -- must choose one randomly
                if (!curr_node_ptr->_children[i]->is_explored())
                {
                    unexplored_children.push_back(i);
                }
            }
            if (unexplored_children.size()==0)
                all_children_explored=true;
        }

        if (!all_children_explored)
        {
            // if not all children are explored, choose an unexplored node randomly
            std::uniform_real_distribution<double> unif(0.0,1.0);
            best_action=(size_t)(unif(Rand)*(double)unexplored_children.size())
        }
        else
        {
            double max_uct = std::numeric_limits<double>::min();
            // standard uct formula, see e.g. https://en.wikipedia.org/wiki/Monte_Carlo_tree_search
            // for a theoretical explanation. the negative sign on the first term
            // accounts for the fact that evaluations in the child nodes
            // are from villain's perspective, ergo a sign flip is needed
            // to get them from hero's.
            double Q = -curr_node_ptr->children[i]->Q_sum / (double)curr_node_ptr->children[i]->visit_count;
            double U;
            if (use_puct)
            {
                U = sqrt((double)curr_node_ptr->visit_count-1.0);  // the -1 comes from the fact that the first visit to the parent node did not conincide with a visit to the child node
                / (1+(double)curr_node_ptr->children[i]->visit_count);
                if (use_probs)
                    U *= eval_probs[i];
            }
            else
            {
                double log_visit_count = std::log((double)curr_node_ptr->visit_count);
                U=sqrt(log_visit_count / (double)curr_node_ptr->children[i]->visit_count);
            }

            double curr_uct = Q + c * U;
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

// chooses an action to take from current board position based on epsilon-greedy policy
template <typename G>
typename mcts::uct_node<G>::uct_node_ptr mcts::uct_node<G>::choose_best_action(
    Rand & rand,
    const double epsilon,
    const bool decide_using_visits, // false means we decide using equity
    )
{
    if(epsilon <0 || epsilon>1)
        throw std::string("Error: improper use of choose_best_action. Check arguments.");

    std::vector<uct_node_ptr> _children = get_children();
    size_t num_legal_moves = _children.size();

    if (_children.size()==0)
        throw std::string("Error: no legal moves!");

    size_t choice=0;
    double eval=0;
    if (state.check_non_terminal_eval(eval))
    {
        // if it's possible to get a (heuristic), non-terminal
        // evaluation for this state, we will make our move decision
        // according to that criteria rather than uct.
        // this basically signifies that we're now in the territory
        // of domain-specific knowledge and no longer need the tree
        int min_non_terminal_rank = std::numeric_limits<int>::min();
        for (size_t i=0;i<num_legal_moves;++i)
        {
            double _;
            bool curr_flag = _children[i]->state.check_non_terminal_eval(_); // never choose a child action which lacks a non-terminal eval !
            int curr_rank = _children[i]->state.get_non_terminal_rank();
            if (curr_flag && curr_rank > min_non_terminal_rank)
            {
                min_non_terminal_rank = curr_rank;
                choice=i;
            }
        }
    }
    else
    {
        std::uniform_real_distribution<double> unif(0.0,1.0); // call unif(rand)
        bool greedy = !(epsilon > 0 && unif(rand) < epsilon)

        if(greedy)
        {
            // randomly choose between ties (helps avoid infinite loops)
            std::vector<size_t> choices_queue;
            if (decide_using_visits)
            {

                size_t max_visit_count=0;
                for (size_t i=0;i<num_legal_moves;++i)
                {
                    if (_children[i]->visit_count > max_visit_count)
                    {
                        choices_queue.clear();
                        max_visit_count = _children[i]->visit_count;
                    }
                    if (_children[i]->visit_count >= max_visit_count) // NB: this is always true when the above if is true
                    {
                        choices_queue.push_back(i);
                    }
                }
            } else if {


            }

            // randomly select a value from choices_queue
            if (choices_queue.size()>1)
                choice = choices_queue[(size_t)(unif(rand) * (double)choices_queue.size())];
            else
                choice = choices_queue[0];
        }
        else
        {
            choice = unif(rand) * (double)num_legal_moves;
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
double mcts::uct_node<G>::rollout(Rand & rand) const
{
    return rollout<G>()(state,rand);
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
std::vector<uct_node_ptr> mcts::uct_node<G>::get_children()
{
    // nb: expand can be thought of memoization for a child of a lazy evaluated
    // (which itself is a lazy tree)
    if (children.size==0)
    {
        children.clear();
        state.get_legal_moves(*this);
        children.shrink_to_fit();
    }
    return children;
}

template <typename G>
void mcts::uct_node<G>::explore(Rand & rand, bool use_rollout)
{
    if (!is_explored())
    {
        // check if game is over
        double non_terminal_eval;
        if (state->is_terminal())
            eval_Q=get_terminal_eval();
        // check if a non-terminal exact eval is available
        else if (state->check_non_termiinal_eval(non_terminal_eval))
            eval_Q=non_terminal_eval;
        else if (use_rollout)
            // use random rollout
            eval_Q=rollout(rand);
        else {
            const std::vector<uct_node_ptr> & _children = get_children();
            state->eval(eval_Q,_children,eval_probs);
            // test code
            assert (eval_probs.size()==0 || eval_probs.size()==_children.size())
        }

        // set initial explored state
        visit_count=1;
        Q_sum=eval_Q;
        eval_probs.shrink_to_fit();
        return;
    }

    throw std::string("Error: exploring when already explored");
}

template <typename G>
void mcts::uct_node<G>::Set_Null()
{
    parent = NULL;
    Q_sum = 0;
    visit_count = 0;
    eval_Q = 0;
    all_children_explored = false;
}

// performs the "backup" phase of the MCTS search
template <typename G>
void mcts::uct_node<G>::backprop(const double eval)
{
    uct_node * curr_node_ptr = this;
    bool initial_heros_turn = true;
    while(curr_node_ptr)
    {
        curr_node_ptr->Q_sum+=(initial_heros_turn?1.0:-1.0) * eval;
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
            equity = -_child->Q_sum / (double)_child->visit_count;

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
bool mcts::uct_node<G>::is_explored() const
{
    return visit_count>0;
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