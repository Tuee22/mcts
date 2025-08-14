#pragma once

#include "boost_python_utils.h"
#include "mcts_threaded.hpp"
#include "board.h"

using namespace boost_python_utils;

namespace p = boost::python;
namespace np = boost::python::numpy;
namespace sm = shallow_matrix;

typedef mcts::threaded_tree<corridors::board,mcts::uct_node<corridors::board>> corridors_base;

typedef std::mt19937_64 Rand; 
typedef uint_fast64_t Seed;

corridors::board python_to_c(const p::dict & board);

class corridors_threaded_api : protected corridors_base
{
public:
    corridors_threaded_api(
        const double c,
        const Seed seed,
        const size_t min_simulations,
        const size_t max_simulations,
        const size_t sim_increment,
        const bool use_rollout,
        const bool eval_children,
        const bool use_puct,
        const bool use_probs,
        const bool decide_using_visits);

    std::string display(const bool flip);
    void make_move(const std::string & action_text, const bool flip);
    p::list get_sorted_actions(const bool flip);
    std::string choose_best_action(const double epsilon);
    void ensure_sims(const size_t sims);
    double get_evaluation();
    std::string set_state_and_make_best_move(const p::dict & board);
};