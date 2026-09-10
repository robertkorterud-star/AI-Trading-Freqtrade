"""
ATLAS Settings Service
"""

from atlas.core.config import AtlasConfig
from atlas.database.connection import Database


class SettingsService:
    """Manage safe ATLAS trading settings with optional database persistence."""

    _PERSISTED_KEYS = (
        "trading_mode",
        "paper_trading",
        "language",
        "ai_provider",
    )

    def __init__(self, config=None):
        self.config = config or AtlasConfig()
        self.database = Database(self.config.database_path)
        self._ensure_storage()
        if self.config.load_persisted_settings:
            self._load_persisted_settings()

    def _ensure_storage(self):
        with self.database.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS atlas_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def _load_persisted_settings(self):
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT key, value FROM atlas_settings"
            ).fetchall()

        persisted = {row["key"]: row["value"] for row in rows}
        if "trading_mode" in persisted:
            self.config.trading_mode = persisted["trading_mode"]
        if "paper_trading" in persisted:
            self.config.paper_trading = persisted["paper_trading"] == "true"
        if "language" in persisted:
            self.config.language = persisted["language"]
        if "ai_provider" in persisted:
            self.config.ai_provider = persisted["ai_provider"]

    def _persist(self, key, value):
        if key not in self._PERSISTED_KEYS:
            raise ValueError(f"Unsupported setting: {key}")
        if not self.config.load_persisted_settings:
            return

        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO atlas_settings(key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, str(value).lower() if isinstance(value, bool) else str(value)),
            )
            connection.commit()

    def get_config(self):
        return self.config

    def get_trading_status(self):
        return {
            "mode": self.config.trading_mode,
            "paper_trading": self.config.paper_trading,
            "live_orders": False,
        }

    def get_language(self):
        return getattr(self.config, "language", "no")

    def set_language(self, language):
        if language not in ("no", "en"):
            raise ValueError(
                "Unsupported language. Use 'no' or 'en'."
            )

        self.config.language = language
        self._persist("language", language)

    def get_ai_provider(self):
        return getattr(
            self.config,
            "ai_provider",
            "ollama",
        )

    def set_ai_provider(self, provider):
        if provider not in ("openai", "ollama"):
            raise ValueError(
                "Unsupported AI provider. "
                "Use 'openai' or 'ollama'."
            )

        self.config.ai_provider = provider
        self._persist("ai_provider", provider)

    def set_trading_mode(self, mode):
        if mode == "advisor":
            self.config.trading_mode = "advisor"
            self.config.paper_trading = True
            self._persist("trading_mode", "advisor")
            self._persist("paper_trading", True)
            return

        if mode == "paper":
            self.config.trading_mode = "paper"
            self.config.paper_trading = True
            self._persist("trading_mode", "paper")
            self._persist("paper_trading", True)
            return

        raise ValueError(
            "Unsupported trading mode. "
            "Use 'advisor' or 'paper'."
        )
