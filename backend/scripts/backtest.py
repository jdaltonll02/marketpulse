"""
Backtest the MarketPulse pipeline against known earnings outcomes.

For each company, we know what actually happened at their most recent earnings.
We compare our signal (BULLISH/BEARISH/NEUTRAL) against the actual outcome
(beat/miss) to produce a directional accuracy score.

Usage:
    python scripts/backtest.py

Outcomes sourced from public earnings reports (Q1 2026 / most recent available).
Beat  = company beat EPS and/or revenue estimate AND stock reacted positively.
Miss  = company missed estimate OR beat but stock fell on guidance concerns.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.run import run_pipeline
from utils.logger import get_logger, _LOG_DIR
from datetime import datetime

log = get_logger("backtest")

# ── Ground truth: actual earnings outcomes ────────────────────────────────────
# Format: (ticker, company, actual_outcome, notes)
GROUND_TRUTH = [
    ("AAPL",  "Apple Inc.",             "NEUTRAL", "Q1 2026: beat EPS, services growth, but stock flat on tariff concerns"),
    ("MSFT",  "Microsoft Corporation",  "BULLISH", "Q3 FY2026: beat on cloud/Azure, raised guidance, stock +5%"),
    ("NVDA",  "NVIDIA Corporation",     "BULLISH", "Q1 FY2026: massive beat, data center revenue surged, stock +9%"),
    ("META",  "Meta Platforms",         "BEARISH", "Q1 2026: beat EPS but stock fell on rising AI capex, expense concerns"),
    ("GOOGL", "Alphabet Inc.",          "BULLISH", "Q1 2026: strong beat, search + cloud both accelerated, stock +10%"),
    ("AMZN",  "Amazon.com Inc.",        "BULLISH", "Q1 2026: beat on AWS and advertising, raised guidance"),
    ("TSLA",  "Tesla Inc.",             "BEARISH", "Q1 2026: missed revenue, margin pressure, lowered delivery outlook"),
    ("CRWD",  "CrowdStrike Holdings",   "BULLISH", "Q4 FY2026: beat on ARR growth, strong net new logo adds"),
    ("PLTR",  "Palantir Technologies",  "BULLISH", "Q1 2026: US commercial beat, raised full-year guidance"),
    ("NFLX",  "Netflix Inc.",           "BULLISH", "Q1 2026: beat on subscribers and revenue, ad tier accelerating"),
]

# ── Signal direction mapping ──────────────────────────────────────────────────
def is_correct(predicted: str, actual: str) -> bool:
    """BULLISH vs BULLISH = correct. NEUTRAL treated as abstain (not counted)."""
    if predicted == "NEUTRAL":
        return None   # abstain
    return predicted == actual


# ── Run backtest ──────────────────────────────────────────────────────────────
results = []
correct = 0
wrong   = 0
abstain = 0

log.info(f"Running backtest on {len(GROUND_TRUTH)} companies...")
print()

for ticker, company, actual, notes in GROUND_TRUTH:
    log.info(f"Processing {ticker}...")
    obj       = run_pipeline(ticker, company)
    predicted = obj.composite_signal
    outcome   = is_correct(predicted, actual)

    if outcome is True:
        correct += 1
        verdict = "✓ CORRECT"
    elif outcome is False:
        wrong   += 1
        verdict = "✗ WRONG"
    else:
        abstain += 1
        verdict = "~ ABSTAIN"

    results.append({
        "ticker":    ticker,
        "predicted": predicted,
        "actual":    actual,
        "correct":   outcome,
        "confidence": obj.confidence,
        "verdict":   verdict,
        "notes":     notes,
    })

    print(f"  {ticker:<6} predicted={predicted:<8} actual={actual:<8} conf={obj.confidence:>3}%  {verdict}")

# ── Summary ───────────────────────────────────────────────────────────────────
decided   = correct + wrong
accuracy  = (correct / decided * 100) if decided else 0

print()
print("=" * 60)
print(f"BACKTEST RESULTS — {len(GROUND_TRUTH)} companies")
print("=" * 60)
print(f"  Correct  : {correct}/{decided} directional calls")
print(f"  Wrong    : {wrong}/{decided}")
print(f"  Abstained: {abstain} (NEUTRAL signals)")
print(f"  Accuracy : {accuracy:.0f}% on decided calls")
print("=" * 60)

# Save results
out_file = _LOG_DIR / f"backtest_{datetime.utcnow().strftime('%Y-%m-%d_%H%M')}.json"
with open(out_file, "w") as f:
    json.dump({
        "accuracy":  round(accuracy, 1),
        "correct":   correct,
        "wrong":     wrong,
        "abstained": abstain,
        "results":   results,
    }, f, indent=2)

log.info(f"Backtest saved to {out_file}")
