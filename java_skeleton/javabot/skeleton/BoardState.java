package javabot.skeleton;

import java.util.List;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Set;
import java.util.HashSet;
import java.lang.Integer;
import java.lang.String;

/**
 * Encodes the game tree for one board within a round.
 */
public class BoardState extends State {
    public final int pot;
    public final List<Integer> pips;
    public final List<List<String>> hands;
    public final List<String> deck;
    public final State previousState;
    public final boolean settled;

    public BoardState(int pot, List<Integer> pips, List<List<String>> hands,
                      List<String> deck, State previousState) {
        this(pot, pips, hands, deck, previousState, false);
    }

    public BoardState(int pot, List<Integer> pips, List<List<String>> hands,
                      List<String> deck, State previousState, boolean settled) {
        this.pot = pot;
        this.pips = Collections.unmodifiableList(pips);
        if (hands == null) {
            this.hands = null;
        } else {
            this.hands = Collections.unmodifiableList(
                Arrays.asList(
                    Collections.unmodifiableList(hands.get(0)),
                    Collections.unmodifiableList(hands.get(1))
                )
            );
        }
        this.deck = Collections.unmodifiableList(deck);
        this.previousState = previousState;
        this.settled = settled;
    }

    /**
     * Compares the players' hands and computes payoffs.
     */
    public State showdown() {
        return new TerminalState(Arrays.asList(0, 0), this);
    }

    /**
     * Returns the active player's legal moves on this board.
     */
    public Set<ActionType> legalActions(int button, List<Integer> stacks) {
        int active = button % 2;
        if (active < 0) active += 2;
        if ((this.hands == null) || (this.hands.get(active).size() == 0)) {
            return new HashSet<ActionType>(Arrays.asList(ActionType.ASSIGN_ACTION_TYPE));
        } else if (this.settled) {
            return new HashSet<ActionType>(Arrays.asList(ActionType.CHECK_ACTION_TYPE));
        }
        // board being played on
        int continueCost = this.pips.get(1-active) - this.pips.get(active);
        if (continueCost == 0) {
            // we can only raise the stakes if both players can afford it
            boolean betsForbidden = ((stacks.get(0) == 0) | (stacks.get(1) == 0));
            if (betsForbidden) {
                return new HashSet<ActionType>(Arrays.asList(ActionType.CHECK_ACTION_TYPE));
            }
            return new HashSet<ActionType>(Arrays.asList(ActionType.CHECK_ACTION_TYPE, ActionType.RAISE_ACTION_TYPE));
        }
        // continueCost > 0
        // similarly, re-raising is only allowed if both players can afford it
        boolean raisesForbidden = ((continueCost == stacks.get(active)) | (stacks.get(1-active) == 0));
        if (raisesForbidden) {
            return new HashSet<ActionType>(Arrays.asList(ActionType.FOLD_ACTION_TYPE, ActionType.CALL_ACTION_TYPE));
        }
        return new HashSet<ActionType>(Arrays.asList(ActionType.FOLD_ACTION_TYPE,
                                                     ActionType.CALL_ACTION_TYPE,
                                                     ActionType.RAISE_ACTION_TYPE));
    }

    /**
     * Returns a list of the minimum and maximum legal raises on this board.
     */
    public List<Integer> raiseBounds(int button, List<Integer> stacks) {
        int active = button % 2;
        if (active < 0) active += 2;
        int continueCost = this.pips.get(1-active) - this.pips.get(active);
        int maxContribution = Math.min(stacks.get(active), stacks.get(1-active) + continueCost);
        int minContribution = Math.min(maxContribution, continueCost + Math.max(continueCost, State.BIG_BLIND));
        return Arrays.asList(this.pips.get(active) + minContribution, this.pips.get(active) + maxContribution);
    }

    /**
     * Advances the game tree by one action performed by the active player on the current board..
     */
    public State proceed(Action action, int button, int street) {
        int active = button % 2;
        if (active < 0) active += 2;
        switch (action.actionType) {
            case ASSIGN_ACTION_TYPE: {
                List<List<String>> newHands = Arrays.asList(new ArrayList<String>(), new ArrayList<String>());
                newHands.set(active, action.cards);
                if (this.hands != null) {
                    List<String> oppHands = this.hands.get(1-active);
                    newHands.set(1-active, oppHands);
                }
                return new BoardState(this.pot, this.pips, newHands, this.deck, this);
            }
            case FOLD_ACTION_TYPE: {
                int newPot = this.pot + this.pips.stream().mapToInt(Integer::intValue).sum();
                List<Integer> winnings;
                if (active == 0) {
                    winnings = Arrays.asList(0, newPot);
                } else {
                    winnings = Arrays.asList(newPot, 0);
                }
                return new TerminalState(winnings, new BoardState(newPot, Arrays.asList(0, 0), this.hands, this.deck, this, true));
            }
            case CALL_ACTION_TYPE: {
                if (button == 0) {  // sb calls bb
                    return new BoardState(this.pot, Arrays.asList(State.BIG_BLIND, State.BIG_BLIND),
                                          this.hands, this.deck, this);
                }
                // both players acted
                List<Integer> newPips = new ArrayList<Integer>(this.pips);
                int contribution = newPips.get(1-active) - newPips.get(active);
                newPips.set(active, newPips.get(active) + contribution);
                return new BoardState(this.pot, newPips, this.hands, this.deck, this, true);
            }
            case CHECK_ACTION_TYPE: {
                if (((street == 0) & (button > 0)) | (button > 1)) {  // both players acted
                    return new BoardState(this.pot, this.pips, this.hands, this.deck, this, true);
                }
                // let opponent act
                return new BoardState(this.pot, this.pips, this.hands, this.deck, this, this.settled);
            }
            default: {  // RAISE_ACTION_TYPE
                List<Integer> newPips = new ArrayList<Integer>(this.pips);
                int contribution = action.amount - newPips.get(active);
                newPips.set(active, newPips.get(active) + contribution);
                return new BoardState(this.pot, newPips, this.hands, this.deck, this);
            }
        }
    }
}