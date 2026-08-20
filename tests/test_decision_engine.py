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

    import atlas.adapters.ai

    monkeypatch.setattr(
        atlas.adapters.ai,
        "AIAdapter",
        FakeAIAdapter,
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

