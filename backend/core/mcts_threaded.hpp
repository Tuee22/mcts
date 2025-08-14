#pragma once
#include "mcts.hpp"
#include <thread>
#include <mutex>
#include <atomic>
#include <condition_variable>
#include <memory>
#include <chrono>
#include <limits>

// threaded wrapper for e.g. an instance of uct_node<G>
// that runs simulations continuously in another thread
// while providing ways to query and alter it while it's running
namespace mcts {
    template <typename G, typename TREE>
    class threaded_tree {
        typedef std::shared_ptr<TREE> tree_ptr;

        // Non-copyable
        threaded_tree(const threaded_tree&) = delete;
        threaded_tree& operator=(const threaded_tree&) = delete;

        public:
            threaded_tree(
                const double c,
                const uint64_t seed,
                const size_t min_simulations,
                const size_t max_simulations,
                const size_t sim_increment,
                const bool use_rollout,
                const bool eval_children,
                const bool use_puct,
                const bool use_probs,
                const bool decide_using_visits) noexcept; // start threaded event loop        
            virtual ~threaded_tree();

            std::string display(const bool flip = false) const;
            void make_move(const std::string & action, const bool flip = false);
            std::vector<std::tuple<size_t,double,std::string>> get_sorted_actions(const bool flip = false) const;
            void ensure_sims(const size_t sims);
            double get_evaluation() const;
            std::string set_state_and_make_best_move(const G & board, const bool flip = false);

        private:
            void worker_thread();
            void run_simulation();
            
            mutable std::mutex mutex_;
            std::condition_variable cv_;
            std::atomic<bool> stop_flag_{false};
            std::thread worker_;
            
            tree_ptr tree_;
            mcts::Rand rand_;
            
            // Configuration
            double c_param_;
            std::atomic<size_t> target_sims_{0};
            std::atomic<size_t> min_sims_;
            std::atomic<size_t> max_sims_;
            size_t sim_increment_;
            bool use_rollout_;
            bool eval_children_;
            bool use_puct_;
            bool use_probs_;
            bool decide_using_visits_;
    };

    // Implementation
    template <typename G, typename TREE>
    threaded_tree<G,TREE>::threaded_tree(
        const double c,
        const uint64_t seed,
        const size_t min_simulations,
        const size_t max_simulations,
        const size_t sim_increment,
        const bool use_rollout,
        const bool eval_children,
        const bool use_puct,
        const bool use_probs,
        const bool decide_using_visits) noexcept
        : rand_(seed)
        , c_param_(c)
        , min_sims_(min_simulations)
        , max_sims_(max_simulations) 
        , sim_increment_(sim_increment)
        , use_rollout_(use_rollout)
        , eval_children_(eval_children)
        , use_puct_(use_puct)
        , use_probs_(use_probs)
        , decide_using_visits_(decide_using_visits)
    {
        // Initialize tree with default board state
        G default_board;
        tree_ = std::make_shared<TREE>(default_board);
        worker_ = std::thread(&threaded_tree::worker_thread, this);
    }

    template <typename G, typename TREE>
    threaded_tree<G,TREE>::~threaded_tree() {
        stop_flag_ = true;
        cv_.notify_all();
        if (worker_.joinable()) {
            worker_.join();
        }
    }

    template <typename G, typename TREE>
    void threaded_tree<G,TREE>::worker_thread() {
        std::unique_lock<std::mutex> lock(mutex_);
        while (!stop_flag_) {
            size_t target = target_sims_.load();
            if (target > 0) {
                lock.unlock();
                // Run simulations outside the lock
                try {
                    size_t sims_to_run = std::min(sim_increment_, target_sims_.load());
                    
                    // Guard against infinite loop if sim_increment is 0
                    if (sim_increment_ == 0) {
                        target_sims_.store(0);  // Clear target to avoid infinite loop
                        continue;
                    }
                    
                    for (size_t i = 0; i < sims_to_run && !stop_flag_ && target_sims_.load() > 0; ++i) {
                        run_simulation();
                        target_sims_.fetch_sub(1);
                    }
                } catch (...) {
                    // Handle simulation errors gracefully
                }
                lock.lock();
            } else {
                cv_.wait(lock);
            }
        }
    }

    template <typename G, typename TREE>
    void threaded_tree<G,TREE>::run_simulation() {
        std::lock_guard<std::mutex> lock(mutex_);
        try {
            tree_->simulate(1, rand_, c_param_, use_rollout_, eval_children_, use_puct_, use_probs_);
        } catch (const std::string& e) {
            // Handle MCTS simulation errors (e.g., terminal states)
        } catch (...) {
            // Handle other errors
        }
    }

    template <typename G, typename TREE>
    std::string threaded_tree<G,TREE>::display(const bool flip) const {
        std::lock_guard<std::mutex> lock(mutex_);
        G state_to_display(tree_->get_state(), flip);
        return state_to_display.display();
    }

    template <typename G, typename TREE>
    void threaded_tree<G,TREE>::make_move(const std::string & action, const bool flip) {
        std::lock_guard<std::mutex> lock(mutex_);
        try {
            auto new_tree = tree_->make_move(action, flip);
            tree_ = new_tree;
        } catch (const std::string& e) {
            throw std::runtime_error("Illegal move: " + action);
        }
    }

    template <typename G, typename TREE>
    std::vector<std::tuple<size_t,double,std::string>> threaded_tree<G,TREE>::get_sorted_actions(const bool flip) const {
        std::lock_guard<std::mutex> lock(mutex_);
        return tree_->get_sorted_actions(flip);
    }

    template <typename G, typename TREE>
    void threaded_tree<G,TREE>::ensure_sims(const size_t sims) {
        // Guard against invalid sim_increment
        if (sim_increment_ == 0) {
            return; // Cannot run simulations with zero increment
        }
        
        size_t current_visits = 0;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            current_visits = tree_->get_visit_count();
        }
        
        if (current_visits < sims) {
            size_t needed_sims = sims - current_visits;
            target_sims_.store(needed_sims);
            cv_.notify_one();
            
            // Wait for completion with timeout
            auto start_time = std::chrono::steady_clock::now();
            const auto timeout = std::chrono::seconds(10);
            
            while (target_sims_.load() > 0 && !stop_flag_) {
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
                
                // Timeout protection
                if (std::chrono::steady_clock::now() - start_time > timeout) {
                    target_sims_.store(0); // Force completion
                    break;
                }
            }
            
            // Double-check we have enough visits - run one more if needed
            {
                std::lock_guard<std::mutex> lock(mutex_);
                size_t final_visits = tree_->get_visit_count();
                if (final_visits < sims && sim_increment_ > 0) {
                    target_sims_.store(1);
                    cv_.notify_one();
                    start_time = std::chrono::steady_clock::now();
                    while (target_sims_.load() > 0 && !stop_flag_) {
                        std::this_thread::sleep_for(std::chrono::milliseconds(1));
                        if (std::chrono::steady_clock::now() - start_time > timeout) {
                            target_sims_.store(0);
                            break;
                        }
                    }
                }
            }
        }
    }

    template <typename G, typename TREE>
    double threaded_tree<G,TREE>::get_evaluation() const {
        std::lock_guard<std::mutex> lock(mutex_);
        try {
            return tree_->get_equity();
        } catch (...) {
            return 0.0; // Default if no evaluation available
        }
    }

    template <typename G, typename TREE>
    std::string threaded_tree<G,TREE>::set_state_and_make_best_move(const G & board, const bool flip) {
        std::lock_guard<std::mutex> lock(mutex_);
        
        // Create new tree with the given board state
        tree_ = std::make_shared<TREE>(board);
        
        // Run some simulations to get good moves
        size_t min_sims = min_sims_.load();
        if (min_sims > 0) {
            // Unlock temporarily to run simulations
            mutex_.unlock();
            target_sims_.store(min_sims);
            cv_.notify_one();
            
            // Wait for simulations
            while (target_sims_.load() > 0 && !stop_flag_) {
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
            }
            
            mutex_.lock();
        }
        
        // Get best action
        try {
            auto best_node = tree_->choose_best_action(rand_, 0.0, decide_using_visits_);
            tree_ = best_node;
            return tree_->get_state().get_action_text(flip);
        } catch (const std::string& e) {
            throw std::runtime_error("No legal moves available");
        }
    }
}