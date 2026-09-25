from datetime import datetime, timedelta

from atlas.services.portfolio_service import PortfolioService
from atlas.trading.trade_record import TradeRecord


def test_portfolio_starts_with_5000_nok():

    portfolio = PortfolioService(5000)

    result = portfolio.as_dict(9.50)

    assert result["starting_capital_nok"] == 5000.0
    assert result["cash_nok"] == 5000.0
    assert result["total_equity_nok"] == 5000.0
    assert result["position_count"] == 0


def test_portfolio_buy_reduces_cash():

    portfolio = PortfolioService(5000)

    portfolio.buy(
        symbol="BTC-USD",
        amount_nok=1000,
        price_usd=65000,
        usd_nok=9.50,
    )

    result = portfolio.as_dict(9.50)

    assert result["cash_nok"] == 4000.0
    assert result["invested_nok"] == 1000.0
    assert result["position_count"] == 1


def test_portfolio_tracks_unrealized_profit():

    portfolio = PortfolioService(5000)

    portfolio.buy(
        symbol="BTC-USD",
        amount_nok=1000,
        price_usd=65000,
        usd_nok=9.50,
    )

    portfolio.update_prices({
        "BTC-USD": 70000
    })

    result = portfolio.as_dict(9.50)

    assert result["positions_value_nok"] == 1076.92
    assert result["unrealized_pnl_nok"] == 76.92
    assert result["total_pnl_nok"] == 76.92


def test_portfolio_sell_moves_profit_to_vault():

    portfolio = PortfolioService(5000)

    portfolio.buy(
        symbol="BTC-USD",
        amount_nok=1000,
        price_usd=65000,
        usd_nok=9.50,
    )

    trade = portfolio.sell(
        symbol="BTC-USD",
        price_usd=70000,
        usd_nok=9.50,
    )

    result = portfolio.as_dict(9.50)

    assert trade["sale_value_nok"] == 1076.92
    assert trade["realized_pnl_nok"] == 76.92

    assert result["cash_nok"] == 5000.0
    assert result["profit_vault_nok"] == 76.92
    assert result["position_count"] == 0
    assert result["total_equity_nok"] == 5076.92
    assert result["total_pnl_nok"] == 76.92
    assert result["return_percent"] == 1.54


def test_portfolio_restores_position_and_cash_from_persisted_trades():
    started = datetime(2026, 9, 14, 7, 0, 0)
    trades = [
        TradeRecord(
            symbol="BTC-USD",
            action="BUY",
            quantity=0.01,
            price_usd=65000.0,
            amount_nok=617.50,
            realized_pnl_nok=0.0,
            timestamp=started,
        ),
        TradeRecord(
            symbol="BTC-USD",
            action="BUY",
            quantity=0.01,
            price_usd=60000.0,
            amount_nok=570.00,
            realized_pnl_nok=0.0,
            timestamp=started + timedelta(minutes=1),
        ),
        TradeRecord(
            symbol="BTC-USD",
            action="SELL",
            quantity=0.01,
            price_usd=70000.0,
            amount_nok=665.00,
            realized_pnl_nok=47.50,
            timestamp=started + timedelta(minutes=2),
        ),
    ]

    portfolio = PortfolioService(5000)
    portfolio.restore_from_trades(reversed(trades))

    result = portfolio.as_dict(9.50)

    assert result["cash_nok"] == 4430.0
    assert result["profit_vault_nok"] == 47.5
    assert result["position_count"] == 1
    assert result["positions"][0]["quantity"] == 0.01
    assert result["positions"][0]["average_price_usd"] == 62500.0



def test_position_tracks_peak_price_across_market_updates():
    portfolio = PortfolioService(5000)
    portfolio.buy(
        symbol="BTC-USD",
        amount_nok=1000.0,
        price_usd=100.0,
        usd_nok=10.0,
    )

    portfolio.update_prices({"BTC-USD": 120.0})
    portfolio.update_prices({"BTC-USD": 110.0})

    result = portfolio.as_dict(10.0)
    position = result["positions"][0]

    assert position["current_price_usd"] == 110.0
    assert position["peak_price_usd"] == 120.0
