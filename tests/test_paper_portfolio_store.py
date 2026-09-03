from atlas.trading.paper_portfolio import PaperPortfolio
from atlas.trading.paper_portfolio_store import PaperPortfolioStore


def test_store_round_trip_preserves_cash_positions_and_pnl(tmp_path):
    path = tmp_path / "paper_portfolio.json"
    store = PaperPortfolioStore(path)

    portfolio = PaperPortfolio(initial_cash=5000.0)
    portfolio.buy("BTCUSDT", 100.0, 10.0)
    portfolio.sell("BTCUSDT", 110.0, 5.0)
    store.save(portfolio)

    restored = store.load(initial_cash=5000.0)

    assert restored.initial_cash == 5000.0
    assert restored.cash == portfolio.cash
    assert restored.realized_pnl == portfolio.realized_pnl
    assert restored.positions["BTCUSDT"].quantity == 5.0
    assert restored.positions["BTCUSDT"].average_price == 100.0


def test_store_returns_fresh_account_for_missing_state(tmp_path):
    store = PaperPortfolioStore(tmp_path / "missing.json")

    portfolio = store.load(initial_cash=5000.0)

    assert portfolio.cash == 5000.0
    assert portfolio.positions == {}
    assert portfolio.realized_pnl == 0.0
