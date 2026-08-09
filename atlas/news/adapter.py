"""
News Adapter
"""

import os
from datetime import date, timedelta

import requests
from dotenv import load_dotenv

from atlas.news.models import NewsArticle

load_dotenv()


class NewsAdapter:

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self):

        self.api_key = os.getenv("FINNHUB_API_KEY")

    def latest(self):

        today = date.today()

        week = today - timedelta(days=7)

        response = requests.get(

            f"{self.BASE_URL}/news",

            params={

                "category": "general",

                "minId": 0,

                "token": self.api_key,

            },

            timeout=10,

        )

        response.raise_for_status()

        data = response.json()

        news = []

        for article in data:

            news.append(

                NewsArticle(

                    title=article.get("headline", ""),

                    source=article.get("source", ""),

                    summary=article.get("summary", ""),

                    url=article.get("url", ""),

                )

            )

        return news