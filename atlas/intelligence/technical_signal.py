"""Pure technical signal engine for ATLAS market snapshots."""

from dataclasses import dataclass

from atlas.adapters.market_data import MarketData
from atlas.models.action import Action


@dataclass(frozen=True)
class TechnicalSignal:
    """Normalized technical signal with explainable evidence."""

    symbol: str
    action: Action
    confidence: int
    reasons: tuple[str, ...]


def generate_technical_signal(data: MarketData) -> TechnicalSignal:
    """Translate a normalized market snapshot into a deterministic signal.

    Moving averages determine direction. Volume only adjusts confidence and
    never creates a BUY or SELL signal by itself.
    """
    if data.price > data.ma20 > data.ma50:
        action = Action.BUY
        confidence = 70
        reasons = ["price_above_ma20", "ma20_above_ma50"]
        volume_supports = data.volume_ratio >= 1.5
    elif data.price < data.ma20 < data.ma50:
        action = Action.SELL
        confidence = 70
        reasons = ["price_below_ma20", "ma20_below_ma50"]
        volume_supports = data.volume_ratio >= 1.5
    else:
        action = Action.HOLD
        confidence = 55
        reasons = ["mixed_market_trend"]
        volume_supports = False

    if data.volume_ratio >= 1.5:
        reasons.append(f"volume_{data.volume_ratio:.2f}x_average")
        confidence += 8 if volume_supports else 0
    elif data.volume_ratio < 0.75:
        reasons.append(f"low_volume_{data.volume_ratio:.2f}x_average")
        confidence -= 5

    confidence = max(0, min(100, confidence))

    return TechnicalSignal(
        symbol=data.symbol,
        action=action,
        confidence=confidence,
        reasons=tuple(reasons),
    )
