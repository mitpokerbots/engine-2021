package javabot.skeleton;

import java.util.List;
import java.util.Arrays;
import java.util.Collections;
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

    public BoardState(int pot, List<Integer> pips, List<List<String>> hands,
                      List<String> deck, State previousState) {
        this.pot = pot;
        this.pips = Collections.unmodifiableList(pips);
        this.hands = Collections.unmodifiableList(
            Arrays.asList(
                Collections.unmodifiableList(hands.get(0)),
                Collections.unmodifiableList(hands.get(1))
            )
        );
        this.deck = Collections.unmodifiableList(deck);
        this.previousState = previousState;
    }
}