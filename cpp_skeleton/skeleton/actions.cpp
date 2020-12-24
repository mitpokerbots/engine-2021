/**
 * The actions that the player is allowed to take.
 */
#include "actions.hpp"

Action FoldAction()
{
    return (Action) { FOLD_ACTION_TYPE, 0 };
}

Action CallAction()
{
    return (Action) { CALL_ACTION_TYPE, 0 };
}

Action CheckAction()
{
    return (Action) { CHECK_ACTION_TYPE, 0 };
}

Action RaiseAction(int amount)
{
    return (Action) { RAISE_ACTION_TYPE, amount };
}