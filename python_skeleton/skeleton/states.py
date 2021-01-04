'''
Encapsulates game and round state information for the player.
'''
from collections import namedtuple
from .actions import FoldAction, CallAction, CheckAction, RaiseAction, AssignAction

GameState = namedtuple('GameState', ['bankroll', 'opp_bankroll', 'game_clock', 'round_num'])
TerminalState = namedtuple('TerminalState', ['deltas', 'previous_state'])

NUM_ROUNDS = 500
STARTING_STACK = 200
BIG_BLIND = 2
SMALL_BLIND = 1
NUM_BOARDS = 3

class BoardState(namedtuple('_BoardState', ['pot', 'pips', 'hands', 'deck', 'previous_state', 'settled', 'reveal'], defaults=[False, True])):
    '''
    Encodes the game tree for one board within a round.
    '''
    def showdown(self):
        '''
        Compares the players' hands and computes payoffs.
        '''
        return TerminalState([0, 0], self)


    def legal_actions(self, button, stacks):
        '''
        Returns a set which corresponds to the active player's legal moves on this board.
        '''
        active = button % 2
        if (self.hands is None) or (len(self.hands[active]) == 0):
            return {AssignAction}
        elif self.settled:
            return {CheckAction}
        # board being played on
        continue_cost = self.pips[1-active] - self.pips[active]
        if continue_cost == 0:
            # we can only raise the stakes if both players can afford it
            bets_forbidden = (stacks[0] == 0 or stacks[1] == 0)
            return {CheckAction} if bets_forbidden else {CheckAction, RaiseAction}
        # continue_cost > 0
        # similarly, re-raising is only allowed if both players can afford it
        raises_forbidden = (continue_cost == stacks[active] or stacks[1-active] == 0)
        return {FoldAction, CallAction} if raises_forbidden else {FoldAction, CallAction, RaiseAction}

    def raise_bounds(self, button, stacks):
        '''
        Returns a tuple of the minimum and maximum legal raises on this board.
        '''
        active = button % 2
        continue_cost = self.pips[1-active] - self.pips[active]
        max_contribution = min(stacks[active], stacks[1-active] + continue_cost)
        min_contribution = min(max_contribution, continue_cost + max(continue_cost, BIG_BLIND))
        return (self.pips[active] + min_contribution, self.pips[active] + max_contribution)

    def proceed(self, action, button, street):
        '''
        Advances the game tree by one action performed by the active player on the current board.
        '''
        active = button % 2
        if isinstance(action, AssignAction):
            new_hands = [[]] * 2
            new_hands[active] = action.cards
            if self.hands is not None:
                opp_hands = self.hands[1-active]
                new_hands[1-active] = opp_hands
            return BoardState(self.pot, self.pips, new_hands, self.deck, self)
        if isinstance(action, FoldAction):
            new_pot = self.pot + sum(self.pips)
            winnings = [0, new_pot] if active == 0 else [new_pot, 0]
            return TerminalState(winnings, BoardState(new_pot, [0, 0], self.hands, self.deck, self, True, False))
        if isinstance(action, CallAction):
            if button == 0: # sb calls bb
                return BoardState(self.pot, [BIG_BLIND] * 2, self.hands, self.deck, self)
            # both players acted
            new_pips = list(self.pips)
            contribution = new_pips[1-active] - new_pips[active]
            new_pips[active] += contribution
            return BoardState(self.pot, new_pips, self.hands, self.deck, self, True)
        if isinstance(action, CheckAction):
            if (street == 0 and button > 0) or button > 1:  # both players acted
                return BoardState(self.pot, self.pips, self.hands, self.deck, self, True, self.reveal)
            # let opponent act
            return BoardState(self.pot, self.pips, self.hands, self.deck, self, self.settled, self.reveal)
        # isinstance(action, RaiseAction)
        new_pips = list(self.pips)
        contribution = action.amount - new_pips[active]
        new_pips[active] += contribution
        return BoardState(self.pot, new_pips, self.hands, self.deck, self)


class RoundState(namedtuple('_RoundState', ['button', 'street', 'stacks', 'hands', 'board_states', 'previous_state'])):
    '''
    Encodes the game tree for one round of poker.
    '''
    def showdown(self):
        '''
        Compares the players' hands and computes payoffs.
        '''
        terminal_board_states = [board_state.showdown() if isinstance(board_state, BoardState) else board_state for board_state in self.board_states]
        return TerminalState([0, 0], RoundState(self.button, self.street, self.stacks, self.hands, terminal_board_states, self))


    def legal_actions(self):
        '''
        Returns a list of sets which correspond to the active player's legal moves on each board.
        '''
        return [board_state.legal_actions(self.button, self.stacks) if isinstance(board_state, BoardState) else {CheckAction} for board_state in self.board_states]

    def raise_bounds(self):
        '''
        Returns a tuple of the minimum and maximum legal raises summed across boards.
        '''
        active = self.button % 2
        net_continue_cost = 0
        net_pips_unsettled = 0
        for board_state in self.board_states:
            if isinstance(board_state, BoardState) and not board_state.settled:
                net_continue_cost += board_state.pips[1-active] - board_state.pips[active]
                net_pips_unsettled += board_state.pips[active]
        return (0, net_pips_unsettled + min(self.stacks[active], self.stacks[1-active] + net_continue_cost))

    def proceed_street(self):
        '''
        Resets the players' pips on each board and advances the game tree to the next round of betting.
        '''
        new_pots = [0]*NUM_BOARDS
        for i in range(NUM_BOARDS):
            if isinstance(self.board_states[i], BoardState):
                new_pots[i] = self.board_states[i].pot + sum(self.board_states[i].pips)
        new_board_states = [BoardState(new_pots[i], [0, 0], self.board_states[i].hands, self.board_states[i].deck, self.board_states[i]) if isinstance(self.board_states[i], BoardState) else self.board_states[i] for i in range(NUM_BOARDS)]
        all_terminal = [isinstance(board_state, TerminalState) for board_state in new_board_states]
        if self.street == 5 or all(all_terminal):
            return RoundState(self.button, 5, self.stacks, self.hands, new_board_states, self).showdown()
        new_street = 3 if self.street == 0 else self.street + 1        
        return RoundState(1, new_street, self.stacks, self.hands, new_board_states, self)

    def proceed(self, actions):
        '''
        Advances the game tree by one tuple of actions performed by the active player across all boards.
        '''
        new_board_states = [self.board_states[i].proceed(actions[i], self.button, self.street) if isinstance(self.board_states[i], BoardState) else self.board_states[i] for i in range(NUM_BOARDS)]
        active = self.button % 2
        new_stacks = list(self.stacks)
        contribution = 0
        for i in range(NUM_BOARDS):
            if isinstance(new_board_states[i], BoardState) and isinstance(self.board_states[i], BoardState):
                contribution += new_board_states[i].pips[active] - self.board_states[i].pips[active]
        new_stacks[active] -= contribution
        settled = [(isinstance(board_state, TerminalState) or board_state.settled) for board_state in new_board_states]
        state = RoundState(self.button + 1, self.street, new_stacks, self.hands, new_board_states, self)
        return state.proceed_street() if all(settled) else state
