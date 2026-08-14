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
                    "title": "NVIDIA analysis",
                    "description": "AI demand remains strong.",
                    "publishedAt": "2026-08-14T08:00:00Z",
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
    assert results[0]["title"] == "NVIDIA analysis"
    assert results[0]["sentiment"] == "neutral"
    assert results[0]["url"] == (
        "https://www.youtube.com/watch?v=abc123"
    )
