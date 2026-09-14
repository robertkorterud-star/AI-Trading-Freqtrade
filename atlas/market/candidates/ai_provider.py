"""AI-powered candidate discovery for ATLAS."""

from __future__ import annotations

import json
from typing import Any

from atlas.market.candidates.source import Candidate


class AICandidateProvider:
    """Use an existing ATLAS AI provider to discover candidates."""

    def __init__(self, ai_provider: Any):
        self.ai_provider = ai_provider

    def discover_candidates(
        self,
        research: str = "",
    ) -> list[Candidate]:
        """Ask the configured AI provider for research candidates."""

        response = self._request(research)

        return self._parse_candidates(response)

    def _request(self, research: str) -> Any:
        """Request structured candidate research from the AI provider."""

        if hasattr(self.ai_provider, "discover_candidates"):
            return self.ai_provider.discover_candidates(research)

        prompt = self._build_prompt(research)

        if hasattr(self.ai_provider, "research"):
            return self.ai_provider.research(prompt)

        if hasattr(self.ai_provider, "generate"):
            return self.ai_provider.generate(prompt)

        raise TypeError(
            "Configured AI provider does not support candidate research."
        )

    @staticmethod
    def _build_prompt(research: str) -> str:
        """Build a fallback candidate-discovery prompt."""

        return f"""
You are the candidate research analyst for ATLAS.

Identify financial assets that deserve deeper analysis.

You are NOT allowed to make a trade decision.

Use only the supplied research context.

Rules:
- Prefer specific assets over broad sectors.
- Do not invent symbols.
- Do not return BUY or SELL instructions.
- Do not claim facts unsupported by the research.
- Return an empty list when evidence is insufficient.
- Return ONLY valid JSON.

Required format:

[
  {{
    "symbol": "NVDA",
    "score": 85,
    "reason": "Short evidence-based explanation",
    "metadata": {{}}
  }}
]

RESEARCH CONTEXT:

{research}
""".strip()

    @staticmethod
    def _parse_candidates(response: Any) -> list[Candidate]:
        """Parse and validate AI candidate output."""

        if isinstance(response, str):
            response = json.loads(response)

        if isinstance(response, dict):
            response = response.get("candidates", [])

        if not isinstance(response, list):
            return []

        candidates = []

        for item in response:
            if not isinstance(item, dict):
                continue

            symbol = str(item.get("symbol", "")).strip().upper()

            if not symbol:
                continue

            try:
                score = float(item.get("score", 0))
            except (TypeError, ValueError):
                score = 0.0

            score = max(0.0, min(100.0, score))

            metadata = item.get("metadata", {})

            if not isinstance(metadata, dict):
                metadata = {}

            candidates.append(
                Candidate(
                    symbol=symbol,
                    source="ai_research",
                    score=score,
                    reason=str(item.get("reason", "")).strip(),
                    metadata=metadata,
                )
            )

        return candidates
