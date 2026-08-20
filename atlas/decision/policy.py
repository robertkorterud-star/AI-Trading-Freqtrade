"""
ATLAS Decision Policy

Centralizes the rules used to translate analyst
evidence and agreement into a final action.
"""

from atlas.models.action import Action


BUY_THRESHOLD = 80.0
HOLD_THRESHOLD = 60.0

# Minimum analyst agreement required for a BUY.
BUY_AGREEMENT_THRESHOLD = 66.7

# Minimum analyst agreement required for a SELL.
SELL_AGREEMENT_THRESHOLD = 66.7


def determine_action(
    evidence: float,
    agreement: float,
    conflict: bool,
    buy_count: int,
    hold_count: int,
    sell_count: int,
) -> Action:
    """
    Determine the final ATLAS action.

    Safety principle:
    High evidence alone must not create an aggressive
    BUY/SELL decision when analyst signals conflict.
    """

    # Strong unanimous/majority BUY.
    if (
        evidence >= BUY_THRESHOLD
        and agreement >= BUY_AGREEMENT_THRESHOLD
        and buy_count > hold_count
        and buy_count > sell_count
        and not conflict
    ):
        return Action.BUY

    # Strong unanimous/majority SELL.
    if (
        evidence >= HOLD_THRESHOLD
        and agreement >= SELL_AGREEMENT_THRESHOLD
        and sell_count > buy_count
        and sell_count > hold_count
        and not conflict
    ):
        return Action.SELL

    # Any conflicting signals require HOLD.
    if conflict:
        return Action.HOLD

    # Normal evidence thresholds.
    if evidence >= BUY_THRESHOLD:
        return Action.BUY

    if evidence >= HOLD_THRESHOLD:
        return Action.HOLD

    return Action.SELL
