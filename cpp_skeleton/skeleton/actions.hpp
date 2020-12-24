#ifndef __SKELETON_ACTIONS_HPP__
#define __SKELETON_ACTIONS_HPP__

enum ActionType
{
    FOLD_ACTION_TYPE  = (1 << 0),
    CALL_ACTION_TYPE  = (1 << 1),
    CHECK_ACTION_TYPE = (1 << 2),
    RAISE_ACTION_TYPE = (1 << 3)
};

struct Action
{
    ActionType action_type;
    int amount;
};

Action FoldAction();
Action CallAction();
Action CheckAction();
Action RaiseAction(int amount);

#endif  // __SKELETON_ACTIONS_HPP__