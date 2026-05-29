"""
synthesis/multi_agent.py — A7: Multi-agent synthesis pipeline.

4 specialist agents run in parallel, an orchestrator synthesises their reports.
Workers analyse one signal domain each; orchestrator resolves conflicts and
produces the final IntelligenceObject assessment.
"""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from openai import OpenAI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
load_dotenv()

from pipeline.synthesis.agent import _retrieve_context  # A6: ChromaDB RAG

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    organization=os.getenv("OPENAI_ORG_ID"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)

MODEL = os.getenv("OPENAI_MODEL", "claude-sonnet-4-20250514-v1:0")

SPECIALIST_PROMPTS = {
    "news": """You are a financial news sentiment analyst specialising in pre-earnings signals.
Analyse the provided headlines and return ONLY a JSON object:
{"signal":"BULLISH"|"BEARISH"|"NEUTRAL","confidence":0-100,"key_finding":"one concise sentence","evidence":["headline or fact"]}""",

    "hiring": """You are a labour market intelligence analyst focused on hiring as a leading indicator.
Analyse the provided hiring data and return ONLY a JSON object:
{"signal":"BULLISH"|"BEARISH"|"NEUTRAL","confidence":0-100,"key_finding":"one concise sentence","evidence":["finding"]}""",

    "filing": """You are an SEC filing analyst specialising in regulatory language and management tone.
Analyse the provided filing text and return ONLY a JSON object:
{"signal":"BULLISH"|"BEARISH"|"NEUTRAL","confidence":0-100,"key_finding":"one concise sentence","tone":"positive"|"neutral"|"negative"}""",

    "financial": """You are a quantitative analyst assessing financial health metrics.
Analyse the provided Yahoo Finance metrics and return ONLY a JSON object:
{"signal":"BULLISH"|"BEARISH"|"NEUTRAL","confidence":0-100,"key_finding":"one concise sentence","metrics_summary":"brief"}""",
}

ORCHESTRATOR_PROMPT = """You are a senior quantitative equity research analyst.
You receive four specialist analyst reports (news, hiring, filing, financial) for a company.
Synthesise them into a final pre-earnings intelligence assessment.

Output ONLY a JSON object matching this exact schema:
{
  "confidence": <integer 0-100>,
  "composite_signal": <"BULLISH" | "BEARISH" | "NEUTRAL">,
  "key_risks": [<string>, ...],
  "recommended_action": <string, one sentence>,
  "reasoning": <string, 2-3 sentences explaining how you weighed the specialist reports>
}

Rules:
- High confidence = specialists agree AND evidence is strong
- Resolve conflicts by weighing news + financial > hiring > filing (in data quality order)
- key_risks must be specific, not generic boilerplate
- Output ONLY the JSON object — no preamble, no markdown"""


def _call_specialist(name: str, data: str) -> dict:
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            max_tokens=250,
            temperature=0,
            messages=[
                {"role": "system", "content": SPECIALIST_PROMPTS[name]},
                {"role": "user",   "content": f"Analyse this data:\n{data}"},
            ],
        )
        raw = resp.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return {"agent": name, "result": json.loads(raw)}
    except Exception as e:
        return {"agent": name, "result": {
            "signal": "NEUTRAL", "confidence": 0,
            "key_finding": f"Agent unavailable: {e}",
        }}


def synthesise_multi_agent(
    ticker: str,
    company: str,
    signals,
    extra_context: str = "",
) -> dict:
    """
    Run 4 specialist agents in parallel, then orchestrate into a final verdict.
    Falls back gracefully if any specialist fails.
    """
    # A6: retrieve historical context from ChromaDB before synthesis
    historical = _retrieve_context(ticker, "earnings signals hiring news sentiment")

    # Split extra_context into SEC filing text vs Yahoo Finance metrics
    filing_ctx  = ""
    finance_ctx = ""
    if extra_context:
        parts = extra_context.split("Yahoo Finance metrics:")
        filing_ctx  = parts[0].replace("SEC EDGAR filing text:", "").strip()
        finance_ctx = parts[1].strip() if len(parts) > 1 else ""

    data_bundles = {
        "news": json.dumps({
            "company": company,
            "articles_analyzed": signals.news_sentiment.articles_analyzed,
            "sentiment_score":   signals.news_sentiment.score,
            "label":             signals.news_sentiment.label,
            "top_headlines":     signals.news_sentiment.top_headlines[:5],
        }),
        "hiring": json.dumps({
            "company": company,
            "articles_about_hiring": signals.hiring_trend.jobs_30d,
            "signal":                signals.hiring_trend.signal,
            "data_available":        signals.hiring_trend.data_available,
        }),
        "filing": json.dumps({
            "company":       company,
            "guidance_tone": signals.filing_language.guidance_tone,
            "filing_text":   filing_ctx[:800] if filing_ctx else "Not available",
        }),
        "financial": json.dumps({
            "company": company,
            "metrics": finance_ctx[:600] if finance_ctx else "Not available",
        }),
    }

    # Run all 4 specialists in parallel
    reports = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {name: pool.submit(_call_specialist, name, data)
                   for name, data in data_bundles.items()}
        for name, future in as_completed(futures):
            try:
                reports[name] = future.result(timeout=45)["result"]
            except Exception as e:
                reports[name] = {"signal": "NEUTRAL", "confidence": 0, "key_finding": str(e)}

    # Orchestrator synthesises the 4 reports
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            max_tokens=600,
            temperature=0,
            messages=[
                {"role": "system", "content": ORCHESTRATOR_PROMPT},
                {"role": "user",   "content": (
                    f"Company: {company} ({ticker})\n\n"
                    f"Specialist reports:\n{json.dumps(reports, indent=2)}\n\n"
                    + (f"Historical context from previous runs:\n{historical}\n\n" if historical else "")
                    + "Produce the final intelligence assessment JSON."
                )},
            ],
        )
        raw = resp.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        result["_agents"] = reports   # attach specialist reports for transparency
        return result
    except Exception as e:
        return {
            "confidence": 30,
            "composite_signal": "NEUTRAL",
            "key_risks": [f"Orchestrator error: {e}"],
            "recommended_action": "Re-run pipeline when data quality improves.",
            "reasoning": "Multi-agent orchestration failed — falling back to neutral.",
        }
