import pytest

from atlas.agents.news_analyst import NewsAnalyst
from atlas.decision.engine import DecisionEngine
from atlas.models.action import Action


class FakeAIAdapter:

    def analyze_news(self, symbol, articles):
        return {
            "symbol": symbol,
            "relevance": 95,
            "sentiment": "POSITIVE",
            "impact": "HIGH",
            "time_horizon": "SHORT",
            "action": "BUY",
            "confidence": 95,
            "reason": "Strong positive evidence.",
        }


def test_decision_engine_returns_buy(monkeypatch):

    from atlas.core.ai_provider_factory import (
        AIProviderFactory,
    )

    monkeypatch.setattr(
        AIProviderFactory,
        "create",
        classmethod(
            lambda cls, config=None:
                FakeAIAdapter()
        ),
    )

    analyst = NewsAnalyst()

    articles = [
        {
            "title": "Strong positive market news",
            "summary": "Excellent developments.",
            "source": "Test News",
        }
    ]

    results = [
        analyst.analyze_news(
            "BTC",
            articles,
        )
    ]

    engine = DecisionEngine()

    decision = engine.evaluate(
        results
    )

    assert decision.action == Action.BUY


def test_decision_engine_includes_agent_weights():

    from atlas.models.analysis_result import AnalysisResult

    class FakeWeightEngine:

        def calculate(self):
            return {
                "Technical Analyst": 0.60,
                "News Analyst": 0.40,
            }

    result = AnalysisResult(
        symbol="BTC-USD",
        analyst="Technical Analyst",
        action=Action.BUY,
        confidence=90.0,
        evidence=90.0,
        reasoning=["Strong technical evidence."],
    )

    engine = DecisionEngine()
    engine.agent_weight_engine = FakeWeightEngine()

    decision = engine.evaluate(
        [result]
    )

    assert decision.agent_weights == {
        "Technical Analyst": 0.60,
        "News Analyst": 0.40,
    }


def test_decision_engine_uses_adaptive_weights_in_evidence():

    from atlas.models.analysis_result import AnalysisResult

    class FakeWeightEngine:

        def calculate(self):
            return {
                "Technical Analyst": 0.85,
                "News Analyst": 0.10,
                "Company Analyst": 0.05,
            }

    results = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Technical Analyst",
            action=Action.BUY,
            confidence=100.0,
            evidence=100.0,
            reasoning=["Very strong technical evidence."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="News Analyst",
            action=Action.HOLD,
            confidence=20.0,
            evidence=20.0,
            reasoning=["Weak news evidence."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Company Analyst",
            action=Action.HOLD,
            confidence=20.0,
            evidence=20.0,
            reasoning=["Weak company evidence."],
        ),
    ]

    engine = DecisionEngine()
    engine.agent_weight_engine = FakeWeightEngine()

    decision = engine.evaluate(results)

    assert decision.evidence == 88.0
    assert decision.confidence == 88.0

    assert decision.agent_weights == {
        "Technical Analyst": 0.85,
        "News Analyst": 0.10,
        "Company Analyst": 0.05,
    }


def test_high_weight_agent_can_influence_final_decision():

    from atlas.models.analysis_result import AnalysisResult

    class FakeWeightEngine:

        def calculate(self):
            return {
                "Technical Analyst": 0.85,
                "News Analyst": 0.10,
                "Company Analyst": 0.05,
            }

    results = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Technical Analyst",
            action=Action.BUY,
            confidence=100.0,
            evidence=100.0,
            reasoning=["Very strong technical BUY signal."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="News Analyst",
            action=Action.SELL,
            confidence=100.0,
            evidence=0.0,
            reasoning=["Strong negative news signal."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Company Analyst",
            action=Action.SELL,
            confidence=100.0,
            evidence=0.0,
            reasoning=["Negative company signal."],
        ),
    ]

    engine = DecisionEngine()
    engine.agent_weight_engine = FakeWeightEngine()

    decision = engine.evaluate(results)

    assert decision.evidence == 85.0
    assert decision.confidence == 100.0

    assert decision.action == Action.BUY

def test_decision_explains_adaptive_weighted_buy():

    from atlas.models.analysis_result import AnalysisResult

    class FakeWeightEngine:

        def calculate(self):
            return {
                "Technical Analyst": 0.85,
                "News Analyst": 0.10,
                "Company Analyst": 0.05,
            }

    results = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Technical Analyst",
            action=Action.BUY,
            confidence=100.0,
            evidence=100.0,
            reasoning=["Very strong technical BUY signal."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="News Analyst",
            action=Action.SELL,
            confidence=100.0,
            evidence=0.0,
            reasoning=["Negative news signal."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Company Analyst",
            action=Action.SELL,
            confidence=100.0,
            evidence=0.0,
            reasoning=["Negative company signal."],
        ),
    ]

    engine = DecisionEngine()
    engine.agent_weight_engine = FakeWeightEngine()

    decision = engine.evaluate(results)

    assert decision.action == Action.BUY

    assert any(
        "85.0%" in reason
        for reason in decision.reasoning
    )

    assert any(
        "adaptive" in reason.lower()
        for reason in decision.reasoning
    )


def test_decision_explains_normal_aligned_buy():

    from atlas.models.analysis_result import AnalysisResult

    results = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Technical Analyst",
            action=Action.BUY,
            confidence=100.0,
            evidence=90.0,
            reasoning=["Strong technical BUY signal."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="News Analyst",
            action=Action.BUY,
            confidence=90.0,
            evidence=85.0,
            reasoning=["Positive news signal."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Company Analyst",
            action=Action.BUY,
            confidence=90.0,
            evidence=85.0,
            reasoning=["Positive company signal."],
        ),
    ]

    engine = DecisionEngine()

    decision = engine.evaluate(results)

    assert decision.action == Action.BUY

    assert any(
        "combined analyst evidence" in reason.lower()
        for reason in decision.reasoning
    )

def test_decision_robustness_level_strong():

    from atlas.models.analysis_result import AnalysisResult

    results = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Technical Analyst",
            action=Action.BUY,
            confidence=100.0,
            evidence=100.0,
            reasoning=["Strong BUY."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="News Analyst",
            action=Action.BUY,
            confidence=100.0,
            evidence=100.0,
            reasoning=["Positive news."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Company Analyst",
            action=Action.BUY,
            confidence=100.0,
            evidence=100.0,
            reasoning=["Positive company signal."],
        ),
    ]

    decision = DecisionEngine().evaluate(results)

    assert decision.robustness >= 80.0
    assert decision.robustness_level == "STRONG"


def test_decision_robustness_level_moderate():

    from atlas.models.analysis_result import AnalysisResult

    class FakeWeightEngine:

        def calculate(self):
            return {
                "Technical Analyst": 0.70,
                "News Analyst": 0.20,
                "Company Analyst": 0.10,
            }

    results = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Technical Analyst",
            action=Action.BUY,
            confidence=100.0,
            evidence=70.0,
            reasoning=["BUY."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="News Analyst",
            action=Action.HOLD,
            confidence=70.0,
            evidence=50.0,
            reasoning=["HOLD."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Company Analyst",
            action=Action.HOLD,
            confidence=70.0,
            evidence=50.0,
            reasoning=["HOLD."],
        ),
    ]

    engine = DecisionEngine()
    engine.agent_weight_engine = FakeWeightEngine()

    decision = engine.evaluate(results)

    assert decision.robustness == 47.2
    assert decision.robustness_level == "WEAK"


def test_decision_robustness_level_weak():

    from atlas.models.analysis_result import AnalysisResult

    class FakeWeightEngine:

        def calculate(self):
            return {
                "Technical Analyst": 0.40,
                "News Analyst": 0.30,
                "Company Analyst": 0.30,
            }

    results = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Technical Analyst",
            action=Action.BUY,
            confidence=60.0,
            evidence=40.0,
            reasoning=["Weak BUY."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="News Analyst",
            action=Action.SELL,
            confidence=60.0,
            evidence=40.0,
            reasoning=["Negative news."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Company Analyst",
            action=Action.HOLD,
            confidence=60.0,
            evidence=40.0,
            reasoning=["Uncertain."],
        ),
    ]

    engine = DecisionEngine()
    engine.agent_weight_engine = FakeWeightEngine()

    decision = engine.evaluate(results)

    assert decision.robustness < 60.0
    assert decision.robustness_level == "WEAK"

def test_realistic_unanimous_buy_is_strong():

    from atlas.models.analysis_result import AnalysisResult

    results = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Technical Analyst",
            action=Action.BUY,
            confidence=92.0,
            evidence=90.0,
            reasoning=["Strong bullish technical structure."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="News Analyst",
            action=Action.BUY,
            confidence=88.0,
            evidence=85.0,
            reasoning=["Positive market news."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Company Analyst",
            action=Action.BUY,
            confidence=86.0,
            evidence=82.0,
            reasoning=["Positive fundamental conditions."],
        ),
    ]

    decision = DecisionEngine().evaluate(results)

    assert decision.action == Action.BUY
    assert decision.dominant_action == Action.BUY
    assert decision.robustness_level == "STRONG"
    assert decision.robustness >= 80.0


def test_realistic_unanimous_sell_is_strong():

    from atlas.models.analysis_result import AnalysisResult

    results = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Technical Analyst",
            action=Action.SELL,
            confidence=92.0,
            evidence=85.0,
            reasoning=["Strong bearish structure."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="News Analyst",
            action=Action.SELL,
            confidence=90.0,
            evidence=82.0,
            reasoning=["Negative market news."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Company Analyst",
            action=Action.SELL,
            confidence=88.0,
            evidence=80.0,
            reasoning=["Negative fundamental conditions."],
        ),
    ]

    decision = DecisionEngine().evaluate(results)

    assert decision.action == Action.SELL
    assert decision.dominant_action == Action.SELL
    assert decision.robustness_level == "STRONG"


def test_realistic_buy_hold_becomes_hold_when_conflicted():

    from atlas.models.analysis_result import AnalysisResult

    results = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Technical Analyst",
            action=Action.BUY,
            confidence=90.0,
            evidence=85.0,
            reasoning=["Bullish technical setup."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="News Analyst",
            action=Action.HOLD,
            confidence=70.0,
            evidence=60.0,
            reasoning=["News remains uncertain."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Company Analyst",
            action=Action.HOLD,
            confidence=68.0,
            evidence=58.0,
            reasoning=["Fundamentals are neutral."],
        ),
    ]

    decision = DecisionEngine().evaluate(results)

    assert decision.action == Action.HOLD
    assert decision.opposing_analysts
    assert decision.robustness_level in {
        "WEAK",
        "MODERATE",
    }


def test_realistic_buy_sell_conflict_is_safe_hold():

    from atlas.models.analysis_result import AnalysisResult

    results = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Technical Analyst",
            action=Action.BUY,
            confidence=90.0,
            evidence=90.0,
            reasoning=["Strong bullish momentum."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="News Analyst",
            action=Action.SELL,
            confidence=90.0,
            evidence=85.0,
            reasoning=["Major negative news risk."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Company Analyst",
            action=Action.HOLD,
            confidence=70.0,
            evidence=55.0,
            reasoning=["Fundamentals are uncertain."],
        ),
    ]

    decision = DecisionEngine().evaluate(results)

    assert decision.action == Action.HOLD
    assert decision.adaptive_override is False
    assert decision.opposing_analysts


def test_realistic_low_evidence_does_not_create_strong_decision():

    from atlas.models.analysis_result import AnalysisResult

    results = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Technical Analyst",
            action=Action.BUY,
            confidence=55.0,
            evidence=40.0,
            reasoning=["Weak bullish signal."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="News Analyst",
            action=Action.BUY,
            confidence=52.0,
            evidence=35.0,
            reasoning=["Limited positive news."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Company Analyst",
            action=Action.BUY,
            confidence=50.0,
            evidence=30.0,
            reasoning=["Limited fundamental evidence."],
        ),
    ]

    decision = DecisionEngine().evaluate(results)

    assert decision.action == Action.BUY
    assert decision.robustness_level == "WEAK"
    assert decision.robustness < 60.0



def test_decision_preserves_technical_volume_confirmation():

    from atlas.models.analysis_result import AnalysisResult

    technical = AnalysisResult(
        symbol="BTC-USD",
        analyst="Technical Analyst",
        action=Action.BUY,
        confidence=88.0,
        evidence=85.0,
        reasoning=[
            "Price is above MA20.",
            "MA20 is above MA50.",
            "Volume level: STRONG (2.00x average volume).",
            "BUY signal has strong volume confirmation.",
        ],
    )

    news = AnalysisResult(
        symbol="BTC-USD",
        analyst="News Analyst",
        action=Action.BUY,
        confidence=80.0,
        evidence=80.0,
        reasoning=["Positive market news."],
    )

    company = AnalysisResult(
        symbol="BTC-USD",
        analyst="Company Analyst",
        action=Action.BUY,
        confidence=80.0,
        evidence=80.0,
        reasoning=["Positive fundamentals."],
    )

    decision = DecisionEngine().evaluate(
        [technical, news, company]
    )

    reasoning = " ".join(decision.reasoning)

    assert "Volume level: STRONG" in reasoning
    assert "2.00x" in reasoning
    assert "strong volume confirmation" in reasoning.lower()


def test_decision_preserves_low_volume_confirmation():

    from atlas.models.analysis_result import AnalysisResult

    technical = AnalysisResult(
        symbol="BTC-USD",
        analyst="Technical Analyst",
        action=Action.BUY,
        confidence=88.0,
        evidence=85.0,
        reasoning=[
            "Price is above MA20.",
            "MA20 is above MA50.",
            "Volume level: WEAK (0.50x average volume).",
            "BUY signal has weak volume confirmation.",
        ],
    )

    news = AnalysisResult(
        symbol="BTC-USD",
        analyst="News Analyst",
        action=Action.BUY,
        confidence=80.0,
        evidence=80.0,
        reasoning=["Positive market news."],
    )

    company = AnalysisResult(
        symbol="BTC-USD",
        analyst="Company Analyst",
        action=Action.BUY,
        confidence=80.0,
        evidence=80.0,
        reasoning=["Positive fundamentals."],
    )

    decision = DecisionEngine().evaluate(
        [technical, news, company]
    )

    reasoning = " ".join(decision.reasoning)

    assert "Volume level: WEAK" in reasoning
    assert "0.50x" in reasoning
    assert "weak volume confirmation" in reasoning.lower()



def test_decision_engine_blocks_repeated_buy_until_accumulation_drop():
    from atlas.models.analysis_result import AnalysisResult
    from atlas.algorithms.position_exit import PositionExitEngine

    result = AnalysisResult(
        symbol="BTC-USD",
        analyst="Technical Analyst",
        action=Action.BUY,
        confidence=100.0,
        evidence=100.0,
        reasoning=["Strong BUY."],
    )

    engine = DecisionEngine(
        position_exit_engine=PositionExitEngine(accumulation_drop_pct=2.0)
    )

    first = engine.evaluate(
        [result],
        price=20000.0,
        current_position=0.0,
    )
    repeated = engine.evaluate(
        [result],
        price=19900.0,
        current_position=0.5,
        last_buy_price=20000.0,
        average_price=20000.0,
    )
    accumulated = engine.evaluate(
        [result],
        price=19600.0,
        current_position=0.5,
        last_buy_price=20000.0,
        average_price=20000.0,
    )

    assert first.action is Action.BUY
    assert repeated.action is Action.HOLD
    assert accumulated.action is Action.BUY



def test_decision_engine_preserves_weak_buy_reduction_quantity():
    from atlas.algorithms.position_exit import PositionExitEngine
    from atlas.models.analysis_result import AnalysisResult
    from atlas.risk.manager import RiskManager

    result = AnalysisResult(
        symbol="BTC-USD",
        analyst="Technical Analyst",
        action=Action.BUY,
        confidence=40.0,
        evidence=40.0,
        reasoning=["Weak BUY with an existing position."],
    )

    engine = DecisionEngine(
        risk_manager=RiskManager(),
        position_exit_engine=PositionExitEngine(),
    )

    decision = engine.evaluate(
        [result],
        price=100.0,
        equity=10_000.0,
        current_position=0.8,
        last_buy_price=100.0,
        average_price=100.0,
    )

    assert decision.action is Action.SELL
    assert decision.risk_assessment is not None
    assert decision.risk_assessment.position_size == pytest.approx(0.2)


def test_decision_engine_applies_position_exit_engine_to_sell():
    from atlas.algorithms.position_exit import PositionExitEngine
    from atlas.models.analysis_result import AnalysisResult

    result = AnalysisResult(
        symbol="BTC-USD",
        analyst="Technical Analyst",
        action=Action.SELL,
        confidence=50.0,
        evidence=50.0,
        reasoning=["Moderate SELL."],
    )

    engine = DecisionEngine(
        position_exit_engine=PositionExitEngine(
            entry_confidence=0.65,
            reduce_confidence=0.45,
            exit_confidence=0.30,
        )
    )

    decision = engine.evaluate(
        [result],
        price=100.0,
        current_position=1.0,
        last_buy_price=100.0,
        average_price=100.0,
    )

    assert decision.action is Action.SELL



def test_decision_engine_preserves_partial_reduce_quantity():
    from atlas.algorithms.position_exit import PositionExitEngine
    from atlas.models.analysis_result import AnalysisResult
    from atlas.risk.manager import RiskManager

    result = AnalysisResult(
        symbol="BTC-USD",
        analyst="Technical Analyst",
        action=Action.SELL,
        confidence=50.0,
        evidence=50.0,
        reasoning=["Moderate SELL."],
    )

    engine = DecisionEngine(
        risk_manager=RiskManager(),
        position_exit_engine=PositionExitEngine(
            entry_confidence=0.65,
            reduce_confidence=0.45,
            exit_confidence=0.30,
        ),
    )

    decision = engine.evaluate(
        [result],
        price=100.0,
        equity=10_000.0,
        current_position=1.0,
        last_buy_price=100.0,
        average_price=100.0,
    )

    assert decision.action is Action.SELL
    assert decision.risk_assessment is not None
    assert decision.risk_assessment.position_size == pytest.approx(0.5)


def test_decision_engine_preserves_strong_sell_exit():
    from atlas.algorithms.position_exit import PositionExitEngine
    from atlas.models.analysis_result import AnalysisResult

    result = AnalysisResult(
        symbol="BTC-USD",
        analyst="Technical Analyst",
        action=Action.SELL,
        confidence=90.0,
        evidence=90.0,
        reasoning=["Strong SELL."],
    )

    engine = DecisionEngine(
        position_exit_engine=PositionExitEngine()
    )

    decision = engine.evaluate(
        [result],
        price=90.0,
        current_position=1.0,
        last_buy_price=100.0,
        average_price=100.0,
    )

    assert decision.action is Action.SELL


def test_decision_engine_protective_exit_overrides_buy_signal():
    from atlas.algorithms.position_exit import PositionExitEngine
    from atlas.models.analysis_result import AnalysisResult

    result = AnalysisResult(
        symbol="BTC-USD",
        analyst="Technical Analyst",
        action=Action.BUY,
        confidence=90.0,
        evidence=90.0,
        reasoning=["Strong BUY despite price decline."],
    )

    engine = DecisionEngine(
        position_exit_engine=PositionExitEngine(stop_loss=0.08)
    )

    decision = engine.evaluate(
        [result],
        price=90.0,
        current_position=1.0,
        last_buy_price=100.0,
        average_price=100.0,
    )

    assert decision.action is Action.SELL



def test_decision_engine_protective_exit_overrides_hold_signal():
    from atlas.algorithms.position_exit import PositionExitEngine
    from atlas.models.analysis_result import AnalysisResult

    result = AnalysisResult(
        symbol="BTC-USD",
        analyst="Technical Analyst",
        action=Action.HOLD,
        confidence=90.0,
        evidence=90.0,
        reasoning=["No directional change."],
    )

    engine = DecisionEngine(
        position_exit_engine=PositionExitEngine(stop_loss=0.08)
    )

    decision = engine.evaluate(
        [result],
        price=90.0,
        current_position=1.0,
        last_buy_price=100.0,
        average_price=100.0,
    )

    assert decision.action is Action.SELL



def test_decision_engine_uses_position_peak_for_trailing_stop():
    from atlas.algorithms.position_exit import PositionExitEngine
    from atlas.models.analysis_result import AnalysisResult

    result = AnalysisResult(
        symbol="BTC-USD",
        analyst="Technical Analyst",
        action=Action.HOLD,
        confidence=90.0,
        evidence=90.0,
        reasoning=["No directional change."],
    )

    engine = DecisionEngine(
        position_exit_engine=PositionExitEngine(
            stop_loss=0.20,
            trailing_stop=0.08,
        )
    )

    decision = engine.evaluate(
        [result],
        price=110.0,
        current_position=1.0,
        last_buy_price=100.0,
        average_price=100.0,
        peak_price=120.0,
    )

    assert decision.action is Action.SELL



def test_decision_engine_uses_real_directional_history_for_learned_support():
    from atlas.models.analysis_result import AnalysisResult
    from atlas.trading.agent_performance_tracker import AgentPerformanceTracker
    from atlas.trading.agent_weight_engine import AgentWeightEngine

    performance = AgentPerformanceTracker()

    for analyst, buy_correct, sell_correct in (
        ("Technical Analyst", 18, 6),
        ("Company Analyst", 10, 10),
        ("News Analyst", 6, 18),
    ):
        for index in range(20):
            performance.record(
                analyst=analyst,
                correct=index < buy_correct,
                action="BUY",
            )
            performance.record(
                analyst=analyst,
                correct=index < sell_correct,
                action="SELL",
            )

    engine = DecisionEngine()
    engine.agent_weight_engine = AgentWeightEngine(
        performance
    )

    decision = engine.evaluate(
        [
            AnalysisResult(
                symbol="BTC-USD",
                analyst="Technical Analyst",
                action=Action.HOLD,
                confidence=80.0,
                evidence=80.0,
                reasoning=["Neutral current signal."],
            ),
            AnalysisResult(
                symbol="BTC-USD",
                analyst="Company Analyst",
                action=Action.HOLD,
                confidence=80.0,
                evidence=80.0,
                reasoning=["Neutral current signal."],
            ),
            AnalysisResult(
                symbol="BTC-USD",
                analyst="News Analyst",
                action=Action.HOLD,
                confidence=80.0,
                evidence=80.0,
                reasoning=["Neutral current signal."],
            ),
        ]
    )

    assert decision.action == Action.HOLD
    assert decision.action_support_analyst == "Technical Analyst"
    assert decision.action_support_action == Action.BUY
    assert decision.action_support_weight > 0.0
    assert decision.decision_margin == 100.0
    assert any(
        "Learned support: Technical Analyst supports BUY"
        in reason
        for reason in decision.reasoning
    )

def test_decision_engine_holds_known_buy_without_positive_net_return():
    from types import SimpleNamespace

    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult
    from atlas.trading.trading_cost_model import TradingCostModel

    class StubExpectedReturnService:
        def estimate_with_status(self, symbol, action):
            assert symbol == "BTC-USD"
            assert action is Action.BUY
            return SimpleNamespace(value=0.0024, ready=True)

    engine = DecisionEngine(
        expected_return_service=StubExpectedReturnService(),
        trading_cost_model=TradingCostModel(),
    )

    decision = engine.evaluate(
        [
            AnalysisResult(
                analyst="test",
                symbol="BTC-USD",
                action=Action.BUY,
                confidence=90.0,
                evidence=90.0,
                reasoning=["Strong BUY evidence."],
            )
        ]
    )

    assert decision.action is Action.HOLD
    assert decision.expected_return == 0.0024
    assert decision.expected_return_ready is True
    assert any(
        "trading costs" in reason.lower()
        for reason in decision.reasoning
    )


def test_decision_engine_preserves_buy_when_expected_return_is_unknown():
    from types import SimpleNamespace

    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult
    from atlas.trading.trading_cost_model import TradingCostModel

    class StubExpectedReturnService:
        def estimate_with_status(self, symbol, action):
            assert symbol == "BTC-USD"
            assert action is Action.BUY
            return SimpleNamespace(value=0.0, ready=False)

    engine = DecisionEngine(
        expected_return_service=StubExpectedReturnService(),
        trading_cost_model=TradingCostModel(),
    )

    decision = engine.evaluate(
        [
            AnalysisResult(
                analyst="test",
                symbol="BTC-USD",
                action=Action.BUY,
                confidence=90.0,
                evidence=90.0,
                reasoning=["Strong BUY evidence."],
            )
        ]
    )

    assert decision.action is Action.BUY
    assert decision.expected_return == 0.0
    assert decision.expected_return_ready is False

