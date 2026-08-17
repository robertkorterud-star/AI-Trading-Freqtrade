from atlas.adapters.youtube_research import YouTubeResearchAdapter


def test_extracts_youtube_video_id():

    adapter = YouTubeResearchAdapter()

    assert (
        adapter.extract_video_id(
            "https://www.youtube.com/watch?v=abc123"
        )
        == "abc123"
    )


def test_extracts_youtube_short_url():

    adapter = YouTubeResearchAdapter()

    assert (
        adapter.extract_video_id(
            "https://youtu.be/abc123"
        )
        == "abc123"
    )


def test_rejects_invalid_youtube_url():

    adapter = YouTubeResearchAdapter()

    assert (
        adapter.extract_video_id(
            "https://example.com/video"
        )
        is None
    )

def test_research_fetches_transcript():

    class FakeTranscript:

        def get(self, video_id):
            assert video_id == "abc123"

            return (
                "RSI falls below 30. "
                "Buy when RSI crosses back above 30."
            )

    adapter = YouTubeResearchAdapter(
        transcript=FakeTranscript(),
    )

    result = adapter.research(
        "https://www.youtube.com/watch?v=abc123",
        symbol="NVDA",
    )

    assert result["symbol"] == "NVDA"
    assert result["video_id"] == "abc123"
    assert result["source"] == "YouTube"
    assert "RSI falls below 30." in result["transcript"]
    assert result["status"] == "ready"
