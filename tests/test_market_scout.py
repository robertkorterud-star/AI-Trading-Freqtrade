from atlas.market.market_scout import AssetType, MarketObservation, MarketScout


def test_scout_prefers_high_momentum_volume_and_catalyst():
    scout = MarketScout()
    candidates = scout.scan(
        [
            MarketObservation(
                symbol="CALM",
                asset_type=AssetType.STOCK,
                price=12.0,
                volume=500_000,
                average_volume=100_000,
                change_percent=4.0,
                gap_percent=2.0,
                relative_volume_5m=2.0,
            ),
            MarketObservation(
                symbol="HOT",
                asset_type=AssetType.STOCK,
                price=8.0,
                volume=1_000_000,
                average_volume=100_000,
                change_percent=15.0,
                gap_percent=8.0,
                relative_volume_5m=6.0,
                float_shares=5_000_000,
                news_catalyst=True,
            ),
        ]
    )

    assert [candidate.symbol for candidate in candidates] == ["HOT", "CALM"]
    assert candidates[0].score > candidates[1].score
    assert "high relative volume" in candidates[0].reasons
    assert "news catalyst" in candidates[0].reasons
    assert "low float" in candidates[0].reasons


def test_scout_filters_ineligible_observations():
    scout = MarketScout()
    candidates = scout.scan(
        [
            MarketObservation(
                symbol="LOWPRICE",
                asset_type=AssetType.STOCK,
                price=0.50,
                volume=1_000_000,
                average_volume=100_000,
            ),
            MarketObservation(
                symbol="LOWVOL",
                asset_type=AssetType.STOCK,
                price=10.0,
                volume=50_000,
                average_volume=100_000,
            ),
            MarketObservation(
                symbol="ILLIQUID",
                asset_type=AssetType.STOCK,
                price=10.0,
                volume=1_000_000,
                average_volume=100_000,
                liquid=False,
            ),
        ]
    )

    assert candidates == []


def test_scout_supports_crypto_without_stock_price_floor():
    scout = MarketScout()
    candidates = scout.scan(
        [
            MarketObservation(
                symbol="BTC/USDT",
                asset_type=AssetType.CRYPTO,
                price=0.50,
                volume=1_000_000,
                average_volume=100_000,
                change_percent=12.0,
                relative_volume_5m=5.0,
            )
        ]
    )

    assert len(candidates) == 1
    assert candidates[0].asset_type is AssetType.CRYPTO
    assert candidates[0].score > 0


def test_scout_evidence_is_explainable_and_bounded():
    scout = MarketScout()
    evidence = scout.evidence(
        MarketObservation(
            symbol="TEST",
            asset_type=AssetType.STOCK,
            price=10.0,
            volume=10_000_000,
            average_volume=100_000,
            change_percent=50.0,
            gap_percent=20.0,
            relative_volume_5m=20.0,
            news_catalyst=True,
        )
    )

    assert 0.0 <= evidence.score <= 100.0
    assert 0.0 <= evidence.momentum_score <= 100.0
    assert 0.0 <= evidence.volume_score <= 100.0
    assert 0.0 <= evidence.breakout_score <= 100.0
    assert evidence.catalyst_score == 100.0
    assert evidence.reasons


def test_market_observation_accepts_optional_market_cap():
    observation = MarketObservation(
        symbol="BTCUSDT",
        asset_type=AssetType.CRYPTO,
        price=100.0,
        volume=1_000_000.0,
        average_volume=500_000.0,
        market_cap=50_000_000.0,
    )

    assert observation.market_cap == 50_000_000.0
