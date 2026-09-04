import pytest

from atlas.intelligence.signal_ensemble import SignalEnsemble, SignalInput
from atlas.models.action import Action


def test_ensemble_combines_independent_signals():
    result = SignalEnsemble().combine([
        SignalInput("technical", Action.BUY, 80),
        SignalInput("momentum", Action.BUY, 70),
        SignalInput("ai", Action.SELL, 40),
    ])
    assert result.action == Action.BUY
    assert result.confidence == pytest.approx(78.9474, rel=1e-4)
    assert result.contributors == ("technical", "momentum", "ai")


def test_ensemble_supports_hold():
    result = SignalEnsemble().combine([
        SignalInput("technical", Action.BUY, 60),
        SignalInput("risk", Action.HOLD, 90),
    ])
    assert result.action == Action.HOLD
    assert result.confidence == pytest.approx(60.0)


def test_ensemble_rejects_empty_input():
    with pytest.raises(ValueError, match="No signals provided"):
        SignalEnsemble().combine([])


def test_ensemble_rejects_invalid_confidence():
    with pytest.raises(ValueError, match="between 0 and 100"):
        SignalEnsemble().combine([SignalInput("technical", Action.BUY, 101)])
