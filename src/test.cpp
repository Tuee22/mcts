#include "mcts.hpp"
#include "board.h"

#include <iostream>
#include <vector>
#include <algorithm>
#include <ctime>
#include <memory>
#include "conio.h"
#include <random>


int main()
{
/*     {
        std::shared_ptr<mcts::uct_node<corridors::board>> my_mcts(new mcts::uct_node<corridors::board>());
        mcts::Rand rand(42);
        double c = std::sqrt(2.0);
        size_t sims = 1000;
        my_mcts->simulate(sims, rand, c);
        std::cout << my_mcts->display();
    }*/

    /*
    // rollout timing loop
    {
        corridors::board sb;
        mcts::Rand rand(42);
        size_t evals = 10000;
        double sum=0;
        std::cout << "Pure rollouts:" << std::endl;
        clock_t begin = clock();
        for (size_t i = 0;i<evals;++i)
            sum += mcts::rollout<corridors::board>()(sb,rand);
        clock_t end = clock();
        double elapsed_secs = double(end - begin) / CLOCKS_PER_SEC;
        std::cout << "It took " << elapsed_secs/(double)evals << " per rollout, or " << (double)evals / elapsed_secs << " per second."<< std::endl;
        std::cout << "Mean value: " << sum / (double) evals << std::endl;
        std::cout << std::endl;
    }*/

    
    // self-play testing loop
    {   
        // hyperparameters
        mcts::Rand rand(66); // 63 segfaults; 66 infinite cycle at end 
        double c = std::sqrt(0.25);
        size_t initial_sims = 100;
        size_t per_move_sims = 100;
        bool use_rollout = true;
        bool eval_children = true;
        bool use_puct = true;
        bool use_probs = false;
        bool decide_using_visits = true;
        bool terminate_early = false; // true means we terminate when there's a non-terminal eval
        bool getch_each_move = false; // true means pauses for user input


        try {

            std::shared_ptr<mcts::uct_node<corridors::board>> my_mcts(new mcts::uct_node<corridors::board>());
            clock_t begin, end;
            double elapsed_secs; // eval
            size_t move_number = 0;
            std::cout << "***Self play simulation***" << std::endl;
            begin = clock();
            my_mcts->simulate(initial_sims,rand,c,use_rollout,eval_children,use_puct,use_probs);
            end = clock();
            elapsed_secs = double(end - begin) / CLOCKS_PER_SEC;
            std::cout << "Initial sims took " << elapsed_secs/(double)initial_sims << " per simulation, or " << (double)initial_sims / elapsed_secs << " per second."<< std::endl;
            std::cout << std::endl;

            bool initial_heros_turn = true;
            do
            {
                // flip board (if necessary) then display
                std::cout << "Move number: " << move_number++ << std::endl;
                std::cout << (initial_heros_turn?"Hero to play":"Villain to play") << std::endl;
                corridors::board curr_move_heros_perspective(my_mcts->get_state(), !initial_heros_turn);
                std::cout << curr_move_heros_perspective.display();

                // simulate
                std::string pre_sim_equity = my_mcts->is_evaluated()
                    ? boost::lexical_cast<std::string>(my_mcts->get_equity())
                    : "NA";
                begin = clock();
                my_mcts->simulate(per_move_sims,rand,c,use_rollout,eval_children,use_puct,use_probs);
                end = clock();
                elapsed_secs = double(end - begin) / CLOCKS_PER_SEC;
                std::cout << "Move sims took " << elapsed_secs/(double)per_move_sims << " per simulation, or " << (double)per_move_sims / elapsed_secs << " per second."<< std::endl;
                std::string post_sim_equity = my_mcts->is_evaluated()
                    ? boost::lexical_cast<std::string>(my_mcts->get_equity())
                    : "NA";
                std::cout << "Pre sim Q value: " << pre_sim_equity  << std::endl;
                std::cout << "Post sim Q value: " << post_sim_equity << std::endl;
                std::cout << my_mcts->display(initial_heros_turn);

                if (getch_each_move)
                    getch();

                // make move
                my_mcts = my_mcts->choose_best_action(rand,0.00,decide_using_visits);
                initial_heros_turn = !initial_heros_turn;
            }
            while (
                !my_mcts->get_state().is_terminal()
                && (terminate_early
                    ? !my_mcts->check_non_terminal_eval()
                    : true)
            );

            corridors::board final_state_heros_perspective(my_mcts->get_state(), !initial_heros_turn);
            double heros_final_eval;
            if (final_state_heros_perspective.is_terminal())
            {
                heros_final_eval=(double)final_state_heros_perspective.hero_wins();
            }
            else if(!final_state_heros_perspective.check_non_terminal_eval(heros_final_eval))
            {
                throw std::string("Error: could not determine who won"); 
            }

            std::string win_text(
                heros_final_eval>0
                    ? "Hero wins!"
                    : "Villain wins!"
            );

            std::cout << win_text <<std::endl;
            std::cout << final_state_heros_perspective.display();
        }
        catch (std::string err)
        {
            std::cout << err << std::endl;
        }
        catch (std::vector<corridors::board> & moves)
        {
            std::cout << "error: reached end of simulations without end" << std::endl;
            std::cout << "board has " << moves.size() << " moves" << std::endl;
            for(size_t i=0; i<moves.size();++i)
            {
                corridors::board curr_move_flipped(moves[i], i%2);
                std::cout << "move number: " << i << std::endl;
                std::cout << curr_move_flipped.display();
                getch();
            }
        }
    }
    
    return 0;
}