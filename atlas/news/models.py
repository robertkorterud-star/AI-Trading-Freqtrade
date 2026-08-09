"""
News Models
"""

from dataclasses import dataclass


@dataclass
class NewsArticle:

    title: str

    source: str

    summary: str

    url: str

    sentiment: str = "UNKNOWN"