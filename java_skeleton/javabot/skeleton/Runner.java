package javabot.skeleton;

import java.util.List;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.lang.Integer;
import java.lang.String;
import java.net.Socket;
import java.io.PrintWriter;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.IOException;

/**
 * Interacts with the engine.
 */
public class Runner {
    private String host;
    private int port;
    private Bot pokerbot;
    private Socket socket;
    private PrintWriter outStream;
    private BufferedReader inStream;

    /**
     * Returns an incoming message from the engine.
     */
    public String[] receive() throws IOException {
        String line = this.inStream.readLine().trim();
        return line.split(" ");
    }

    /**
     * Encodes an action and sends it to the engine.
     */
    public void send(List<Action> actions) {
        String[] codes = new String[State.NUM_BOARDS];
        for (int i = 0; i < State.NUM_BOARDS; i++) {
            switch (actions.get(i).actionType) {
                case ASSIGN_ACTION_TYPE: {
                    codes[i] = (i + 1) + "A" + String.join(",", actions.get(i).cards);
                    break;
                }
                case FOLD_ACTION_TYPE: {
                    codes[i] = (i + 1) + "F";
                    break;
                }
                case CALL_ACTION_TYPE: {
                    codes[i] = (i + 1) + "C";
                    break;
                }
                case CHECK_ACTION_TYPE: {
                    codes[i] = (i + 1) + "K";
                    break;
                }
                default: {  // RAISE_ACTION_TYPE
                    codes[i] = (i + 1) + "R" + Integer.toString(actions.get(i).amount);
                    break;
                }
            }
        }
        String code = String.join(";", codes);
        this.outStream.println(code);
    }

    /**
     * Reconstructs the game tree based on the action history received from the engine.
     */
    public void run() throws IOException {
        GameState gameState = new GameState(0, 0, (float)0., 1);
        List<State> boardStates = new ArrayList<State>();
        for (int i = 0; i < State.NUM_BOARDS; i++) {
            boardStates.add(new BoardState((i+1)*State.BIG_BLIND, Arrays.asList(0, 0),
                                            Arrays.asList(Arrays.asList(""), Arrays.asList("")),
                                            Arrays.asList(""), null));
        }
        State roundState = new RoundState(-2, 0, Arrays.asList(0, 0),
                                          Arrays.asList(Arrays.asList(""), Arrays.asList("")),
                                          boardStates, null);
        int active = 0;
        boolean roundFlag = true;
        while (true) {
            String[] packet = this.receive();
            for (String clause : packet) {
                String leftover = clause.substring(1, clause.length());
                switch (clause.charAt(0)) {
                    case 'T': {
                        gameState = new GameState(gameState.bankroll, gameState.oppBankroll, Float.parseFloat(leftover), gameState.roundNum);
                        break;
                    }
                    case 'P': {
                        active = Integer.parseInt(leftover);
                        break;
                    }
                    case 'H': {
                        String[] cards = leftover.split(",");
                        List<List<String>> hands = new ArrayList<List<String>>(
                            Arrays.asList(
                                new ArrayList<String>(),
                                new ArrayList<String>()
                            )
                        );
                        hands.set(active, Arrays.asList(cards));
                        String[] oppHands = new String[cards.length];
                        Arrays.fill(oppHands, "");
                        hands.set(1 - active, Arrays.asList(oppHands));
                        List<String> deck = new ArrayList<String>(Arrays.asList("", "", "", "", ""));
                        List<Integer> pips = Arrays.asList(State.SMALL_BLIND, State.BIG_BLIND);
                        boardStates = new ArrayList<State>();
                        for (int i = 0; i < State.NUM_BOARDS; i++) {
                            boardStates.add(new BoardState((i+1)*State.BIG_BLIND, pips,
                                            Arrays.asList(new ArrayList<String>(), new ArrayList<String>()),
                                            deck, null));
                        }
                        List<Integer> stacks = Arrays.asList(State.STARTING_STACK - State.NUM_BOARDS*State.SMALL_BLIND,
                                                             State.STARTING_STACK - State.NUM_BOARDS*State.BIG_BLIND);
                        roundState = new RoundState(-2, 0, stacks, hands, boardStates, null);
                        if (roundFlag) {
                            this.pokerbot.handleNewRound(gameState, (RoundState)roundState, active);
                            roundFlag = false;
                        }
                        break;
                    }
                    case 'D': {
                        String[] subclauses = clause.split(";");
                        int delta = Integer.parseInt(subclauses[0].substring(1, subclauses[0].length()));
                        int oppDelta = Integer.parseInt(subclauses[1].substring(1, subclauses[1].length()));
                        List<Integer> deltas = new ArrayList<Integer>(Arrays.asList(delta, oppDelta));
                        deltas.set(active, delta);
                        deltas.set(1-active, oppDelta);
                        roundState = new TerminalState(deltas, ((TerminalState)roundState).previousState);
                        gameState = new GameState(gameState.bankroll + delta, gameState.oppBankroll + oppDelta, gameState.gameClock, gameState.roundNum);
                        this.pokerbot.handleRoundOver(gameState, (TerminalState)roundState, active);
                        gameState = new GameState(gameState.bankroll, gameState.oppBankroll, gameState.gameClock, gameState.roundNum + 1);
                        roundFlag = true;
                        break;
                    }
                    case 'Q': {
                        return;
                    }
                    case '1': {
                        roundState = this.parseMultiCode(clause, roundState, active);
                        break;
                    }
                    default: {
                        break;
                    }
                }
            }
            if (roundFlag) {  // ack the engine
                List<Action> ack = new ArrayList<Action>();
                for (int i = 0; i < State.NUM_BOARDS; i++) {
                    ack.add(new Action(ActionType.CHECK_ACTION_TYPE));
                }
                this.send(ack);
            } else {
                List<Action> actions = this.pokerbot.getActions(gameState, (RoundState)roundState, active);
                this.send(actions);
            }
        }
    }

    /**
     * Parses clauses which contain codes across multiple boards.
      */
    public State parseMultiCode(String clause, State roundState, int active) {
        String[] subclauses = clause.split(";");
        if (clause.contains("B")) {
            List<State> newBoardStates = new ArrayList<State>();
            for (int i = 0; i < State.NUM_BOARDS; i++) {
                String leftover = subclauses[i].substring(2, subclauses[i].length());
                String[] cards = leftover.split(",");
                List<String> revisedDeck = new ArrayList<String>(Arrays.asList("", "", "", "", ""));
                for (int j = 0; j < cards.length; j++) {
                    revisedDeck.set(j, cards[j]);
                }
                if (((RoundState)roundState).boardStates.get(i) instanceof BoardState) {
                    BoardState maker = (BoardState)((RoundState)roundState).boardStates.get(i);
                    newBoardStates.add(new BoardState(maker.pot, maker.pips, maker.hands,
                                                        revisedDeck, maker.previousState));
                } else {
                    TerminalState terminal = (TerminalState)((RoundState)roundState).boardStates.get(i);
                    BoardState maker = (BoardState)terminal.previousState;
                    newBoardStates.add(new TerminalState(terminal.deltas,
                                                        new BoardState(maker.pot, maker.pips, maker.hands,
                                                                        revisedDeck, maker.previousState,
                                                                        maker.settled)));
                }
            }
            RoundState maker = (RoundState)roundState;
            return new RoundState(maker.button, maker.street, maker.stacks, maker.hands,
                                    newBoardStates, maker.previousState);
        } else if (clause.contains("O")) {
            List<State> newBoardStates = new ArrayList<State>();
            roundState = (RoundState)((TerminalState)roundState).previousState;
            for (int i = 0; i < State.NUM_BOARDS; i++) {
                String leftover = subclauses[i].substring(2, subclauses[i].length());
                if ("".equals(leftover)) {
                    newBoardStates.add(((RoundState)roundState).boardStates.get(i));
                } else {
                    // backtrack
                    String[] cards = leftover.split(",");
                    TerminalState terminal = (TerminalState)((RoundState)roundState).boardStates.get(i);
                    BoardState maker = (BoardState)terminal.previousState;
                    List<List<String>> revisedHands = new ArrayList<List<String>>(maker.hands);
                    revisedHands.set(1 - active, Arrays.asList(cards[0], cards[1]));
                    newBoardStates.add(new TerminalState(terminal.deltas, new BoardState(maker.pot, maker.pips, revisedHands, maker.deck, maker.previousState, maker.settled)));
                }
            }
            RoundState maker = (RoundState)roundState;
            roundState = new RoundState(maker.button, maker.street, maker.stacks, maker.hands, newBoardStates, maker.previousState);
            return new TerminalState(Arrays.asList(0, 0), roundState);
        }
        else {
            List<Action> actions = new ArrayList<Action>();
            for(String subclause : subclauses) {
                String leftover = subclause.substring(2, subclause.length());
                switch (subclause.charAt(1)) {
                    case 'F': {
                        actions.add(new Action(ActionType.FOLD_ACTION_TYPE));
                        break;
                    }
                    case 'C': {
                        actions.add(new Action(ActionType.CALL_ACTION_TYPE));
                        break;
                    }
                    case 'K': {
                        actions.add(new Action(ActionType.CHECK_ACTION_TYPE));
                        break;
                    }
                    case 'R': {
                        actions.add(new Action(ActionType.RAISE_ACTION_TYPE, Integer.parseInt(leftover)));
                        break;
                    }
                    case 'A': {
                        String[] cards = leftover.split(",");
                        if ("".equals(leftover)) {
                            actions.add(new Action(ActionType.ASSIGN_ACTION_TYPE, Arrays.asList("", "")));
                        } else {
                            actions.add(new Action(ActionType.ASSIGN_ACTION_TYPE, Arrays.asList(cards)));
                        }
                        break;
                    }
                    default: {
                        break;
                    }
                }
            }
            return ((RoundState)roundState).proceed(actions);
        }
    }

    /**
     * Parses arguments corresponding to socket connection information.
     */
    public void parseArgs(String[] rawArgs) {
        boolean hostFlag = false;
        this.host = "localhost";
        for (String arg : rawArgs) {
            if (arg.equals("-h") | arg.equals("--host")) {
                hostFlag = true;
            } else if (arg.equals("--port")) {
                // nothing to do
            } else if (hostFlag) {
                this.host = arg;
                hostFlag = false;
            } else {
                this.port = Integer.parseInt(arg);
            }
        }
    }

    /**
     * Runs the pokerbot.
     */
    public void runBot(Bot pokerbot) {
        this.pokerbot = pokerbot;
        try {
            this.socket = new Socket(this.host, this.port);
            this.socket.setTcpNoDelay(true);
            this.outStream = new PrintWriter(socket.getOutputStream(), true);
            this.inStream = new BufferedReader(new InputStreamReader(socket.getInputStream()));
        } catch (IOException e) {
            System.out.println("Could not connect to " + host + ":" + Integer.toString(port));
            return;
        }
        try {
            this.run();
            this.inStream.close();
            this.inStream = null;
            this.outStream.close();
            this.outStream = null;
            this.socket.close();
            this.socket = null;
        } catch (IOException e) {
            System.out.println("Engine disconnected.");
        }
    }
}
