from atlas.market.asset import Asset
from atlas.market.asset_discovery import DiscoveryScore
from atlas.market.asset_type import AssetType
from atlas.market.candidate_selector import CandidateSelector


def make_score(symbol, score, asset_type=AssetType.STOCK):
    return DiscoveryScore(
        asset=Asset(
            symbol=symbol,
            name=symbol,
            asset_type=asset_type,
            market="US",
            currency="USD",
        ),
        score=score,
    )


def test_selector_returns_highest_scoring_candidates():

    candidates = [
        make_score("AAPL", 70.0),
        make_score("NVDA", 90.0),
        make_score("MSFT", 80.0),
    ]

    selector = CandidateSelector()

    selected = selector.select(
        candidates,
        limit=2,
    )

    assert [item.symbol for item in selected] == [
        "NVDA",
        "MSFT",
    ]


def test_selector_preserves_discovery_order_when_scores_match():

    candidates = [
        make_score("AAPL", 80.0),
        make_score("NVDA", 80.0),
        make_score("MSFT", 80.0),
    ]

    selector = CandidateSelector()

    selected = selector.select(
        candidates,
        limit=2,
    )

    assert [item.symbol for item in selected] == [
        "AAPL",
        "NVDA",
    ]


def test_selector_can_require_minimum_discovery_score():

    candidates = [
        make_score("NVDA", 90.0),
        make_score("AAPL", 70.0),
        make_score("MSFT", 40.0),
    ]

    selector = CandidateSelector()

    selected = selector.select(
        candidates,
        limit=10,
        minimum_score=60.0,
    )

    assert [item.symbol for item in selected] == [
        "NVDA",
        "AAPL",
    ]


def test_selector_returns_all_valid_candidates_when_limit_is_none():

    candidates = [
        make_score("AAPL", 70.0),
        make_score("NVDA", 90.0),
        make_score("MSFT", 80.0),
    ]

    selector = CandidateSelector()

    selected = selector.select(
        candidates,
        limit=None,
    )

    assert [item.symbol for item in selected] == [
        "NVDA",
        "MSFT",
        "AAPL",
    ]
