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
"""


def initialize_database(database: Database):
    """Create the ATLAS database schema."""

    with database.connect() as connection:
        connection.executescript(SCHEMA)

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

        connection.commit()
