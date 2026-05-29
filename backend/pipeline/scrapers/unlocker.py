"""
scrapers/unlocker.py — Fetch any public web page via Bright Data Web Unlocker.

Bypasses bot detection, CAPTCHAs, and geo-blocks automatically.
Use this for sources not covered by the pre-built dataset scrapers.
"""
import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from config import UNLOCKER_PROXIES

# verify=False is required — Bright Data performs SSL interception
_SESSION_KWARGS = dict(proxies=UNLOCKER_PROXIES, verify=False, timeout=30)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=20))
def fetch_html(url: str, country: str = "US") -> str:
    """
    Fetch raw HTML from any public URL via Web Unlocker.

    Args:
        url:     Target URL
        country: ISO country code for geo-targeting (US, GB, DE, etc.)

    Returns:
        HTML string, or empty string on failure.
    """
    headers = {
        "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        resp = requests.get(url, headers=headers, **_SESSION_KWARGS)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"  [Unlocker] ERROR fetching {url}: {e}")
        return ""


def fetch_text(url: str) -> str:
    """Fetch a page and return cleaned plain text (no HTML tags)."""
    html = fetch_html(url)
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    # Remove script and style elements
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)[:8000]  # cap at 8k chars


def fetch_sec_filing_text(ticker: str) -> str:
    """
    Fetch the most recent 10-K filing index from SEC EDGAR directly.
    EDGAR is a public government API — no proxy needed, just a valid User-Agent.
    """
    print(f"  [SEC] Fetching EDGAR filing index for {ticker}...")
    url = (
        f"https://www.sec.gov/cgi-bin/browse-edgar"
        f"?action=getcompany&CIK={ticker}&type=10-K&dateb=&owner=include&count=3"
    )
    headers = {"User-Agent": "MarketPulse research/1.0 research@marketpulse.ai"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        print(f"  [SEC] Got {len(text)} chars")
        return text[:5000]
    except Exception as e:
        print(f"  [SEC] ERROR: {e}")
        return ""


def fetch_yahoo_finance(ticker: str) -> dict:
    """
    Fetch key financial metrics via the yfinance library.
    Returns a dict of metrics the synthesis agent can reference.
    """
    print(f"  [Yahoo] Fetching financial data for {ticker}...")
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        keys = [
            "currentPrice", "marketCap", "trailingPE", "forwardPE",
            "revenueGrowth", "earningsGrowth", "profitMargins",
            "recommendationMean", "targetMeanPrice",
            "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
        ]
        result = {k: info[k] for k in keys if k in info and info[k] is not None}
        print(f"  [Yahoo] Got {len(result)} fields")
        return result
    except Exception as e:
        print(f"  [Yahoo] ERROR: {e}")
        return {}


def fetch_geo_pricing(url: str, country_code: str = "DE") -> str:
    """
    Fetch a pricing page from a specific country IP.
    Useful for detecting geo-based pricing differences.
    """
    from config import BRIGHTDATA_CUSTOMER_ID, UNLOCKER_ZONE, UNLOCKER_PASSWORD, PROXY_HOST, PROXY_PORT
    user = f"brd-customer-{BRIGHTDATA_CUSTOMER_ID}-zone-{UNLOCKER_ZONE}-country-{country_code.lower()}"
    geo_proxies = {
        "http":  f"http://{user}:{UNLOCKER_PASSWORD}@{PROXY_HOST}:{PROXY_PORT}",
        "https": f"http://{user}:{UNLOCKER_PASSWORD}@{PROXY_HOST}:{PROXY_PORT}",
    }
    try:
        resp = requests.get(url, proxies=geo_proxies, verify=False, timeout=30)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"  [Unlocker Geo] ERROR: {e}")
        return ""
