# MarketPulse AI

> **Web Data UNLOCKED Hackathon · May 2026 · Track 2: Finance & Market Intelligence**

An AI agent that synthesises pre-earnings signals from live web data — hiring trends, SEC filings, news sentiment, and financial metrics — into confidence-scored **intelligence objects** delivered through a live dashboard and REST API.

---

## What it does

Public companies report earnings quarterly. In the days before that report, enormous amounts of information about what's likely in it are already publicly available — scattered across job boards, regulatory filings, and news articles. MarketPulse automates the entire process: find the signals, reason across them, and deliver a structured verdict before the earnings call happens.

**Example output for META:**

```json
{
  "ticker": "META",
  "composite_signal": "BEARISH",
  "confidence": 65,
  "key_risks": [
    "Rising AI investment expenses pressuring margins despite revenue beats",
    "Market concerns about AI spending ROI timeline"
  ],
  "recommended_action": "Monitor upcoming earnings call for specific AI monetization timelines.",
  "reasoning": "Headlines about rising capex and investor concern outweigh the revenue beat signal."
}
```

---

## Architecture

![Architecture](./docs/marketpulse_v2_architecture.svg)

```
React Dashboard  →  Flask REST API  →  Pipeline Orchestrator
                                              │
                        ┌─────────────────────┼──────────────────────┐
                        ▼                     ▼                      ▼
                  Bright Data           SEC EDGAR             Yahoo Finance
                  SERP API              (direct)              (yfinance)
                  (news + hiring)
                        │
                        ▼
              Multi-Agent Claude Synthesis
              (4 specialists + orchestrator)
                        │
                        ▼
              IntelligenceObject  →  ChromaDB  →  Cache  →  API
```

Four data sources feed four signal types. A multi-agent Claude system (4 specialist analysts + orchestrator) reasons across all signals simultaneously and resolves conflicts. Every result is stored in a vector database for trend detection across runs.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full technical reference.

---

## Quick start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Bright Data account with SERP API zone active
- CMU AI Gateway access (or direct Anthropic API key)

### 1. Clone and configure

```bash
git clone https://github.com/YOUR_USERNAME/marketpulse-ai
cd marketpulse-ai
cp .env.example .env
# Edit .env — fill in Bright Data credentials and AI gateway key
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
python api/server.py
```

The API starts at `http://localhost:5000`. On startup it pre-loads all 5 seed companies in the background.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard at `http://localhost:5173`. **The first account you register becomes superadmin.**

---

## Data sources

| Source | Tool | What it provides |
|--------|------|-----------------|
| Google News | Bright Data SERP API | 10 articles per ticker — news sentiment + hiring signals |
| SEC EDGAR | Direct HTTP (no proxy) | Filing index text — management tone |
| Yahoo Finance | `yfinance` library | P/E, market cap, revenue growth, profit margins |

---

## Signal pipeline

```
Raw data
  └── SERP articles  →  analyse_news()               →  NewsSentimentSignal
  └── SERP hiring    →  analyse_hiring_from_news()    →  HiringTrendSignal
  └── SEC text       →  [context passed to Claude]
  └── Yahoo Finance  →  [context passed to Claude]
        │
        ▼
Multi-agent synthesis:
  news_agent + hiring_agent + filing_agent + financial_agent  (parallel)
        │
  orchestrator  →  confidence + composite_signal + key_risks + recommended_action
        │
        ▼
IntelligenceObject  (Pydantic-validated, versioned, cached)
```

---

## Authentication

- **Register** at `/register` — first account becomes superadmin, all others get user role
- **Login** at `/login` — JWT token issued, stored in browser
- **Admin dashboard** at `/admin` — user management, role promotion, live cache status
- All intelligence API endpoints require a valid JWT token

---

## Production upgrades

| Upgrade | Status | Description |
|---------|--------|-------------|
| APScheduler | ✅ Active | Stale cache auto-refreshes every 6 hours |
| Persistent cache | ✅ Active | Cache survives server restarts via `logs/cache.json` |
| ChromaDB RAG | ✅ Active | Historical intelligence stored for trend detection |
| Multi-agent synthesis | ✅ Active | 4 specialist agents + orchestrator in parallel |
| Parallel fetching | ✅ Active | All 4 scrapers + all 5 companies run simultaneously |
| Rate limiting | ✅ Active | 300 req/day, 60 req/hour per IP |
| JWT authentication | ✅ Active | All endpoints protected, role-based access |

---

## Project structure

```
marketpulse-ai/
├── backend/
│   ├── api/
│   │   ├── server.py          # Flask REST API — 6 endpoints
│   │   └── auth.py            # JWT auth + SQLite user management
│   ├── pipeline/
│   │   ├── run.py             # Orchestrator
│   │   ├── schema.py          # Pydantic models
│   │   ├── scrapers/
│   │   │   ├── serp.py        # Bright Data SERP API (news + hiring)
│   │   │   └── unlocker.py    # SEC EDGAR + Yahoo Finance
│   │   ├── signals/
│   │   │   ├── news.py        # Sentiment scoring
│   │   │   └── hiring.py      # Hiring signal from news
│   │   └── synthesis/
│   │       ├── agent.py       # Single-agent Claude + ChromaDB RAG
│   │       └── multi_agent.py # 4 specialists + orchestrator
│   ├── scripts/
│   │   ├── run_pipeline.py    # Run all companies in parallel
│   │   └── backtest.py        # Accuracy test against known outcomes
│   ├── tests/                 # Component and end-to-end tests
│   └── utils/                 # Logging, validation
├── frontend/
│   └── src/
│       ├── App.jsx            # Routes + Dashboard
│       ├── api/client.js      # Fetch helper with JWT headers
│       ├── context/AuthContext.jsx
│       ├── components/        # CompanyCard, SearchBar, ProtectedRoute
│       └── pages/             # Login, Register, AdminDashboard
├── docs/
│   └── ARCHITECTURE.md        # Full technical reference
├── .env.example
└── .gitignore
```

---

## CLI reference

```bash
# Single company pipeline
python -m pipeline.run --ticker AAPL --company "Apple Inc."

# All 5 seed companies in parallel
python scripts/run_pipeline.py

# Backtest against 10 known earnings outcomes
python scripts/backtest.py

# Tests
pytest tests/test_signals.py -v       # no API calls needed
python tests/test_serp.py             # live SERP test
python tests/test_unlocker.py         # live SEC + Yahoo Finance
python tests/test_pipeline_all.py     # full end-to-end
```

---

## Why this matters

Hedge funds pay $50,000–$1,000,000/year for alternative data subscriptions that provide signals similar to what this pipeline produces. The infrastructure already existed — Bright Data handles the hard parts of web data access. What's new is the intelligence layer: a multi-agent Claude system that reasons across conflicting signals and produces a calibrated confidence score, not just a data dump.

---

## Hackathon submission

Built for the [Bright Data Web Data UNLOCKED Hackathon](https://lablab.ai/ai-hackathons/brightdata-ai-agents-web-data-hackathon) — Track 2: Finance & Market Intelligence.

**Bright Data products used:** SERP API · Web Unlocker · Web Scraper API  
**AI:** Claude via CMU AI Gateway (OpenAI-compatible)  
**Stack:** Python · Flask · React · Vite · Tailwind · SQLite · ChromaDB
