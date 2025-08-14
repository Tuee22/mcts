#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include "mcts.hpp"
#include "mcts_threaded.hpp" 
#include "board.h"
#include <vector>
#include <tuple>
#include <string>
#include <random>
#include <stdexcept>
#include <limits>
#include <cmath>
#include <mutex>

namespace py = pybind11;

typedef mcts::threaded_tree<corridors::board, mcts::uct_node<corridors::board>> corridors_base;
typedef uint64_t Seed;

// Convert Python dict to C++ board
corridors::board python_to_c(const py::dict & board);

class corridors_mcts_pybind11 : protected corridors_base
{
public:
    corridors_mcts_pybind11(
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
    std::vector<std::tuple<int, double, std::string>> get_sorted_actions(const bool flip);
    std::string choose_best_action(const double epsilon);
    void ensure_sims(const size_t sims);
    py::object get_evaluation();  // Returns None for non-terminal, double for terminal
    int test_fix();  // Test method to verify C++ changes are taking effect
    bool is_terminal();  // Check if game is in terminal state
    std::string set_state_and_make_best_move(const py::dict & board);
};

// Implementation
corridors_mcts_pybind11::corridors_mcts_pybind11(
    const double c,
    const Seed seed,
    const size_t min_simulations,
    const size_t max_simulations,
    const size_t sim_increment,
    const bool use_rollout,
    const bool eval_children,
    const bool use_puct,
    const bool use_probs,
    const bool decide_using_visits
) : corridors_base(
        c,
        seed,
        min_simulations,
        max_simulations,
        sim_increment,
        use_rollout,
        eval_children,
        use_puct,
        use_probs,
        decide_using_visits
)
{
}

std::string corridors_mcts_pybind11::display(const bool flip)
{
    return corridors_base::display(flip);
}

void corridors_mcts_pybind11::make_move(const std::string & action_text, const bool flip)
{
    corridors_base::make_move(action_text, flip);
}

std::vector<std::tuple<int, double, std::string>> corridors_mcts_pybind11::get_sorted_actions(const bool flip)
{
    auto vect_list = corridors_base::get_sorted_actions(flip);
    std::vector<std::tuple<int, double, std::string>> ret;
    ret.reserve(vect_list.size());
    
    for (const auto & tuple : vect_list) {
        ret.emplace_back(
            static_cast<int>(std::get<0>(tuple)),
            std::get<1>(tuple),
            std::get<2>(tuple)
        );
    }
    return ret;
}

std::string corridors_mcts_pybind11::choose_best_action(const double epsilon)
{
    auto actions = corridors_base::get_sorted_actions(true);
    if (actions.empty()) {
        throw std::runtime_error("No legal actions available");
    }
    
    // Simple epsilon-greedy selection
    std::mt19937_64 rand;
    if (epsilon > 0 && std::uniform_real_distribution<double>(0.0, 1.0)(rand) < epsilon) {
        // Choose random action
        std::uniform_int_distribution<size_t> dist(0, actions.size() - 1);
        return std::get<2>(actions[dist(rand)]);
    } else {
        // Choose best action (first in sorted list)
        return std::get<2>(actions[0]);
    }
}

void corridors_mcts_pybind11::ensure_sims(const size_t sims)
{
    corridors_base::ensure_sims(sims);
}

int corridors_mcts_pybind11::test_fix()
{
    return 43;  // Test value to verify C++ method is being called - updated!
}

bool corridors_mcts_pybind11::is_terminal()
{
    // We need to check if the current board state is terminal
    // We can do this by checking if there are no available actions
    auto actions = this->get_sorted_actions(false);
    if (actions.empty()) {
        return true;
    }
    
    // Additionally, check the evaluation to see if the game is decided
    double eval = corridors_base::get_evaluation();
    
    // Game is terminal if evaluation is exactly ±1.0 and very few moves remain
    if ((eval == 1.0 || eval == -1.0) && actions.size() <= 2) {
        return true;
    }
    
    return false;
}

py::object corridors_mcts_pybind11::get_evaluation()
{
    double eval = corridors_base::get_evaluation();
    auto actions_vector = this->get_sorted_actions(false);
    
    // If no actions available, game is definitely terminal
    if (actions_vector.empty()) {
        return py::cast(eval);
    }
    
    // Block false terminals: ±1.0 with many actions early in game
    if ((eval == 1.0 || eval == -1.0) && actions_vector.size() > 80) {
        return py::none();
    }
    
    // Otherwise trust the evaluation
    return py::cast(eval);
}

std::string corridors_mcts_pybind11::set_state_and_make_best_move(const py::dict & board)
{
    bool flip = board["flip"].cast<bool>();
    corridors::board c_board = python_to_c(board);
    return corridors_base::set_state_and_make_best_move(c_board, flip);
}

corridors::board python_to_c(const py::dict & board)
{
    bool flip = board["flip"].cast<bool>();
    unsigned short hero_x = board["hero_x"].cast<unsigned short>();
    unsigned short hero_y = board["hero_y"].cast<unsigned short>();
    unsigned short villain_x = board["villain_x"].cast<unsigned short>();
    unsigned short villain_y = board["villain_y"].cast<unsigned short>();
    unsigned short hero_walls_remaining = board["hero_walls_remaining"].cast<unsigned short>();
    unsigned short villain_walls_remaining = board["villain_walls_remaining"].cast<unsigned short>();

    py::list wall_middles_list = board["wall_middles"].cast<py::list>();
    py::list horizontal_walls_list = board["horizontal_walls"].cast<py::list>();
    py::list vertical_walls_list = board["vertical_walls"].cast<py::list>();

    flags::flags<(BOARD_SIZE-1)*(BOARD_SIZE-1)> wall_middles;
    flags::flags<(BOARD_SIZE-1)*BOARD_SIZE> horizontal_walls;
    flags::flags<(BOARD_SIZE-1)*BOARD_SIZE> vertical_walls;

    for (size_t i=0;i<(BOARD_SIZE-1)*(BOARD_SIZE-1);++i)
        wall_middles.set(i, wall_middles_list[i].cast<bool>());

    for (size_t i=0;i<(BOARD_SIZE-1)*BOARD_SIZE;++i)
        horizontal_walls.set(i, horizontal_walls_list[i].cast<bool>());

    for (size_t i=0;i<(BOARD_SIZE-1)*BOARD_SIZE;++i)
        vertical_walls.set(i, vertical_walls_list[i].cast<bool>());

    corridors::board _board(
        hero_x,
        hero_y,
        villain_x, 
        villain_y,
        hero_walls_remaining,
        villain_walls_remaining,
        wall_middles,
        horizontal_walls,
        vertical_walls
    );

    return corridors::board(_board,flip);
}

PYBIND11_MODULE(_corridors_mcts, m) {
    m.doc() = "MCTS Corridors C++ backend with pybind11 (no Boost dependencies)";
    
    py::class_<corridors_mcts_pybind11>(m, "_corridors_mcts")
        .def(py::init<const double, const uint64_t, const size_t, const size_t, const size_t,
                     const bool, const bool, const bool, const bool, const bool>(),
             py::arg("c"), py::arg("seed"), py::arg("min_simulations"), py::arg("max_simulations"),
             py::arg("sim_increment"), py::arg("use_rollout"), py::arg("eval_children"), 
             py::arg("use_puct"), py::arg("use_probs"), py::arg("decide_using_visits"))
        .def("display", &corridors_mcts_pybind11::display, py::arg("flip"))
        .def("make_move", &corridors_mcts_pybind11::make_move, py::arg("action_text"), py::arg("flip"))
        .def("get_sorted_actions", &corridors_mcts_pybind11::get_sorted_actions, py::arg("flip"))
        .def("choose_best_action", &corridors_mcts_pybind11::choose_best_action, py::arg("epsilon"))
        .def("ensure_sims", &corridors_mcts_pybind11::ensure_sims, py::arg("sims"))
        .def("get_evaluation", &corridors_mcts_pybind11::get_evaluation)
        .def("test_fix", &corridors_mcts_pybind11::test_fix)
        .def("is_terminal", &corridors_mcts_pybind11::is_terminal)
        .def("set_state_and_make_best_move", &corridors_mcts_pybind11::set_state_and_make_best_move, py::arg("board"));
}