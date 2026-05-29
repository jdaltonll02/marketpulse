import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.scrapers.unlocker import fetch_sec_filing_text, fetch_yahoo_finance

# ── Test 1: SEC EDGAR ─────────────────────────────────────────────────────────
print("=" * 50)
print("Test 1: SEC EDGAR filing (AAPL)")
print("=" * 50)
filing = fetch_sec_filing_text("AAPL")
print(f"Got {len(filing)} chars")
if filing:
    print(filing[:400])
else:
    print("No filing text returned")

# ── Test 2: Yahoo Finance ─────────────────────────────────────────────────────
print()
print("=" * 50)
print("Test 2: Yahoo Finance quote (AAPL)")
print("=" * 50)
yf_data = fetch_yahoo_finance("AAPL")
print(f"Got {len(yf_data)} fields")
if yf_data:
    for k, v in list(yf_data.items())[:8]:
        print(f"  {k}: {v}")
else:
    print("No Yahoo Finance data returned")
