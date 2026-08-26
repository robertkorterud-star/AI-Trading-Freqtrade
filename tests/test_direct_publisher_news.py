from atlas.adapters.direct_publisher_news import (
    DirectPublisherNewsAdapter,
)


def test_yahoo_finance_results_are_normalized(
    monkeypatch,
):
    class FakeResponse:

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "news": [
                    {
                        "title": "XRP market outlook",
                        "link":
                            "https://finance.yahoo.com/news/xrp",
                        "publisher":
                            "Yahoo Finance",
                        "providerPublishTime":
                            1234567890,
                    }
                ]
            }

    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr(
        "atlas.adapters.direct_publisher_news.requests.get",
        fake_get,
    )

    results = (
        DirectPublisherNewsAdapter()
        ._yahoo_finance("XRP-USD")
    )

    assert len(results) == 1
    assert (
        results[0]["source"]
        == "Yahoo Finance"
    )
    assert (
        results[0]["publisher"]
        == "Yahoo Finance"
    )


def test_publisher_failures_do_not_raise(
    monkeypatch,
):
    def fake_get(*args, **kwargs):
        raise RuntimeError(
            "publisher unavailable"
        )

    monkeypatch.setattr(
        "atlas.adapters.direct_publisher_news.requests.get",
        fake_get,
    )

    adapter = DirectPublisherNewsAdapter()

    assert adapter.search(
        "XRP-USD"
    ) == []
