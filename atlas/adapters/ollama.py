"""
Ollama Adapter

Local AI adapter for ATLAS using Ollama.
Default model: qwen3:4b
"""

import json
import os

import requests


class OllamaAdapter:
    """Interface to a local Ollama model."""

    DEFAULT_BASE_URL = "http://localhost:11434"
    DEFAULT_MODEL = "qwen3:4b"

    def __init__(
        self,
        language="en",
        model=None,
        base_url=None,
    ):
        self.language = (
            language if language in ("no", "en") else "en"
        )

        self.model = (
            model
            or os.getenv(
                "OLLAMA_MODEL",
                self.DEFAULT_MODEL,
            )
        )

        self.base_url = (
            base_url
            or os.getenv(
                "OLLAMA_BASE_URL",
                self.DEFAULT_BASE_URL,
            )
        ).rstrip("/")

    def analyze_news(
        self,
        symbol: str,
        articles: list,
    ) -> dict:
        """Analyze financial news using local Ollama."""

        if not articles:
            return {
                "symbol": symbol,
                "relevance": 0,
                "sentiment": "NEUTRAL",
                "impact": "LOW",
                "time_horizon": "SHORT",
                "action": "HOLD",
                "confidence": 0,
                "reason": "No relevant news available.",
            }

        news_text = []

        for article in articles[:10]:
            if isinstance(article, dict):
                title = article.get("title", "")
                summary = article.get("summary", "")
                source = article.get("source", "")
            else:
                title = getattr(article, "title", "")
                summary = getattr(article, "summary", "")
                source = getattr(article, "source", "")

            news_text.append(
                f"""
SOURCE: {source}
TITLE: {title}
SUMMARY: {summary}
"""
            )

        prompt = f"""
You are the financial News Intelligence analyst
for an algorithmic trading system called ATLAS.

Analyze the following recent news for:

SYMBOL: {symbol}

Your job is NOT to blindly recommend a trade.

Evaluate:

1. How relevant the news is to the specific asset.
2. Overall sentiment.
3. Potential market impact.
4. Expected time horizon.
5. Whether the news supports BUY, HOLD or SELL.
6. Confidence in the assessment.

Important rules:

- Ignore political/world news unless it has a
  meaningful connection to the asset.
- Do not treat the presence of a single word such
  as "growth", "loss", "surge" or "risk" as enough
  to determine sentiment.
- Consider the meaning of the entire headline and
  summary.
- Distinguish direct company/asset news from
  general market news.
- If evidence is mixed, use HOLD.
- Never invent facts that are not present in the
  supplied news.
- Confidence must reflect the quality and consistency
  of the evidence.

LANGUAGE RULE:

The selected response language is:
{self.language}

If the language is "no":
- Write the "reason" field in Norwegian.
- Keep all JSON field names and allowed enum values in English.

If the language is "en":
- Write the "reason" field in English.
- Keep all JSON field names and allowed enum values in English.

Return ONLY valid JSON with these fields:

{{
  "symbol": "{symbol}",
  "relevance": 0,
  "sentiment": "POSITIVE",
  "impact": "HIGH",
  "time_horizon": "SHORT",
  "action": "BUY",
  "confidence": 0,
  "reason": "short explanation"
}}

Allowed values:

sentiment:
POSITIVE, NEGATIVE, MIXED, NEUTRAL

impact:
HIGH, MEDIUM, LOW

time_horizon:
SHORT, MEDIUM, LONG

action:
BUY, HOLD, SELL

relevance:
0-100

confidence:
0-100

NEWS:

{"".join(news_text)}
"""

        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
            },
            timeout=120,
        )

        response.raise_for_status()

        data = response.json()

        output = data.get("response", "")

        # Qwen3 may place the generated JSON in the
        # thinking field when structured JSON output
        # is requested.
        if not output:
            output = data.get("thinking", "")

        if not output:
            raise ValueError(
                "Ollama returned an empty response."
            )

        return json.loads(output)
