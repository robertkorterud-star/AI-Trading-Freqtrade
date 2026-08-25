from atlas.adapters.web_research import WebResearchAdapter


def test_web_research_adapter_parses_search_results(monkeypatch):

    rss = """<?xml version="1.0"?>
    <rss version="2.0">
      <channel>
        <item>
          <title>XRP RSI trading strategy</title>
          <description>RSI oversold strategy and moving average crossover.</description>
          <link>https://example.com/xrp</link>
          <pubDate>Mon, 25 Aug 2026 10:00:00 GMT</pubDate>
        </item>
      </channel>
    </rss>
    """

    class FakeResponse:
        content = rss.encode("utf-8")

        def raise_for_status(self):
            pass

    monkeypatch.setattr(
        "requests.get",
        lambda *args, **kwargs: FakeResponse(),
    )

    adapter = WebResearchAdapter()

    results = adapter.search("XRP")

    assert len(results) == 1
    assert results[0]["source"] == "Google News"
    assert results[0]["title"] == "XRP RSI trading strategy"
    assert "RSI" in results[0]["summary"]
    assert results[0]["url"] == "https://example.com/xrp"


def test_web_research_adapter_handles_network_failure(
    monkeypatch,
):

    def fail(*args, **kwargs):
        raise RuntimeError("network unavailable")

    monkeypatch.setattr(
        "requests.get",
        fail,
    )

    adapter = WebResearchAdapter()

    assert adapter.search("XRP") == []


def test_web_research_adapter_uses_strategy_focused_queries(
    monkeypatch,
):

    captured = []

    class FakeResponse:
        content = b"""
        <rss>
          <channel></channel>
        </rss>
        """

        def raise_for_status(self):
            pass

    def fake_get(url, params=None, **kwargs):
        captured.append(params["q"])
        return FakeResponse()

    monkeypatch.setattr(
        "requests.get",
        fake_get,
    )

    adapter = WebResearchAdapter()
    adapter.search("XRP")

    assert captured

    combined = " ".join(
        captured
    ).lower()

    assert "xrp" in combined
    assert (
        "trading strategy" in combined
        or "rsi" in combined
        or "moving average" in combined
    )


def test_web_research_adapter_uses_rule_focused_queries(
    monkeypatch,
):

    captured = []

    class FakeResponse:
        content = b"""
        <rss>
          <channel></channel>
        </rss>
        """

        def raise_for_status(self):
            pass

    def fake_get(url, params=None, **kwargs):
        captured.append(params["q"])
        return FakeResponse()

    monkeypatch.setattr(
        "requests.get",
        fake_get,
    )

    adapter = WebResearchAdapter()
    adapter.search("XRP-USD")

    combined = " ".join(
        captured
    ).lower()

    assert "xrp-usd" in combined
    assert (
        "below 30" in combined
        or "crosses above 30" in combined
        or "20 50" in combined
        or "golden cross" in combined
        or "breakout" in combined
    )


def test_web_research_adapter_fetches_article_text(
    monkeypatch,
):

    rss = """<?xml version="1.0"?>
    <rss version="2.0">
      <channel>
        <item>
          <title>XRP trading strategy</title>
          <description>
            <a href="https://example.com/xrp">
              XRP trading strategy
            </a>
          </description>
          <link>https://example.com/xrp</link>
          <pubDate>Mon, 25 Aug 2026 10:00:00 GMT</pubDate>
        </item>
      </channel>
    </rss>
    """

    article = """
    <html>
      <body>
        <nav>Navigation</nav>
        <article>
          <h1>XRP RSI Trading Strategy</h1>
          <p>
            Buy when RSI crosses above 30 after oversold
            conditions.
          </p>
          <p>
            Exit when RSI reaches 50.
          </p>
        </article>
      </body>
    </html>
    """

    class FakeResponse:
        def __init__(self, content):
            self.content = content

        def raise_for_status(self):
            pass

    responses = iter(
        [
            FakeResponse(
                rss.encode("utf-8")
            ),
            FakeResponse(
                article.encode("utf-8")
            ),
        ]
    )

    monkeypatch.setattr(
        "requests.get",
        lambda *args, **kwargs: next(responses),
    )

    adapter = WebResearchAdapter()

    # Keep the test to one query.
    adapter.QUERY_TEMPLATES = (
        "{symbol} trading strategy",
    )

    results = adapter.search("XRP-USD")

    assert results
    assert "RSI" in results[0]["summary"]
    assert "crosses above 30" in (
        results[0]["summary"]
    )


def test_web_research_adapter_keeps_rss_result_when_article_fetch_fails(
    monkeypatch,
):

    rss = """<?xml version="1.0"?>
    <rss version="2.0">
      <channel>
        <item>
          <title>XRP trading strategy</title>
          <description>
            <a href="https://example.com/xrp">
              XRP trading strategy
            </a>
          </description>
          <link>https://example.com/xrp</link>
        </item>
      </channel>
    </rss>
    """

    class FakeResponse:
        content = rss.encode("utf-8")

        def raise_for_status(self):
            pass

    def fake_get(url, *args, **kwargs):
        if "example.com" in url:
            raise RuntimeError(
                "article unavailable"
            )

        return FakeResponse()

    monkeypatch.setattr(
        "requests.get",
        fake_get,
    )

    adapter = WebResearchAdapter()

    adapter.QUERY_TEMPLATES = (
        "{symbol} trading strategy",
    )

    results = adapter.search("XRP-USD")

    assert len(results) == 1
    assert results[0]["title"] == (
        "XRP trading strategy"
    )
