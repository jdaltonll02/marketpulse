"""
scrapers/serp.py — Real-time news via Bright Data SERP API.
Uses zone proxy method instead of direct API endpoint.
"""
import requests
import urllib3
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
import sys, os
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
load_dotenv()

CUSTOMER_ID   = os.getenv("BRIGHTDATA_CUSTOMER_ID")
SERP_ZONE     = os.getenv("SERP_ZONE")
SERP_PASSWORD = os.getenv("SERP_PASSWORD")
PROXY_HOST    = os.getenv("PROXY_HOST", "brd.superproxy.io")
PROXY_PORT    = os.getenv("PROXY_PORT", "33335")

proxy_url = f"http://brd-customer-{CUSTOMER_ID}-zone-{SERP_ZONE}:{SERP_PASSWORD}@{PROXY_HOST}:{PROXY_PORT}"

PROXIES = {
    "http":  proxy_url,
    "https": proxy_url,
}


def _parse_news_html(soup: "BeautifulSoup", num: int) -> list[dict]:
    articles = []
    seen_urls: set[str] = set()

    # Strategy 1: known Google News container classes
    containers = soup.select(
        "div.SoaBEf, div.WlydOe, div.xuvV6b, div.DBd4re, div.g"
    )
    for container in containers[:num]:
        title_el   = container.select_one("div.MBeuO, div.n0jPhd, div.JheGif, h3")
        snippet_el = container.select_one("div.GI74Re, div.Y3v8qd, div.yDYNvb")
        source_el  = container.select_one("div.CEMjEf, span.NUnG9d, div.SVJrMe")
        link_el    = container.select_one("a[href]")

        title   = title_el.get_text(strip=True)   if title_el   else ""
        url     = link_el["href"]                  if link_el    else ""
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        source  = source_el.get_text(strip=True)  if source_el  else ""

        if title and url and url not in seen_urls:
            seen_urls.add(url)
            articles.append({"title": title, "url": url, "snippet": snippet, "source": source, "date": ""})

    if articles:
        return articles

    # Strategy 2: any <a> containing an <h3> — works regardless of container class names
    for a_tag in soup.find_all("a", href=True):
        if len(articles) >= num:
            break
        h3 = a_tag.find("h3")
        if not h3:
            continue
        title = h3.get_text(strip=True)
        url   = a_tag["href"]
        if not title or not url.startswith("http"):
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)

        snippet = ""
        parent = a_tag.parent
        if parent:
            for el in parent.find_all(["div", "span"]):
                text = el.get_text(strip=True)
                if text and text != title and len(text) > 20:
                    snippet = text[:200]
                    break

        articles.append({"title": title, "url": url, "snippet": snippet, "source": "", "date": ""})

    return articles


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=3, max=15))
def google_news(query: str, num: int = 20, days_back: int = 7) -> list[dict]:
    """
    Fetch Google News results via SERP zone proxy.
    """
    tbs_map = {1: "qdr:d", 7: "qdr:w", 30: "qdr:m"}
    tbs = tbs_map.get(days_back, "qdr:w")

    params = {
        "q":   query,
        "tbm": "nws",
        "num": min(num, 100),
        "tbs": tbs,
        "hl":  "en",
    }

    try:
        resp = requests.get(
            "https://www.google.com/search",
            params=params,
            proxies=PROXIES,
            verify=False,
            timeout=30,
        )
        if resp.status_code == 402:
            raise RuntimeError("Credits exhausted")
        resp.raise_for_status()

        # Bright Data SERP zone returns structured JSON — parse that first
        try:
            data = resp.json()
            news_items = data.get("news", [])
            if news_items:
                return [
                    {
                        "title":   item.get("title", ""),
                        "url":     item.get("link", ""),
                        "snippet": item.get("description", "") or item.get("snippet", ""),
                        "source":  item.get("source", ""),
                        "date":    item.get("date", "") or item.get("time", ""),
                    }
                    for item in news_items[:num]
                    if item.get("title")
                ]
        except ValueError:
            pass

        # Fallback: HTML parsing (plain proxy mode)
        soup = BeautifulSoup(resp.text, "html.parser")
        articles = _parse_news_html(soup, num)

        if not articles:
            print(f"  [SERP] WARNING: 0 articles parsed. HTTP {resp.status_code}. Preview:")
            print(resp.text[:1500])

        return articles

    except Exception as e:
        print(f"  [SERP] ERROR for query '{query}': {e}")
        return []


def fetch_ticker_news(ticker: str, company: str, days_back: int = 7) -> list[dict]:
    """
    Fetch earnings-focused news for a ticker.
    Primary query targets earnings/revenue/guidance; falls back to broader search
    if fewer than 5 substantive articles are returned.
    """
    primary_query = f'{ticker} "{company}" earnings revenue results guidance 2026'
    print(f"  [SERP] Fetching news: {primary_query}")
    results = google_news(primary_query, num=20, days_back=days_back)

    if len(results) < 5:
        fallback_query = f'{ticker} stock earnings analyst outlook 2026'
        print(f"  [SERP] Fallback query: {fallback_query}")
        fallback = google_news(fallback_query, num=20, days_back=30)
        seen = {r["url"] for r in results}
        results += [r for r in fallback if r["url"] not in seen]

    print(f"  [SERP] Got {len(results)} articles")
    return results[:20]


def fetch_hiring_via_serp(company: str, days_back: int = 30) -> list[dict]:
    """
    Fetch hiring signals via SERP.
    Primary query targets workforce/headcount news; falls back to broader hiring terms.
    """
    primary_query = f'"{company}" hiring workforce employees headcount expansion 2026'
    print(f"  [SERP] Fetching hiring signals: {primary_query}")
    results = google_news(primary_query, num=20, days_back=days_back)

    if len(results) < 5:
        fallback_query = f'"{company}" jobs recruitment talent 2026'
        print(f"  [SERP] Fallback hiring query: {fallback_query}")
        fallback = google_news(fallback_query, num=10, days_back=60)
        seen = {r["url"] for r in results}
        results += [r for r in fallback if r["url"] not in seen]

    print(f"  [SERP] Got {len(results)} hiring articles")
    return results[:20]


def fetch_competitor_news(company: str, competitors: list[str]) -> dict[str, list[dict]]:
    """
    Fetch news for a list of competitors.
    """
    out = {}
    for comp in competitors:
        out[comp] = google_news(f'"{comp}" pricing announcement', num=10, days_back=30)
    return out