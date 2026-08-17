"""
YouTube Transcript Adapter

Fetches available transcripts from YouTube videos.
"""

from youtube_transcript_api import YouTubeTranscriptApi


class YouTubeTranscriptAdapter:
    """Fetches and combines YouTube video transcripts."""

    def get(self, video_id: str) -> str:
        """Return the transcript text for a YouTube video."""

        try:
            transcript = YouTubeTranscriptApi().fetch(
                video_id
            )

            return " ".join(
                snippet.text
                for snippet in transcript
            ).strip()

        except Exception:
            return ""
