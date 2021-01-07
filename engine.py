'''
6.176 MIT POKERBOTS GAME ENGINE
DO NOT REMOVE, RENAME, OR EDIT THIS FILE
'''
from collections import namedtuple
from threading import Thread
from queue import Queue
import time
import json
import subprocess
import socket
import eval7
import sys
import os

sys.path.append(os.getcwd())
from config import *

FoldAction = namedtuple('FoldAction', [])
CallAction = namedtuple('CallAction', [])
CheckAction = namedtuple('CheckAction', [])
# we coalesce BetAction and RaiseAction for convenience
RaiseAction = namedtuple('RaiseAction', ['amount'])
AssignAction = namedtuple('AssignAction', ['cards'])
TerminalState = namedtuple('TerminalState', ['deltas', 'previous_state'])

STREET_NAMES = ['Flop', 'Turn', 'River']
DECODE = {'F': FoldAction, 'C': CallAction, 'K': CheckAction, 'R': RaiseAction, 'A': AssignAction}
CCARDS = lambda cards: ','.join(map(str, cards))
PCARDS = lambda cards: '[{}]'.format(' '.join(map(str, cards)))
PVALUE = lambda name, value: ', {} ({})'.format(name, value)
STATUS = lambda players: ''.join([PVALUE(p.name, p.bankroll) for p in players])
POTVAL = lambda value: ', ({})'.format(value)

# Socket encoding scheme:
#
# T#.### the player's game clock
# P# the player's index
# H**,** the player's holde cards in common format
# #F a fold action in the round history on a particular board
# #C a call action in the round history on a particular board
# #K a check action in the round history on a particular board
# #R### a raise action in the round history on a particular board
# #B**,**,**,**,** the board cards in common format for each board
# #O**,** the opponent's hand in common format for each board
# D###;D## the player's, followed by opponent's, bankroll delta from the round
# Q game over
#
# Board clauses are separated by semicolons
# Clauses are separated by spaces
# Messages end with '\n'
# The engine expects a response of #K for each board at the end of the round as an ack,
# otherwise a response which encodes the player's action
# Action history is sent once, including the player's actions


class SmallDeck(eval7.Deck):
    '''
    Provides method for creating new deck from existing eval7.Deck object.
    '''
    def __init__(self, existing_deck):
        self.cards = [eval7.Card(str(card)) for card in existing_deck.cards]


class BoardState(namedtuple('_BoardState', ['pot', 'pips', 'hands', 'deck', 'previous_state', 'settled', 'reveal'], defaults=[False, True])):
    '''
    Encodes the game tree for one board within a round.
    '''
    def showdown(self):
        '''
        Compares the players' hands and computes payoffs.
        '''
        score0 = eval7.evaluate(self.deck.peek(5) + self.hands[0])
        score1 = eval7.evaluate(self.deck.peek(5) + self.hands[1])
        if score0 > score1:
            winnings = [self.pot, 0]
        elif score0 < score1:
            winnings = [0, self.pot]
        else:  # split the pot
            winnings = [self.pot//2, self.pot//2]
        return TerminalState(winnings, self)

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
        net_winnings = [0, 0]
        for board_state in terminal_board_states:
            net_winnings[0] += board_state.deltas[0]
            net_winnings[1] += board_state.deltas[1]
        end_stacks = [self.stacks[0] + net_winnings[0], self.stacks[1] + net_winnings[1]]
        deltas = [end_stacks[0] - STARTING_STACK, end_stacks[1] - STARTING_STACK]
        return TerminalState(deltas, RoundState(self.button, self.street, self.stacks, self.hands, terminal_board_states, self))

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


class Player():
    '''
    Handles subprocess and socket interactions with one player's pokerbot.
    '''

    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.game_clock = STARTING_GAME_CLOCK
        self.bankroll = 0
        self.commands = None
        self.bot_subprocess = None
        self.socketfile = None
        self.bytes_queue = Queue()

    def build(self):
        '''
        Loads the commands file and builds the pokerbot.
        '''
        try:
            with open(self.path + '/commands.json', 'r') as json_file:
                commands = json.load(json_file)
            if ('build' in commands and 'run' in commands and
                    isinstance(commands['build'], list) and
                    isinstance(commands['run'], list)):
                self.commands = commands
            else:
                print(self.name, 'commands.json missing command')
        except FileNotFoundError:
            print(self.name, 'commands.json not found - check PLAYER_PATH')
        except json.decoder.JSONDecodeError:
            print(self.name, 'commands.json misformatted')
        if self.commands is not None and len(self.commands['build']) > 0:
            try:
                proc = subprocess.run(self.commands['build'],
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                      cwd=self.path, timeout=BUILD_TIMEOUT, check=False)
                self.bytes_queue.put(proc.stdout)
            except subprocess.TimeoutExpired as timeout_expired:
                error_message = 'Timed out waiting for ' + self.name + ' to build'
                print(error_message)
                self.bytes_queue.put(timeout_expired.stdout)
                self.bytes_queue.put(error_message.encode())
            except (TypeError, ValueError):
                print(self.name, 'build command misformatted')
            except OSError:
                print(self.name, 'build failed - check "build" in commands.json')

    def run(self):
        '''
        Runs the pokerbot and establishes the socket connection.
        '''
        if self.commands is not None and len(self.commands['run']) > 0:
            try:
                server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                with server_socket:
                    server_socket.bind(('', 0))
                    server_socket.settimeout(CONNECT_TIMEOUT)
                    server_socket.listen()
                    port = server_socket.getsockname()[1]
                    proc = subprocess.Popen(self.commands['run'] + [str(port)],
                                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                            cwd=self.path)
                    self.bot_subprocess = proc
                    # function for bot listening
                    def enqueue_output(out, queue):
                        try:
                            for line in out:
                                queue.put(line)
                        except ValueError:
                            pass
                    # start a separate bot listening thread which dies with the program
                    Thread(target=enqueue_output, args=(proc.stdout, self.bytes_queue), daemon=True).start()
                    # block until we timeout or the player connects
                    client_socket, _ = server_socket.accept()
                    with client_socket:
                        client_socket.settimeout(CONNECT_TIMEOUT)
                        sock = client_socket.makefile('rw')
                        self.socketfile = sock
                        print(self.name, 'connected successfully')
            except (TypeError, ValueError):
                print(self.name, 'run command misformatted')
            except OSError:
                print(self.name, 'run failed - check "run" in commands.json')
            except socket.timeout:
                print('Timed out waiting for', self.name, 'to connect')

    def stop(self):
        '''
        Closes the socket connection and stops the pokerbot.
        '''
        if self.socketfile is not None:
            try:
                self.socketfile.write('Q\n')
                self.socketfile.close()
            except socket.timeout:
                print('Timed out waiting for', self.name, 'to disconnect')
            except OSError:
                print('Could not close socket connection with', self.name)
        if self.bot_subprocess is not None:
            try:
                outs, _ = self.bot_subprocess.communicate(timeout=CONNECT_TIMEOUT)
                self.bytes_queue.put(outs)
            except subprocess.TimeoutExpired:
                print('Timed out waiting for', self.name, 'to quit')
                self.bot_subprocess.kill()
                outs, _ = self.bot_subprocess.communicate()
                self.bytes_queue.put(outs)
        with open(self.name + '.txt', 'wb') as log_file:
            bytes_written = 0
            for output in self.bytes_queue.queue:
                try:
                    bytes_written += log_file.write(output)
                    if bytes_written >= PLAYER_LOG_SIZE_LIMIT:
                        break
                except TypeError:
                    pass

    def query(self, round_state, player_message, game_log, index):
        '''
        Requests NUM_BOARDS actions from the pokerbot over the socket connection.
        At the end of the round, we request NUM_BOARDS CheckAction's from the pokerbot.
        '''
        if self.socketfile is not None and self.game_clock > 0.:
            clauses = ''
            try:
                player_message[0] = 'T{:.3f}'.format(self.game_clock)
                message = ' '.join(player_message) + '\n'
                del player_message[1:]  # do not send redundant action history
                start_time = time.perf_counter()
                self.socketfile.write(message)
                self.socketfile.flush()
                clauses = self.socketfile.readline().strip()
                end_time = time.perf_counter()
                if ENFORCE_GAME_CLOCK:
                    self.game_clock -= end_time - start_time
                if self.game_clock <= 0.:
                    raise socket.timeout
                assert_flag = (';' in clauses)
                clauses = clauses.split(';')
                if assert_flag:
                    assert (len(clauses) == NUM_BOARDS)
                actions = [self.query_board(round_state.board_states[i], clauses[i], game_log, round_state.button, round_state.stacks)
                    if isinstance(round_state, RoundState) else self.query_board(round_state.previous_state.board_states[i], clauses[i],
                    game_log, round_state.previous_state.button, round_state.previous_state.stacks) for i in range(NUM_BOARDS)]
                if all(isinstance(a, AssignAction) for a in actions):
                    if set().union(*[set(a.cards) for a in actions]) == set(round_state.hands[index]):
                        return actions
                    #else: (assigned cards not in hand or some cards unassigned)
                    game_log.append(self.name + ' attempted illegal assignment')
                else:
                    contribution = 0
                    for i in range(NUM_BOARDS):
                        if isinstance(actions[i], RaiseAction):
                            contribution += actions[i].amount - round_state.board_states[i].pips[index]
                        elif isinstance(actions[i], CallAction):
                            contribution += round_state.board_states[i].pips[1-index] - round_state.board_states[i].pips[index]
                    min_contribution = 0
                    if isinstance(round_state, RoundState):
                        max_contribution = round_state.stacks[index]
                    else:
                        max_contribution = 0
                    if min_contribution <= contribution <= max_contribution:
                        return actions
                    #else: (attempted negative net raise or net raise larger than bankroll)
                    game_log.append(self.name + " attempted net illegal RaiseAction's or CallAction's")
            except socket.timeout:
                error_message = self.name + ' ran out of time'
                game_log.append(error_message)
                print(error_message)
                self.game_clock = 0.
            except AssertionError:
                error_message = self.name + ' did not submit ' + str(NUM_BOARDS) + ' actions'
                game_log.append(error_message)
                print(error_message)
                self.game_clock = 0.
            except OSError:
                error_message = self.name + ' disconnected'
                game_log.append(error_message)
                print(error_message)
                self.game_clock = 0.
            except (IndexError, KeyError, ValueError):
                game_log.append(self.name + ' response misformatted: ' + str(clauses))
        default_actions = round_state.legal_actions() if isinstance(round_state, RoundState) else [{CheckAction} for i in range(NUM_BOARDS)]
        return [CheckAction() if CheckAction in default else FoldAction() for default in default_actions]

    def query_board(self, board_state, clause, game_log, button, stacks):
        '''
        Parses one action from the pokerbot for a specific board.
        '''
        legal_actions = board_state.legal_actions(button, stacks) if isinstance(board_state, BoardState) else {CheckAction}
        action = DECODE[clause[1]]
        if action in legal_actions:
            if clause[1] == 'R':
                amount = int(clause[2:])
                min_raise, max_raise = board_state.raise_bounds(button, stacks)
                if min_raise <= amount <= max_raise:
                    return action(amount)
            elif clause[1] == 'A':
                cards_strings = clause[2:].split(',')
                cards = [eval7.Card(s) for s in cards_strings]
                return action(cards)
            else:
                return action()
        game_log.append(self.name + ' attempted illegal ' + action.__name__)
        return CheckAction() if CheckAction in legal_actions else FoldAction()


class Game():
    '''
    Manages logging and the high-level game procedure.
    '''

    def __init__(self):
        self.log = ['6.176 MIT Pokerbots - ' + PLAYER_1_NAME + ' vs ' + PLAYER_2_NAME]
        self.player_messages = [[], []]

    def log_round_state(self, players, round_state):
        '''
        Incorporates RoundState information into the game log and player messages.
        '''
        if round_state.street == 0 and round_state.button == -2:
            self.log.append('{} posts the blind of {} on each board'.format(players[0].name, SMALL_BLIND))
            self.log.append('{} posts the blind of {} on each board'.format(players[1].name, BIG_BLIND))
            self.log.append('{} dealt {}'.format(players[0].name, PCARDS(round_state.hands[0])))
            self.log.append('{} dealt {}'.format(players[1].name, PCARDS(round_state.hands[1])))
            self.player_messages[0] = ['T0.', 'P0', 'H' + CCARDS(round_state.hands[0])]
            self.player_messages[1] = ['T0.', 'P1', 'H' + CCARDS(round_state.hands[1])]
        elif round_state.street > 0 and round_state.button == 1:
            boards = [board_state.deck.peek(round_state.street) if isinstance(board_state, BoardState) else [] for board_state in round_state.board_states]
            for i in range(NUM_BOARDS):
                log_message = ''
                if isinstance(round_state.board_states[i], BoardState):
                    log_message += STREET_NAMES[round_state.street - 3] + ' ' + PCARDS(boards[i])
                    log_message += POTVAL(round_state.board_states[i].pot)
                    log_message += PVALUE(players[0].name, round_state.stacks[0])
                    log_message += PVALUE(players[1].name, round_state.stacks[1])
                    log_message += ' on board ' + str(i+1)
                else:
                    log_message = 'Board {}'.format(i+1)
                    log_message += POTVAL(round_state.board_states[i].previous_state.pot)
                self.log.append(log_message)
            compressed_board = ';'.join([str(i+1) + 'B' + CCARDS(boards[i]) for i in range(NUM_BOARDS)])
            self.player_messages[0].append(compressed_board)
            self.player_messages[1].append(compressed_board)

    def log_actions(self, name, actions, bet_overrides, active):
        '''
        Incorporates action information into the game log and player messages.
        '''
        codes = [self.log_board_action(name, actions[i], bet_overrides[i], i+1) for i in range(NUM_BOARDS)]
        code = ';'.join(codes)
        if 'A' in code:
            self.player_messages[active].append(code)
            self.player_messages[1-active].append(';'.join([str(i+1) + 'A' for i in range(NUM_BOARDS)]))
        else:
            self.player_messages[0].append(code)
            self.player_messages[1].append(code)

    def log_board_action(self, name, action, bet_override, board_num):
        '''
        Incorporates action information from a single board into the game log.

        Returns code for a single action on one board.
        '''
        if isinstance(action, AssignAction):
            phrasing = ' assigns ' + PCARDS(action.cards) + ' to board ' + str(board_num)
            code = str(board_num) + 'A' + CCARDS(action.cards)
        elif isinstance(action, FoldAction):
            phrasing = ' folds on board ' + str(board_num)
            code = str(board_num) + 'F'
        elif isinstance(action, CallAction):
            phrasing = ' calls on board ' + str(board_num)
            code = str(board_num) + 'C'
        elif isinstance(action, CheckAction):
            phrasing = ' checks on board ' + str(board_num)
            code = str(board_num) + 'K'
        else:  # isinstance(action, RaiseAction)
            phrasing = (' bets ' if bet_override else ' raises to ') + str(action.amount) + ' on board ' + str(board_num)
            code = str(board_num) + 'R' + str(action.amount)
        self.log.append(name + phrasing)
        return code

    def log_terminal_state(self, players, round_state):
        '''
        Incorporates TerminalState information from each board and the overall round into the game log and player messages.
        '''
        previous_round = round_state.previous_state
        log_message_zero = [''] * NUM_BOARDS
        log_message_one = [''] * NUM_BOARDS
        for i in range(NUM_BOARDS):
            previous_board = previous_round.board_states[i].previous_state
            if previous_board.reveal:
                self.log.append('{} shows {} on board {}'.format(players[0].name, PCARDS(previous_board.hands[0]), i+1))
                self.log.append('{} shows {} on board {}'.format(players[1].name, PCARDS(previous_board.hands[1]), i+1))
                log_message_zero[i] = str(i+1) + 'O' + CCARDS(previous_board.hands[1])
                log_message_one[i] = str(i+1) + 'O' + CCARDS(previous_board.hands[0])
            else:
                log_message_zero[i] = str(i+1) + 'O'
                log_message_one[i] = str(i+1) + 'O'
        self.player_messages[0].append(';'.join(log_message_zero))
        self.player_messages[1].append(';'.join(log_message_one))
        self.log.append('{} awarded {}'.format(players[0].name, round_state.deltas[0]))
        self.log.append('{} awarded {}'.format(players[1].name, round_state.deltas[1]))
        log_messages = ['D' + str(round_state.deltas[0]), 'D' + str(round_state.deltas[1])]
        self.player_messages[0].append(';'.join(log_messages))
        self.player_messages[1].append(';'.join(log_messages[::-1]))

    def run_round(self, players):
        '''
        Runs one round of poker.
        '''
        deck = eval7.Deck()
        deck.shuffle()
        hands = [deck.deal(NUM_BOARDS*2), deck.deal(NUM_BOARDS*2)]
        new_decks  = [SmallDeck(deck) for i in range(NUM_BOARDS)]
        for new_deck in new_decks:
            new_deck.shuffle()
        stacks = [STARTING_STACK - NUM_BOARDS*SMALL_BLIND, STARTING_STACK - NUM_BOARDS*BIG_BLIND]
        board_states = [BoardState((i+1)*BIG_BLIND, [SMALL_BLIND, BIG_BLIND], None, new_decks[i], None) for i in range(NUM_BOARDS)]
        round_state = RoundState(-2, 0, stacks, hands, board_states, None)
        while not isinstance(round_state, TerminalState):
            self.log_round_state(players, round_state)
            active = round_state.button % 2
            player = players[active]
            actions = player.query(round_state, self.player_messages[active], self.log, active)
            bet_overrides = [(round_state.board_states[i].pips == [0, 0]) if isinstance(round_state.board_states[i], BoardState) else None for i in range(NUM_BOARDS)]
            self.log_actions(player.name, actions, bet_overrides, active)
            round_state = round_state.proceed(actions)
        self.log_terminal_state(players, round_state)
        for player, player_message, delta in zip(players, self.player_messages, round_state.deltas):
            player.query(round_state, player_message, self.log, None)
            player.bankroll += delta

    def run(self):
        '''
        Runs one game of poker.
        '''
        print('   __  _____________  ___       __           __        __    ')
        print('  /  |/  /  _/_  __/ / _ \\___  / /_____ ____/ /  ___  / /____')
        print(' / /|_/ // /  / /   / ___/ _ \\/  \'_/ -_) __/ _ \\/ _ \\/ __(_-<')
        print('/_/  /_/___/ /_/   /_/   \\___/_/\\_\\\\__/_/ /_.__/\\___/\\__/___/')
        print()
        print('Starting the Pokerbots engine...')
        players = [
            Player(PLAYER_1_NAME, PLAYER_1_PATH),
            Player(PLAYER_2_NAME, PLAYER_2_PATH)
        ]
        for player in players:
            player.build()
            player.run()
        for round_num in range(1, NUM_ROUNDS + 1):
            self.log.append('')
            self.log.append('Round #' + str(round_num) + STATUS(players))
            self.run_round(players)
            players = players[::-1]
        self.log.append('')
        self.log.append('Final' + STATUS(players))
        for player in players:
            player.stop()
        name = GAME_LOG_FILENAME + '.txt'
        print('Writing', name)
        with open(name, 'w') as log_file:
            log_file.write('\n'.join(self.log))


if __name__ == '__main__':
    Game().run()
