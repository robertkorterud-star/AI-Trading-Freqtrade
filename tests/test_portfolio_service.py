from atlas.services.portfolio_service import PortfolioService


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
