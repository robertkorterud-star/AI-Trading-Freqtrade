"""
ATLAS BTC Regime × Strategy Research Runner.

Research-only executable script.

Loads historical BTC OHLC data through the existing
CoinGecko adapter, evaluates the real ATLAS strategies
by market regime, prints strategy recommendations,
and stores the research results in Strategy Memory.

No trading, orders, or DecisionEngine calls are performed.
"""

from datetime import datetime, timedelta, timezone

from atlas.adapters.coingecko import CoinGeckoAdapter
from atlas.core.database_config import DatabaseConfig
from atlas.database.connection import Database
from atlas.database.schema import initialize_database
from atlas.database.strategy_memory_repository import (
    StrategyMemoryRepository,
)
from atlas.trading.coingecko_ohlc import (
    CoinGeckoOHLCProvider,
)
from atlas.trading.regime_strategy_backtest import (
    RegimeStrategyBacktestResearch,
)
from atlas.trading.strategy_memory import (
    StrategyMemory,
)
from atlas.trading.strategy_memory_service import (
    StrategyMemoryService,
)
from atlas.trading.strategy_regime_recommendation import (
    StrategyRegimeRecommender,
)


def build_research_run_id(
    *,
    symbol: str,
    start: datetime,
    end: datetime,
) -> str:
    """Identify one actual historical research period."""
    normalized_symbol = (
        symbol.strip().lower().replace("-", "_")
    )

    return (
        f"{normalized_symbol}-regime-"
        f"{start.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%S')}-"
        f"{end.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
    )


def main() -> None:
    symbol = "BTC-USD"

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=30)

    print()
    print("ATLAS BTC REGIME × STRATEGY RESEARCH")
    print("=====================================")
    print()
    print(f"Symbol:     {symbol}")
    print(f"Start:      {start.isoformat()}")
    print(f"End:        {end.isoformat()}")
    print()

    client = CoinGeckoAdapter(
        timeout=20.0,
        user_agent="ATLAS/1.0",
    )

    provider = CoinGeckoOHLCProvider(
        client=client,
        coin_ids={
            "BTC-USD": "bitcoin",
        },
        vs_currency="usd",
        timeframe="4h",
        source="coingecko",
    )

    print("Loading historical BTC data...")

    data = provider.load(
        symbol=symbol,
        start=start,
        end=end,
    )

    print(f"Candles:    {len(data)}")
    print(f"Timeframe:  {data.timeframe}")
    print(f"Source:     {data.source}")

    if data.start is not None:
        print(
            f"Data start: {data.start.isoformat()}"
        )

    if data.end is not None:
        print(
            f"Data end:   {data.end.isoformat()}"
        )

    print()

    if len(data) < 30:
        raise RuntimeError(
            "Not enough historical BTC candles "
            "for regime strategy research."
        )

    print("Running strategy backtests...")

    backtest = (
        RegimeStrategyBacktestResearch()
        .run(data)
    )

    if data.start is None or data.end is None:
        raise RuntimeError(
            "Historical BTC data must have an actual "
            "start and end timestamp."
        )

    research_run_id = build_research_run_id(
        symbol=symbol,
        start=data.start,
        end=data.end,
    )

    print(
        f"Research run: {research_run_id}"
    )

    database_config = DatabaseConfig()

    database = Database(
        database_config.path
    )

    initialize_database(database)

    memory = StrategyMemory()

    repository = StrategyMemoryRepository(
        database
    )

    memory_service = StrategyMemoryService(
        memory=memory,
        repository=repository,
    )

    memory_service.remember(
        symbol=symbol,
        summary=backtest,
        research_run_id=research_run_id,
    )

    recommender = StrategyRegimeRecommender()

    regimes = sorted(
        {
            result.regime
            for result in backtest.results
        }
    )

    print()
    print("REGIME × STRATEGY RESULTS")
    print("--------------------------")

    for regime in regimes:
        recommendation = recommender.recommend(
            backtest,
            regime,
        )

        historical_candidates = [
            result
            for result in backtest.results
            if result.regime == regime
            and result.trade_count > 0
        ]

        if not historical_candidates:
            continue

        historical_leader = max(
            historical_candidates,
            key=lambda item: (
                item.total_return_percent,
                item.average_trade_return_percent,
                item.trade_count,
                -item.losing_trades,
                item.strategy_name,
            ),
        )

        print()
        print(regime)
        print(
            f"  Historical leader: "
            f"{historical_leader.strategy_name}"
        )
        print(
            f"  Robust winner:     "
            f"{recommendation.recommended_strategy}"
        )
        print(
            f"  Evidence:          "
            f"{recommendation.evidence_strength}"
        )
        print(
            f"  Confidence:        "
            f"{recommendation.confidence:.2f}%"
        )
        print(
            f"  Trades:            "
            f"{recommendation.trade_count}"
        )
        print(
            f"  Win rate:          "
            f"{recommendation.win_rate_percent:.1f}%"
        )
        print(
            f"  Avg trade:         "
            f"{recommendation.average_trade_return_percent:.3f}%"
        )
        print(
            f"  Total return:      "
            f"{recommendation.total_return_percent:.3f}%"
        )

        print("  Evidence:")

        for result in backtest.results:
            if result.regime != regime:
                continue

            print(
                f"    {result.strategy_name:20} "
                f"trades={result.trade_count:4} "
                f"avg={result.average_trade_return_percent:8.3f}% "
                f"total={result.total_return_percent:8.3f}%"
            )

    print()
    print("STRATEGY MEMORY")
    print("---------------")

    print(
        f"Stored records: {len(memory.all())}"
    )

    for record in memory.all():
        print(
            f"  {record.regime:18} "
            f"{record.strategy_name:20} "
            f"trades={record.trade_count:4} "
            f"win_rate={record.win_rate_percent:6.1f}% "
            f"avg={record.average_trade_return_percent:7.3f}% "
            f"total={record.total_return_percent:8.3f}% "
            f"evidence={record.evidence_strength:10} "
            f"robust={record.robust_winner}"
        )

    print()
    print("RESEARCH CONCLUSION")
    print("-------------------")

    if backtest.results:
        print(
            "Historical strategy performance "
            "was evaluated by entry regime."
        )
        print(
            "Research results were stored in "
            "Strategy Memory."
        )
        print(
            "A historical leader is not automatically "
            "a robust winner."
        )
        print(
            "The recommendation is research-only "
            "and does not generate trading decisions."
        )
    else:
        print(
            "No strategy/regime results were produced."
        )

    print()


if __name__ == "__main__":
    main()
