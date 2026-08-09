"""
News Sentiment
"""


class SentimentAnalyzer:

    POSITIVE = [

        "up",

        "growth",

        "record",

        "beats",

        "strong",

        "surge",

        "profit",

        "buy",

    ]

    NEGATIVE = [

        "down",

        "loss",

        "lawsuit",

        "fall",

        "cuts",

        "sell",

        "bankruptcy",

    ]

    def analyze(self, text):

        score = 0

        lower = text.lower()

        for word in self.POSITIVE:

            if word in lower:

                score += 1

        for word in self.NEGATIVE:

            if word in lower:

                score -= 1

        if score > 0:

            return "BUY"

        if score < 0:

            return "SELL"

        return "HOLD"