from unittest.mock import patch

from atlas.adapters.finnhub_intelligence import (
    FinnhubIntelligenceAdapter,
)


def test_finnhub_returns_empty_without_api_key():

    with patch.dict(
        "os.environ",
        {},
        clear=True,
    ):
        adapter = FinnhubIntelligenceAdapter()

    assert adapter.search("NVDA") == []


def test_finnhub_parses_company_news():

    response_data = [
        {
            "headline": "NVIDIA outlook remains strong",
            "summary": "AI demand continues to support growth.",
            "url": "https://example.com/nvda",
            "datetime": 1780000000,
        }
    ]

    with patch.dict(
        "os.environ",
        {"FINNHUB_API_KEY": "test-key"},
        clear=True,
    ):
        adapter = FinnhubIntelligenceAdapter()

    with patch(
        "atlas.adapters.finnhub_intelligence.requests.get"
    ) as mock_get:

        mock_get.return_value.json.return_value = response_data
        mock_get.return_value.raise_for_status.return_value = None

        results = adapter.search("NVDA")

    assert len(results) == 1
    assert results[0]["source"] == "Finnhub"
    assert results[0]["title"] == (
        "NVIDIA outlook remains strong"
    )
    assert results[0]["sentiment"] == "neutral"
    assert results[0]["url"] == (
        "https://example.com/nvda"
    )
