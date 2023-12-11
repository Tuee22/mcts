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

    // rollout timing loop
    {
        corridors::board sb;
        mcts::Rand rand(42);
        size_t evals = 100000;
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
    }

    // self-play testing loop
    {   
        // hyperparameters
        mcts::Rand rand(63);
        double c = std::sqrt(0.25);
        size_t initial_sims = 100000;
        size_t per_move_sims = 10000;

        std::shared_ptr<mcts::uct_node<corridors::board>> my_mcts(new mcts::uct_node<corridors::board>());
        clock_t begin, end;
        double elapsed_secs, eval;
        size_t move_number = 0;
        std::cout << "***Self play simulation***" << std::endl;
        begin = clock();
        my_mcts->simulate(initial_sims,rand,c);
        end = clock();
        elapsed_secs = double(end - begin) / CLOCKS_PER_SEC;
        std::cout << "Initial sims took " << elapsed_secs/(double)initial_sims << " per simulation, or " << (double)initial_sims / elapsed_secs << " per second."<< std::endl;
        std::cout << std::endl;

        bool initial_heros_turn = true;

        try {
            //while(!my_mcts->get_state()->is_terminal())
            while(!my_mcts->get_state().check_non_terminal_eval(eval))
            {
                // flip board (if necessary) then display
                std::cout << "Move number: " << move_number++ << std::endl;
                std::cout << (initial_heros_turn?"Hero to play":"Villain to play")<<std::endl;
                corridors::board curr_move_flipped(my_mcts->get_state(), !initial_heros_turn);
                std::cout << curr_move_flipped.display();

                // simulate
                begin = clock();
                my_mcts->simulate(per_move_sims,rand,c);
                end = clock();
                elapsed_secs = double(end - begin) / CLOCKS_PER_SEC;
                std::cout << "Move sims took " << elapsed_secs/(double)per_move_sims << " per simulation, or " << (double)per_move_sims / elapsed_secs << " per second."<< std::endl;
                std::cout << my_mcts->display(initial_heros_turn);

                //getch();

                // make move
                my_mcts = my_mcts->choose_best_action(rand,0.00);
                initial_heros_turn = !initial_heros_turn;
            }
            corridors::board curr_move_flipped(my_mcts->get_state(), !initial_heros_turn);
            std::cout << (curr_move_flipped.hero_wins()?"Hero wins!":"Villain wins!")<<std::endl;
            std::cout << curr_move_flipped.display();
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