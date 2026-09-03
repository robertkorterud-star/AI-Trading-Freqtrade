"""
Persistent storage for the ATLAS dry-run paper portfolio.

The state file is runtime data and is intentionally kept outside git.
"""

import json
from pathlib import Path

from atlas.trading.paper_portfolio import PaperPortfolio, PaperPosition


DEFAULT_STATE_PATH = Path("atlas/dashboard/static/paper_portfolio.json")


class PaperPortfolioStore:
    """Load and save a PaperPortfolio without connecting to an exchange."""

    def __init__(self, path: str | Path = DEFAULT_STATE_PATH):
        self.path = Path(path)

    def load(self, initial_cash: float) -> PaperPortfolio:
        """Load persisted state, or create a fresh paper account."""
        try:
            payload = json.loads(self.path.read_text())
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return PaperPortfolio(initial_cash=initial_cash)

        if not isinstance(payload, dict):
            return PaperPortfolio(initial_cash=initial_cash)

        portfolio = PaperPortfolio(
            initial_cash=float(payload.get("initial_cash", initial_cash)),
            fee_rate=float(payload.get("fee_rate", 0.001)),
            cash=float(payload.get("cash", initial_cash)),
            realized_pnl=float(payload.get("realized_pnl", 0.0)),
        )

        positions = payload.get("positions", {})
        if isinstance(positions, dict):
            for symbol, data in positions.items():
                if not isinstance(data, dict):
                    continue
                quantity = float(data.get("quantity", 0.0))
                average_price = float(data.get("average_price", 0.0))
                if quantity > 0.0 and average_price > 0.0:
                    portfolio.positions[str(symbol)] = PaperPosition(
                        symbol=str(symbol),
                        quantity=quantity,
                        average_price=average_price,
                    )

        return portfolio

    def save(self, portfolio: PaperPortfolio) -> None:
        """Persist the complete paper account atomically."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "initial_cash": portfolio.initial_cash,
            "fee_rate": portfolio.fee_rate,
            "cash": portfolio.cash,
            "realized_pnl": portfolio.realized_pnl,
            "positions": {
                symbol: {
                    "quantity": position.quantity,
                    "average_price": position.average_price,
                }
                for symbol, position in portfolio.positions.items()
            },
        }

        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2) + "\n")
        temporary.replace(self.path)
