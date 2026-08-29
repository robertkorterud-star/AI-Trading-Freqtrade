"""ATLAS momentum intelligence agent."""

from __future__ import annotations

from atlas.agents.base import AgentObservation


class MomentumAgent:
    """Measures recent price acceleration."""

    name = "momentum"
    category = "technical"

    def observe(
        self,
        symbol: str,
        market_data: dict,
    ) -> AgentObservation:
        candles = market_data.get("candles", [])

        if len(candles) < 6:
            return AgentObservation(
                agent=self.name,
                symbol=symbol,
                timestamp=None,
                category=self.category,
                score=0.0,
                confidence=0.0,
                direction="neutral",
                evidence=["insufficient candle history"],
            )

        closes = [
            float(candle["close"])
            for candle in candles
        ]

        previous = closes[-6]
        current = closes[-1]

        if previous <= 0.0:
            change = 0.0
        else:
            change = (current - previous) / previous

        score = max(-1.0, min(1.0, change * 15.0))

        if score > 0.05:
            direction = "bullish"
        elif score < -0.05:
            direction = "bearish"
        else:
            direction = "neutral"

        return AgentObservation(
            agent=self.name,
            symbol=symbol,
            timestamp=candles[-1].get("timestamp"),
            category=self.category,
            score=score,
            confidence=min(1.0, abs(score)),
            direction=direction,
            source="market_candles",
            features={
                "lookback_return": change,
            },
            evidence=[
                "six-candle price return used as momentum signal",
            ],
        )
