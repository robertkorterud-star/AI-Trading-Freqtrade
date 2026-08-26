from datetime import datetime

from atlas.database.connection import Database
from atlas.database.prediction_repository import (
    PredictionRepository,
)
from atlas.database.schema import initialize_database
from atlas.trading.prediction_record import (
    PredictionRecord,
)


def test_prediction_features_survive_database_roundtrip(
    tmp_path,
):

    database = Database(
        tmp_path / "prediction_features.db"
    )

    initialize_database(database)

    repository = PredictionRepository(
        database
    )

    prediction = PredictionRecord(
        symbol="BTC-USD",
        action="BUY",
        confidence=87.0,
        evidence=0.9,
        price_usd=100000.0,
        timestamp=datetime.now(),
        analysts=["technical"],
        reason="test",
        features={
            "trend": 1.0,
            "momentum": 1.0,
            "rsi_signal": 1.0,
            "macd_signal": 1.0,
            "multi_timeframe_signal": 1.0,
            "multi_timeframe_alignment": 0.92,
        },
    )

    repository.save(prediction)

    restored = repository.get_all()[0]

    assert restored.features == {
        "trend": 1.0,
        "momentum": 1.0,
        "rsi_signal": 1.0,
        "macd_signal": 1.0,
        "multi_timeframe_signal": 1.0,
        "multi_timeframe_alignment": 0.92,
    }


def test_old_prediction_without_features_is_safe(
    tmp_path,
):

    database = Database(
        tmp_path / "legacy.db"
    )

    initialize_database(database)

    repository = PredictionRepository(
        database
    )

    prediction = PredictionRecord(
        symbol="ETH-USD",
        action="WAIT",
        confidence=50.0,
        evidence=0.0,
        price_usd=4000.0,
        timestamp=datetime.now(),
    )

    repository.save(prediction)

    restored = repository.get_all()[0]

    assert restored.features == {}
