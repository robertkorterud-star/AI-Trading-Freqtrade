
from unittest.mock import patch

from atlas.adapters.youtube_transcript import (
    YouTubeTranscriptAdapter,
)


def test_transcript_adapter_returns_transcript():

    adapter = YouTubeTranscriptAdapter()

    with patch(
        "atlas.adapters.youtube_transcript.YouTubeTranscriptApi"
    ) as mock_api:

        mock_api.return_value.fetch.return_value = [
            type("Snippet", (), {"text": "RSI falls below 30."})(),
            type(
                "Snippet",
                (),
                {"text": "Buy when RSI crosses back above 30."},
            )(),
            type(
                "Snippet",
                (),
                {"text": "Take profit at RSI 60."},
            )(),
        ]

        result = adapter.get("abc123")

    assert result == (
        "RSI falls below 30. "
        "Buy when RSI crosses back above 30. "
        "Take profit at RSI 60."
    )


def test_transcript_adapter_returns_empty_when_unavailable():

    adapter = YouTubeTranscriptAdapter()

    with patch(
        "atlas.adapters.youtube_transcript.YouTubeTranscriptApi"
    ) as mock_api:

        mock_api.get_transcript.side_effect = Exception(
            "Transcript unavailable"
        )

        result = adapter.get("abc123")

    assert result == ""
