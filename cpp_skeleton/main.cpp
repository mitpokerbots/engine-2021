/**
 * Main program for running a C++ pokerbot.
 */
#include "./skeleton/runner.hpp"
#include "player.hpp"

int main(int argc, char* argv[])
{
    Player player = Player();
    vector<string> args = parse_args(argc, argv);
    run_bot(&player, args);
    return 0;
}