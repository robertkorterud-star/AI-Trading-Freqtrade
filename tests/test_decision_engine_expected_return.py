from atlas.decision.engine import DecisionEngine
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult


class FakeExpectedReturnService:
    def __init__(self, value=0.0125):
        self.value = value
        self.calls = []

    def estimate(self, symbol, action):
        self.calls.append((symbol, action))
        return self.value


def _buy_results():
    return [
        AnalysisResult(
            analyst="trend",
            symbol="BTCUSDT",
            action=Action.BUY,
            confidence=90.0,
            evidence=90.0,
        ),
        AnalysisResult(
            analyst="momentum",
            symbol="BTCUSDT",
            action=Action.BUY,
            confidence=85.0,
            evidence=85.0,
        ),
    ]


def test_engine_includes_expected_return_without_changing_action():
    service = FakeExpectedReturnService()
    engine = DecisionEngine(expected_return_service=service)

    decision = engine.evaluate(_buy_results())

    assert decision.action is Action.BUY
    assert decision.expected_return == 0.0125
    assert service.calls == [("BTCUSDT", Action.BUY)]


def test_engine_defaults_expected_return_to_zero_when_service_is_absent():
    engine = DecisionEngine()

    decision = engine.evaluate(_buy_results())

    assert decision.action is Action.BUY
    assert decision.expected_return == 0.0


def test_engine_uses_final_action_for_expected_return():
    service = FakeExpectedReturnService(value=0.02)
    engine = DecisionEngine(expected_return_service=service)

    results = [
        AnalysisResult(
            analyst="trend",
            symbol="BTCUSDT",
            action=Action.HOLD,
            confidence=90.0,
            evidence=90.0,
        ),
        AnalysisResult(
            analyst="momentum",
            symbol="BTCUSDT",
            action=Action.HOLD,
            confidence=90.0,
            evidence=90.0,
        ),
    ]

    decision = engine.evaluate(results)

    assert decision.action is Action.HOLD
    assert decision.expected_return == 0.02
    assert service.calls == [("BTCUSDT", Action.HOLD)]
