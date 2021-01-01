package javabot.skeleton;

import java.util.List;
import java.util.Arrays;
import java.util.Collections;
import java.lang.String;

/**
 * The actions that the player is allowed to take.
 */
public class Action {
    public ActionType actionType;
    public int amount;
    public List<String> cards;

    public Action(ActionType actionType) {
        this.actionType = actionType;
        this.amount = 0;
        this.cards = Collections.unmodifiableList(
            Arrays.asList(
                new String(),
                new String()
            )
        );
    }

    public Action(ActionType actionType, int amount) {
        this.actionType = actionType;
        this.amount = amount;
        this.cards = Collections.unmodifiableList(
            Arrays.asList(
                new String(),
                new String()
            )
        );
    }

    public Action(ActionType actionType, List<String> cards) {
        this.actionType = actionType;
        this.amount = 0;
        this.cards = Collections.unmodifiableList(
            Arrays.asList(
                cards.get(0),
                cards.get(1)
            )
        );
    }
}