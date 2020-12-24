#ifndef __PLAYER_HPP__
#define __PLAYER_HPP__

#include "./skeleton/actions.hpp"
#include "./skeleton/states.hpp"
#include "./skeleton/bot.hpp"


/**
 * A pokerbot.
 */
class Player : public Bot
{
    private:
        // Your private instance variables go here.

    public:
        /**
         * Called when a new game starts. Called exactly once.
         */
        Player();

        /**
         * Called when a new round starts. Called NUM_ROUNDS times.
         *
         * @param game_state Pointer to the GameState object.
         * @param round_state Pointer to the RoundState object.
         * @param active Your player's index.
         */
        void handle_new_round(GameState* game_state, RoundState* round_state, int active);

        /**
         * Called when a round ends. Called NUM_ROUNDS times.
         *
         * @param game_state Pointer to the GameState object.
         * @param terminal_state Pointer to the TerminalState object.
         * @param active Your player's index.
         */
        void handle_round_over(GameState* game_state, TerminalState* terminal_state, int active);

        /**
         * Where the magic happens - your code should implement this function.
         * Called any time the engine needs an action from your bot.
         *
         * @param game_state Pointer to the GameState object.
         * @param round_state Pointer to the RoundState object.
         * @param active Your player's index.
         * @return Your action.
         */
        Action get_action(GameState* game_state, RoundState* round_state, int active);
};


#endif  // __PLAYER_HPP__