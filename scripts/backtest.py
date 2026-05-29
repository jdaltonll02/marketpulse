"""
scripts/backtest.py — Run the pipeline against companies with known earnings outcomes.

Usage:
    python scripts/backtest.py

Output:
    Prints accuracy report and saves results to docs/backtest_results.md
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from datetime import datetime

# Companies with known recent earnings outcomes.
# actual: "BEAT" if EPS beat consensus, "MISS" if missed.
# Replace with real data — check earnings calendars for Q1 2026 results.
BACKTEST_SET = [
    {"ticker": "AAPL",  "company": "Apple Inc.",             "earnings_date": "2026-05-01", "actual": "BEAT"},
    {"ticker": "MSFT",  "company": "Microsoft Corporation",  "earnings_date": "2026-04-29", "actual": "BEAT"},
    {"ticker": "META",  "company": "Meta Platforms",         "earnings_date": "2026-04-23", "actual": "BEAT"},
    {"ticker": "GOOGL", "company": "Alphabet Inc.",          "earnings_date": "2026-04-29", "actual": "MISS"},
    {"ticker": "AMZN",  "company": "Amazon.com Inc.",        "earnings_date": "2026-05-01", "actual": "BEAT"},
    # Add 10+ more companies for statistical significance
    # Find Q1 2026 earnings dates at: https://finance.yahoo.com/calendar/earnings
]


def run_backtest():
    from pipeline.run import run_pipeline

    results = []
    print(f"Running backtest on {len(BACKTEST_SET)} companies...\n")

    for entry in BACKTEST_SET:
        ticker  = entry["ticker"]
        company = entry["company"]
        actual  = entry["actual"]

        print(f"Testing {ticker}...")
        try:
            obj = run_pipeline(ticker, company)
            # Map composite signal to predicted direction
            predicted = "BEAT" if obj.composite_signal == "BULLISH" else "MISS"
            correct   = predicted == actual

            results.append({
                "ticker":     ticker,
                "predicted":  predicted,
                "actual":     actual,
                "signal":     obj.composite_signal,
                "confidence": obj.confidence,
                "correct":    correct,
            })
            status = "✓" if correct else "✗"
            print(f"  {status} Predicted {predicted}, Actual {actual} (confidence: {obj.confidence})\n")

        except Exception as e:
            print(f"  ERROR: {e}\n")
            results.append({"ticker": ticker, "error": str(e), "correct": False})

    # Accuracy
    n_results = [r for r in results if "error" not in r]
    accuracy  = sum(r["correct"] for r in n_results) / len(n_results) if n_results else 0

    # Calibration by confidence band
    bands = {"high (>70)": [], "mid (40-70)": [], "low (<40)": []}
    for r in n_results:
        c = r.get("confidence", 50)
        if c > 70:   bands["high (>70)"].append(r["correct"])
        elif c >= 40: bands["mid (40-70)"].append(r["correct"])
        else:         bands["low (<40)"].append(r["correct"])

    print("="*50)
    print(f"BACKTEST RESULTS — {datetime.utcnow().strftime('%Y-%m-%d')}")
    print(f"Companies tested: {len(BACKTEST_SET)}")
    print(f"Successful runs:  {len(n_results)}")
    print(f"Overall accuracy: {accuracy*100:.1f}%")
    print()
    print("Calibration by confidence band:")
    for band, vals in bands.items():
        if vals:
            pct = sum(vals)/len(vals)*100
            print(f"  {band}: {pct:.1f}% accurate (n={len(vals)})")

    # Save to docs
    os.makedirs("docs", exist_ok=True)
    with open("docs/backtest_results.md", "w") as f:
        f.write(f"# Backtest Results\n\n")
        f.write(f"**Run date:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n\n")
        f.write(f"**Overall accuracy:** {accuracy*100:.1f}% on {len(n_results)} companies\n\n")
        f.write("| Ticker | Predicted | Actual | Correct | Confidence |\n")
        f.write("|--------|-----------|--------|---------|------------|\n")
        for r in results:
            if "error" not in r:
                mark = "✓" if r["correct"] else "✗"
                f.write(f"| {r['ticker']} | {r['predicted']} | {r['actual']} | {mark} | {r['confidence']} |\n")
        f.write(f"\n**Calibration:**\n\n")
        for band, vals in bands.items():
            if vals:
                f.write(f"- {band}: {sum(vals)/len(vals)*100:.1f}% accurate (n={len(vals)})\n")

    print("\nResults saved to docs/backtest_results.md")
    return accuracy


if __name__ == "__main__":
    run_backtest()
