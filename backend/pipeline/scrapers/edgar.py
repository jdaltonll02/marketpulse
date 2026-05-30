"""
pipeline/scrapers/edgar.py — Fetch real SEC 10-K/10-Q filing text from EDGAR.

Uses EDGAR's public APIs (no API key, no proxy required):
  - sec.gov/files/company_tickers.json  → ticker → CIK mapping
  - data.sec.gov/submissions/CIK{n}.json → filing metadata + primary document name
  - sec.gov/Archives/edgar/data/        → actual filing HTML

Extracts the MD&A (Management Discussion & Analysis) section —
the most signal-rich part of any 10-K or 10-Q.

Usage:
    from pipeline.scrapers.edgar import fetch_filing
    text, form_type, date = fetch_filing("AAPL")
"""
import re
import requests
from bs4 import BeautifulSoup

_HEADERS  = {"User-Agent": "MarketPulse research@marketpulse.ai"}
_SESSION  = requests.Session()
_SESSION.headers.update(_HEADERS)
_CIK_MAP: dict[str, tuple[str, str]] = {}   # ticker → (cik_padded, title)


def _get_cik(ticker: str) -> tuple[str, str]:
    t = ticker.upper()
    if t in _CIK_MAP:
        return _CIK_MAP[t]
    try:
        resp = _SESSION.get(
            "https://www.sec.gov/files/company_tickers.json", timeout=10
        )
        for entry in resp.json().values():
            if entry["ticker"].upper() == t:
                cik = str(entry["cik_str"]).zfill(10)
                _CIK_MAP[t] = (cik, entry.get("title", t))
                return _CIK_MAP[t]
    except Exception:
        pass
    return "", ""


def _get_latest_filing(cik_padded: str) -> dict | None:
    try:
        resp = _SESSION.get(
            f"https://data.sec.gov/submissions/CIK{cik_padded}.json", timeout=10
        )
        recent = resp.json().get("filings", {}).get("recent", {})
        forms   = recent.get("form", [])
        dates   = recent.get("filingDate", [])
        accnums = recent.get("accessionNumber", [])
        prim    = recent.get("primaryDocument", [])
        for i, form in enumerate(forms):
            if form in ("10-K", "10-Q"):
                return {
                    "form":      form,
                    "date":      dates[i]   if i < len(dates)   else "",
                    "accession": (accnums[i] if i < len(accnums) else "").replace("-", ""),
                    "primary":   prim[i]    if i < len(prim)    else "",
                }
    except Exception:
        pass
    return None


def _extract_mda(html: str) -> str:
    """Pull the MD&A section from a 10-K/10-Q HTML document."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "table"]):
        tag.decompose()
    text  = soup.get_text(separator=" ", strip=True)
    lower = text.lower()

    # Find start of Item 7 (MD&A)
    start = -1
    for pat in [r"item\s+7[\.\s]+management", r"management.s discussion and analysis"]:
        m = re.search(pat, lower)
        if m:
            start = m.start()
            break
    if start == -1:
        return text[:5000]

    # Find end of MD&A (Item 7A or Item 8)
    end = len(text)
    for pat in [r"item\s+7a[\.\s]", r"item\s+8[\.\s]"]:
        m = re.search(pat, lower[start + 200:])
        if m:
            end = start + 200 + m.start()
            break

    return text[start : min(end, start + 6000)]


def fetch_filing(ticker: str) -> tuple[str, str, str]:
    """
    Fetch the most recent 10-K or 10-Q MD&A section text.
    Returns (text, form_type, filing_date). Falls back to ("", "", "") on error.
    """
    print(f"  [EDGAR] Fetching filing for {ticker}...")
    cik_padded, _ = _get_cik(ticker)
    if not cik_padded:
        print(f"  [EDGAR] CIK not found for {ticker}")
        return "", "", ""

    filing = _get_latest_filing(cik_padded)
    if not filing or not filing["primary"]:
        print(f"  [EDGAR] No 10-K/10-Q found for {ticker}")
        return "", "", ""

    cik_int   = str(int(cik_padded))
    accession = filing["accession"]
    url = (
        f"https://www.sec.gov/Archives/edgar/data/"
        f"{cik_int}/{accession}/{filing['primary']}"
    )
    try:
        resp = _SESSION.get(url, timeout=25)
        resp.raise_for_status()
        text = _extract_mda(resp.text)
        print(f"  [EDGAR] {filing['form']} ({filing['date']}) — {len(text)} chars extracted")
        return text, filing["form"], filing["date"]
    except Exception as e:
        print(f"  [EDGAR] Document fetch error: {e}")
        return "", "", ""
