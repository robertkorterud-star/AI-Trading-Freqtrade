from atlas.models.action import Action
from atlas.algorithms.position_exit import PositionExitEngine
from atlas.trading.dry_run_trader import DryRunTrader
from atlas.trading.paper_portfolio import PaperPortfolio
from atlas.trading.trade_journal import TradeJournal


def test_paper_portfolio_buy_and_sell():
    portfolio = PaperPortfolio(
        initial_cash=10_000.0,
        fee_rate=0.0,
    )

    portfolio.buy(
        "BTC-USD",
        price=100.0,
        quantity=10.0,
    )

    assert portfolio.positions["BTC-USD"].quantity == 10.0

    pnl = portfolio.sell(
        "BTC-USD",
        price=120.0,
        quantity=10.0,
    )

    assert pnl == 200.0
    assert portfolio.realized_pnl == 200.0
    assert "BTC-USD" not in portfolio.positions


def test_paper_portfolio_marks_equity():
    portfolio = PaperPortfolio(
        initial_cash=10_000.0,
        fee_rate=0.0,
    )

    portfolio.buy(
        "BTC-USD",
        price=100.0,
        quantity=10.0,
    )

    # Cash after purchase: 9,000
    # Market value of 10 BTC at 110: 1,100
    # Total equity: 10,100
    assert portfolio.equity(
        {"BTC-USD": 110.0}
    ) == 10_100.0


def test_dry_run_enters_position():
    trader = DryRunTrader(
        portfolio=PaperPortfolio(
            initial_cash=100_000.0,
            fee_rate=0.0,
        ),
        journal=TradeJournal(),
        max_position_value=10_000.0,
    )

    result = trader.process_signal(
        "BTC-USD",
        Action.BUY,
        price=100.0,
        confidence=0.95,
        risk_score=0.10,
    )

    assert result.action.value == "enter"
    assert result.quantity > 0.0
    assert "BTC-USD" in trader.portfolio.positions
    assert trader.journal.trade_count == 1


def test_dry_run_strong_sell_exits():
    trader = DryRunTrader(
        portfolio=PaperPortfolio(
            initial_cash=100_000.0,
            fee_rate=0.0,
        ),
        journal=TradeJournal(),
        max_position_value=10_000.0,
    )

    trader.process_signal(
        "BTC-USD",
        Action.BUY,
        price=100.0,
        confidence=0.95,
        risk_score=0.10,
    )

    result = trader.process_signal(
        "BTC-USD",
        Action.SELL,
        price=105.0,
        confidence=0.95,
        risk_score=0.10,
    )

    assert result.action.value == "exit"
    assert "BTC-USD" not in trader.portfolio.positions
    assert trader.portfolio.realized_pnl > 0.0


def test_dry_run_weak_signal_does_not_trade():
    trader = DryRunTrader(
        portfolio=PaperPortfolio(
            initial_cash=100_000.0,
            fee_rate=0.0,
        ),
        journal=TradeJournal(),
        max_position_value=10_000.0,
    )

    result = trader.process_signal(
        "BTC-USD",
        Action.BUY,
        price=100.0,
        confidence=0.20,
        risk_score=0.10,
    )

    assert result.action.value == "hold"
    assert result.quantity == 0.0
    assert "BTC-USD" not in trader.portfolio.positions


def test_dry_run_passes_actual_buy_amount_to_risk_engine():
    class RecordingRiskEngine:
        def __init__(self):
            self.calls = []

        def evaluate(
            self,
            *,
            decision,
            total_equity_nok,
            cash_nok,
            requested_amount_nok,
            position_exists,
        ):
            self.calls.append(
                {
                    "symbol": decision.symbol,
                    "action": decision.action,
                    "total_equity_nok": total_equity_nok,
                    "cash_nok": cash_nok,
                    "requested_amount_nok": requested_amount_nok,
                    "position_exists": position_exists,
                }
            )

            class Result:
                approved = True
                reason = "approved"

            return Result()

    risk_engine = RecordingRiskEngine()

    trader = DryRunTrader(
        portfolio=PaperPortfolio(
            initial_cash=100_000.0,
            fee_rate=0.0,
        ),
        journal=TradeJournal(),
        risk_engine=risk_engine,
        max_position_value=10_000.0,
    )

    result = trader.process_signal(
        "BTC-USD",
        Action.BUY,
        price=100.0,
        confidence=0.95,
        risk_score=0.10,
    )

    assert result.quantity > 0.0
    assert len(risk_engine.calls) == 1

    call = risk_engine.calls[0]

    assert call["symbol"] == "BTC-USD"
    assert call["action"] is Action.BUY
    assert call["cash_nok"] == 100_000.0
    assert call["total_equity_nok"] == 100_000.0

    # The risk gate must see the actual configured order value,
    # not an arbitrary value unrelated to the trade.
    assert call["requested_amount_nok"] == 10_000.0
    assert call["position_exists"] is False


def test_dry_run_risk_block_prevents_buy():
    class BlockingRiskEngine:
        def evaluate(self, **kwargs):
            class Result:
                approved = False
                reason = "Maximum position risk exceeded"

            return Result()

    trader = DryRunTrader(
        portfolio=PaperPortfolio(
            initial_cash=100_000.0,
            fee_rate=0.0,
        ),
        journal=TradeJournal(),
        risk_engine=BlockingRiskEngine(),
        max_position_value=10_000.0,
    )

    result = trader.process_signal(
        "BTC-USD",
        Action.BUY,
        price=100.0,
        confidence=0.95,
        risk_score=0.10,
    )

    assert result.executed is False
    assert result.quantity == 0.0
    assert result.action.value == "hold"
    assert "Risk blocked" in result.reason
    assert "BTC-USD" not in trader.portfolio.positions
    assert trader.journal.trade_count == 0


def test_dry_run_risk_block_prevents_sell():
    class BlockingRiskEngine:
        def evaluate(self, **kwargs):
            class Result:
                approved = False
                reason = "Exit blocked by risk policy"

            return Result()

    trader = DryRunTrader(
        portfolio=PaperPortfolio(
            initial_cash=100_000.0,
            fee_rate=0.0,
        ),
        journal=TradeJournal(),
        risk_engine=BlockingRiskEngine(),
        max_position_value=10_000.0,
    )

    # First create a position using the normal risk engine.
    trader.risk_engine = type(
        "AllowingRiskEngine",
        (),
        {
            "evaluate": lambda self, **kwargs: type(
                "Result",
                (),
                {
                    "approved": True,
                    "reason": "approved",
                },
            )(),
        },
    )()

    trader.process_signal(
        "BTC-USD",
        Action.BUY,
        price=100.0,
        confidence=0.95,
        risk_score=0.10,
    )

    assert "BTC-USD" in trader.portfolio.positions

    # Replace the gate with a blocking engine before SELL.
    trader.risk_engine = BlockingRiskEngine()

    result = trader.process_signal(
        "BTC-USD",
        Action.SELL,
        price=105.0,
        confidence=0.95,
        risk_score=0.10,
    )

    assert result.executed is False
    assert result.quantity == 0.0
    assert result.action.value == "hold"
    assert "Risk blocked" in result.reason

    # The position must still exist because the SELL was blocked.
    assert "BTC-USD" in trader.portfolio.positions
    assert trader.journal.trade_count == 1


def test_dry_run_protective_stop_loss_executes_during_hold():
    trader = DryRunTrader(
        portfolio=PaperPortfolio(
            initial_cash=100_000.0,
            fee_rate=0.0,
        ),
        journal=TradeJournal(),
        max_position_value=10_000.0,
    )

    entry = trader.process_signal(
        "BTC-USD",
        Action.BUY,
        price=100.0,
        confidence=0.95,
        risk_score=0.10,
    )

    assert entry.action.value == "enter"
    assert entry.quantity > 0.0
    assert "BTC-USD" in trader.portfolio.positions

    result = trader.process_signal(
        "BTC-USD",
        Action.HOLD,
        price=90.0,
        confidence=0.95,
        risk_score=0.10,
    )

    assert result.action.value == "exit"
    assert result.executed is True
    assert result.quantity > 0.0
    assert "stop loss" in result.reason
    assert "BTC-USD" not in trader.portfolio.positions

def test_dry_run_sell_respects_canonical_approved_quantity():
    """Canonical RiskManager sizing must cap a paper SELL execution."""
    portfolio = PaperPortfolio(
        initial_cash=100_000.0,
        fee_rate=0.0,
    )
    trader = DryRunTrader(
        portfolio=portfolio,
        journal=TradeJournal(),
        max_position_value=10_000.0,
    )

    portfolio.buy(
        "BTC-USD",
        price=100.0,
        quantity=5.0,
    )

    result = trader.process_signal(
        "BTC-USD",
        Action.SELL,
        price=100.0,
        confidence=0.95,
        risk_score=0.10,
        approved_quantity=1.25,
    )

    assert result.quantity == 1.25
    assert portfolio.positions["BTC-USD"].quantity == 3.75


def test_dry_run_trailing_stop_tracks_peak_reached_after_entry():
    """Paper lifecycle must trail from the highest observed price after entry."""
    trader = DryRunTrader(
        portfolio=PaperPortfolio(
            initial_cash=100_000.0,
            fee_rate=0.0,
        ),
        journal=TradeJournal(),
        position_engine=PositionExitEngine(
            stop_loss=0.50,
            trailing_stop=0.10,
        ),
        max_position_value=10_000.0,
    )

    entry = trader.process_signal(
        "BTC-USD",
        Action.BUY,
        price=100.0,
        confidence=0.95,
        risk_score=0.10,
    )

    assert entry.action.value == "enter"
    assert "BTC-USD" in trader.portfolio.positions

    # Price establishes a new post-entry peak.
    rising = trader.process_signal(
        "BTC-USD",
        Action.HOLD,
        price=120.0,
        confidence=0.95,
        risk_score=0.10,
    )

    assert rising.action.value == "hold"
    assert "BTC-USD" in trader.portfolio.positions

    # 110 is above the 50% stop-loss from the 100 entry,
    # but more than 10% below the observed 120 peak.
    trailing_exit = trader.process_signal(
        "BTC-USD",
        Action.HOLD,
        price=107.0,
        confidence=0.95,
        risk_score=0.10,
    )

    assert trailing_exit.action.value == "exit"
    assert trailing_exit.executed is True
    assert "trailing stop" in trailing_exit.reason
    assert "BTC-USD" not in trader.portfolio.positions


def test_dry_run_trader_uses_all_last_known_prices_for_risk_equity():
    """A multi-symbol execution must use current prices for every position."""
    class RecordingRiskEngine:
        def __init__(self):
            self.equities = []

        def evaluate(self, **kwargs):
            self.equities.append(kwargs["total_equity_nok"])
            return type("Result", (), {"approved": True, "reason": "approved"})()

    portfolio = PaperPortfolio(initial_cash=100_000.0, fee_rate=0.0)
    portfolio.buy("BTCUSDT", 100.0, 100.0)
    portfolio.buy("ETHUSDT", 100.0, 100.0)
    risk = RecordingRiskEngine()
    trader = DryRunTrader(portfolio=portfolio, risk_engine=risk)

    trader.process_signal(
        "ETHUSDT", Action.HOLD, price=80.0,
        confidence=0.5, risk_score=0.0,
        market_prices={"BTCUSDT": 150.0, "ETHUSDT": 80.0},
    )

    assert risk.equities[-1] == 103_000.0
