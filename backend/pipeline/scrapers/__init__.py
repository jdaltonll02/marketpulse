"""
pipeline/scrapers — Data ingestion layer.

Each module fetches raw data from one external source.
No signal logic or AI calls live here.

Modules
-------
serp.py         Bright Data SERP API — news articles and hiring signals via Google News
unlocker.py     SEC EDGAR (direct HTTP) + Yahoo Finance (yfinance library)
linkedin.py     LinkedIn Jobs via Bright Data Web Scraper API (datasets require purchase;
                hiring signals currently sourced from serp.py instead)

Usage
-----
    from pipeline.scrapers import (
        fetch_ticker_news,
        fetch_hiring_via_serp,
        fetch_sec_filing_text,
        fetch_yahoo_finance,
    )
"""
from pipeline.scrapers.serp     import fetch_ticker_news, fetch_hiring_via_serp, fetch_competitor_news
from pipeline.scrapers.unlocker import fetch_sec_filing_text, fetch_yahoo_finance

__all__ = [
    "fetch_ticker_news",
    "fetch_hiring_via_serp",
    "fetch_competitor_news",
    "fetch_sec_filing_text",
    "fetch_yahoo_finance",
]
