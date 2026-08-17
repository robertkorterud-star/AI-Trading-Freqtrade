from unittest.mock import patch


from atlas.adapters.news import NewsAdapter


def make_adapter():
    adapter = NewsAdapter.__new__(NewsAdapter)
    adapter.api_key = "test-key"
    return adapter


def test_crypto_news_keeps_only_selected_asset():
    adapter = make_adapter()

    articles = [
        {
            "headline": "Bitcoin surges after institutional demand",
            "summary": "BTC sees strong buying.",
            "source": "Test",
            "url": "https://example.com/btc",
        },
        {
            "headline": "Ethereum rises on ETF demand",
            "summary": "ETH gains strongly.",
            "source": "Test",
            "url": "https://example.com/eth",
        },
        {
            "headline": "Solana rallies as network activity grows",
            "summary": "SOL gains.",
            "source": "Test",
            "url": "https://example.com/sol",
        },
    ]

    with patch(
        "atlas.adapters.news.requests.get"
    ) as mock_get:

        mock_get.return_value.json.return_value = articles
        mock_get.return_value.raise_for_status.return_value = None

        result = adapter._crypto_news("BTC-USD")

    assert len(result) == 1
    assert "Bitcoin" in result[0].title


def test_crypto_news_does_not_fill_with_other_crypto():
    adapter = make_adapter()

    articles = [
        {
            "headline": "Solana rallies strongly",
            "summary": "SOL gains.",
            "source": "Test",
            "url": "https://example.com/sol",
        },
        {
            "headline": "Bitcoin rises",
            "summary": "BTC gains.",
            "source": "Test",
            "url": "https://example.com/btc",
        },
    ]

    with patch(
        "atlas.adapters.news.requests.get"
    ) as mock_get:

        mock_get.return_value.json.return_value = articles
        mock_get.return_value.raise_for_status.return_value = None

        result = adapter._crypto_news("SOL-USD")

    assert len(result) == 1
    assert "Solana" in result[0].title


def test_company_news_filters_irrelevant_companies():
    adapter = make_adapter()

    articles = [
        {
            "headline": "NVIDIA outlook remains strong",
            "summary": "NVDA AI demand continues.",
            "source": "Test",
            "url": "https://example.com/nvda",
        },
        {
            "headline": "Eli Lilly launches new drug",
            "summary": "Pharmaceutical news.",
            "source": "Test",
            "url": "https://example.com/lilly",
        },
        {
            "headline": "IREN expands data center operations",
            "summary": "New infrastructure investment.",
            "source": "Test",
            "url": "https://example.com/iren",
        },
    ]

    with patch(
        "atlas.adapters.news.requests.get"
    ) as mock_get:

        mock_get.return_value.json.return_value = articles
        mock_get.return_value.raise_for_status.return_value = None

        result = adapter._company_news("NVDA")

    assert len(result) == 1
    assert "NVIDIA" in result[0].title
