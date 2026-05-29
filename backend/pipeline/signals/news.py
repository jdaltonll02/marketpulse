"""
signals/news.py — Analyse raw SERP articles into a NewsSentimentSignal.
"""
from pipeline.schema import NewsSentimentSignal

# Keyword lists — tune these based on your backtest results
BULLISH_WORDS = [
    "beat", "beats", "exceeded", "record", "growth", "raised guidance",
    "upgrade", "outperform", "strong demand", "expansion", "partnership",
    "acquisition", "raised", "buyback", "dividend increase", "top estimate",
    "surged", "surge", "boost", "boosted", "jumped", "rally", "rallied",
    "soared", "lifted", "strong earnings", "profit rise", "revenue beat",
]
BEARISH_WORDS = [
    "miss", "missed", "downgrade", "layoff", "layoffs", "lawsuit", "loss",
    "decline", "warning", "probe", "investigation", "recall", "bankruptcy",
    "cut guidance", "below estimate", "underperform", "revenue warning",
    "executive departure", "CEO resign", "fraud", "breach",
]


def _score_article(text: str) -> float:
    """Return a sentiment score for a single article text."""
    text_lower = text.lower()
    bull = sum(1 for w in BULLISH_WORDS if w in text_lower)
    bear = sum(1 for w in BEARISH_WORDS if w in text_lower)
    return float(bull - bear)


def analyse_news(articles: list[dict], company: str) -> NewsSentimentSignal:
    """
    Score a list of news articles and return a NewsSentimentSignal.

    Args:
        articles: List of article dicts from scrapers/serp.py
        company:  Company name — used to filter only relevant articles

    Returns:
        NewsSentimentSignal
    """
    if not articles:
        return NewsSentimentSignal(
            score=0.0,
            label="NEUTRAL",
            articles_analyzed=0,
        )

    # Use all articles — the SERP query already targets the company,
    # so every result is relevant by construction.
    relevant = articles

    scores = []
    for article in relevant:
        text = article.get("title", "") + " " + article.get("snippet", "")
        scores.append(_score_article(text))

    avg = sum(scores) / len(scores) if scores else 0.0
    # Normalise to -1..1 range
    norm = max(-1.0, min(1.0, avg / 3.0))

    if norm > 0.15:
        label = "BULLISH"
    elif norm < -0.15:
        label = "BEARISH"
    else:
        label = "NEUTRAL"

    return NewsSentimentSignal(
        score=round(norm, 3),
        label=label,
        articles_analyzed=len(relevant),
        top_headlines=[a.get("title", "") for a in relevant[:3]],
        sources=list({a.get("source", "") for a in relevant if a.get("source")})[:5],
    )
