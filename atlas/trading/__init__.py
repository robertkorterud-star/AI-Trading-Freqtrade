"""ATLAS trading package.

Heavy trading-loop modules are imported lazily so lightweight modules such as
market_data can be imported without creating circular dependencies.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from atlas.trading.dry_run_loop import DryRunCycleResult, DryRunLoop
    from atlas.trading.dry_run_trader import DryRunResult, DryRunTrader
    from atlas.trading.market_data import Candle, MarketSnapshot
    from atlas.trading.paper_portfolio import PaperPortfolio
    from atlas.trading.trade_journal import TradeJournal

__all__ = [
    "Candle",
    "DryRunCycleResult",
    "DryRunLoop",
    "DryRunResult",
    "DryRunTrader",
    "MarketSnapshot",
    "PaperPortfolio",
    "TradeJournal",
]


def __getattr__(name: str):
    """Lazily expose trading classes while avoiding import cycles."""
    if name in {"Candle", "MarketSnapshot"}:
        from atlas.trading.market_data import Candle, MarketSnapshot
        return {"Candle": Candle, "MarketSnapshot": MarketSnapshot}[name]

    if name in {"DryRunCycleResult", "DryRunLoop"}:
        from atlas.trading.dry_run_loop import DryRunCycleResult, DryRunLoop
        return {"DryRunCycleResult": DryRunCycleResult, "DryRunLoop": DryRunLoop}[name]

    if name in {"DryRunResult", "DryRunTrader"}:
        from atlas.trading.dry_run_trader import DryRunResult, DryRunTrader
        return {"DryRunResult": DryRunResult, "DryRunTrader": DryRunTrader}[name]

    if name == "PaperPortfolio":
        from atlas.trading.paper_portfolio import PaperPortfolio
        return PaperPortfolio

    if name == "TradeJournal":
        from atlas.trading.trade_journal import TradeJournal
        return TradeJournal

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
