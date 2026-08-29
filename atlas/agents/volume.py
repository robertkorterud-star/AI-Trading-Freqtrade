"""ATLAS volume intelligence agent."""

from __future__ import annotations

from atlas.agents.base import AgentObservation


class VolumeAgent:
    """Detects unusual volume relative to recent activity."""

    name = "volume"
    category = "volume"

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

        recent = [
            float(candle.get("volume", 0.0))
            for candle in candles[-6:-1]
        ]

        current = float(candles[-1].get("volume", 0.0))
        average = sum(recent) / len(recent)

        if average <= 0.0:
            ratio = 1.0
        else:
            ratio = current / average

        price_change = 0.0
        previous_close = float(candles[-2].get("close", 0.0))
        current_close = float(candles[-1].get("close", 0.0))

        if previous_close > 0.0:
            price_change = (
                current_close - previous_close
            ) / previous_close

        volume_strength = max(
            0.0,
            min(1.0, (ratio - 1.0) / 2.0),
        )

        if volume_strength <= 0.05:
            score = 0.0
        else:
            direction_sign = (
                1.0
                if price_change >= 0.0
                else -1.0
            )
            score = volume_strength * direction_sign

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
            confidence=volume_strength,
            direction=direction,
            source="market_candles",
            features={
                "current_volume": current,
                "average_volume": average,
                "volume_ratio": ratio,
                "price_change": price_change,
            },
            evidence=[
                "current volume compared with five-candle average",
            ],
        )
