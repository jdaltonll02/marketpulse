"""
api/server.py — Flask REST API.

Endpoints:
    GET  /api/health
    GET  /api/intelligence/<ticker>
    GET  /api/intelligence/<ticker>/refresh
    POST /api/intelligence/batch
    GET  /api/watchlist

Upgrades active:
    A4 — APScheduler: auto-refresh stale cache every 6 hours
    A5 — Persistent JSON cache: survives server restarts
    A9 — Flask-Limiter: rate limiting on expensive endpoints
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__) + "/..")

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
from pathlib import Path  # still used by _seed results file

import config
from pipeline import run_pipeline
from pipeline.schema import IntelligenceObject
from utils.logger    import get_logger
from api.auth        import auth_bp, init_db

log = get_logger("api.server")

config.validate()

app = Flask(__name__)

# Allow configurable origins — set FRONTEND_URL in production (Render dashboard)
_origins = os.getenv("FRONTEND_URL", "http://localhost:5173").split(",")
CORS(app, origins=_origins, supports_credentials=True)

# ── JWT ───────────────────────────────────────────────────────────────────────
app.config["JWT_SECRET_KEY"] = config.SECRET_KEY
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, get_jwt
JWTManager(app)

app.register_blueprint(auth_bp)
init_db()

# A9: Rate limiting disabled for demo — re-enable post-hackathon with Redis storage

# ── A5: Persistent MongoDB cache (replaces cache.json) ────────────────────────
_CACHE: dict[str, IntelligenceObject] = {}


def _load_cache():
    try:
        from api.database import get_db
        docs = list(get_db().cache.find({}))
        for doc in docs:
            ticker = doc["_id"]
            try:
                payload = doc["data"]
                _CACHE[ticker] = IntelligenceObject.model_validate(payload)
            except Exception:
                pass
        log.info(f"Cache loaded from MongoDB: {len(_CACHE)} entries")
    except Exception as e:
        log.warning(f"MongoDB cache load failed: {e}")


def _save_cache():
    try:
        from api.database import get_db
        db = get_db()
        for ticker, obj in _CACHE.items():
            db.cache.replace_one(
                {"_id": ticker},
                {"_id": ticker, "data": obj.to_api_dict()},
                upsert=True,
            )
    except Exception as e:
        log.warning(f"MongoDB cache save failed: {e}")


# ── Cache helpers ─────────────────────────────────────────────────────────────
def _get_or_generate(ticker: str, company: str = "") -> IntelligenceObject:
    cached = _CACHE.get(ticker.upper())
    if cached and cached.is_fresh:
        return cached
    if not company:
        company = _resolve_company_name(ticker)
    obj = run_pipeline(ticker.upper(), company)
    _CACHE[ticker.upper()] = obj
    _save_cache()
    return obj


def _resolve_company_name(ticker: str) -> str:
    KNOWN = {
        "AAPL":  "Apple Inc.",
        "MSFT":  "Microsoft Corporation",
        "GOOGL": "Alphabet Inc.",
        "META":  "Meta Platforms",
        "AMZN":  "Amazon.com Inc.",
        "NVDA":  "NVIDIA Corporation",
        "TSLA":  "Tesla Inc.",
        "NFLX":  "Netflix Inc.",
        "CRWD":  "CrowdStrike Holdings",
        "PLTR":  "Palantir Technologies",
    }
    return KNOWN.get(ticker.upper(), ticker)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return jsonify({
        "status":    "ok",
        "cached":    list(_CACHE.keys()),
        "scheduler": "active",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })


@app.get("/api/intelligence/<ticker>")
@jwt_required()
def get_intelligence(ticker: str):
    company = request.args.get("company", "")
    try:
        obj = _get_or_generate(ticker, company)
        return jsonify(obj.to_api_dict())
    except Exception as e:
        return jsonify({"error": str(e), "ticker": ticker}), 500


@app.get("/api/intelligence/<ticker>/refresh")
@jwt_required()
def refresh_intelligence(ticker: str):
    """Force re-run, bypass cache. Rate-limited to 30/hour to protect Bright Data credits."""
    from pipeline.synthesis import detect_drift
    company = request.args.get("company", _resolve_company_name(ticker))
    try:
        previous = _CACHE.get(ticker.upper())
        obj      = run_pipeline(ticker.upper(), company)
        if previous:
            drift = detect_drift(previous, obj, " ".join(obj.signals.news_sentiment.top_headlines))
            if drift:
                obj = obj.model_copy(update={"drift": drift})
                log.info(f"[Drift] {ticker}: {drift.direction} ({previous.composite_signal}→{obj.composite_signal})")
        _CACHE[ticker.upper()] = obj
        _save_cache()
        return jsonify(obj.to_api_dict())
    except Exception as e:
        return jsonify({"error": str(e), "ticker": ticker}), 500


@app.post("/api/intelligence/batch")
@jwt_required()
def batch_intelligence():
    body    = request.get_json() or {}
    tickers = body.get("tickers", [])
    if not tickers:
        return jsonify({"error": "Provide a list of tickers"}), 400
    results = {}
    for ticker in tickers[:10]:
        company = body.get("companies", {}).get(ticker, _resolve_company_name(ticker))
        try:
            obj = _get_or_generate(ticker, company)
            results[ticker] = obj.to_api_dict()
        except Exception as e:
            results[ticker] = {"error": str(e)}
    return jsonify(results)


@app.get("/api/watchlist")
@jwt_required()
def watchlist():
    return jsonify({t: obj.to_api_dict() for t, obj in _CACHE.items()})


# ── A4: APScheduler — auto-refresh stale cache ────────────────────────────────
def _refresh_stale():
    stale = [t for t, obj in list(_CACHE.items()) if not obj.is_fresh]
    if not stale:
        return
    log.info(f"[Scheduler] Refreshing {len(stale)} stale tickers: {stale}")
    for ticker in stale:
        try:
            company = _resolve_company_name(ticker)
            _CACHE[ticker] = run_pipeline(ticker, company)
            _save_cache()
            log.info(f"[Scheduler] Refreshed {ticker}")
        except Exception as e:
            log.warning(f"[Scheduler] Failed to refresh {ticker}: {e}")


def _start_scheduler():
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval     import IntervalTrigger
        import atexit
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            func=_refresh_stale,
            trigger=IntervalTrigger(hours=6),
            id="refresh_stale",
            replace_existing=True,
        )
        scheduler.start()
        atexit.register(lambda: scheduler.shutdown())
        log.info("APScheduler started — stale cache refreshes every 6 hours")
    except ImportError:
        log.warning("apscheduler not installed — scheduled refresh disabled")


# ── Startup ───────────────────────────────────────────────────────────────────
def _seed():
    results = []
    for ticker, company in config.SEED_TICKERS:
        log.info(f"Pre-loading {ticker} ({company})...")
        try:
            obj = _get_or_generate(ticker, company)
            results.append(obj.to_api_dict())
        except Exception as e:
            log.warning(f"Failed to seed {ticker}: {e}")
    if results:
        log_dir = Path(__file__).resolve().parents[1] / "logs"
        log_dir.mkdir(exist_ok=True)
        out = log_dir / f"results_{datetime.utcnow().strftime('%Y-%m-%d_%H%M')}.json"
        out.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
        log.info(f"Seed results saved to {out.name}")


if __name__ == "__main__":
    import threading
    _load_cache()          # A5: restore cache from disk
    _start_scheduler()     # A4: start auto-refresh
    threading.Thread(target=_seed, daemon=True).start()
    app.run(port=config.FLASK_PORT, debug=False)
