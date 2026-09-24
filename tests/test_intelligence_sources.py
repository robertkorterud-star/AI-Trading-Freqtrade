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


def test_intelligence_source_adapter_adds_youtube_transcript():

    class FakeYouTube:
        def search(self, symbol):
            return [
                {
                    "source": "YouTube",
                    "title": "NVDA RSI Strategy",
                    "summary": "Trading strategy.",
                    "sentiment": "neutral",
                    "video_id": "abc123",
                }
            ]

    class FakeTranscript:
        def get(self, video_id):
            assert video_id == "abc123"
            return (
                "RSI falls below 30. "
                "Buy when RSI crosses back above 30."
            )

    class FakeFinnhub:
        def search(self, symbol):
            return []

    adapter = IntelligenceSourceAdapter(
        youtube=FakeYouTube(),
        finnhub=FakeFinnhub(),
        transcript=FakeTranscript(),
    )

    results = adapter.get("NVDA")

    assert len(results) == 1
    assert results[0]["source"] == "YouTube"
    assert "RSI falls below 30" in results[0]["summary"]
    assert results[0]["transcript"] == (
        "RSI falls below 30. "
        "Buy when RSI crosses back above 30."
    )


def test_intelligence_source_adapter_adds_sec_research():

    class FakeYouTube:
        def search(self, symbol):
            return []


    class FakeFinnhub:
        def search(self, symbol):
            return []


    class FakeTranscript:
        def get(self, video_id):
            return ""


    class FakeSEC:
        def get_company_filings(self, cik):
            assert cik == "0001045810"

            return [
                {
                    "source": "SEC",
                    "company": "NVIDIA CORP",
                    "form": "10-Q",
                    "filing_date": "2026-08-01",
                    "accession_number": "0000000001-26-000001",
                    "primary_document": "nvda-q1.htm",
                    "cik": "0001045810",
                }
            ]


    adapter = IntelligenceSourceAdapter(
        youtube=FakeYouTube(),
        finnhub=FakeFinnhub(),
        transcript=FakeTranscript(),
        sec=FakeSEC(),
    )

    results = adapter.get(
        "NVDA",
        cik="0001045810",
    )

    assert len(results) == 1
    assert results[0]["source"] == "SEC"
    assert results[0]["company"] == "NVIDIA CORP"
    assert results[0]["form"] == "10-Q"


def test_intelligence_source_adapter_adds_sec_research():

    class FakeYouTube:
        def search(self, symbol):
            return []


    class FakeFinnhub:
        def search(self, symbol):
            return []


    class FakeTranscript:
        def get(self, video_id):
            return ""


    class FakeSEC:
        def get_company_filings(self, cik):
            assert cik == "0001045810"

            return [
                {
                    "source": "SEC",
                    "company": "NVIDIA CORP",
                    "form": "10-Q",
                    "filing_date": "2026-08-01",
                    "accession_number": "0000000001-26-000001",
                    "primary_document": "nvda-q1.htm",
                    "cik": "0001045810",
                }
            ]


    adapter = IntelligenceSourceAdapter(
        youtube=FakeYouTube(),
        finnhub=FakeFinnhub(),
        transcript=FakeTranscript(),
        sec=FakeSEC(),
    )

    results = adapter.get(
        "NVDA",
        cik="0001045810",
    )

    assert len(results) == 1
    assert results[0]["source"] == "SEC"
    assert results[0]["company"] == "NVIDIA CORP"
    assert results[0]["form"] == "10-Q"


def test_intelligence_source_adapter_finds_sec_cik_automatically():

    class FakeYouTube:
        def search(self, symbol):
            return []


    class FakeFinnhub:
        def search(self, symbol):
            return []


    class FakeTranscript:
        def get(self, video_id):
            return ""


    class FakeSEC:
        def find_cik(self, symbol):
            assert symbol == "NVDA"
            return "0001045810"

        def get_company_filings(self, cik):
            assert cik == "0001045810"

            return [
                {
                    "source": "SEC",
                    "company": "NVIDIA CORP",
                    "form": "10-Q",
                    "filing_date": "2026-08-01",
                    "accession_number": "0000000001-26-000001",
                    "primary_document": "nvda-q1.htm",
                    "cik": "0001045810",
                }
            ]


    adapter = IntelligenceSourceAdapter(
        youtube=FakeYouTube(),
        finnhub=FakeFinnhub(),
        transcript=FakeTranscript(),
        sec=FakeSEC(),
    )

    results = adapter.get(
        "NVDA",
        include_sec=True,
    )

    assert len(results) == 1
    assert results[0]["source"] == "SEC"
    assert results[0]["company"] == "NVIDIA CORP"
    assert results[0]["cik"] == "0001045810"


def test_intelligence_sources_includes_web_research():

    class FakeWeb:

        def search(self, symbol):
            return [
                {
                    "source": "Google News",
                    "title": "XRP RSI strategy",
                    "summary": "XRP RSI trading strategy",
                    "sentiment": "neutral",
                }
            ]

    service = IntelligenceSourceAdapter(
        youtube=type(
            "EmptyYouTube",
            (),
            {"search": lambda self, symbol: []},
        )(),
        finnhub=type(
            "EmptyFinnhub",
            (),
            {"search": lambda self, symbol: []},
        )(),
        web=FakeWeb(),
        direct_publishers=type(
            "EmptyDirectPublishers",
            (),
            {"search": lambda self, symbol: []},
        )(),
    )

    results = service.get("XRP-USD")

    assert len(results) == 1
    assert results[0]["source"] == "Google News"
    assert "RSI" in results[0]["summary"]


def test_intelligence_source_adapter_can_skip_youtube_transcripts():

    class FakeYouTube:
        def search(self, symbol):
            return [
                {
                    "source": "YouTube",
                    "title": "NVDA analysis",
                    "summary": "Market update.",
                    "sentiment": "neutral",
                    "video_id": "abc123",
                }
            ]

    class FailingTranscript:
        def get(self, video_id):
            raise AssertionError("transcript fetch should be skipped")

    class EmptyFinnhub:
        def search(self, symbol):
            return []

    adapter = IntelligenceSourceAdapter(
        youtube=FakeYouTube(),
        finnhub=EmptyFinnhub(),
        transcript=FailingTranscript(),
    )

    results = adapter.get("NVDA", include_transcripts=False)

    assert len(results) == 1
    assert results[0]["title"] == "NVDA analysis"
    assert "transcript" not in results[0]
