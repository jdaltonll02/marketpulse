"""
api/server.py — Flask REST API.
Serves intelligence objects from cache or triggers the pipeline on demand.

Endpoints:
    GET  /api/health                     — health check
    GET  /api/intelligence/<ticker>      — get or generate intelligence object
    POST /api/intelligence/batch         — generate for a list of tickers
    GET  /api/intelligence/<ticker>/refresh — force re-run the pipeline
    GET  /api/watchlist                  — list all cached tickers
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__) + "/..")

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime

import config
from pipeline.run    import run_pipeline
from pipeline.schema import IntelligenceObject

config.validate()   # fail fast on startup if credentials are missing

app  = Flask(__name__)
CORS(app)           # allow the React frontend on localhost:5173

# In-memory cache — replace with Redis for production
_CACHE: dict[str, IntelligenceObject] = {}


def _get_or_generate(ticker: str, company: str = "") -> IntelligenceObject:
    """Return cached object if fresh, otherwise run pipeline."""
    cached = _CACHE.get(ticker.upper())
    if cached and cached.is_fresh:
        return cached
    # Resolve company name if not provided
    if not company:
        company = _resolve_company_name(ticker)
    obj = run_pipeline(ticker.upper(), company)
    _CACHE[ticker.upper()] = obj
    return obj


def _resolve_company_name(ticker: str) -> str:
    """Simple lookup — extend this with a real data source."""
    KNOWN = {
        "AAPL": "Apple Inc.",
        "MSFT": "Microsoft Corporation",
        "GOOGL": "Alphabet Inc.",
        "META": "Meta Platforms",
        "AMZN": "Amazon.com Inc.",
        "NVDA": "NVIDIA Corporation",
        "TSLA": "Tesla Inc.",
        "CRWD": "CrowdStrike Holdings",
        "PLTR": "Palantir Technologies",
    }
    return KNOWN.get(ticker.upper(), ticker)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return jsonify({
        "status":    "ok",
        "cached":    list(_CACHE.keys()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })


@app.get("/api/intelligence/<ticker>")
def get_intelligence(ticker: str):
    company = request.args.get("company", "")
    try:
        obj = _get_or_generate(ticker, company)
        return jsonify(obj.to_api_dict())
    except Exception as e:
        return jsonify({"error": str(e), "ticker": ticker}), 500


@app.get("/api/intelligence/<ticker>/refresh")
def refresh_intelligence(ticker: str):
    """Force re-run the pipeline, bypassing cache."""
    company = request.args.get("company", _resolve_company_name(ticker))
    try:
        obj = run_pipeline(ticker.upper(), company)
        _CACHE[ticker.upper()] = obj
        return jsonify(obj.to_api_dict())
    except Exception as e:
        return jsonify({"error": str(e), "ticker": ticker}), 500


@app.post("/api/intelligence/batch")
def batch_intelligence():
    """Generate intelligence objects for multiple tickers."""
    body    = request.get_json() or {}
    tickers = body.get("tickers", [])
    if not tickers:
        return jsonify({"error": "Provide a list of tickers"}), 400

    results = {}
    for ticker in tickers[:10]:   # cap at 10 to protect credits
        company = body.get("companies", {}).get(ticker, _resolve_company_name(ticker))
        try:
            obj = _get_or_generate(ticker, company)
            results[ticker] = obj.to_api_dict()
        except Exception as e:
            results[ticker] = {"error": str(e)}

    return jsonify(results)


@app.get("/api/watchlist")
def watchlist():
    """Return all cached intelligence objects."""
    return jsonify({
        ticker: obj.to_api_dict()
        for ticker, obj in _CACHE.items()
    })


# ── Startup: pre-load seed tickers ────────────────────────────────────────────
def _seed():
    for ticker, company in config.SEED_TICKERS:
        print(f"Pre-loading {ticker} ({company})...")
        try:
            _get_or_generate(ticker, company)
        except Exception as e:
            print(f"  Failed to seed {ticker}: {e}")


if __name__ == "__main__":
    import threading
    threading.Thread(target=_seed, daemon=True).start()
    app.run(port=config.FLASK_PORT, debug=False)
