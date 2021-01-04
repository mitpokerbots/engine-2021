'''
Simple example pokerbot, written in Python.
'''
from skeleton.actions import FoldAction, CallAction, CheckAction, RaiseAction, AssignAction
from skeleton.states import GameState, TerminalState, RoundState, BoardState
from skeleton.states import NUM_ROUNDS, STARTING_STACK, BIG_BLIND, SMALL_BLIND, NUM_BOARDS
from skeleton.bot import Bot
from skeleton.runner import parse_args, run_bot


class Player(Bot):
    '''
    A pokerbot.
    '''

    def __init__(self):
        '''
        Called when a new game starts. Called exactly once.

        Arguments:
        Nothing.

        Returns:
        Nothing.
        '''
        pass

    def handle_new_round(self, game_state, round_state, active):
        '''
        Called when a new round starts. Called NUM_ROUNDS times.

        Arguments:
        game_state: the GameState object.
        round_state: the RoundState object.
        active: your player's index.

        Returns:
        Nothing.
        '''
        #my_bankroll = game_state.bankroll  # the total number of chips you've gained or lost from the beginning of the game to the start of this round
        #opp_bankroll = game_state.opp_bankroll # ^but for your opponent
        #game_clock = game_state.game_clock  # the total number of seconds your bot has left to play this game
        #round_num = game_state.round_num  # the round number from 1 to NUM_ROUNDS
        #my_cards = round_state.hands[active]  # your six cards at teh start of the round
        #big_blind = bool(active)  # True if you are the big blind
        pass

    def handle_round_over(self, game_state, terminal_state, active):
        '''
        Called when a round ends. Called NUM_ROUNDS times.

        Arguments:
        game_state: the GameState object.
        terminal_state: the TerminalState object.
        active: your player's index.

        Returns:
        Nothing.
        '''
        # my_delta = terminal_state.deltas[active]  # your bankroll change from this round
        # opp_delta = terminal_state.deltas[1-active] # your opponent's bankroll change from this round 
        # previous_state = terminal_state.previous_state  # RoundState before payoffs
        # street = previous_state.street  # 0, 3, 4, or 5 representing when this round ended
        # for terminal_board_state in previous_state.board_states:
        #     previous_board_state = terminal_board_state.previous_state
        #     my_cards = previous_board_state.hands[active]  # your cards
        #     opp_cards = previous_board_state.hands[1-active]  # opponent's cards or [] if not revealed
        pass

    def get_actions(self, game_state, round_state, active):
        '''
        Where the magic happens - your code should implement this function.
        Called any time the engine needs a triplet of actions from your bot.

        Arguments:
        game_state: the GameState object.
        round_state: the RoundState object.
        active: your player's index.

        Returns:
        Your actions.
        '''
        legal_actions = round_state.legal_actions()  # the actions you are allowed to take
        # street = round_state.street  # 0, 3, 4, or 5 representing pre-flop, flop, turn, or river respectively
        my_cards = round_state.hands[active]  # your cards across all boards
        # board_cards = [board_state.deck if isinstance(board_state, BoardState) else board_state.previous_state.deck for board_state in round_state.board_states] #the board cards
        # my_pips = [board_state.pips[active] if isinstance(board_state, BoardState) else 0 for board_state in round_state.board_states] # the number of chips you have contributed to the pot on each board this round of betting
        # opp_pips = [board_state.pips[1-active] if isinstance(board_state, BoardState) else 0 for board_state in round_state.board_states] # the number of chips your opponent has contributed to the pot on each board this round of betting
        # continue_cost = [opp_pips[i] - my_pips[i] for i in range(NUM_BOARDS)] #the number of chips needed to stay in each board's pot
        # my_stack = round_state.stacks[active]  # the number of chips you have remaining
        # opp_stack = round_state.stacks[1-active]  # the number of chips your opponent has remaining
        # stacks = [my_stack, opp_stack]
        # net_upper_raise_bound = round_state.raise_bounds()[1] # max raise across 3 boards
        # net_cost = 0 # keep track of the net additional amount you are spending across boards this round
        my_actions = [None] * NUM_BOARDS
        for i in range(NUM_BOARDS):
            if AssignAction in legal_actions[i]:
                cards = [my_cards[2*i], my_cards[2*i+1]]
                my_actions[i] = AssignAction(cards)
            elif CheckAction in legal_actions[i]:  # check-call
                my_actions[i] = CheckAction()
            else:
                my_actions[i] = CallAction()
        return my_actions


if __name__ == '__main__':
    run_bot(Player(), parse_args())
