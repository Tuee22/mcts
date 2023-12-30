#pragma once
#include "mcts.hpp"
#include <boost/interprocess/sync/interprocess_semaphore.hpp>
#include <boost/core/noncopyable.hpp>
#include <thread>
#include <mutex>
#include <atomic>
#include <condition_variable>

// threaded wrapper for e.g. an instance of uct_node<G>
// that runs simulations continuiously in another thread
// while providing ways to query and alter it while it's running
namespace mcts {
    template <typename G, typename TREE>
    class threaded_tree : boost::noncopyable {
        typedef std::shared_ptr<TREE> tree_ptr;

        public:
            threaded_tree(
                const double c,
                const Seed seed,
                const size_t min_simulations,
                const size_t max_simulations,
                const size_t sim_increment) noexcept; // start threaded event loop        
            virtual ~threaded_tree();

            void set_state(const G & state);
            std::vector<std::tuple<size_t, double, std::string>> get_sorted_actions(const bool flip);
            void make_move(const size_t mv_number);
            void make_move(const std::string & action_text, const bool flip);
            std::string display(const bool flip);
            //void choose_best_action(Rand rand, const double epsilon, const bool use_visit_count);
            void ensure_sims(const size_t sims);
            std::string set_state_and_make_best_move(const G & board, const bool flip);
            double get_evaluation();

        private:
            tree_ptr _node;
            std::mutex _node_mut; // don't touch _node without acquiring this with std::lock_guard<std::mutex> lock(_node_mut);
            std::condition_variable _cv;

            boost::interprocess::interprocess_semaphore _sem;
            std::thread _thread;
            std::atomic_bool _terminate, _pause_loop;

            Rand _rand;
            size_t _min_simulations, _max_simulations, _sim_increment;
            double _c;

            std::shared_ptr<std::lock_guard<std::mutex>> get_lock(const bool enforce_min_sims=false); // use auto get_lock(); at the beginning of any function interacting with _node
    };
}// namespace mcts

template <typename G, typename TREE>
mcts::threaded_tree<G,TREE>::threaded_tree(
    const double c,
    const Seed seed,
    const size_t min_simulations,
    const size_t max_simulations,
    const size_t sim_increment) noexcept
    : _sem(1), _rand(seed), _node(new TREE())
{
    // initialize everything
    _terminate = false;
    _pause_loop = false;
    _c = c;
    _min_simulations=min_simulations;
    _max_simulations=max_simulations;
    _sim_increment=sim_increment;

    // start the simulation loop in a separate thread
    _thread = std::thread([&](){
        try{
            while(!_terminate) // _terminate signals for the loop to stop when we're destructing
            {
                _sem.wait(); // semaphore controls the continuation/stopping of the loop based on _max_simulations
                if (!_terminate) // check _terminate again in case we were waiting on the semaphore when we destructed (avoids an extra simulation)
                {
                    std::unique_lock<std::mutex> lk(_node_mut); // obtain a lock
                    _cv.wait(lk, [&]{return !_pause_loop;}); // _pause_loop signals that the main thread wants access
                    
                    if (!_node->get_state().is_terminal())
                    {
                        _node->simulate(_sim_increment,_rand,_c,true,false,false,false); // simulate returns false when no sims were done (e.g. when the game is done)
                        if (_node->get_visit_count()<_max_simulations)
                            _sem.post(); // post if we want to keep looping (so we don't block on _sem.wait())
                    }
                }
            }
        }
        catch(...) // any thrown exception kills the loop
        {
            _terminate=true; // ensures no spurious loop re-starts (probably not necessary)
            throw std::string("Error: simulation loop killed due to thrown exception.");
        }
    });
}

template <typename G, typename TREE>
void mcts::threaded_tree<G,TREE>::set_state(const G & input)
{
    auto _lock = get_lock(false);
    _node->set_state(input, _node);
    _sem.post();
}

template <typename G, typename TREE>
mcts::threaded_tree<G,TREE>::~threaded_tree()
{    
    _terminate = true; // signals to stop the loop
    _sem.post(); // to ensure while loop isn't blocked on _sem.wait()
    _thread.join(); // wait for the thread to shutdown gracefully
} // member destructors now called

template <typename G, typename TREE>
std::shared_ptr<std::lock_guard<std::mutex>> mcts::threaded_tree<G,TREE>::get_lock(const bool enforce_min_sims)
{
    // this will cause the loop to block (with the mutex available) on its next _cv.wait statement
    _pause_loop=true; 

    // acquire the mutex so the loop doesn't alter state
    std::shared_ptr<std::lock_guard<std::mutex>> lock_ptr(new std::lock_guard<std::mutex>(_node_mut));
    
    // this is so the loop doesn't block on the next wait statement it encounters (even though right now it's still waiting on _cv.wait)
    _pause_loop=false; 

    // this notifies the loop to check the _pause_loop condition, and notice that it is now false,
    // indicating it is allowed to lock the mutex once it is available again
    // (which happens when the lock_guard above goes out of scope)
    _cv.notify_one(); 

    // ensure we have performed the minimum number of simulations (if applicible)
    if (enforce_min_sims && !_node->get_state().is_terminal() && _node->get_visit_count()<_min_simulations)
        _node->simulate(_min_simulations -_node->get_visit_count()+1,_rand,_c, true, false, false, false);

    // give ownership of the lock to the user-- the loop will now remain blocked
    // until they release it, and the user can safely alter state
    return std::move(lock_ptr);
}

template <typename G, typename TREE>
std::vector<std::tuple<size_t, double, std::string>> mcts::threaded_tree<G,TREE>::get_sorted_actions(const bool flip)
{
    auto _lock = get_lock(true);
    return _node->get_sorted_actions(flip);
}

template <typename G, typename TREE>
void mcts::threaded_tree<G,TREE>::make_move(const size_t choice)
{
    auto _lock = get_lock(false);
    _node = _node->make_move(choice);
    _sem.post();
}

template <typename G, typename TREE>
void mcts::threaded_tree<G,TREE>::make_move(const std::string & action_text, const bool flip)
{
    auto _lock = get_lock(false);
    _node = _node->make_move(action_text, flip);
    _sem.post();
}

template <typename G, typename TREE>
std::string mcts::threaded_tree<G,TREE>::display(const bool flip)
{
    auto _lock = get_lock(false);
    G state_to_display(_node->get_state(),flip);
    return state_to_display.display();
}
/*
template <typename G, typename TREE>
void mcts::threaded_tree<G,TREE>::choose_best_action(Rand rand, const double epsilon, const bool use_visit_count)
{
    auto _lock = get_lock(true);
    _node = _node->choose_best_action(rand,epsilon,use_visit_count);
    _sem.post();
}*/

template <typename G, typename TREE>
void mcts::threaded_tree<G,TREE>::ensure_sims(const size_t sims)
{
    auto _lock = get_lock(true);
    if (!_node->get_state().is_terminal() && _node->get_visit_count()<sims)
        _node->simulate(sims -_node->get_visit_count()+1,_rand,_c,true,false,false,false);
}

template <typename G, typename TREE>
std::string mcts::threaded_tree<G,TREE>::set_state_and_make_best_move(const G & board, const bool flip)
{
    auto _lock = get_lock(false);
    // set the state (shouldn't have an effect in most cases, as we'll already be on the appropriate state)
    _node->set_state(board, _node);
    _sem.post();

    // ensure we have performed the minimum number of simulations on the current state
    if (!_node->get_state().is_terminal() && _node->get_visit_count()<_min_simulations)
        _node->simulate(_min_simulations -_node->get_visit_count()+1,_rand,_c,true,false,false,false);

    // get the best move
    std::vector<std::tuple<size_t, double, std::string>> move_vect = _node->get_sorted_actions(flip);

    // handle case where there are no legal moves
    // to avoid segfault 
    if (move_vect.empty())
        return "No legal moves.";

    std::string best_move_text = std::get<2>(move_vect[0]);

    // make the best move in the tree
    _node = _node->make_move(best_move_text, flip);

    // return the text description for the best move
    return best_move_text;
}

template <typename G, typename TREE>
double mcts::threaded_tree<G,TREE>::get_evaluation()
{
    auto _lock = get_lock(false);
    double eval=0;
    _node->get_state().check_non_terminal_eval(eval);
    return eval;
}
