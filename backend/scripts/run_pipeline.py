"""
Run the full MarketPulse pipeline for all seed companies.

Usage:
    python scripts/run_pipeline.py
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from config import SEED_TICKERS, MAX_PARALLEL
from pipeline.run import run_pipeline
from utils.logger import get_logger, _LOG_DIR

log = get_logger("run_pipeline")

results_file = _LOG_DIR / f"results_{datetime.utcnow().strftime('%Y-%m-%d_%H%M')}.json"

log.info(f"Starting parallel pipeline run for {len(SEED_TICKERS)} companies (max {MAX_PARALLEL} workers)")
log.info(f"Results will be saved to {results_file}")

results = []

# A8: run all companies in parallel
with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as executor:
    future_map = {
        executor.submit(run_pipeline, ticker, company): (ticker, company)
        for ticker, company in SEED_TICKERS
    }
    for future in as_completed(future_map):
        ticker, company = future_map[future]
        try:
            obj = future.result()
            results.append(obj.to_api_dict())
            log.info(f"  ✓ {ticker}: {obj.composite_signal} (confidence: {obj.confidence})")
        except Exception as e:
            log.error(f"  ✗ {ticker}: {e}")

with open(results_file, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, default=str)

log.info(f"Done. {len(results)} intelligence objects saved to {results_file}")

print("\n" + "=" * 60)
print(f"SUMMARY")
print("=" * 60)
for r in results:
    confidence = r["confidence"]
    signal = r["composite_signal"]
    ticker = r["ticker"]
    bar = "█" * (confidence // 10) + "░" * (10 - confidence // 10)
    print(f"  {ticker:<6} {signal:<8}  {bar}  {confidence}/100")
print("=" * 60)
print(f"Log : logs/pipeline_{datetime.utcnow().strftime('%Y-%m-%d')}.log")
print(f"JSON: {results_file.name}")
