#ifndef __SKELETON_BOT_HPP__
#define __SKELETON_BOT_HPP__

#include "actions.hpp"


/**
 * The base class for a pokerbot.
 */
class Bot
{
    public:
        /**
         * Called when a new round starts. Called NUM_ROUNDS times.
         *
         * @param game_state Pointer to the GameState object.
         * @param round_state Pointer to the RoundState object.
         * @param active Your player's index.
         */
        virtual void handle_new_round(GameState* game_state, RoundState* round_state, int active) = 0;

        /**
         * Called when a round ends. Called NUM_ROUNDS times.
         *
         * @param game_state Pointer to the GameState object.
         * @param terminal_state Pointer to the TerminalState object.
         * @param active Your player's index.
         */
        virtual void handle_round_over(GameState* game_state, TerminalState* terminal_state, int active) = 0;

        /**
         * Where the magic happens - your code should implement this function.
         * Called any time the engine needs an action from your bot.
         *
         * @param game_state Pointer to the GameState object.
         * @param round_state Pointer to the RoundState object.
         * @param active Your player's index.
         * @return Your action.
         */
        virtual Action get_action(GameState* game_state, RoundState* round_state, int active) = 0;
};


#endif  // __SKELETON_BOT_HPP__