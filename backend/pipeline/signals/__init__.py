"""
pipeline/signals — Signal analysis layer.

Converts raw scraper output into typed, scored signal objects.
Pure domain logic — no API calls, no imports from synthesis.

Modules
-------
news.py         Keyword-based sentiment scoring → NewsSentimentSignal
                Contains BULLISH_WORDS and BEARISH_WORDS lists
hiring.py       Hiring signal derived from news articles → HiringTrendSignal
                analyse_hiring()          — from raw LinkedIn job records
                analyse_hiring_from_news() — from SERP news articles (active path)

Usage
-----
    from pipeline.signals import analyse_news, analyse_hiring_from_news
"""
from pipeline.signals.news   import analyse_news
from pipeline.signals.hiring import analyse_hiring_from_news, analyse_hiring

__all__ = [
    "analyse_news",
    "analyse_hiring_from_news",
    "analyse_hiring",
]
