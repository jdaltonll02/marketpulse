import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import SEED_TICKERS
from pipeline.run import run_pipeline

print(f"Running pipeline for {len(SEED_TICKERS)} companies...\n")

for ticker, company in SEED_TICKERS:
    print("=" * 60)
    print(f"  {ticker} — {company}")
    print("=" * 60)
    result = run_pipeline(ticker, company)
    print(json.dumps(result.to_api_dict(), indent=2, default=str))
    print()
