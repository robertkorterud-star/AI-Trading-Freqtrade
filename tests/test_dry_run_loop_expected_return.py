from datetime import datetime

from atlas.models.action import Action
from atlas.trading.dry_run_loop import DryRunLoop
from atlas.trading.dry_run_trader import DryRunTrader
from atlas.trading.expected_return_model import ExpectedReturnModel
from atlas.trading.expected_return_service import ExpectedReturnService
from atlas.trading.historical_return_provider import HistoricalReturnProvider
from atlas.trading.market_data import Candle, MarketSnapshot
from atlas.trading.paper_portfolio import PaperPortfolio
from atlas.trading.prediction_record import PredictionRecord
from atlas.trading.trade_journal import TradeJournal


class BullishAgent:
    name = "bullish"

    def analyze(self, snapshot):
        from atlas.agents.base import AgentObservation

        return AgentObservation(
            agent=self.name,
            symbol=snapshot.symbol,
            score=0.90,
            confidence=0.90,
            direction="bullish",
            reason="strong bullish test signal",
        )


class FakePredictionRepository:
    def __init__(self, returns):
        self.predictions = [
            PredictionRecord(
                symbol="BTC-USD",
                action="BUY",
                confidence=0.90,
                evidence=0.90,
                price_usd=100.0,
                timestamp=datetime(2026, 1, index + 1),
                evaluated=True,
                correct=True,
                evaluated_price_usd=100.0 * (1.0 + value),
                price_change_percent=value * 100.0,
            )
            for index, value in enumerate(returns)
        ]

    def get_evaluated(self):
        return self.predictions


def expected_return_service(historical_return):
    repository = FakePredictionRepository(
        [historical_return] * 10
    )
    provider = HistoricalReturnProvider(repository)
    model = ExpectedReturnModel(
        min_samples=10,
        haircut=0.5,
    )
    return ExpectedReturnService(
        provider=provider,
        model=model,
    )


def snapshot():
    candles = [
        Candle(
            timestamp=i,
            open=100 + (i - 1) * 0.15,
            high=101 + (i - 1) * 0.15,
            low=99 + (i - 1) * 0.15,
            close=100 + (i - 1) * 0.15,
            volume=1000 + i * 100,
        )
        for i in range(1, 23)
    ]
    candles.append(
        Candle(
            timestamp=23,
            open=103,
            high=105,
            low=102,
            close=104,
            volume=3300,
        )
    )
    return MarketSnapshot.from_candles("BTC-USD", candles)


def process_without_market_regime(loop, market_snapshot):
    """Exercise expected-return behavior independently of the 4h trend gate."""
    original_decide = loop.orchestrator.decide

    def decide_without_regime(*args, **kwargs):
        kwargs["market_regime"] = None
        return original_decide(*args, **kwargs)

    loop.orchestrator.decide = decide_without_regime
    return loop.process(market_snapshot)


def paper_trader():
    return DryRunTrader(
        portfolio=PaperPortfolio(
            initial_cash=100_000.0,
            fee_rate=0.001,
        ),
        journal=TradeJournal(),
        max_position_value=10_000.0,
    )


def test_expected_return_flows_from_history_to_paper_execution():
    loop = DryRunLoop(
        agents=[BullishAgent()],
        expected_return_service=expected_return_service(0.01),
        trader=paper_trader(),
    )

    result = process_without_market_regime(loop, snapshot())

    # 1.0% historical mean * 50% haircut = 0.5% expected gross return.
    assert result.decision.action.value == "buy"
    assert result.expected_return == 0.005
    assert result.execution.executed is True
    assert result.execution.action.value == "enter"
    assert result.execution.quantity > 0.0
    assert "BTC-USD" in loop.trader.portfolio.positions


def test_expected_return_below_trading_cost_blocks_paper_entry():
    loop = DryRunLoop(
        agents=[BullishAgent()],
        expected_return_service=expected_return_service(0.004),
        trader=paper_trader(),
    )

    result = process_without_market_regime(loop, snapshot())

    # 0.4% historical mean * 50% haircut = 0.2%,
    # below the default 0.24% round-trip direct trading cost.
    assert result.decision.action.value == "buy"
    assert result.expected_return == 0.002
    assert result.execution.executed is False
    assert result.execution.action.value == "hold"
    assert result.execution.quantity == 0.0
    assert "Trading cost blocked" in result.execution.reason
    assert "BTC-USD" not in loop.trader.portfolio.positions


def test_expected_return_remains_optional_without_service():
    trader = paper_trader()

    loop = DryRunLoop(
        agents=[BullishAgent()],
        trader=trader,
    )

    result = process_without_market_regime(loop, snapshot())

    assert result.expected_return is None
    assert result.execution.executed is True
    assert "BTC-USD" in trader.portfolio.positions
