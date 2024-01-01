#include "corridors_threaded_api.h"
#include <algorithm>

corridors_threaded_api::corridors_threaded_api(
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

std::string corridors_threaded_api::display(const bool flip)
{
    return corridors_base::display(flip);
}

void corridors_threaded_api::make_move(const std::string & action_text, const bool flip)
{
    corridors_base::make_move(action_text, flip);
}

p::list corridors_threaded_api::get_sorted_actions(const bool flip)
{
    p::list ret;
    auto vect_list = corridors_base::get_sorted_actions(flip);
    std::for_each(vect_list.cbegin(), vect_list.cend(), [&](const auto & tuple)
    {
        ret.append(
            p::make_tuple(
                std::get<0>(tuple),
                std::get<1>(tuple),
                std::get<2>(tuple)
            )
        );
    });
    return ret;
}

/*
void corridors_threaded_api::choose_best_action(Rand rand, const double epsilon, const bool decide_using_visits)
{
    corridors_base::choose_best_action(rand,epsilon,decide_using_visits);
}
*/

void corridors_threaded_api::ensure_sims(const size_t sims)
{
    corridors_base::ensure_sims(sims);
}

double corridors_threaded_api::get_evaluation()
{
    return corridors_base::get_evaluation();
}

std::string corridors_threaded_api::set_state_and_make_best_move(const p::dict & board)
{
    bool flip = p::extract<bool>(board.get("flip"));
    corridors::board c_board = python_to_c(board);
    return corridors_base::set_state_and_make_best_move(c_board, true);
}

corridors::board python_to_c(const p::dict & board)
{
    bool flip = p::extract<bool>(board.get("flip"));
    unsigned short hero_x = p::extract<unsigned short>(board.get("hero_x"));
    unsigned short hero_y = p::extract<unsigned short>(board.get("hero_y"));
    unsigned short villain_x = p::extract<unsigned short>(board.get("villain_x"));
    unsigned short villain_y = p::extract<unsigned short>(board.get("villain_y"));
    unsigned short hero_walls_remaining = p::extract<unsigned short>(board.get("hero_walls_remaining"));
    unsigned short villain_walls_remaining = p::extract<unsigned short>(board.get("villain_walls_remaining"));

    p::list wall_middles_list(board.get("wall_middles"));
    p::list horizontal_walls_list(board.get("horizontal_walls"));
    p::list vertical_walls_list(board.get("vertical_walls"));

    flags::flags<(BOARD_SIZE-1)*(BOARD_SIZE-1)> wall_middles;
    flags::flags<(BOARD_SIZE-1)*BOARD_SIZE> horizontal_walls;
    flags::flags<(BOARD_SIZE-1)*BOARD_SIZE> vertical_walls;

    for (size_t i=0;i<(BOARD_SIZE-1)*(BOARD_SIZE-1);++i)
        wall_middles.set(i, p::extract<bool>(wall_middles_list[i]));

    for (size_t i=0;i<(BOARD_SIZE-1)*BOARD_SIZE;++i)
        horizontal_walls.set(i, p::extract<bool>(horizontal_walls_list[i]));

    for (size_t i=0;i<(BOARD_SIZE-1)*BOARD_SIZE;++i)
        vertical_walls.set(i, p::extract<bool>(vertical_walls_list[i]));

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
