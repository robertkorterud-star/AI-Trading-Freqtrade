"""
News Engine
"""

from atlas.news.adapter import NewsAdapter
from atlas.news.sentiment import SentimentAnalyzer


class NewsEngine:

    def __init__(self):

        self.adapter = NewsAdapter()

        self.sentiment = SentimentAnalyzer()

    def latest(self):

        news = self.adapter.latest()

        for article in news:

            article.sentiment = self.sentiment.analyze(

                article.title + " " + article.summary

            )

        return news