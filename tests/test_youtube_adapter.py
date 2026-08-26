from unittest.mock import patch

from atlas.adapters.youtube import YouTubeAdapter


def test_youtube_returns_empty_without_api_key():

    with patch.dict(
        "os.environ",
        {},
        clear=True,
    ):
        adapter = YouTubeAdapter()

    assert adapter.search("NVDA") == []


def test_youtube_parses_search_results():

    response_data = {
        "items": [
            {
                "id": {
                    "videoId": "abc123",
                },
                "snippet": {
                    "title": "NVIDIA trading strategy",
                    "description": "RSI and moving averages.",
                    "publishedAt": "2026-08-14T08:00:00Z",
                    "channelTitle": "Professional Trading Channel",
                },
            }
        ]
    }

    with patch.dict(
        "os.environ",
        {"YOUTUBE_API_KEY": "test-key"},
        clear=True,
    ):
        adapter = YouTubeAdapter()

    with patch(
        "atlas.adapters.youtube.requests.get"
    ) as mock_get:

        mock_get.return_value.json.return_value = response_data
        mock_get.return_value.raise_for_status.return_value = None

        results = adapter.search("NVDA")

    assert len(results) == 1
    assert results[0]["source"] == "YouTube"
    assert results[0]["video_id"] == "abc123"
    assert results[0]["title"] == "NVIDIA trading strategy"
    assert results[0]["channel"] == "Professional Trading Channel"
    assert results[0]["sentiment"] == "neutral"


def test_youtube_search_uses_multiple_research_queries():

    response_data = {
        "items": []
    }

    with patch.dict(
        "os.environ",
        {"YOUTUBE_API_KEY": "test-key"},
        clear=True,
    ):
        adapter = YouTubeAdapter()

    with patch(
        "atlas.adapters.youtube.requests.get"
    ) as mock_get:

        mock_get.return_value.json.return_value = response_data
        mock_get.return_value.raise_for_status.return_value = None

        adapter.search("NVDA")

    assert mock_get.call_count >= 3

    queries = [
        call.kwargs["params"]["q"].lower()
        for call in mock_get.call_args_list
    ]

    combined = " ".join(queries)

    assert "trading strategy" in combined
    assert "technical analysis" in combined
    assert "professional trader" in combined


def test_youtube_search_includes_expert_research():

    response_data = {
        "items": []
    }

    with patch.dict(
        "os.environ",
        {"YOUTUBE_API_KEY": "test-key"},
        clear=True,
    ):
        adapter = YouTubeAdapter()

    with patch(
        "atlas.adapters.youtube.requests.get"
    ) as mock_get:

        mock_get.return_value.json.return_value = response_data
        mock_get.return_value.raise_for_status.return_value = None

        adapter.search("NVDA")

    queries = [
        call.kwargs["params"]["q"].lower()
        for call in mock_get.call_args_list
    ]

    combined = " ".join(queries)

    assert "warren buffett" in combined
    assert "michael burry" in combined
    assert "stanley druckenmiller" in combined
    assert len(mock_get.call_args_list) == 3


def test_youtube_marks_symbol_relevance():

    item = {
        "title": "NVDA technical analysis",
        "summary": "NVIDIA is above MA20.",
        "channel": "Trading Channel",
    }

    score = YouTubeAdapter._score_result(
        item,
        "NVDA",
    )

    assert score > 0


def test_youtube_penalizes_unrelated_symbol():

    item = {
        "title": "TSLA momentum strategy",
        "summary": "Tesla technical analysis.",
        "channel": "Trading Channel",
    }

    score = YouTubeAdapter._score_result(
        item,
        "NVDA",
    )

    assert score < 0


def test_youtube_detects_negative_symbol_context():

    item = {
        "title": "The Next AI Trade isn't NVDA",
        "summary": "Three setups beyond semiconductors.",
        "channel": "TraderLion",
    }

    score = YouTubeAdapter._score_result(
        item,
        "NVDA",
    )

    assert score < 10
