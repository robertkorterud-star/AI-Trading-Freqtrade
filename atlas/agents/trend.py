"""ATLAS trend intelligence agent."""

from __future__ import annotations

from atlas.agents.base import AgentObservation


class TrendAgent:
    """Measures directional trend strength from closing prices."""

    name = "trend"
    category = "technical"

    def observe(
        self,
        symbol: str,
        market_data: dict,
    ) -> AgentObservation:
        candles = market_data.get("candles", [])

        if len(candles) < 10:
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
            if float(candle.get("close", 0.0)) > 0.0
        ]

        if len(closes) < 10:
            return AgentObservation(
                agent=self.name,
                symbol=symbol,
                timestamp=None,
                category=self.category,
                score=0.0,
                confidence=0.0,
                direction="neutral",
                evidence=["insufficient valid closing prices"],
            )

        short = sum(closes[-5:]) / 5.0
        long = sum(closes[-10:]) / 10.0

        score = 0.0 if long <= 0 else (short - long) / long
        score = max(-1.0, min(1.0, score * 20.0))

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
                "short_average": short,
                "long_average": long,
                "trend_spread": score,
            },
            evidence=[
                "five-period average compared with ten-period average",
            ],
        )
