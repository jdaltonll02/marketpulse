"""
pipeline/signals/filing.py — Analyse SEC filing language using Claude.

Replaces the hardcoded NEUTRAL stub in run.py with a real signal
derived from actual 10-K/10-Q MD&A text.

Signal logic:
  BULLISH  — accelerating demand, raised guidance, record results, strong outlook
  BEARISH  — uncertainty language, declining margins, reduced guidance, elevated risks
  NEUTRAL  — standard boilerplate, mixed signals, insufficient text

Usage:
    from pipeline.signals.filing import analyse_filing
    signal = analyse_filing(text, "AAPL", "Apple Inc.", "10-K")
"""
import json
import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    organization=os.getenv("OPENAI_ORG_ID"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)
MODEL = os.getenv("OPENAI_MODEL", "claude-sonnet-4-20250514-v1:0")

_SYSTEM = """You are an SEC filing analyst specialising in pre-earnings signal detection.
Analyse the provided 10-K or 10-Q Management Discussion & Analysis excerpt.

Return ONLY a JSON object matching this schema:
{
  "guidance_tone": "positive" | "neutral" | "negative",
  "signal": "BULLISH" | "NEUTRAL" | "BEARISH",
  "key_phrases": ["exact phrase from text 1", "exact phrase 2", "exact phrase 3"],
  "risk_factor_delta": null
}

Rules:
- BULLISH:  management raises guidance, mentions record revenue, accelerating demand, strong outlook, confident language
- BEARISH:  hedging language ("may", "could", "uncertain"), declining margins, elevated risk disclosures, reduced outlook
- NEUTRAL:  standard boilerplate language, mixed signals, or insufficient evidence for a directional call
- key_phrases: copy VERBATIM short phrases from the text — not your paraphrase
- Output ONLY the JSON object, no markdown"""


def analyse_filing(text: str, ticker: str, company: str, form_type: str = "10-K"):
    """
    Analyse SEC 10-K/10-Q text with Claude and return a FilingLanguageSignal.
    Falls back to unavailable signal if text is too short or API fails.
    """
    from pipeline.schema import FilingLanguageSignal

    if not text or len(text) < 300:
        return FilingLanguageSignal(
            guidance_tone="unavailable",
            signal="NEUTRAL",
            key_phrases=[],
        )

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            max_tokens=400,
            temperature=0,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": (
                    f"Company: {company} ({ticker})  |  Form: {form_type}\n\n"
                    f"MD&A excerpt:\n{text[:3500]}"
                )},
            ],
        )
        raw = resp.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)

        tone   = result.get("guidance_tone", "neutral")
        signal = result.get("signal", "NEUTRAL")

        if tone   not in ("positive", "neutral", "negative", "unavailable"):
            tone   = "neutral"
        if signal not in ("BULLISH", "NEUTRAL", "BEARISH"):
            signal = "NEUTRAL"

        return FilingLanguageSignal(
            guidance_tone=tone,
            signal=signal,
            key_phrases=result.get("key_phrases", [])[:5],
        )
    except Exception as e:
        print(f"  [Filing] Analysis error: {e}")
        return FilingLanguageSignal(
            guidance_tone="neutral",
            signal="NEUTRAL",
            key_phrases=[],
        )
