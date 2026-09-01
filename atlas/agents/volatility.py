"""ATLAS volatility intelligence agent."""

from __future__ import annotations

from atlas.agents.base import AgentObservation


class VolatilityAgent:
    """Measures recent realized price volatility."""

    name = "volatility"
    category = "risk"

    def observe(
        self,
        symbol: str,
        market_data: dict,
    ) -> AgentObservation:
        candles = market_data.get("candles", [])

        def candle_value(candle, field, default=None):
            if isinstance(candle, dict):
                return candle.get(field, default)
            return getattr(candle, field, default)

        if len(candles) < 8:
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

        returns: list[float] = []

        for previous, current in zip(
            candles[-8:-1],
            candles[-7:],
        ):
            previous_close = float(candle_value(previous, "close"))
            current_close = float(candle_value(current, "close"))

            if previous_close > 0.0:
                returns.append(
                    (current_close - previous_close)
                    / previous_close
                )

        if not returns:
            volatility = 0.0
        else:
            mean = sum(returns) / len(returns)
            variance = sum(
                (value - mean) ** 2
                for value in returns
            ) / len(returns)
            volatility = variance ** 0.5

        normalized = min(1.0, volatility * 20.0)

        if normalized > 0.60:
            direction = "high_volatility"
        elif normalized > 0.25:
            direction = "elevated_volatility"
        else:
            direction = "low_volatility"

        return AgentObservation(
            agent=self.name,
            symbol=symbol,
            timestamp=candle_value(candles[-1], "timestamp"),
            category=self.category,
            score=0.0,
            confidence=min(
                1.0,
                0.40 + normalized * 0.60,
            ),
            direction=direction,
            source="market_candles",
            features={
                "realized_volatility": volatility,
                "normalized_volatility": normalized,
            },
            evidence=[
                "seven-period realized return volatility",
            ],
        )
