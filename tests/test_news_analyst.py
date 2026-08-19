from atlas.agents.news_analyst import NewsAnalyst
from atlas.models.action import Action


class FakeAIAdapter:

    def analyze_news(self, symbol, articles):
        return {
            "symbol": symbol,
            "relevance": 90,
            "sentiment": "POSITIVE",
            "impact": "HIGH",
            "time_horizon": "SHORT",
            "action": "BUY",
            "confidence": 92,
            "reason": "Strong positive market evidence.",
        }


def test_news_analyst_returns_analysis_result(monkeypatch):

    analyst = NewsAnalyst()

    monkeypatch.setattr(
        "atlas.agents.news_analyst.AIAdapter",
        FakeAIAdapter,
        raising=False,
    )

    # AIAdapter is imported inside analyze_news(), so patch
    # the module where it is actually imported.
    import atlas.adapters.ai

    monkeypatch.setattr(
        atlas.adapters.ai,
        "AIAdapter",
        FakeAIAdapter,
    )

    articles = [
        {
            "title": "Strong positive news",
            "summary": "Excellent market development.",
            "source": "Test News",
        }
    ]

    result = analyst.analyze_news(
        "BTC",
        articles,
    )

    assert result.symbol == "BTC"
    assert result.analyst == "News Analyst"
    assert result.action == Action.BUY
    assert result.confidence == 92
    assert result.evidence == 95
    assert result.reasoning


def test_news_analyst_can_use_ollama_provider(monkeypatch):
    from atlas.core.config import AtlasConfig

    class FakeOllamaAdapter:

        def __init__(self, language="en"):
            self.language = language

        def analyze_news(self, symbol, articles):
            return {
                "symbol": symbol,
                "relevance": 80,
                "sentiment": "POSITIVE",
                "impact": "HIGH",
                "time_horizon": "SHORT",
                "action": "BUY",
                "confidence": 85,
                "reason": "Ollama test analysis.",
            }

    import atlas.adapters.ollama

    monkeypatch.setattr(
        atlas.adapters.ollama,
        "OllamaAdapter",
        FakeOllamaAdapter,
    )

    config = AtlasConfig(
        language="no",
        ai_provider="ollama",
    )

    analyst = NewsAnalyst(
        config=config,
    )

    articles = [
        {
            "title": "Positive test news",
            "summary": "Strong positive development.",
            "source": "ATLAS TEST",
        }
    ]

    result = analyst.analyze_news(
        "NVDA",
        articles,
    )

    assert result.symbol == "NVDA"
    assert result.action == Action.BUY
    assert result.confidence == 85
    assert result.reasoning


def test_news_analyst_selects_ollama_adapter(monkeypatch):
    from atlas.core.config import AtlasConfig

    calls = []

    class FakeOllamaAdapter:

        def __init__(self, language="en"):
            calls.append(("init", language))

        def analyze_news(self, symbol, articles):
            calls.append(("analyze", symbol))

            return {
                "symbol": symbol,
                "relevance": 80,
                "sentiment": "POSITIVE",
                "impact": "HIGH",
                "time_horizon": "SHORT",
                "action": "BUY",
                "confidence": 85,
                "reason": "Ollama provider test.",
            }

    monkeypatch.setattr(
        "atlas.adapters.ollama.OllamaAdapter",
        FakeOllamaAdapter,
    )

    analyst = NewsAnalyst(
        config=AtlasConfig(
            language="no",
            ai_provider="ollama",
        )
    )

    result = analyst.analyze_news(
        "NVDA",
        [
            {
                "title": "Positive test",
                "summary": "Strong development.",
                "source": "ATLAS TEST",
            }
        ],
    )

    assert result.action == Action.BUY
    assert result.confidence == 85
    assert ("init", "no") in calls
    assert ("analyze", "NVDA") in calls


def test_news_analyst_uses_ai_provider_factory(monkeypatch):

    from atlas.core.config import AtlasConfig

    calls = []

    class FakeAIAdapter:

        def __init__(self):
            pass

        def analyze_news(self, symbol, articles):
            calls.append(("analyze", symbol))

            return {
                "symbol": symbol,
                "relevance": 80,
                "sentiment": "POSITIVE",
                "impact": "HIGH",
                "time_horizon": "SHORT",
                "action": "BUY",
                "confidence": 88,
                "reason": "Factory provider test.",
            }

    class FakeFactory:

        @classmethod
        def create(cls, config=None):
            calls.append(
                (
                    "factory",
                    config.ai_provider,
                    config.language,
                )
            )

            return FakeAIAdapter()

    monkeypatch.setattr(
        "atlas.agents.news_analyst.AIProviderFactory",
        FakeFactory,
        raising=False,
    )

    analyst = NewsAnalyst(
        config=AtlasConfig(
            language="no",
            ai_provider="ollama",
        )
    )

    result = analyst.analyze_news(
        "NVDA",
        [
            {
                "title": "Positive test",
                "summary": "Strong development.",
                "source": "ATLAS TEST",
            }
        ],
    )

    assert result.action == Action.BUY
    assert result.confidence == 88
    assert (
        "factory",
        "ollama",
        "no",
    ) in calls
    assert (
        "analyze",
        "NVDA",
    ) in calls
