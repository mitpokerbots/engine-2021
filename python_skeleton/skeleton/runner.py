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
        code = ''
        for i in range(NUM_BOARDS):
            if isinstance(actions[i], FoldAction):
                code += 'F'
            elif isinstance(actions[i], CallAction):
                code += 'C'
            elif isinstance(actions[i], CheckAction):
                code += 'K'
            elif isinstance(actions[i], AssignAction):
                code += 'A'
            else:  # isinstance(action, RaiseAction)
                code += 'R' + str(actions[i].amount)
        code += ';'
        self.socketfile.write(code + '\n')
        self.socketfile.flush()
       
    # last thing that has it's logic changed   
    def run(self):
        '''
        Reconstructs the game tree based on the action history received from the engine.
        '''
        game_state = GameState(0, 0, 0., 1)
        board_states = []
        for i in range(NUM_BOARDS):
            board_states.append(BoardState((i+1)*BIG_BLIND, [0,0], [[],[]],[""],None))
        round_state = RoundState(0,0,[0,0],[[],[]],board_states,None)

        active = 0
        round_flag = True

        for packet in self.receive():
            for clause in packet:
                if clause[1] == 'T':
                    game_state = GameState(game_state.bankroll, game_state.opp_bankroll, float(clause[2:]), game_state.round_num)
                elif clause[1] == 'P':
                    active = int(clause[2:])
                elif clause[1] == 'H':
                    hands = [[], []]
                    hands[active] = clause[1:].split(',')
                    pips = [SMALL_BLIND, BIG_BLIND]
                    stacks = [STARTING_STACK - SMALL_BLIND, STARTING_STACK - BIG_BLIND]
                    board_states = []
                    deck = ["", "", "", "", ""]
                    for i in range(NUM_BOARDS):
                        board_states.append(BoardState((i+1)*BIG_BLIND, pips, hands, deck,None))
                    round_state = RoundState(0, 0, pips, stacks, hands, board_states, None)
                    if round_flag:
                        self.pokerbot.handle_new_round(game_state, round_state, active)
                        round_flag = False
                elif clause[1] == 'D':
                    subclauses = clause.split(';')
                    assert isinstance(round_state, TerminalState)
                    delta = int(subclauses[0][1:])
                    opp_delta = int(subclauses[1][1:])
                    deltas = [-delta, -opp_delta]
                    deltas[active] = delta
                    round_state = TerminalState(deltas, round_state.previous_state)
                    game_state = GameState(game_state.bankroll + delta, game_state.opp_bankroll + opp_delta, game_state.game_clock, game_state.round_num)
                    self.pokerbot.handle_round_over(game_state, round_state, active)
                    game_state = GameState(game_state.bankroll, game_state.opp_bankroll, game_state.game_clock, game_state.round_num + 1)
                    round_flag = True
                elif clause[1] == 'Q':
                    return
                elif clause[1] == '1':
                    round_state = parse_multi_code(clause,round_state,active)
                    break
            if round_flag:  # ack the engine
                self.send(CheckAction())
            else:
                assert active == round_state.button % 2
                action = self.pokerbot.get_action(game_state, round_state, active)
                self.send(action)

def parse_multi_code(clause, roundState, active):
    subclauses = clause.split(';')
    if clause.contains('B'):
        new_board_state = []
        for i in range(NUM_BOARDS):
            leftover = subclauses[i][1:]
            cards = leftover.split(',')
            revised_deck = ["", "", "", "", ""]
            for j in range(len(cards)):
                revised_deck[j] = cards[j]
        # missing getting instance of board state and progressing the game tree
        # missing terminal state    
    elif clause[1] == 'O':
        # unedited for the current version
        # backtrack
        round_state = round_state.previous_state
        revised_hands = list(round_state.hands)
        revised_hands[1-active] = clause[1:].split(',')
        # rebuild history
        round_state = RoundState(round_state.button, round_state.street, round_state.pips, round_state.stacks,
                                    revised_hands, round_state.deck, round_state.previous_state)
        round_state = TerminalState([0, 0], round_state)
    # are these round state or board state changes?    
    elif clause[1] == 'F':
        round_state = round_state.proceed(FoldAction())
    elif clause[1] == 'C':
        round_state = round_state.proceed(CallAction())
    elif clause[1] == 'K':
        round_state = round_state.proceed(CheckAction())
    elif clause[1] == 'R':
        round_state = round_state.proceed(RaiseAction(int(clause[1:])))   
    elif cluase[1] == 'A':
        # need to implement A changes





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
