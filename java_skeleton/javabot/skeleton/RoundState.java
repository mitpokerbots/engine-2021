package javabot.skeleton;

import java.util.List;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Set;
import java.util.HashSet;
import java.util.Collections;
import java.lang.Integer;
import java.lang.String;

/**
 * Encodes the game tree for one round of poker.
 */
public class RoundState extends State {
    public final int button;
    public final int street;
    public final List<Integer> stacks;
    public final List<List<String>> hands;
    public final List<State> boardStates;
    public final State previousState;

    public RoundState(int button, int street, List<Integer> stacks, List<List<String>> hands,
                      List<State> boardStates, State previousState) {
        this.button = button;
        this.street = street;
        this.stacks = Collections.unmodifiableList(stacks);
        this.hands = Collections.unmodifiableList(
            Arrays.asList(
                Collections.unmodifiableList(hands.get(0)),
                Collections.unmodifiableList(hands.get(1))
            )
        );
        this.boardStates = boardStates;
        this.previousState = previousState;
    }

    /**
     * Compares the players' hands and computes payoffs.
     */
    public State showdown() {
        List<State> terminalBoardStates = new ArrayList<State>();
        for (State boardState : this.boardStates) {
            if (boardState instanceof BoardState) {
                terminalBoardStates.add((TerminalState)(((BoardState)boardState).showdown()));
            } else {
                terminalBoardStates.add((TerminalState)boardState);
            }
        }
        return new TerminalState(Arrays.asList(0, 0), new RoundState(this.button, this.street, this.stacks, this.hands, terminalBoardStates, this));
    }

    /**
     * Returns the active player's legal moves on each board.
     */
    public List<Set<ActionType>> legalActions() {
        List<Set<ActionType>> output = new ArrayList<Set<ActionType>>();
        for (State boardState : this.boardStates) {
            if (boardState instanceof BoardState) {
                output.add(((BoardState)boardState).legalActions(this.button, this.stacks));
            } else {
                output.add(new HashSet<ActionType>(Arrays.asList(ActionType.CHECK_ACTION_TYPE)));
            }
        }
        return output;
    }

    /**
     * Returns a list of the minimum and maximum legal raises summed across boards.
     */
    public List<Integer> raiseBounds() {
        int active = this.button % 2;
        if (active < 0) active += 2;
        int netContinueCost = 0;
        int netPipsUnsettled = 0;
        for (State boardState : this.boardStates) {
            if ((boardState instanceof BoardState) && (!((BoardState)boardState).settled)) {
                BoardState bs = (BoardState)boardState;
                netContinueCost += bs.pips.get(1-active) - bs.pips.get(active);
                netPipsUnsettled += bs.pips.get(active);
            }
        }
        return Arrays.asList(0, netPipsUnsettled + Math.min(this.stacks.get(active), this.stacks.get(1-active) + netContinueCost));
    }

    /**
     * Resets the players' pips on each board and advances the game tree to the next round of betting.
     */
    public State proceedStreet() {
        int[] newPots = new int[State.NUM_BOARDS];
        for (int i = 0; i < State.NUM_BOARDS; i++) {
            if (this.boardStates.get(i) instanceof BoardState) {
                BoardState adder = (BoardState)this.boardStates.get(i);
                newPots[i] = adder.pot + adder.pips.stream().mapToInt(Integer::intValue).sum();
            }
        }
        List<State> newBoardStates = new ArrayList<State>();
        for (int i = 0; i < State.NUM_BOARDS; i++) {
            if (this.boardStates.get(i) instanceof BoardState) {
                BoardState bs = (BoardState)this.boardStates.get(i);
                newBoardStates.add(new BoardState(newPots[i], Arrays.asList(0, 0), bs.hands, bs.deck, this.boardStates.get(i)));
            } else {
                newBoardStates.add(this.boardStates.get(i));
            }
        }
        List<Boolean> allTerminal = new ArrayList<Boolean>();
        for (State boardState : newBoardStates) {
            allTerminal.add(boardState instanceof TerminalState);
        }
        if ((this.street == 5) || (!allTerminal.contains(false))) {
            return (new RoundState(this.button, 5, this.stacks, this.hands, newBoardStates, this)).showdown();
        }
        int newStreet;
        if (this.street == 0) {
            newStreet = 3;
        } else {
            newStreet = this.street + 1;
        }
        return new RoundState(1, newStreet, this.stacks, this.hands, newBoardStates, this);
    }

    /**
     * Advances the game tree by one list of actions performed by the active player across all boards.
     */
    public State proceed(List<Action> actions) {
        List<State> newBoardStates = new ArrayList<State>();
        for (int i = 0; i < State.NUM_BOARDS; i++) {
            if (this.boardStates.get(i) instanceof BoardState) {
                newBoardStates.add(((BoardState)this.boardStates.get(i)).proceed(actions.get(i), this.button, this.street));
            } else {
                newBoardStates.add(this.boardStates.get(i));
            }
        }
        int active = this.button % 2;
        if (active < 0) active += 2;
        List<Integer> newStacks = new ArrayList<Integer>(this.stacks);
        int contribution = 0;
        for (int i = 0; i < State.NUM_BOARDS; i++) {
            if ((newBoardStates.get(i) instanceof BoardState) && (this.boardStates.get(i) instanceof BoardState)) {
                contribution += ((BoardState)newBoardStates.get(i)).pips.get(active) - ((BoardState)this.boardStates.get(i)).pips.get(active);
            }
        }
        newStacks.set(active, newStacks.get(active) - contribution);
        List<Boolean> settled = new ArrayList<Boolean>();
        for (State boardState : newBoardStates) {
            settled.add((boardState instanceof TerminalState) || (((BoardState)boardState).settled));
        }
        RoundState state = new RoundState(this.button + 1, this.street, newStacks, this.hands, newBoardStates, this);
        if (!settled.contains(false)) {
            return state.proceedStreet();
        } else {
            return state;
        }
    }
}