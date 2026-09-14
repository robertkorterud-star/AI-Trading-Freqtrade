"""
AI Adapter

Uses OpenAI to analyze financial news.

Includes a short in-memory cache so the same news is not
sent to OpenAI repeatedly on every dashboard refresh.
"""

import hashlib
import json
import os
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class AIAdapter:
    """Interface to the OpenAI API."""

    CACHE_TTL_SECONDS = 600  # 10 minutes

    # Shared cache across AIAdapter instances.
    _cache = {}

    def __init__(self, language="en"):
        self.language = language if language in ("no", "en") else "en"

        self.api_key = os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in .env"
            )

        self.client = OpenAI(
            api_key=self.api_key
        )

        self.model = os.getenv(
            "OPENAI_MODEL",
            "gpt-5.6",
        )

    @classmethod
    def _cache_key(
        cls,
        symbol: str,
        articles: list,
        language: str = "en",
    ) -> str:
        """Create a stable cache key from news and language."""

        language = language if language in ("no", "en") else "en"

        parts = [
            symbol.upper(),
            language,
        ]

        for article in articles[:10]:
            if isinstance(article, dict):
                title = article.get("title", "")
                summary = article.get("summary", "")
                source = article.get("source", "")
            else:
                title = getattr(
                    article,
                    "title",
                    "",
                )
                summary = getattr(
                    article,
                    "summary",
                    "",
                )
                source = getattr(
                    article,
                    "source",
                    "",
                )

            parts.extend(
                [
                    str(source),
                    str(title),
                    str(summary),
                ]
            )

        raw = "\n".join(parts)

        return hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()

    def _get_cached(
        self,
        key: str,
    ):
        """Return cached result if it is still valid."""

        entry = self._cache.get(key)

        if not entry:
            return None

        timestamp, result = entry

        age = time.time() - timestamp

        if age > self.CACHE_TTL_SECONDS:
            self._cache.pop(key, None)
            return None

        print(
            f"AI cache HIT - age {age:.0f}s"
        )

        return result

    def _store_cached(
        self,
        key: str,
        result: dict,
    ):
        """Store an AI result in the cache."""

        self._cache[key] = (
            time.time(),
            result,
        )



    def discover_candidates(self, research: str = "") -> list[dict]:
        """Discover promising stocks and crypto from research context."""

        prompt = f"""
You are the candidate research analyst for an algorithmic
trading system called ATLAS.

Your task is to identify financial assets that deserve deeper
analysis by ATLAS.

You are NOT making a trade decision.

Use only the supplied research context.

Look for:
- stocks with meaningful catalysts or changing fundamentals
- crypto assets with meaningful catalysts or changing sentiment
- unusual market developments worth deeper investigation
- assets where multiple pieces of evidence suggest further research

Rules:
- Prefer specific assets over broad sectors.
- Do not invent symbols or facts.
- Do not return BUY, SELL or HOLD instructions.
- Do not make portfolio decisions.
- Return an empty list when evidence is insufficient.
- Score each candidate from 0 to 100 based on research strength.
- Keep the reason short and evidence-based.
- Return ONLY valid JSON.

Required format:

[
  {{
    "symbol": "NVDA",
    "score": 85,
    "reason": "Short evidence-based explanation",
    "metadata": {{
      "asset_type": "stock",
      "catalysts": []
    }}
  }}
]

RESEARCH CONTEXT:

{research}
""".strip()

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )

        result = json.loads(response.output_text)

        if isinstance(result, dict):
            result = result.get("candidates", [])

        if not isinstance(result, list):
            return []

        return result

    def analyze_news(
        self,
        symbol: str,
        articles: list,
    ) -> dict:
        """Analyze financial news for one symbol."""

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

        cache_key = self._cache_key(
            symbol,
            articles,
            language=self.language,
        )

        cached = self._get_cached(
            cache_key
        )

        if cached is not None:
            return cached

        print(
            f"AI cache MISS - analyzing {symbol}"
        )

        news_text = []

        for article in articles[:10]:

            title = getattr(
                article,
                "title",
                "",
            )

            summary = getattr(
                article,
                "summary",
                "",
            )

            source = getattr(
                article,
                "source",
                "",
            )

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

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )

        result = json.loads(
            response.output_text
        )

        self._store_cached(
            cache_key,
            result,
        )

        print(
            f"AI analysis cached for {symbol}"
        )

        return result
