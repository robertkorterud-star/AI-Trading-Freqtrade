from atlas.decision.policy import determine_action
from atlas.models.action import Action


def test_unanimous_high_evidence_buy():
    action = determine_action(
        evidence=90,
        agreement=100,
        conflict=False,
        buy_count=3,
        hold_count=0,
        sell_count=0,
    )

    assert action == Action.BUY


def test_conflicting_buy_signals_become_hold():
    action = determine_action(
        evidence=90,
        agreement=66.7,
        conflict=True,
        buy_count=2,
        hold_count=0,
        sell_count=1,
    )

    assert action == Action.HOLD


def test_balanced_conflict_is_hold():
    action = determine_action(
        evidence=70,
        agreement=33.3,
        conflict=True,
        buy_count=1,
        hold_count=1,
        sell_count=1,
    )

    assert action == Action.HOLD


def test_unanimous_sell():
    action = determine_action(
        evidence=40,
        agreement=100,
        conflict=False,
        buy_count=0,
        hold_count=0,
        sell_count=3,
    )

    assert action == Action.SELL


def test_two_buy_one_hold_with_high_evidence_is_hold():
    action = determine_action(
        evidence=85,
        agreement=66.7,
        conflict=True,
        buy_count=2,
        hold_count=1,
        sell_count=0,
    )

    assert action == Action.HOLD
