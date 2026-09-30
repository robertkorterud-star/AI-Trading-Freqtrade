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



    def discover_candidates(self, research: str = "") -> list[dict]:
        """Discover promising stocks and crypto using local Ollama."""

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

        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string"
                            },
                            "score": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 100
                            },
                            "reason": {
                                "type": "string"
                            },
                            "metadata": {
                                "type": "object"
                            }
                        },
                        "required": [
                            "symbol",
                            "score",
                            "reason",
                            "metadata"
                        ]
                    }
                },
            },
            timeout=120,
        )

        response.raise_for_status()

        data = response.json()
        output = data.get("response", "")

        if not output:
            output = data.get("thinking", "")

        if not output:
            return []

        result = json.loads(output)

        if not isinstance(result, list):
            return []

        return result

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

Return ONLY a JSON object.

The JSON object MUST contain exactly these fields:

- symbol: string
- relevance: number from 0 to 100
- sentiment: POSITIVE, NEGATIVE, MIXED or NEUTRAL
- impact: HIGH, MEDIUM or LOW
- time_horizon: SHORT, MEDIUM or LONG
- action: BUY, HOLD or SELL
- confidence: number from 0 to 100
- reason: a normal text string

IMPORTANT:
- Do not omit any field.
- Do not add extra fields.
- The "reason" field MUST contain normal text.
- Never use ":" as a JSON field name.
- Never output malformed JSON.

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
                "think": False,
                "format": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string"
                        },
                        "relevance": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100
                        },
                        "sentiment": {
                            "type": "string",
                            "enum": [
                                "POSITIVE",
                                "NEGATIVE",
                                "MIXED",
                                "NEUTRAL"
                            ]
                        },
                        "impact": {
                            "type": "string",
                            "enum": [
                                "HIGH",
                                "MEDIUM",
                                "LOW"
                            ]
                        },
                        "time_horizon": {
                            "type": "string",
                            "enum": [
                                "SHORT",
                                "MEDIUM",
                                "LONG"
                            ]
                        },
                        "action": {
                            "type": "string",
                            "enum": [
                                "BUY",
                                "HOLD",
                                "SELL"
                            ]
                        },
                        "confidence": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100
                        },
                        "reason": {
                            "type": "string"
                        }
                    },
                    "required": [
                        "symbol",
                        "relevance",
                        "sentiment",
                        "impact",
                        "time_horizon",
                        "action",
                        "confidence",
                        "reason"
                    ]
                },
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
