"""
Dashboard Service
"""

import time

from atlas.adapters.binance_market_data import BinanceMarketDataAdapter
from atlas.services.binance_scanner_service import BinanceScannerService
from atlas.services.dashboard_data_service import DashboardDataService
from atlas.services.scanner_service import ScannerResult, ScannerService
from atlas.trading.trading_service import TradingService
from atlas.database.connection import Database
from atlas.database.schema import initialize_database
from atlas.database.trade_repository import TradeRepository
from atlas.core.config import AtlasConfig


class _LazyScannerSnapshot(dict):
    """Load the scanner snapshot only when the dashboard actually reads it."""

    def __init__(self, loader):
        super().__init__()
        self._loader = loader
        self._loaded = False

    def _ensure_loaded(self):
        if self._loaded:
            return
        super().update(self._loader())
        self._loaded = True

    def __getitem__(self, key):
        self._ensure_loaded()
        return super().__getitem__(key)

    def get(self, key, default=None):
        self._ensure_loaded()
        return super().get(key, default)

    def items(self):
        self._ensure_loaded()
        return super().items()

    def keys(self):
        self._ensure_loaded()
        return super().keys()

    def values(self):
        self._ensure_loaded()
        return super().values()

    def __iter__(self):
        self._ensure_loaded()
        return super().__iter__()

    def __len__(self):
        self._ensure_loaded()
        return super().__len__()


class DashboardService:
    """Provides dashboard data."""

    SCANNER_CACHE_TTL_SECONDS = 3600.0

    @staticmethod
    def _normalize_dashboard_symbol(symbol):
        """Map Binance-native crypto symbols to the dashboard market symbol."""
        value = str(symbol or "").strip().upper()
        for quote_asset in ("USDT", "USDC"):
            if value.endswith(quote_asset) and len(value) > len(quote_asset):
                return f"{value[:-len(quote_asset)]}-USD"
        return value

    def __init__(self, config=None, binance_market_data=None):
        resolved_config = config or AtlasConfig()
        database = Database(resolved_config.database_path)
        initialize_database(database)
        trading = TradingService(repository=TradeRepository(database))
        self.data = DashboardDataService(config=resolved_config, trading=trading)
        persisted_trades = trading.history()
        if persisted_trades:
            restored = False
            # TradingService exposes newest trades first. Try the newest prefix
            # so valid modern trades survive older legacy records that cannot
            # be replayed safely.
            for trade_count in range(1, len(persisted_trades) + 1):
                try:
                    self.data.portfolio.restore_from_trades(
                        list(reversed(persisted_trades[:trade_count]))
                    )
                    snapshot = self.data.portfolio.as_dict(1.0)
                    if snapshot["cash_nok"] < -1e-9:
                        raise ValueError("Persisted history exceeds available cash.")
                except ValueError:
                    continue
                else:
                    restored = True
                    break
            if not restored:
                self.data.portfolio.reset()
        self._portfolio_trade_count = trading.count()
        self.scanner = ScannerService()
        self.binance_scanner = BinanceScannerService(
            binance_market_data or BinanceMarketDataAdapter(),
            scanner=self.scanner,
        )
        self._scanner_cache = None
        self._scanner_cache_at = 0.0

    def _sync_portfolio_with_new_trades(self):
        """Apply trades created after the dashboard service was initialized.

        ``TradingService`` owns persisted trade history.  The dashboard keeps
        a live ``PortfolioService`` instance, so it must apply only newly
        recorded trades rather than replaying the full legacy history on every
        request. Invalid new records are ignored so they cannot poison the
        current paper-account state.
        """
        current_count = self.data.trading.count()
        if current_count <= self._portfolio_trade_count:
            return

        new_count = current_count - self._portfolio_trade_count
        new_trades = list(reversed(self.data.trading.history()[:new_count]))

        for trade in new_trades:
            try:
                quantity = float(trade["quantity"])
                price_usd = float(trade["price_usd"])
                amount_nok = float(trade["amount_nok"])
                if quantity <= 0.0 or price_usd <= 0.0 or amount_nok <= 0.0:
                    raise ValueError("Invalid new persisted trade.")

                usd_nok = amount_nok / (quantity * price_usd)
                action = str(trade["action"])

                if action == "BUY":
                    self.data.portfolio.buy(
                        symbol=str(trade["symbol"]),
                        amount_nok=amount_nok,
                        price_usd=price_usd,
                        usd_nok=usd_nok,
                    )
                elif action == "SELL":
                    self.data.portfolio.sell(
                        symbol=str(trade["symbol"]),
                        price_usd=price_usd,
                        usd_nok=usd_nok,
                        quantity=quantity,
                    )
                else:
                    raise ValueError(f"Unsupported new persisted trade: {action}")
            except (KeyError, TypeError, ValueError, ZeroDivisionError):
                continue

        self._portfolio_trade_count = current_count

    def _get_scanner_result(self):
        """Return the hourly scanner snapshot, refreshing it when stale."""
        now = time.monotonic()
        if (
            self._scanner_cache is not None
            and now - self._scanner_cache_at < self.SCANNER_CACHE_TTL_SECONDS
        ):
            return self._scanner_cache

        try:
            result = self.binance_scanner.scan(limit=1000)
        except Exception:
            result = ScannerResult(0, 0, tuple())

        self._scanner_cache = result
        self._scanner_cache_at = now
        return result

    def get_scanner(self):
        """Return the cached scanner snapshot without loading full dashboard data."""
        return self.scanner.as_dict(self._get_scanner_result())

    def get_dashboard(self, selected_symbol=None, trade_history_period="1d", now=None):
        """Return dashboard data, deferring the scanner snapshot until it is read."""
        normalized_symbol = self._normalize_dashboard_symbol(selected_symbol)
        self._sync_portfolio_with_new_trades()
        dashboard = self.data.get_dashboard_data(
            selected_symbol=normalized_symbol,
            trade_history_period=trade_history_period,
            now=now,
        )
        dashboard["scanner"] = _LazyScannerSnapshot(self.get_scanner)
        return dashboard
