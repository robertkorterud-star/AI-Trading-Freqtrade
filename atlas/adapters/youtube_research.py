"""
User-provided YouTube research adapter.

Allows ATLAS to accept a YouTube URL as a
manually selected research source.
"""

from urllib.parse import parse_qs, urlparse

from atlas.adapters.youtube_transcript import YouTubeTranscriptAdapter


class YouTubeResearchAdapter:
    """Handles user-recommended YouTube research."""

    def __init__(self, transcript=None) -> None:
        self.transcript = (
            transcript
            if transcript is not None
            else YouTubeTranscriptAdapter()
        )

    @staticmethod
    def extract_video_id(url: str) -> str | None:
        """Extract a YouTube video ID from a URL."""

        try:
            parsed = urlparse(url)
        except ValueError:
            return None

        host = parsed.netloc.lower()
        path = parsed.path

        if host in {
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
        }:
            query = parse_qs(parsed.query)
            video_id = query.get("v")

            if video_id:
                return video_id[0]

            return None

        if host in {
            "youtu.be",
            "www.youtu.be",
        }:
            video_id = path.strip("/")

            if video_id:
                return video_id

        return None

    def research(
        self,
        url: str,
        symbol: str,
    ) -> dict:
        """Create a research item from a user-provided video."""

        video_id = self.extract_video_id(url)

        if not video_id:
            return {
                "source": "YouTube",
                "symbol": symbol,
                "video_id": None,
                "transcript": "",
                "status": "invalid_url",
            }

        transcript = self.transcript.get(video_id)

        if transcript:
            status = "ready"
        else:
            status = "transcript_unavailable"

        return {
            "source": "YouTube",
            "symbol": symbol,
            "video_id": video_id,
            "url": url,
            "transcript": transcript,
            "status": status,
        }
