"""Basic price-action intelligence agent."""

from __future__ import annotations

from atlas.agents.base import AgentObservation


class PriceActionAgent:
    """
    Produces a simple normalized price-action observation.

    This is deliberately an observation agent, not a trading strategy.
    """

    name = "price_action"
    category = "technical"

    def observe(
        self,
        symbol: str,
        market_data: dict,
    ) -> AgentObservation:
        candles = market_data.get("candles", [])

        if len(candles) < 2:
            return AgentObservation(
                agent=self.name,
                symbol=symbol,
                timestamp=None,
                category=self.category,
                score=0.0,
                confidence=0.0,
                direction="neutral",
                evidence=["insufficient candle data"],
            )

        previous = float(candles[-2]["close"])
        current = float(candles[-1]["close"])

        if previous <= 0.0:
            score = 0.0
        else:
            change = (current - previous) / previous
            score = max(-1.0, min(1.0, change * 20.0))

        if score > 0.05:
            direction = "bullish"
        elif score < -0.05:
            direction = "bearish"
        else:
            direction = "neutral"

        confidence = min(1.0, abs(score))

        return AgentObservation(
            agent=self.name,
            symbol=symbol,
            timestamp=candles[-1].get("timestamp"),
            category=self.category,
            score=score,
            confidence=confidence,
            direction=direction,
            source="market_candles",
            features={
                "previous_close": previous,
                "current_close": current,
                "return": (
                    (current - previous) / previous
                    if previous > 0.0
                    else 0.0
                ),
            },
            evidence=[
                "latest candle close compared with previous close",
            ],
        )
