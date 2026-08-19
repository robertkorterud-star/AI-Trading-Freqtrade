from unittest.mock import patch

from atlas.adapters.ollama import OllamaAdapter


def test_ollama_adapter_defaults_to_qwen3_4b():
    adapter = OllamaAdapter()

    assert adapter.model == "qwen3:4b"
    assert adapter.base_url == "http://localhost:11434"


def test_ollama_adapter_accepts_language():
    assert OllamaAdapter(language="no").language == "no"
    assert OllamaAdapter(language="en").language == "en"
    assert OllamaAdapter(language="invalid").language == "en"


def test_ollama_adapter_returns_empty_news_result():
    adapter = OllamaAdapter(language="no")

    result = adapter.analyze_news(
        "NVDA",
        [],
    )

    assert result == {
        "symbol": "NVDA",
        "relevance": 0,
        "sentiment": "NEUTRAL",
        "impact": "LOW",
        "time_horizon": "SHORT",
        "action": "HOLD",
        "confidence": 0,
        "reason": "No relevant news available.",
    }


def test_ollama_adapter_parses_json_response():
    adapter = OllamaAdapter(
        language="en",
        model="qwen3:4b",
    )

    ollama_response = {
        "response": """
        {
            "symbol": "NVDA",
            "relevance": 90,
            "sentiment": "POSITIVE",
            "impact": "HIGH",
            "time_horizon": "SHORT",
            "action": "BUY",
            "confidence": 85,
            "reason": "Strong positive company news."
        }
        """
    }

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return ollama_response

    articles = [
        {
            "title": "NVIDIA reports strong results",
            "summary": "Revenue exceeded expectations.",
            "source": "Test",
        }
    ]

    with patch(
        "atlas.adapters.ollama.requests.post",
        return_value=FakeResponse(),
    ) as mock_post:
        result = adapter.analyze_news(
            "NVDA",
            articles,
        )

    assert result["symbol"] == "NVDA"
    assert result["relevance"] == 90
    assert result["sentiment"] == "POSITIVE"
    assert result["impact"] == "HIGH"
    assert result["action"] == "BUY"
    assert result["confidence"] == 85

    mock_post.assert_called_once()

    call = mock_post.call_args

    assert call.args[0] == (
        "http://localhost:11434/api/generate"
    )

    payload = call.kwargs["json"]

    assert payload["model"] == "qwen3:4b"
    assert payload["stream"] is False
    assert payload["format"] == "json"


def test_ollama_adapter_supports_article_objects():
    adapter = OllamaAdapter()

    class Article:
        title = "Test headline"
        summary = "Test summary"
        source = "Test source"

    ollama_response = {
        "response": """
        {
            "symbol": "AAPL",
            "relevance": 50,
            "sentiment": "NEUTRAL",
            "impact": "LOW",
            "time_horizon": "MEDIUM",
            "action": "HOLD",
            "confidence": 60,
            "reason": "Mixed evidence."
        }
        """
    }

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return ollama_response

    with patch(
        "atlas.adapters.ollama.requests.post",
        return_value=FakeResponse(),
    ):
        result = adapter.analyze_news(
            "AAPL",
            [Article()],
        )

    assert result["symbol"] == "AAPL"
    assert result["action"] == "HOLD"


def test_ollama_adapter_parses_qwen_thinking_response():
    adapter = OllamaAdapter()

    ollama_response = {
        "response": "",
        "thinking": """
        {
            "symbol": "BTC-USD",
            "relevance": 80,
            "sentiment": "POSITIVE",
            "impact": "HIGH",
            "time_horizon": "SHORT",
            "action": "BUY",
            "confidence": 75,
            "reason": "Positive market evidence."
        }
        """,
    }

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return ollama_response

    articles = [
        {
            "title": "Bitcoin rises",
            "summary": "Bitcoin gained strongly during the session.",
            "source": "ATLAS TEST",
        }
    ]

    with patch(
        "atlas.adapters.ollama.requests.post",
        return_value=FakeResponse(),
    ):
        result = adapter.analyze_news(
            "BTC-USD",
            articles,
        )

    assert result["symbol"] == "BTC-USD"
    assert result["sentiment"] == "POSITIVE"
    assert result["action"] == "BUY"
    assert result["confidence"] == 75
