# MarketPulse AI — Pre-Earnings Intelligence Agent

> Web Data UNLOCKED Hackathon · May 2026 · Track 2: Finance & Market Intelligence

An AI agent that fuses live web data (hiring trends, SEC filings, news sentiment, competitor pricing) into confidence-scored **intelligence objects** for equity analysts — powered by Bright Data and Claude.

---

## What it does

1. **Ingests** live data from 4 Bright Data sources: Web Scraper API (LinkedIn, SEC EDGAR), SERP API (Google News), Web Unlocker (financial pages)
2. **Synthesises** signals using a Claude agent via Bright Data MCP Server
3. **Outputs** a structured JSON intelligence object per company — confidence-scored, CRM-ready
4. **Delivers** via a React dashboard + REST API + Slack alerts

---

## Quick start

```bash
# 1. Clone and install
git clone https://github.com/YOUR_USERNAME/marketpulse-ai
cd marketpulse-ai

# 2. Set up environment
cp .env.example .env
# Fill in your Bright Data and Anthropic credentials

# 3. Install backend
cd backend
pip install -r requirements.txt

# 4. Run the pipeline on one company
python -m pipeline.run --ticker AAPL --company "Apple Inc."

# 5. Start the API server
python -m api.server

# 6. Install and start the frontend (separate terminal)
cd ../frontend
npm install
npm run dev
```

The dashboard will be at `http://localhost:5173`
The API will be at `http://localhost:5000`

---

## Project structure

```
marketpulse/
├── backend/
│   ├── api/              # Flask REST API — serves intelligence objects
│   ├── pipeline/
│   │   ├── scrapers/     # Bright Data data ingestion (one file per source)
│   │   ├── signals/      # Signal analysis (hiring, news, filing, pricing)
│   │   └── synthesis/    # Claude agent — fuses signals into intelligence object
│   ├── utils/            # Shared helpers: validation, logging, retry logic
│   └── tests/            # Pytest test suite
├── frontend/             # React + Vite dashboard
├── scripts/              # Backtest runner, bulk pipeline, seed data
└── docs/                 # Architecture notes
```

---

## Bright Data tools used

| Tool | Purpose | Section in platform guide |
|------|---------|--------------------------|
| Web Scraper API | LinkedIn jobs, SEC EDGAR filings | B5 |
| SERP API | Google News per ticker | B6 |
| Web Unlocker | Paywalled financial pages | B7 |
| MCP Server | Claude agent live web access | B9 |

---

## Intelligence object schema

```json
{
  "ticker": "AAPL",
  "company": "Apple Inc.",
  "generated_at": "2026-05-25T14:30:00Z",
  "confidence": 78,
  "composite_signal": "BULLISH",
  "signals": {
    "news_sentiment": { "score": 0.65, "label": "BULLISH", "articles_analyzed": 18 },
    "hiring_trend":   { "jobs_30d": 234, "signal": "BULLISH" },
    "filing_language":{ "guidance_tone": "positive", "signal": "BULLISH" },
    "pricing":        { "signal": "NEUTRAL" }
  },
  "key_risks": ["Macro slowdown", "China supply chain"],
  "recommended_action": "Monitor earnings call closely"
}
```

---

## Submission checklist

- [ ] GitHub repo public with this README
- [ ] .env.example committed (no real keys)
- [ ] Live demo URL working (Railway/Render)
- [ ] Video demo recorded (< 5 min)
- [ ] Backtest results in `docs/backtest_results.md`
- [ ] Submitted on lablab.ai before 2:00 AM SAST May 31
