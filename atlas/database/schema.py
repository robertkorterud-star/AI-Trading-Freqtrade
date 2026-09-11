"""
ATLAS Database Schema
"""

from atlas.database.connection import Database


SCHEMA = """
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    action TEXT NOT NULL,
    confidence REAL NOT NULL,
    evidence REAL NOT NULL,
    price_usd REAL NOT NULL,
    timestamp TEXT NOT NULL,
    analysts TEXT NOT NULL,
    reason TEXT NOT NULL,
    features TEXT NOT NULL DEFAULT '{}',
    evaluated INTEGER NOT NULL DEFAULT 0,
    correct INTEGER,
    evaluated_price_usd REAL,
    price_change_percent REAL,
    evaluated_at TEXT
);

CREATE TABLE IF NOT EXISTS analysis_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    results TEXT NOT NULL,
    decision TEXT NOT NULL,
    intelligence TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_analysis_snapshots_symbol
ON analysis_snapshots(symbol);

CREATE INDEX IF NOT EXISTS idx_analysis_snapshots_timestamp
ON analysis_snapshots(timestamp);

CREATE TABLE IF NOT EXISTS paper_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    action TEXT NOT NULL,
    quantity REAL NOT NULL,
    price_usd REAL NOT NULL,
    amount_nok REAL NOT NULL,
    realized_pnl_nok REAL NOT NULL,
    timestamp TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    analysis_snapshot_id INTEGER,
    FOREIGN KEY (analysis_snapshot_id)
        REFERENCES analysis_snapshots(id)
);

CREATE INDEX IF NOT EXISTS idx_paper_trades_timestamp
ON paper_trades(timestamp);

CREATE INDEX IF NOT EXISTS idx_predictions_symbol
ON predictions(symbol);

CREATE INDEX IF NOT EXISTS idx_predictions_timestamp
ON predictions(timestamp);

CREATE TABLE IF NOT EXISTS outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    action TEXT NOT NULL,
    prediction_price_usd REAL NOT NULL,
    outcome_price_usd REAL NOT NULL,
    change_percent REAL NOT NULL,
    correct INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (prediction_id)
        REFERENCES predictions(id)
);

CREATE INDEX IF NOT EXISTS idx_outcomes_prediction
ON outcomes(prediction_id);

CREATE INDEX IF NOT EXISTS idx_outcomes_symbol
ON outcomes(symbol);

CREATE INDEX IF NOT EXISTS idx_outcomes_timestamp
ON outcomes(timestamp);

CREATE INDEX IF NOT EXISTS idx_predictions_evaluated
ON predictions(evaluated);

CREATE TABLE IF NOT EXISTS strategy_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    regime TEXT NOT NULL,
    strategy_name TEXT NOT NULL,
    trade_count INTEGER NOT NULL,
    winning_trades INTEGER NOT NULL,
    losing_trades INTEGER NOT NULL,
    win_rate_percent REAL NOT NULL,
    average_trade_return_percent REAL NOT NULL,
    total_return_percent REAL NOT NULL,
    evidence_strength TEXT NOT NULL,
    robust_winner INTEGER NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(symbol, regime, strategy_name)
);

CREATE INDEX IF NOT EXISTS idx_strategy_memory_symbol
ON strategy_memory(symbol);

CREATE INDEX IF NOT EXISTS idx_strategy_memory_regime
ON strategy_memory(symbol, regime);

CREATE INDEX IF NOT EXISTS idx_strategy_memory_updated_at
ON strategy_memory(updated_at);

CREATE TABLE IF NOT EXISTS strategy_memory_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    research_run_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    regime TEXT NOT NULL,
    strategy_name TEXT NOT NULL,
    trade_count INTEGER NOT NULL,
    winning_trades INTEGER NOT NULL,
    losing_trades INTEGER NOT NULL,
    win_rate_percent REAL NOT NULL,
    average_trade_return_percent REAL NOT NULL,
    total_return_percent REAL NOT NULL,
    evidence_strength TEXT NOT NULL,
    robust_winner INTEGER NOT NULL,
    recorded_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_strategy_memory_history_lookup
ON strategy_memory_history(
    symbol,
    regime,
    strategy_name,
    recorded_at
);

CREATE INDEX IF NOT EXISTS idx_strategy_memory_history_recorded_at
ON strategy_memory_history(recorded_at);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    last_seen_at TEXT,
    revoked_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_sessions_user
ON sessions(user_id);

CREATE INDEX IF NOT EXISTS idx_sessions_expires
ON sessions(expires_at);

CREATE TABLE IF NOT EXISTS atlas_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def initialize_database(database: Database):
    """Create the ATLAS database schema."""

    with database.connect() as connection:
        connection.executescript(SCHEMA)

        history_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(strategy_memory_history)"
            ).fetchall()
        }

        if "research_run_id" not in history_columns:
            connection.execute(
                "ALTER TABLE strategy_memory_history "
                "ADD COLUMN research_run_id TEXT"
            )

            connection.execute(
                "UPDATE strategy_memory_history "
                "SET research_run_id = 'legacy-' || id "
                "WHERE research_run_id IS NULL"
            )

        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_strategy_memory_history_run_unique
            ON strategy_memory_history(
                research_run_id,
                symbol,
                regime,
                strategy_name
            )
            """
        )

        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_strategy_memory_history_research_run
            ON strategy_memory_history(
                research_run_id,
                symbol,
                regime,
                strategy_name
            )
            """
        )

        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(predictions)"
            ).fetchall()
        }

        if "features" not in columns:
            connection.execute(
                """
                ALTER TABLE predictions
                ADD COLUMN features TEXT
                NOT NULL DEFAULT '{}'
                """
            )

        trade_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(paper_trades)"
            ).fetchall()
        }

        if "analysis_snapshot_id" not in trade_columns:
            connection.execute(
                """
                ALTER TABLE paper_trades
                ADD COLUMN analysis_snapshot_id INTEGER
                """
            )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_paper_trades_analysis_snapshot
            ON paper_trades(analysis_snapshot_id)
            """
        )

        connection.commit()
