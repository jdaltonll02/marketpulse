"""
pipeline/run.py — Main pipeline orchestrator.

Runs the full ingestion → signal analysis → synthesis loop for one company
and returns a validated IntelligenceObject.

Usage:
    python -m pipeline.run --ticker AAPL --company "Apple Inc."
    python -m pipeline.run --ticker MSFT --company "Microsoft"
"""
import argparse, json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from pipeline.scrapers.serp     import fetch_ticker_news, fetch_hiring_via_serp
from pipeline.scrapers.unlocker import fetch_sec_filing_text, fetch_yahoo_finance
from pipeline.signals.hiring    import analyse_hiring_from_news
from pipeline.signals.news      import analyse_news
from pipeline.synthesis.multi_agent import synthesise_multi_agent
from pipeline.synthesis.agent       import synthesise as synthesise_single, store_context

from pipeline.schema import (
    IntelligenceObject, Signals,
    FilingLanguageSignal, PricingSignal,
)
from utils.validator import validate_intelligence_object
from utils.logger    import get_logger

log = get_logger(__name__)


def run_pipeline(ticker: str, company: str) -> IntelligenceObject:
    """
    Full pipeline for one company. Returns a validated IntelligenceObject.

    Steps:
        1. Ingest — fetch data from all Bright Data sources
        2. Analyse — convert raw data to typed signal objects
        3. Synthesise — Claude agent produces confidence score + composite signal
        4. Validate — check data quality, log warnings
        5. Return — typed IntelligenceObject ready for the API
    """
    log.info(f"Starting pipeline for {ticker} ({company})")
    started = datetime.utcnow()

    # ── 1. Ingest — A8: parallel fetch all sources simultaneously ────────────────
    log.info("  Step 1/4: Ingesting data (parallel fetch)...")

    with ThreadPoolExecutor(max_workers=4) as pool:
        f_hiring  = pool.submit(fetch_hiring_via_serp, company, 30)
        f_news    = pool.submit(fetch_ticker_news, ticker, company, 7)
        f_filing  = pool.submit(fetch_sec_filing_text, ticker)
        f_yf      = pool.submit(fetch_yahoo_finance, ticker)
        hiring_articles = f_hiring.result()
        articles        = f_news.result()
        filing_txt      = f_filing.result()
        yf_data         = f_yf.result()

    # ── 2. Signal analysis ────────────────────────────────────────────────────
    log.info("  Step 2/4: Analysing signals...")

    # ── CHANGED: replaced analyse_hiring with analyse_hiring_from_news
    hiring_signal = analyse_hiring_from_news(hiring_articles)
    news_signal   = analyse_news(articles, company)

    # TODO Day 3: implement a real filing language parser
    filing_signal = FilingLanguageSignal(
        guidance_tone="neutral",
        signal="NEUTRAL",
        key_phrases=[],
    )

    # TODO Day 3: implement pricing signal from Web Unlocker
    pricing_signal = PricingSignal(signal="NEUTRAL")

    signals = Signals(
        news_sentiment=news_signal,
        hiring_trend=hiring_signal,
        filing_language=filing_signal,
        pricing=pricing_signal,
    )

    # ── 3. Synthesise — A7: multi-agent with single-agent fallback ───────────────
    log.info("  Step 3/4: Running multi-agent Claude synthesis...")

    extra_parts = []
    if filing_txt:
        extra_parts.append(f"SEC EDGAR filing text:\n{filing_txt[:2000]}")
    if yf_data:
        extra_parts.append(f"Yahoo Finance metrics:\n{json.dumps(yf_data, indent=2)}")
    extra_context = "\n\n".join(extra_parts)

    try:
        assessment = synthesise_multi_agent(ticker, company, signals, extra_context)
        log.info("  [Multi-agent] Orchestrator synthesis complete")
    except Exception as e:
        log.warning(f"  [Multi-agent] Failed ({e}) — falling back to single agent")
        assessment = synthesise_single(ticker, company, signals, extra_context)

    # ── 4. Build and validate ─────────────────────────────────────────────────
    log.info("  Step 4/4: Building intelligence object...")

    obj = IntelligenceObject(
        ticker=ticker,
        company=company,
        generated_at=started,
        confidence=assessment.get("confidence", 50),
        composite_signal=assessment.get("composite_signal", "NEUTRAL"),
        signals=signals,
        key_risks=assessment.get("key_risks", []),
        recommended_action=assessment.get("recommended_action", ""),
        # ── CHANGED: updated data sources list
        data_sources_used=[
            "Bright Data SERP API (news)",
            "Bright Data SERP API (hiring)",
            "SEC EDGAR (direct)",
            "Yahoo Finance (yfinance)",
            "Multi-agent synthesis (4 specialists + orchestrator)",
        ],
    )

    result = validate_intelligence_object(obj)
    if result.warnings:
        for w in result.warnings:
            log.warning(f"  WARN: {w}")
    if result.errors:
        for e in result.errors:
            log.error(f"  ERROR: {e}")

    # A6: store result in vector memory for future context retrieval
    store_context(
        ticker=ticker,
        doc_id=started.strftime("%Y%m%d_%H%M"),
        text=(
            f"{company} ({ticker}) — {obj.composite_signal} confidence:{obj.confidence} — "
            f"news:{obj.signals.news_sentiment.label} hiring:{obj.signals.hiring_trend.signal} — "
            f"{obj.recommended_action}"
        ),
        doc_type="intelligence",
    )

    elapsed = (datetime.utcnow() - started).total_seconds()
    log.info(f"Pipeline complete for {ticker} in {elapsed:.1f}s — signal: {obj.composite_signal} (confidence: {obj.confidence})")

    return obj


# ── CLI entrypoint ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the MarketPulse pipeline for one company")
    parser.add_argument("--ticker",  required=True, help="Stock ticker (e.g. AAPL)")
    parser.add_argument("--company", required=True, help="Company name (e.g. 'Apple Inc.')")
    args = parser.parse_args()

    import json
    result = run_pipeline(args.ticker, args.company)
    print("\n" + "="*60)
    print(json.dumps(result.to_api_dict(), indent=2, default=str))