package javabot;

import javabot.skeleton.Action;
import javabot.skeleton.ActionType;
import javabot.skeleton.GameState;
import javabot.skeleton.State;
import javabot.skeleton.TerminalState;
import javabot.skeleton.BoardState;
import javabot.skeleton.RoundState;
import javabot.skeleton.Bot;
import javabot.skeleton.Runner;

import java.util.List;
import java.util.Arrays;
import java.util.ArrayList;
import java.util.Set;
import java.lang.Integer;
import java.lang.String;

/**
 * A pokerbot.
 */
public class Player implements Bot {
    // Your instance variables go here.

    /**
     * Called when a new game starts. Called exactly once.
     */
    public Player() {
    }

    /**
     * Called when a new round starts. Called State.NUM_ROUNDS times.
     *
     * @param gameState The GameState object.
     * @param roundState The RoundState object.
     * @param active Your player's index.
     */
    public void handleNewRound(GameState gameState, RoundState roundState, int active) {
        //int myBankroll = gameState.bankroll;  // the total number of chips you've gained or lost from the beginning of the game to the start of this round
        //int oppBankroll = gameState.oppBankroll; // ^ but for your opponent
        //float gameClock = gameState.gameClock;  // the total number of seconds your bot has left to play this game
        //int roundNum = gameState.roundNum;  // the round number from 1 to State.NUM_ROUNDS
        //List<String> myCards = roundState.hands.get(active);  // your six cards at the start of the round
        //boolean bigBlind = (active == 1);  // true if you are the big blind
    }

    /**
     * Called when a round ends. Called State.NUM_ROUNDS times.
     *
     * @param gameState The GameState object.
     * @param terminalState The TerminalState object.
     * @param active Your player's index.
     */
    public void handleRoundOver(GameState gameState, TerminalState terminalState, int active) {
        //int myDelta = terminalState.deltas.get(active);  // your bankroll change from this round
        //int oppDelta = terminalState.deltas.get(1-active);  // your opponent's bankroll change from this round
        //RoundState previousState = (RoundState)(terminalState.previousState);  // RoundState before payoffs
        //int street = previousState.street;  // 0, 3, 4, or 5 representing when this round ended
        //List<List<String>> myCards = new ArrayList<List<String>>();
        //List<List<String>> oppCards = new ArrayList<List<String>>();
        //for (State terminalBoardState : previousState.boardStates) {
        //    BoardState previousBoardState = (BoardState)(((TerminalState)terminalBoardState).previousState);
        //    myCards.add(previousBoardState.hands.get(active)); // your cards
        //    oppCards.add(previousBoardState.hands.get(1-active)); // opponent's cards or "" if not revealed
        //}
    }

    /**
     * Where the magic happens - your code should implement this function.
     * Called any time the engine needs a triplet of actions from your bot.
     *
     * @param gameState The GameState object.
     * @param roundState The RoundState object.
     * @param active Your player's index.
     * @return Your action.
     */
    public List<Action> getActions(GameState gameState, RoundState roundState, int active) {
        List<Set<ActionType>> legalActions = roundState.legalActions();  // the actions you are allowed to take
        // int street = roundState.street;  // 0, 3, 4, or 5 representing pre-flop, flop, turn, or river respectively
        List<String> myCards = roundState.hands.get(active);  // your cards across all boards
        // List<List<String>> boardCards = new ArrayList<List<String>>(); // the board cards
        // int[] myPips = new int[State.NUM_BOARDS];  // the number of chips you have contributed to the pot on each board this round of betting
        // int[] oppPips = new int[State.NUM_BOARDS];  // the number of chips your opponent has contributed to the pot on each board this round of betting
        // int[] continueCost = new int[State.NUM_BOARDS];  // the number of chips needed to stay in each pot
        // for (int i = 0; i < State.NUM_BOARDS; i++) {
        //    if (roundState.boardStates.get(i) instanceof BoardState) {  // if a board is still active (no one folded)
        //         BoardState boardState = (BoardState)roundState.boardStates.get(i);
        //         myPips[i] = boardState.pips.get(active);
        //         oppPips[i] = boardState.pips.get(1-active);
        //         boardCards.add(boardState.deck);
        //    } else {  // someone already folded on this board
        //         TerminalState terminalBoardState = (TerminalState)roundState.boardStates.get(i);
        //         myPips[i] = 0;
        //         oppPips[i] = 0;
        //         boardCards.add(((BoardState)terminalBoardState.previousState).deck);
        //    }
        //    continueCost[i] = oppPips[i] - myPips[i];
        // }
        // int myStack = roundState.stacks.get(active);  // the number of chips you have remaining
        // int oppStack = roundState.stacks.get(1-active);  // the number of chips your opponent has remaining
        // int netUpperRaiseBound = roundState.raiseBounds().get(1);  // the maximum value you can raise across all 3 boards
        // int netCost = 0;  // to keep track of the net additional amount you are spending across boards this round 
        List<Action> myActions = new ArrayList<Action>();
        for (int i = 0; i < State.NUM_BOARDS; i++) {
            Set<ActionType> legalBoardActions = legalActions.get(i);
            if (legalBoardActions.contains(ActionType.ASSIGN_ACTION_TYPE)) { // default assignment of hands to boards
                List<String> cards = new ArrayList<String>();
                cards.add(myCards.get(2*i));
                cards.add(myCards.get(2*i + 1));
                myActions.add(new Action(ActionType.ASSIGN_ACTION_TYPE, cards));
            }
            else if (legalBoardActions.contains(ActionType.CHECK_ACTION_TYPE)) { // check-call
                myActions.add(new Action(ActionType.CHECK_ACTION_TYPE));
            } else {
                myActions.add(new Action(ActionType.CALL_ACTION_TYPE));
            }
        }
        return myActions;
    }

    /**
     * Main program for running a Java pokerbot.
     */
    public static void main(String[] args) {
        Player player = new Player();
        Runner runner = new Runner();
        runner.parseArgs(args);
        runner.runBot(player);
    }
}