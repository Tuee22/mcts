/**
 * Pybind11 bindings for Corridors MCTS implementation.
 * 
 * This module provides Python bindings for the C++ MCTS engine using pybind11.
 * The module exports a class _corridors_mcts that wraps the MCTS functionality.
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <vector>
#include <string>
#include <memory>
#include <random>
#include <tuple>
#include <optional>

#include "board.h"
#include "mcts.hpp"

namespace py = pybind11;

/**
 * Python-facing MCTS wrapper class that matches the interface defined in _corridors_mcts.pyi
 */
class _corridors_mcts {
private:
    std::shared_ptr<mcts::uct_node<corridors::board>> root_node;
    mcts::Rand random_generator;
    
    // MCTS configuration parameters
    double c_param;
    bool use_rollout;
    bool eval_children;
    bool use_puct;
    bool use_probs;
    bool decide_using_visits;
    
public:
    /**
     * Initialize MCTS with configuration parameters.
     */
    _corridors_mcts(
        double c,
        int seed,
        bool use_rollout,
        bool eval_children,
        bool use_puct,
        bool use_probs,
        bool decide_using_visits
    ) : c_param(c),
        use_rollout(use_rollout),
        eval_children(eval_children),
        use_puct(use_puct),
        use_probs(use_probs),
        decide_using_visits(decide_using_visits),
        random_generator(seed)
    {
        // Initialize with starting board position
        reset_to_initial_state();
    }
    
    /**
     * Make a move in the game.
     * @param action String representation of the move
     * @param flip Whether to flip the perspective
     */
    void make_move(const std::string& action, bool flip = false) {
        if (!root_node) {
            throw std::runtime_error("MCTS not initialized");
        }
        
        // Find and make the move
        auto new_node = root_node->make_move(action, flip);
        if (!new_node) {
            throw std::runtime_error("Invalid move: " + action);
        }
        root_node = new_node;
    }
    
    /**
     * Get list of legal moves from current position.
     * @param flip Whether to flip the perspective
     * @return Vector of move strings
     */
    std::vector<std::string> get_legal_moves(bool flip = false) {
        if (!root_node) {
            throw std::runtime_error("MCTS not initialized");
        }
        
        std::vector<std::string> moves;
        
        // Get legal moves from the board
        std::vector<corridors::board> legal_positions;
        root_node->get_state().get_legal_moves(legal_positions);
        
        // Convert to action strings
        for (const auto& board : legal_positions) {
            moves.push_back(board.get_action_text(flip));
        }
        
        return moves;
    }
    
    /**
     * Get sorted actions with visit counts, values, and action strings.
     * @param flip Whether to flip the perspective
     * @return Vector of tuples (visit_count, value, action_string)
     */
    std::vector<std::tuple<int, double, std::string>> get_sorted_actions(bool flip = false) {
        if (!root_node) {
            throw std::runtime_error("MCTS not initialized");
        }
        
        auto actions = root_node->get_sorted_actions(flip);
        
        // Convert size_t to int for Python compatibility
        std::vector<std::tuple<int, double, std::string>> result;
        for (const auto& action : actions) {
            result.emplace_back(
                static_cast<int>(std::get<0>(action)),
                std::get<1>(action),
                std::get<2>(action)
            );
        }
        
        return result;
    }
    
    /**
     * Choose the best action using epsilon-greedy selection.
     * @param epsilon Exploration probability
     * @return Action string
     */
    std::string choose_best_action(double epsilon = 0.0) {
        if (!root_node) {
            throw std::runtime_error("MCTS not initialized");
        }
        
        auto best_node = root_node->choose_best_action(random_generator, epsilon, decide_using_visits);
        if (!best_node) {
            throw std::runtime_error("No valid actions available");
        }
        
        return best_node->get_state().get_action_text(false);
    }
    
    /**
     * Run MCTS simulations.
     * @param n Number of simulations to run
     */
    void run_simulations(int n) {
        if (!root_node) {
            throw std::runtime_error("MCTS not initialized");
        }
        
        if (n <= 0) {
            return;
        }
        
        root_node->simulate(
            static_cast<size_t>(n),
            random_generator,
            c_param,
            use_rollout,
            eval_children,
            use_puct,
            use_probs
        );
    }
    
    /**
     * Get total visit count for the current node.
     * @return Visit count
     */
    int get_visit_count() {
        if (!root_node) {
            return 0;
        }
        return static_cast<int>(root_node->get_visit_count());
    }
    
    /**
     * Get evaluation/equity for the current position.
     * @return Optional evaluation value
     */
    std::optional<double> get_evaluation() {
        if (!root_node) {
            return std::nullopt;
        }
        
        if (!root_node->is_evaluated()) {
            return std::nullopt;
        }
        
        return root_node->get_equity();
    }
    
    /**
     * Display the current board state.
     * @param flip Whether to flip the perspective
     * @return String representation of the board
     */
    std::string display(bool flip = false) {
        if (!root_node) {
            return "MCTS not initialized";
        }
        
        return root_node->display(flip);
    }
    
    /**
     * Reset to initial game state.
     */
    void reset_to_initial_state() {
        // Create initial board state
        corridors::board initial_board;
        
        // Create root node with initial state
        root_node = std::make_shared<mcts::uct_node<corridors::board>>(std::move(initial_board));
    }
    
    /**
     * Check if the current position is terminal.
     * @return True if game is over
     */
    bool is_terminal() {
        if (!root_node) {
            return false;
        }
        return root_node->get_state().is_terminal();
    }
    
    /**
     * Get the winner of the game (if terminal).
     * @return Optional player number (0 or 1), or nullopt if not terminal
     */
    std::optional<int> get_winner() {
        if (!root_node || !is_terminal()) {
            return std::nullopt;
        }
        
        const auto& board = root_node->get_state();
        if (board.hero_wins()) {
            return 0;  // Hero (first player)
        } else if (board.villain_wins()) {
            return 1;  // Villain (second player)
        }
        
        return std::nullopt;  // Shouldn't happen if is_terminal() is true
    }
};

/**
 * Pybind11 module definition.
 * The module name must match the filename and Python import name.
 */
PYBIND11_MODULE(_corridors_mcts, m) {
    m.doc() = "Corridors MCTS C++ implementation with Python bindings";
    
    // Export the main MCTS class
    py::class_<_corridors_mcts>(m, "_corridors_mcts")
        .def(py::init<double, int, bool, bool, bool, bool, bool>(),
             "Initialize MCTS",
             py::arg("c"), py::arg("seed"), py::arg("use_rollout"),
             py::arg("eval_children"), py::arg("use_puct"), 
             py::arg("use_probs"), py::arg("decide_using_visits"))
        .def("make_move", &_corridors_mcts::make_move,
             "Make a move in the game",
             py::arg("action"), py::arg("flip") = false)
        .def("get_legal_moves", &_corridors_mcts::get_legal_moves,
             "Get list of legal moves",
             py::arg("flip") = false)
        .def("get_sorted_actions", &_corridors_mcts::get_sorted_actions,
             "Get sorted actions with statistics",
             py::arg("flip") = false)
        .def("choose_best_action", &_corridors_mcts::choose_best_action,
             "Choose best action with epsilon-greedy",
             py::arg("epsilon") = 0.0)
        .def("run_simulations", &_corridors_mcts::run_simulations,
             "Run MCTS simulations",
             py::arg("n"))
        .def("get_visit_count", &_corridors_mcts::get_visit_count,
             "Get total visit count")
        .def("get_evaluation", &_corridors_mcts::get_evaluation,
             "Get position evaluation")
        .def("display", &_corridors_mcts::display,
             "Display board state",
             py::arg("flip") = false)
        .def("reset_to_initial_state", &_corridors_mcts::reset_to_initial_state,
             "Reset to initial game state")
        .def("is_terminal", &_corridors_mcts::is_terminal,
             "Check if position is terminal")
        .def("get_winner", &_corridors_mcts::get_winner,
             "Get winner if game is over");
}