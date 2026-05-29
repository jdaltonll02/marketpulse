"""
utils/validator.py — Data quality validation for intelligence objects.
Run this before every demo to catch bad data early.
"""
from datetime import datetime, timezone
from pipeline.schema import IntelligenceObject, ValidationResult


def validate_intelligence_object(obj: IntelligenceObject) -> ValidationResult:
    """
    Run quality checks on a completed intelligence object.

    Returns a ValidationResult with a list of warnings and errors.
    Warnings = degraded data quality but usable.
    Errors   = object should not be served to users.
    """
    warnings = []
    errors   = []

    # Freshness
    age_s = (datetime.utcnow() - obj.generated_at.replace(tzinfo=None)).total_seconds()
    if age_s > 86400:
        warnings.append(f"Data is {age_s/3600:.0f}h old — consider re-running the pipeline")

    # News coverage
    news = obj.signals.news_sentiment
    if news.articles_analyzed == 0:
        errors.append("No news articles found — news signal is missing entirely")
    elif news.articles_analyzed < 5:
        warnings.append(f"Only {news.articles_analyzed} articles analysed — news signal may be unreliable")

    # Hiring data
    hiring = obj.signals.hiring_trend
    if not hiring.data_available:
        warnings.append("Hiring data unavailable — LinkedIn scraper returned no results")
    elif hiring.jobs_30d == 0:
        warnings.append("Zero recent job postings — company may not be actively hiring or scraper missed results")

    # Confidence range
    if obj.confidence < 20:
        warnings.append(f"Very low confidence ({obj.confidence}) — insufficient data to form a reliable view")
    if obj.confidence > 95:
        warnings.append(f"Suspiciously high confidence ({obj.confidence}) — verify signal inputs")

    # Required fields
    if not obj.ticker:
        errors.append("Missing ticker symbol")
    if not obj.company:
        errors.append("Missing company name")
    if not obj.recommended_action:
        warnings.append("No recommended action generated — synthesis may have failed")

    return ValidationResult(
        ticker=obj.ticker,
        passed=len(errors) == 0,
        warnings=warnings,
        errors=errors,
    )
