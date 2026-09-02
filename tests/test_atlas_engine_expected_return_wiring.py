from atlas.core.config import AtlasConfig
from atlas.core.engine import AtlasEngine
from atlas.models.action import Action


class RecordingExpectedReturnService:
    def __init__(self, expected_return=0.0125):
        self.expected_return = expected_return
        self.calls = []

    def estimate(self, *, symbol, action):
        self.calls.append((symbol, action))
        return self.expected_return


def test_atlas_engine_wires_expected_return_service_into_decision_engine():
    engine = AtlasEngine(
        config=AtlasConfig(
            trading_mode="paper",
            paper_trading=True,
        )
    )

    service = engine.expected_return_service

    assert service is not None
    assert engine.decision_engine.expected_return_service is service
    assert service.provider is engine.historical_return_provider
    assert service.provider.repository is engine.prediction_repository


def test_atlas_engine_decision_engine_uses_wired_expected_return_service():
    engine = AtlasEngine(
        config=AtlasConfig(
            trading_mode="paper",
            paper_trading=True,
        )
    )

    service = RecordingExpectedReturnService()
    engine.decision_engine.expected_return_service = service

    result = engine.decision_engine.evaluate(
        [
            _analysis_result(
                symbol="BTC-USD",
                action=Action.BUY,
                evidence=90.0,
                confidence=90.0,
            )
        ]
    )

    assert result.expected_return == 0.0125
    assert service.calls == [("BTC-USD", Action.BUY)]


def _analysis_result(*, symbol, action, evidence, confidence):
    from atlas.models.analysis_result import AnalysisResult

    return AnalysisResult(
        analyst="test-analyst",
        symbol=symbol,
        action=action,
        confidence=confidence,
        evidence=evidence,
        reasoning=["controlled test signal"],
    )
