from html import unescape
from re import sub
from xml.etree import ElementTree

import requests


class WebResearchAdapter:
    """Fetch strategy-oriented web research via Google News RSS."""

    BASE_URL = "https://news.google.com/rss/search"

    QUERY_TEMPLATES = (
        "{symbol} RSI oversold below 30",
        "{symbol} RSI crosses above 30",
        "{symbol} moving average 20 50 crossover",
        "{symbol} golden cross",
        "{symbol} breakout entry exit",
        "{symbol} trading strategy",
        "{symbol} momentum strategy",
    )

    MAX_RESULTS = 20
    ARTICLE_FETCH_LIMIT = 5

    @staticmethod
    def _strip_html(text: str) -> str:
        """Convert simple HTML content into readable text."""

        text = unescape(text or "")
        text = sub(
            r"<(script|style)[^>]*>.*?</\1>",
            " ",
            text,
            flags=__import__("re").IGNORECASE
            | __import__("re").DOTALL,
        )
        text = sub(
            r"<[^>]+>",
            " ",
            text,
        )
        text = sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    def _fetch_article_text(
        self,
        url: str,
    ) -> str:
        """Fetch a bounded amount of readable article text."""

        if not url:
            return ""

        try:
            response = requests.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 "
                        "(Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 "
                        "(KHTML, like Gecko) "
                        "Chrome/151.0 Safari/537.36"
                    )
                },
                timeout=10,
            )

            response.raise_for_status()

        except Exception:
            return ""

        html_text = response.content.decode(
            "utf-8",
            errors="ignore",
        )

        # Prefer actual article content.
        matches = []

        for tag in ("article", "main"):
            matches.extend(
                __import__("re").findall(
                    rf"<{tag}\\b[^>]*>(.*?)</{tag}>",
                    html_text,
                    flags=__import__("re").IGNORECASE
                    | __import__("re").DOTALL,
                )
            )

        if matches:
            html_text = max(
                matches,
                key=len,
            )
        else:
            body_matches = __import__("re").findall(
                r"<body\\b[^>]*>(.*?)</body>",
                html_text,
                flags=__import__("re").IGNORECASE
                | __import__("re").DOTALL,
            )

            if body_matches:
                html_text = max(
                    body_matches,
                    key=len,
                )

        # Remove common non-content elements after selecting
        # the semantic content container.
        html_text = sub(
            r"<(script|style|nav|header|footer|aside|form)[^>]*>.*?</\\1>",
            " ",
            html_text,
            flags=__import__("re").IGNORECASE
            | __import__("re").DOTALL,
        )

        text = self._strip_html(
            html_text
        )

        # Keep research payloads bounded for downstream AI analysis.
        return text[:8000]

    def search(
        self,
        symbol: str,
        focus: tuple[str, ...] | None = None,
    ) -> list[dict]:
        """Return normalized web research items."""

        normalized = (symbol or "").strip()

        if not normalized:
            return []

        results = []
        seen_urls = set()
        article_fetches = 0

        templates = (
            tuple(
                f"{{symbol}} {term} strategy"
                for term in focus
            )
            if focus
            else self.QUERY_TEMPLATES
        )

        for template in templates:

            query = template.format(
                symbol=normalized
            )

            try:
                response = requests.get(
                    self.BASE_URL,
                    params={
                        "q": query,
                        "hl": "en",
                        "gl": "US",
                        "ceid": "US:en",
                    },
                    timeout=10,
                )

                response.raise_for_status()

                root = ElementTree.fromstring(
                    response.content
                )

            except Exception:
                continue

            for item in root.findall(".//item"):

                title = (
                    item.findtext(
                        "title",
                        "",
                    )
                    or ""
                ).strip()

                summary = (
                    item.findtext(
                        "description",
                        "",
                    )
                    or ""
                ).strip()

                url = (
                    item.findtext(
                        "link",
                        "",
                    )
                    or ""
                ).strip()

                published_at = (
                    item.findtext(
                        "pubDate",
                        "",
                    )
                    or ""
                ).strip()

                publisher = (
                    item.findtext(
                        "source",
                        "",
                    )
                    or ""
                ).strip()

                if not title:
                    continue

                if url and url in seen_urls:
                    continue

                if url:
                    seen_urls.add(url)

                if (
                    url
                    and article_fetches
                    < self.ARTICLE_FETCH_LIMIT
                ):
                    article_text = (
                        self._fetch_article_text(url)
                    )

                    article_fetches += 1

                    if article_text:
                        summary = article_text

                results.append(
                    {
                        "source": "Google News",
                        "publisher": publisher,
                        "title": title,
                        "summary": summary,
                        "sentiment": "neutral",
                        "url": url,
                        "published_at": published_at,
                        "research_query": query,
                    }
                )

        return results[: self.MAX_RESULTS]
