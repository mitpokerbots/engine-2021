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
    public List<List<String>> assignment;

    public Action(ActionType actionType) {
        this.actionType = actionType;
        this.amount = 0;
        this.assignment = Collections.unmodifiableList(
            Arrays.asList(
                Collections.emptyList(),
                Collections.emptyList()
            )
        );
    }

    public Action(ActionType actionType, int amount) {
        this.actionType = actionType;
        this.amount = amount;
        this.assignment = Collections.unmodifiableList(
            Arrays.asList(
                Collections.emptyList(),
                Collections.emptyList()
            )
        );
    }

    public Action(ActionType actionType, List<List<String>> assignment) {
        this.actionType = actionType;
        this.amount = 0;
        this.assignment = Collections.unmodifiableList(
            Arrays.asList(
                Collections.unmodifiableList(assignment.get(0)),
                Collections.unmodifiableList(assignment.get(1))
            )
        );
    }
}