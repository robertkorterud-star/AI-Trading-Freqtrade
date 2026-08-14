from atlas.adapters.intelligence_sources import (
    IntelligenceItem,
    IntelligenceSourceAdapter,
)


def test_intelligence_item_contains_source_information():

    item = IntelligenceItem(
        source="YouTube",
        title="NVIDIA outlook",
        summary="Strong AI demand.",
        sentiment="positive",
    )

    assert item.source == "YouTube"
    assert item.title == "NVIDIA outlook"
    assert item.summary == "Strong AI demand."
    assert item.sentiment == "positive"


def test_intelligence_source_adapter_combines_sources():

    class FakeYouTube:
        def search(self, symbol):
            return [
                {
                    "source": "YouTube",
                    "title": "NVIDIA analysis",
                    "summary": "Strong AI demand.",
                    "sentiment": "neutral",
                }
            ]

    class FakeFinnhub:
        def search(self, symbol):
            return [
                {
                    "source": "Finnhub",
                    "title": "NVIDIA outlook",
                    "summary": "Growth remains strong.",
                    "sentiment": "neutral",
                }
            ]

    adapter = IntelligenceSourceAdapter(
        youtube=FakeYouTube(),
        finnhub=FakeFinnhub(),
    )

    results = adapter.get("NVDA")

    assert len(results) == 2
    assert results[0]["source"] == "YouTube"
    assert results[1]["source"] == "Finnhub"


def test_intelligence_source_adapter_handles_no_sources():

    class EmptyYouTube:
        def search(self, symbol):
            return []

    class EmptyFinnhub:
        def search(self, symbol):
            return []

    adapter = IntelligenceSourceAdapter(
        youtube=EmptyYouTube(),
        finnhub=EmptyFinnhub(),
    )

    assert adapter.get("NVDA") == []
