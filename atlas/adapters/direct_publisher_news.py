"""
Direct publisher news adapters.

These adapters are best-effort and never make research fail
when a publisher blocks automated access.
"""

import json
import re
from html import unescape
from urllib.parse import quote

import requests


class DirectPublisherNewsAdapter:
    """Fetch publisher-specific news where possible."""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/151.0 Safari/537.36"
        )
    }

    TIMEOUT = 10
    MAX_RESULTS = 10

    def search(self, symbol: str) -> list[dict]:
        """
        Return direct publisher results.

        Failures are isolated per publisher.
        """

        symbol = (symbol or "").strip()

        if not symbol:
            return []

        results = []

        results.extend(
            self._yahoo_finance(symbol)
        )

        results.extend(
            self._reuters(symbol)
        )

        results.extend(
            self._wsj(symbol)
        )

        return results[: self.MAX_RESULTS * 3]

    def _request(
        self,
        url: str,
        params: dict | None = None,
    ) -> str:
        try:
            response = requests.get(
                url,
                params=params,
                headers=self.HEADERS,
                timeout=self.TIMEOUT,
            )

            response.raise_for_status()

            return response.text

        except Exception:
            return ""

    @staticmethod
    def _clean(text: str) -> str:
        text = unescape(
            text or ""
        )

        text = re.sub(
            r"<[^>]+>",
            " ",
            text,
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    def _yahoo_finance(
        self,
        symbol: str,
    ) -> list[dict]:
        """
        Yahoo Finance direct search/news endpoint.

        Yahoo currently exposes finance search/news content on
        finance.yahoo.com. :contentReference[oaicite:1]{index=1}
        """

        url = (
            "https://query2.finance.yahoo.com/"
            "v1/finance/search"
        )

        try:
            response = requests.get(
                url,
                params={
                    "q": symbol,
                    "newsCount": self.MAX_RESULTS,
                },
                headers=self.HEADERS,
                timeout=self.TIMEOUT,
            )

            response.raise_for_status()

            payload = response.json()

        except Exception:
            return []

        results = []

        for item in payload.get(
            "news",
            [],
        ):

            title = str(
                item.get(
                    "title",
                    "",
                )
            ).strip()

            link = str(
                item.get(
                    "link",
                    "",
                )
            ).strip()

            if not title or not link:
                continue

            publisher = str(
                item.get(
                    "publisher",
                    "Yahoo Finance",
                )
            ).strip()

            results.append(
                {
                    "source": "Yahoo Finance",
                    "publisher": publisher
                    or "Yahoo Finance",
                    "title": title,
                    "summary": "",
                    "sentiment": "neutral",
                    "url": link,
                    "published_at": str(
                        item.get(
                            "providerPublishTime",
                            "",
                        )
                    ),
                }
            )

        return results[: self.MAX_RESULTS]

    def _reuters(
        self,
        symbol: str,
    ) -> list[dict]:
        """Best-effort Reuters site search."""

        url = (
            "https://www.reuters.com/site-search/"
        )

        html = self._request(
            url,
            params={
                "query": symbol,
            },
        )

        if not html:
            return []

        results = []

        pattern = re.compile(
            r'href="(/[^"]+)"[^>]*>'
            r"([^<]{20,200})<",
            re.IGNORECASE,
        )

        seen = set()

        for match in pattern.finditer(html):

            href = match.group(1)
            title = self._clean(
                match.group(2)
            )

            if (
                not title
                or href in seen
                or href.startswith(
                    "/site-search"
                )
            ):
                continue

            if not (
                href.startswith("/world/")
                or href.startswith("/business/")
                or href.startswith("/markets/")
                or href.startswith("/technology/")
                or href.startswith("/legal/")
            ):
                continue

            seen.add(href)

            results.append(
                {
                    "source": "Reuters",
                    "publisher": "Reuters",
                    "title": title,
                    "summary": "",
                    "sentiment": "neutral",
                    "url": (
                        "https://www.reuters.com"
                        + href
                    ),
                    "published_at": "",
                }
            )

            if len(results) >= self.MAX_RESULTS:
                break

        return results

    def _wsj(
        self,
        symbol: str,
    ) -> list[dict]:
        """Best-effort Wall Street Journal search."""

        url = (
            "https://www.wsj.com/search"
        )

        html = self._request(
            url,
            params={
                "query": symbol,
            },
        )

        if not html:
            return []

        results = []

        # WSJ pages frequently contain JSON-LD or
        # serialized article metadata.
        json_blocks = re.findall(
            r'<script[^>]+type="application/'
            r'ld\+json"[^>]*>(.*?)</script>',
            html,
            flags=(
                re.IGNORECASE |
                re.DOTALL
            ),
        )

        for block in json_blocks:

            try:
                payload = json.loads(
                    unescape(block)
                )
            except Exception:
                continue

            objects = (
                payload
                if isinstance(payload, list)
                else [payload]
            )

            for item in objects:

                if not isinstance(item, dict):
                    continue

                title = str(
                    item.get(
                        "headline",
                        "",
                    )
                ).strip()

                link = str(
                    item.get(
                        "url",
                        "",
                    )
                ).strip()

                if not title or not link:
                    continue

                results.append(
                    {
                        "source":
                            "Wall Street Journal",
                        "publisher":
                            "Wall Street Journal",
                        "title": title,
                        "summary": str(
                            item.get(
                                "description",
                                "",
                            )
                        ).strip(),
                        "sentiment":
                            "neutral",
                        "url": link,
                        "published_at": str(
                            item.get(
                                "datePublished",
                                "",
                            )
                        ),
                    }
                )

        return results[: self.MAX_RESULTS]
