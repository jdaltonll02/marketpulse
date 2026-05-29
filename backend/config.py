"""
config.py — single source of truth for all environment variables.
Import this everywhere instead of calling os.getenv() directly.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Bright Data ───────────────────────────────────────────────────────────────
BRIGHTDATA_API_KEY     = os.getenv("BRIGHTDATA_API_KEY", "")
BRIGHTDATA_CUSTOMER_ID = os.getenv("BRIGHTDATA_CUSTOMER_ID", "")

SERP_ZONE     = os.getenv("SERP_ZONE", "serp_hackathon")
UNLOCKER_ZONE = os.getenv("UNLOCKER_ZONE", "web_unlocker_main")
BROWSER_ZONE  = os.getenv("SCRAPING_BROWSER_ZONE", "scraping_browser_hk")

SERP_PASSWORD     = os.getenv("SERP_PASSWORD", "")
UNLOCKER_PASSWORD = os.getenv("UNLOCKER_PASSWORD", "")
BROWSER_PASSWORD  = os.getenv("BROWSER_PASSWORD", "")

PROXY_HOST       = os.getenv("PROXY_HOST", "brd.superproxy.io")
PROXY_PORT       = int(os.getenv("PROXY_PORT", "33335"))
BROWSER_CDP_PORT = int(os.getenv("BROWSER_CDP_PORT", "9222"))

# ── CMU AI Gateway (OpenAI-compatible) ───────────────────────────────────────
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
OPENAI_ORG_ID   = os.getenv("OPENAI_ORG_ID", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")

# ── App ───────────────────────────────────────────────────────────────────────
FLASK_PORT   = int(os.getenv("FLASK_PORT", "5000"))
SECRET_KEY   = os.getenv("SECRET_KEY", "dev-secret-change-me")
CACHE_TTL    = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
MAX_PARALLEL = int(os.getenv("MAX_PARALLEL_COMPANIES", "3"))
def _parse_seed_tickers(raw: str) -> list[tuple[str, str]]:
    result = []
    for item in raw.split(","):
        item = item.strip()
        if ":" in item:
            ticker, company = item.split(":", 1)
            result.append((ticker.strip(), company.strip()))
        elif item:
            result.append((item, item))
    return result

SEED_TICKERS: list[tuple[str, str]] = _parse_seed_tickers(
    os.getenv("SEED_TICKERS", "AAPL:Apple Inc.,MSFT:Microsoft Corporation")
)

# ── Optional ──────────────────────────────────────────────────────────────────
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL", "")

# ── Derived proxy credentials ─────────────────────────────────────────────────
def proxy_url(zone: str, password: str) -> str:
    user = f"brd-customer-{BRIGHTDATA_CUSTOMER_ID}-zone-{zone}"
    return f"http://{user}:{password}@{PROXY_HOST}:{PROXY_PORT}"

UNLOCKER_PROXIES = {
    "http":  proxy_url(UNLOCKER_ZONE, UNLOCKER_PASSWORD),
    "https": proxy_url(UNLOCKER_ZONE, UNLOCKER_PASSWORD),
}

SERP_PROXIES = {
    "http":  proxy_url(SERP_ZONE, SERP_PASSWORD),
    "https": proxy_url(SERP_ZONE, SERP_PASSWORD),
}

BROWSER_CDP_URL = (
    f"wss://brd-customer-{BRIGHTDATA_CUSTOMER_ID}-zone-{BROWSER_ZONE}"
    f":{BROWSER_PASSWORD}@{PROXY_HOST}:{BROWSER_CDP_PORT}"
)

# ── Validation ────────────────────────────────────────────────────────────────
def validate():
    """Call on startup to catch missing credentials early."""
    missing = []
    required = {
        "BRIGHTDATA_API_KEY":     BRIGHTDATA_API_KEY,
        "BRIGHTDATA_CUSTOMER_ID": BRIGHTDATA_CUSTOMER_ID,
        "OPENAI_API_KEY":         OPENAI_API_KEY,
    }
    for name, val in required.items():
        if not val:
            missing.append(name)
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            f"Copy .env.example to .env and fill in your credentials."
        )
    print("✓ Config validated — all required credentials present")
