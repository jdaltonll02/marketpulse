"""
synthesis/agent.py — Claude agent that fuses all signals into one intelligence object.

This is the AI core of the pipeline. Claude receives structured signal data
and produces a confidence score, composite signal, key risks, and recommended action.
"""
import json
import os
import sys
from pathlib import Path
from openai import OpenAI
from pipeline.schema import Signals
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

load_dotenv()

# ── A6: ChromaDB vector memory ────────────────────────────────────────────────
_CHROMA_AVAILABLE = False
try:
    import chromadb
    _chroma_dir = Path(__file__).resolve().parents[2] / "data" / "chroma"
    _chroma_dir.mkdir(parents=True, exist_ok=True)
    _chroma_client = chromadb.PersistentClient(path=str(_chroma_dir))
    _collection    = _chroma_client.get_or_create_collection("company_knowledge")
    _CHROMA_AVAILABLE = True
except ImportError:
    pass


def _retrieve_context(ticker: str, query: str, n: int = 3) -> str:
    if not _CHROMA_AVAILABLE:
        return ""
    try:
        results = _collection.query(
            query_texts=[f"{ticker}: {query}"],
            n_results=n,
            where={"ticker": ticker},
        )
        docs = results.get("documents", [[]])[0]
        return "\n---\n".join(docs) if docs else ""
    except Exception:
        return ""


def store_context(ticker: str, doc_id: str, text: str, doc_type: str = "intelligence"):
    """Store a document in the vector knowledge base."""
    if not _CHROMA_AVAILABLE or not text.strip():
        return
    try:
        _collection.upsert(
            ids=[f"{ticker}_{doc_id}"],
            documents=[text],
            metadatas=[{"ticker": ticker, "type": doc_type}],
        )
    except Exception:
        pass

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    organization=os.getenv("OPENAI_ORG_ID"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)

SYSTEM_PROMPT = """You are a quantitative equity research analyst specialising in pre-earnings signal detection.

You receive structured signals derived from live web data for a public company, and you produce a concise, actionable intelligence assessment.

Your output must be valid JSON matching this exact schema:
{
  "confidence": <integer 0-100>,
  "composite_signal": <"BULLISH" | "BEARISH" | "NEUTRAL">,
  "key_risks": [<string>, ...],
  "recommended_action": <string, one sentence>,
  "reasoning": <string, 2-3 sentences explaining the composite signal>
}

Rules:
- Base confidence on data quality and signal agreement. High confidence = multiple signals agree + good data coverage.
- composite_signal must reflect the weight of evidence, not just the loudest signal.
- key_risks should be specific and current, not generic boilerplate.
- recommended_action should be concrete: "Monitor earnings call for guidance language" is better than "Watch the stock."
- Output ONLY the JSON object. No preamble, no markdown fences.
"""


def synthesise(
    ticker: str,
    company: str,
    signals: Signals,
    extra_context: str = "",
) -> dict:
    """
    Call Claude via CMU AI Gateway to synthesise all signals into a final assessment.

    Args:
        ticker:        Stock ticker symbol
        company:       Company name
        signals:       Fully populated Signals object from the pipeline
        extra_context: Optional additional text (e.g. SEC filing excerpt)

    Returns:
        Dict with keys: confidence, composite_signal, key_risks,
        recommended_action, reasoning
    """
    # A6: retrieve relevant historical context from vector memory
    historical = _retrieve_context(ticker, "earnings signals hiring news sentiment")
    if historical:
        extra_context = extra_context + f"\n\nHistorical context:\n{historical}"

    signal_summary = {
        "news_sentiment": {
            "score":             signals.news_sentiment.score,
            "label":             signals.news_sentiment.label,
            "articles_analyzed": signals.news_sentiment.articles_analyzed,
            "top_headlines":     signals.news_sentiment.top_headlines[:3],
        },
        "hiring_trend": {
            "articles_about_hiring": signals.hiring_trend.jobs_30d,
            "signal":                signals.hiring_trend.signal,
            "data_available":        signals.hiring_trend.data_available,
            "note":                  "articles_about_hiring is a count of news articles mentioning hiring activity, not raw job postings",
        },
        "filing_language": {
            "guidance_tone": signals.filing_language.guidance_tone,
            "key_phrases":   signals.filing_language.key_phrases[:5],
            "signal":        signals.filing_language.signal,
        },
        "pricing": {
            "price_changes_30d":  signals.pricing.price_changes_30d,
            "competitor_changes": signals.pricing.competitor_changes,
            "signal":             signals.pricing.signal,
        },
    }

    user_message = f"""Analyse {company} ({ticker}) based on these live web signals:

{json.dumps(signal_summary, indent=2)}

{"Additional context from SEC filing:" + chr(10) + extra_context if extra_context else ""}

Produce the intelligence assessment JSON."""

    try:
        response = client.chat.completions.create(
            model="claude-sonnet-4-20250514-v1:0",
            max_tokens=1000,
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
        )
        raw = response.choices[0].message.content.strip()
        # Strip any accidental markdown fences
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)

    except json.JSONDecodeError as e:
        print(f"  [Agent] JSON parse error: {e}. Raw response: {raw[:200]}")
        return {
            "confidence":         40,
            "composite_signal":   "NEUTRAL",
            "key_risks":          ["Unable to parse agent response — check logs"],
            "recommended_action": "Re-run pipeline with more data",
            "reasoning":          "Agent response could not be parsed.",
        }
    except Exception as e:
        print(f"  [Agent] ERROR: {e}")
        return {
            "confidence":         0,
            "composite_signal":   "NEUTRAL",
            "key_risks":          [str(e)],
            "recommended_action": "Pipeline error — see logs",
            "reasoning":          "An error occurred during synthesis.",
        }