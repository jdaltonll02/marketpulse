"""
tests/test_signals.py — Unit tests for signal analysers.
These run without any API calls — pure logic tests.

Run: pytest backend/tests/ -v
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.signals.hiring import analyse_hiring
from pipeline.signals.news   import analyse_news


# ── Hiring signal tests ───────────────────────────────────────────────────────

def test_hiring_bullish_on_many_jobs():
    jobs = [{"posted_date": "2026-05-20", "department": "Engineering"} for _ in range(60)]
    result = analyse_hiring(jobs)
    assert result.signal == "BULLISH"
    assert result.jobs_30d == 60

def test_hiring_neutral_on_moderate_jobs():
    jobs = [{"posted_date": "2026-05-20", "department": "Sales"} for _ in range(25)]
    result = analyse_hiring(jobs)
    assert result.signal == "NEUTRAL"

def test_hiring_bearish_on_no_jobs():
    result = analyse_hiring([])
    assert result.signal == "NEUTRAL"
    assert result.data_available is False
    assert result.jobs_30d == 0

def test_hiring_top_departments():
    jobs = (
        [{"posted_date": "2026-05-20", "department": "Engineering"}] * 10 +
        [{"posted_date": "2026-05-20", "department": "Sales"}] * 5
    )
    result = analyse_hiring(jobs)
    assert "Engineering" in result.top_departments
    assert result.top_departments[0] == "Engineering"


# ── News sentiment tests ──────────────────────────────────────────────────────

def test_news_bullish_on_positive_articles():
    articles = [
        {"title": "Apple beats Q2 estimates", "snippet": "record revenue growth", "source": "Reuters"},
        {"title": "Apple raises guidance", "snippet": "strong demand expansion", "source": "Bloomberg"},
    ]
    result = analyse_news(articles, "Apple")
    assert result.label == "BULLISH"
    assert result.articles_analyzed == 2

def test_news_bearish_on_negative_articles():
    articles = [
        {"title": "Apple misses revenue estimate", "snippet": "revenue decline warning", "source": "WSJ"},
        {"title": "Apple CEO resignation", "snippet": "investigation probe", "source": "FT"},
    ]
    result = analyse_news(articles, "Apple")
    assert result.label == "BEARISH"

def test_news_neutral_on_empty():
    result = analyse_news([], "Apple")
    assert result.label == "NEUTRAL"
    assert result.articles_analyzed == 0

def test_news_score_range():
    articles = [{"title": "Apple reports earnings", "snippet": "mixed results", "source": "CNBC"}]
    result = analyse_news(articles, "Apple")
    assert -1.0 <= result.score <= 1.0
