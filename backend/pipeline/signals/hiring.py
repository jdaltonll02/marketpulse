"""
signals/hiring.py — Analyse raw LinkedIn job data into a HiringTrendSignal.
"""
from collections import Counter
from datetime import datetime, timedelta
from pipeline.schema import HiringTrendSignal


def analyse_hiring(jobs: list[dict]) -> HiringTrendSignal:
    """
    Turn raw LinkedIn job records into a structured hiring signal.

    Args:
        jobs: Raw list of job dicts from scrapers/linkedin.py

    Returns:
        HiringTrendSignal with jobs_30d count, top departments, and a signal label.
    """
    if not jobs:
        return HiringTrendSignal(
            jobs_30d=0,
            signal="NEUTRAL",
            data_available=False,
        )

    now = datetime.utcnow()
    cutoff = now - timedelta(days=30)

    recent = []
    for job in jobs:
        posted_raw = job.get("posted_date") or job.get("date_posted") or ""
        try:
            posted = datetime.fromisoformat(posted_raw.replace("Z", ""))
            if posted >= cutoff:
                recent.append(job)
        except (ValueError, TypeError):
            # If date is missing/unparseable, include it conservatively
            recent.append(job)

    dept_counter = Counter(
        job.get("department") or job.get("job_function") or "Unknown"
        for job in recent
    )
    top_depts = [d for d, _ in dept_counter.most_common(5) if d != "Unknown"]

    jobs_30d = len(recent)

    # Signal thresholds — adjust based on backtest results
    if jobs_30d >= 50:
        signal = "BULLISH"
    elif jobs_30d >= 10:
        signal = "NEUTRAL"
    else:
        signal = "BEARISH"

    return HiringTrendSignal(
        jobs_30d=jobs_30d,
        top_departments=top_depts,
        signal=signal,
        data_available=True,
    )

def analyse_hiring_from_news(articles: list[dict]) -> HiringTrendSignal:
    """Derive hiring signal from news articles when job data is unavailable."""
    if not articles:
        return HiringTrendSignal(jobs_30d=0, signal="NEUTRAL", data_available=False)

    HIRING_POSITIVE = [
        "hiring", "expanding", "headcount", "new roles",
        "recruiting", "growth", "workforce", "talent",
    ]
    HIRING_NEGATIVE = [
        "layoff", "layoffs", "cuts", "freeze",
        "redundan", "downsiz", "job cut", "let go",
    ]

    positive = 0
    negative = 0
    for a in articles:
        text = (a.get("title", "") + " " + a.get("snippet", "")).lower()
        positive += sum(1 for w in HIRING_POSITIVE if w in text)
        negative += sum(1 for w in HIRING_NEGATIVE if w in text)

    # Use keyword balance, not article count thresholds
    if positive > negative:
        signal = "BULLISH"
    elif negative > positive:
        signal = "BEARISH"
    else:
        signal = "NEUTRAL"

    return HiringTrendSignal(
        jobs_30d=len(articles),
        signal=signal,
        data_available=True,
    )