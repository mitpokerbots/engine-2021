'''
The infrastructure for interacting with the engine.
'''
import argparse
import socket
from .actions import FoldAction, CallAction, CheckAction, RaiseAction, AssignAction
from .states import GameState, TerminalState, RoundState, BoardState
from .states import STARTING_STACK, BIG_BLIND, SMALL_BLIND, NUM_BOARDS
from .bot import Bot


class Runner():
    '''
    Interacts with the engine.
    '''

    def __init__(self, pokerbot, socketfile):
        self.pokerbot = pokerbot
        self.socketfile = socketfile

    def receive(self):
        '''
        Generator for incoming messages from the engine.
        '''
        while True:
            packet = self.socketfile.readline().strip().split(' ')
            if not packet:
                break
            yield packet

    def send(self, actions):
        '''
        Encodes actions and sends it to the engine.
        '''
        codes = [''] * NUM_BOARDS
        for i in range(NUM_BOARDS):
            if isinstance(actions[i], AssignAction):
                codes[i] = str(i+1) + 'A' + ','.join(actions[i].cards)
            elif isinstance(actions[i], FoldAction):
                codes[i] = str(i+1) + 'F'
            elif isinstance(actions[i], CallAction):
                codes[i] = str(i+1) + 'C'
            elif isinstance(actions[i], CheckAction):
                codes[i] = str(i+1) + 'K'
            else:  # isinstance(action, RaiseAction)
                codes[i] = str(i+1) + 'R' + str(actions[i].amount)
        code = ';'.join(codes)
        self.socketfile.write(code + '\n')
        self.socketfile.flush()
       
    def run(self):
        '''
        Reconstructs the game tree based on the action history received from the engine.
        '''
        game_state = GameState(0, 0, 0., 1)
        round_state = None
        active = 0
        round_flag = True
        for packet in self.receive():
            for clause in packet:
                if clause[0] == 'T':
                    game_state = GameState(game_state.bankroll, game_state.opp_bankroll, float(clause[1:]), game_state.round_num)
                elif clause[0] == 'P':
                    active = int(clause[1:])
                elif clause[0] == 'H':
                    cards = clause[1:].split(',')
                    hands = [[], []]
                    hands[active] = cards
                    hands[1-active] = ['']*(2*NUM_BOARDS)
                    deck = ["", "", "", "", ""]
                    pips = [SMALL_BLIND, BIG_BLIND]
                    board_states = [BoardState((i+1)*BIG_BLIND, pips, [[]]*2, deck, None) for i in range(NUM_BOARDS)]
                    stacks = [STARTING_STACK - NUM_BOARDS*SMALL_BLIND, STARTING_STACK - NUM_BOARDS*BIG_BLIND]
                    round_state = RoundState(-2, 0, stacks, hands, board_states, None)
                    if round_flag:
                        self.pokerbot.handle_new_round(game_state, round_state, active)
                        round_flag = False
                elif clause[0] == 'D':
                    assert isinstance(round_state, TerminalState)
                    subclauses = clause.split(';')
                    delta = int(subclauses[0][1:])
                    opp_delta = int(subclauses[1][1:])
                    deltas = [delta, opp_delta]
                    deltas[active] = delta
                    deltas[1-active] = opp_delta
                    round_state = TerminalState(deltas, round_state.previous_state)
                    game_state = GameState(game_state.bankroll + delta, game_state.opp_bankroll + opp_delta, game_state.game_clock, game_state.round_num)
                    self.pokerbot.handle_round_over(game_state, round_state, active)
                    game_state = GameState(game_state.bankroll, game_state.opp_bankroll, game_state.game_clock, game_state.round_num + 1)
                    round_flag = True
                elif clause[0] == 'Q':
                    return
                elif clause[0] == '1':
                    round_state = parse_multi_code(clause, round_state, active)
            if round_flag:  # ack the engine
                self.send([CheckAction()]*NUM_BOARDS)
            else:
                assert active == round_state.button % 2
                actions = self.pokerbot.get_actions(game_state, round_state, active)
                self.send(actions)


def parse_multi_code(clause, round_state, active):
    subclauses = clause.split(';')
    if 'B' in clause:
        new_board_states = [None] * NUM_BOARDS
        for i in range(NUM_BOARDS):
            leftover = subclauses[i][2:]
            cards = leftover.split(',')
            revised_deck = ["", "", "", "", ""]
            for j in range(len(cards)):
                revised_deck[j] = cards[j]
            if isinstance(round_state.board_states[i], BoardState):
                maker = round_state.board_states[i]
                new_board_states[i] = BoardState(maker.pot, maker.pips, maker.hands, revised_deck, maker.previous_state)
            else:
                terminal = round_state.board_states[i]
                maker = terminal.previous_state
                new_board_states[i] = TerminalState(terminal.deltas, BoardState(maker.pot, maker.pips, maker.hands, revised_deck, maker.previous_state, maker.settled))
        return RoundState(round_state.button, round_state.street, round_state.stacks, round_state.hands, new_board_states, round_state.previous_state)
    elif 'O' in clause:
        new_board_states = [None] * NUM_BOARDS
        round_state = round_state.previous_state
        for i in range(NUM_BOARDS):
            leftover = subclauses[i][2:]
            if leftover == "":
                new_board_states[i] = round_state.board_states[i]
            else:
                cards = leftover.split(',')
                terminal = round_state.board_states[i]
                maker = terminal.previous_state
                revised_hands = maker.hands
                revised_hands[1-active] = cards
                new_board_states[i] = TerminalState(terminal.deltas, BoardState(maker.pot, maker.pips, revised_hands, maker.deck, maker.previous_state, maker.settled))
        round_state = RoundState(round_state.button, round_state.street, round_state.stacks, round_state.hands, new_board_states, round_state.previous_state)
        return TerminalState([0, 0], round_state)
    else:
        actions = [None] * NUM_BOARDS
        for i in range(NUM_BOARDS):
            subclause = subclauses[i]
            leftover = subclause[2:]
            if subclause[1] == 'F':
                actions[i] = FoldAction()
            elif subclause[1] == 'C':
                actions[i] = CallAction()
            elif subclause[1] == 'K':
                actions[i] = CheckAction()
            elif subclause[1] == 'R':
                actions[i] = RaiseAction(int(leftover))
            elif subclause[1] == 'A':
                cards = leftover.split(',')
                if leftover == "":
                    actions[i] = AssignAction(["", ""])
                else:
                    actions[i] = AssignAction(cards)
        return round_state.proceed(actions)

def parse_args():
    '''
    Parses arguments corresponding to socket connection information.
    '''
    parser = argparse.ArgumentParser(prog='python3 player.py')
    parser.add_argument('--host', type=str, default='localhost', help='Host to connect to, defaults to localhost')
    parser.add_argument('port', type=int, help='Port on host to connect to')
    return parser.parse_args()

def run_bot(pokerbot, args):
    '''
    Runs the pokerbot.
    '''
    assert isinstance(pokerbot, Bot)
    try:
        sock = socket.create_connection((args.host, args.port))
    except OSError:
        print('Could not connect to {}:{}'.format(args.host, args.port))
        return
    socketfile = sock.makefile('rw')
    runner = Runner(pokerbot, socketfile)
    runner.run()
    socketfile.close()
    sock.close()
