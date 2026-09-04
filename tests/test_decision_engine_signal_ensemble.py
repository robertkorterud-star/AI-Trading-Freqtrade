from atlas.decision.engine import DecisionEngine
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult


def test_decision_engine_exposes_signal_ensemble_result():
    results = [
        AnalysisResult(
            analyst="Technical Analyst",
            symbol="TEST",
            action=Action.BUY,
            confidence=88,
            evidence=85,
            reasoning=["bullish trend"],
            signal_confidence=78,
        ),
        AnalysisResult(
            analyst="Momentum Analyst",
            symbol="TEST",
            action=Action.BUY,
            confidence=80,
            evidence=82,
            reasoning=["positive momentum"],
        ),
    ]

    result = DecisionEngine().evaluate(results)

    assert result.ensemble_action == Action.BUY
    assert result.ensemble_confidence > 50
    assert "Signal ensemble: BUY" in result.reasoning[4]


def test_decision_engine_preserves_legacy_result_confidence_when_signal_confidence_exists():
    result = DecisionEngine().evaluate(
        [
            AnalysisResult(
                analyst="Technical Analyst",
                symbol="TEST",
                action=Action.BUY,
                confidence=88,
                evidence=85,
                signal_confidence=70,
            )
        ]
    )

    assert result.confidence == 88
    assert result.ensemble_confidence == 100
