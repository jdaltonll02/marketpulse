"""
pipeline/scrapers/edgar.py — Fetch real SEC 10-K/10-Q filing text from EDGAR.

Performance optimisations:
  - company_tickers.json loaded once at module import (not per request)
  - 10-K documents streamed with a 1MB cap (full 10-K is 5-10MB — unnecessary)
  - Results cached in MongoDB so repeated calls skip the download entirely
  - Parallel CIK lookups across the 5 seed companies share one downloaded map

Usage:
    from pipeline.scrapers.edgar import fetch_filing
    text, form_type, date = fetch_filing("AAPL")
"""
import re
import threading
import requests
from bs4 import BeautifulSoup

_HEADERS    = {"User-Agent": "MarketPulse research@marketpulse.ai"}
_SESSION    = requests.Session()
_SESSION.headers.update(_HEADERS)

# CIK map loaded once at startup and shared across all threads
_CIK_MAP:  dict[str, tuple[str, str]] = {}
_CIK_LOCK  = threading.Lock()
_CIK_READY = False
_DOC_CACHE: dict[str, tuple[str, str, str]] = {}  # ticker → (text, form, date)

_MAX_BYTES = 1_000_000   # stream cap — 10-Ks are 5-10MB, we need ~1MB to reach MD&A


def _load_cik_map():
    """Download company_tickers.json once and populate _CIK_MAP."""
    global _CIK_READY
    with _CIK_LOCK:
        if _CIK_READY:
            return
        try:
            resp = _SESSION.get(
                "https://www.sec.gov/files/company_tickers.json", timeout=15
            )
            for entry in resp.json().values():
                t = entry["ticker"].upper()
                _CIK_MAP[t] = (str(entry["cik_str"]).zfill(10), entry.get("title", t))
            _CIK_READY = True
        except Exception as e:
            print(f"  [EDGAR] CIK map load failed: {e}")


def _get_cik(ticker: str) -> tuple[str, str]:
    if not _CIK_READY:
        _load_cik_map()
    return _CIK_MAP.get(ticker.upper(), ("", ""))


def _get_latest_filing(cik_padded: str) -> dict | None:
    try:
        resp = _SESSION.get(
            f"https://data.sec.gov/submissions/CIK{cik_padded}.json", timeout=10
        )
        recent  = resp.json().get("filings", {}).get("recent", {})
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


def _stream_document(url: str, max_bytes: int = _MAX_BYTES) -> str:
    """Stream a document and stop after max_bytes to avoid downloading full 10-K."""
    resp = _SESSION.get(url, stream=True, timeout=25)
    resp.raise_for_status()
    chunks = []
    total  = 0
    for chunk in resp.iter_content(chunk_size=32_768):
        chunks.append(chunk)
        total += len(chunk)
        if total >= max_bytes:
            break
    return b"".join(chunks).decode("utf-8", errors="ignore")


def _extract_mda(html: str) -> str:
    """Extract Management Discussion & Analysis from 10-K/10-Q HTML."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "table"]):
        tag.decompose()
    text  = soup.get_text(separator=" ", strip=True)
    lower = text.lower()

    start = -1
    for pat in [r"item\s+7[\.\s]+management", r"management.s discussion and analysis"]:
        m = re.search(pat, lower)
        if m:
            start = m.start()
            break
    if start == -1:
        return text[:5000]

    end = len(text)
    for pat in [r"item\s+7a[\.\s]", r"item\s+8[\.\s]"]:
        m = re.search(pat, lower[start + 200:])
        if m:
            end = start + 200 + m.start()
            break

    return text[start : min(end, start + 6000)]


def _check_mongodb_cache(ticker: str) -> tuple[str, str, str] | None:
    """Return cached filing from MongoDB if it exists and is recent (< 7 days)."""
    try:
        from api.database import get_db
        from datetime import datetime, timezone, timedelta
        doc = get_db().filings.find_one({"ticker": ticker})
        if doc:
            saved = datetime.fromisoformat(doc["saved_at"])
            if saved.tzinfo is None:
                saved = saved.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - saved).days < 7:
                return doc["text"], doc["form_type"], doc["filing_date"]
    except Exception:
        pass
    return None


def _save_mongodb_cache(ticker: str, text: str, form_type: str, filing_date: str):
    try:
        from api.database import get_db
        from datetime import datetime, timezone
        get_db().filings.replace_one(
            {"ticker": ticker},
            {"ticker": ticker, "text": text, "form_type": form_type,
             "filing_date": filing_date, "saved_at": datetime.now(timezone.utc).isoformat()},
            upsert=True,
        )
    except Exception:
        pass


def fetch_filing(ticker: str) -> tuple[str, str, str]:
    """
    Fetch the most recent 10-K or 10-Q MD&A section for a ticker.
    Returns (text, form_type, filing_date).

    Cache strategy:
      1. Check MongoDB (7-day TTL) — returns in <50ms if cached
      2. Download from EDGAR (streamed, 1MB cap) — 3-8 seconds
      3. Save result to MongoDB for future requests
    """
    print(f"  [EDGAR] Filing for {ticker}...")

    # 1 — MongoDB cache
    cached = _check_mongodb_cache(ticker)
    if cached:
        print(f"  [EDGAR] Served from cache ({cached[1]} {cached[2]})")
        return cached

    # 2 — Download from EDGAR
    cik_padded, _ = _get_cik(ticker)
    if not cik_padded:
        return "", "", ""

    filing = _get_latest_filing(cik_padded)
    if not filing or not filing["primary"]:
        return "", "", ""

    cik_int   = str(int(cik_padded))
    accession = filing["accession"]
    url = (
        f"https://www.sec.gov/Archives/edgar/data/"
        f"{cik_int}/{accession}/{filing['primary']}"
    )
    try:
        html = _stream_document(url)
        text = _extract_mda(html)
        print(f"  [EDGAR] {filing['form']} ({filing['date']}) — {len(text)} chars")
        _save_mongodb_cache(ticker, text, filing["form"], filing["date"])
        return text, filing["form"], filing["date"]
    except Exception as e:
        print(f"  [EDGAR] Error: {e}")
        return "", "", ""


# Pre-load CIK map at import time in a background thread so it's ready by first request
threading.Thread(target=_load_cik_map, daemon=True).start()
