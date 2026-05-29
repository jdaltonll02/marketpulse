"""
synthesis/drift.py — Detect and explain signal drift between pipeline runs.

Drift is only computed on explicit refreshes, not on first-time fetches.
The explanation is a focused Claude call asking why the signal changed.
"""
import json, os, sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from openai import OpenAI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    organization=os.getenv("OPENAI_ORG_ID"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)
MODEL = os.getenv("OPENAI_MODEL", "claude-sonnet-4-20250514-v1:0")

_RANK = {"BULLISH": 1, "NEUTRAL": 0, "BEARISH": -1}


def _direction(prev_signal: str, new_signal: str, prev_conf: int, new_conf: int) -> str | None:
    old_r = _RANK[prev_signal]
    new_r = _RANK[new_signal]

    if old_r == new_r:
        if abs(new_conf - prev_conf) >= 15:
            return "confidence_shift"
        return None  # stable — not worth reporting

    if (old_r == 1 and new_r == -1) or (old_r == -1 and new_r == 1):
        return "reversed"
    return "improved" if new_r > old_r else "deteriorated"


def _explain(
    company: str,
    ticker: str,
    prev_signal: str,
    prev_conf: int,
    new_signal: str,
    new_conf: int,
    direction: str,
    current_headlines: list[str],
    extra_context: str,
) -> str:
    direction_text = {
        "improved":         f"improved from {prev_signal} to {new_signal}",
        "deteriorated":     f"deteriorated from {prev_signal} to {new_signal}",
        "reversed":         f"completely reversed from {prev_signal} to {new_signal}",
        "confidence_shift": f"stayed {new_signal} but confidence {'rose' if new_conf > prev_conf else 'fell'} "
                            f"from {prev_conf}% to {new_conf}%",
    }[direction]

    prompt = f"""The pre-earnings signal for {company} ({ticker}) has {direction_text}.

Recent headlines:
{chr(10).join(f'- {h}' for h in current_headlines[:5])}

Additional context:
{extra_context[:600] if extra_context else 'None available'}

In exactly 2 sentences, explain what specific information drove this signal change.
Be concrete — reference the actual headlines or data, not generic market commentary."""

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            max_tokens=150,
            temperature=0,
            messages=[
                {"role": "system", "content": "You are a financial analyst explaining why a pre-earnings signal changed. Be concise and specific."},
                {"role": "user",   "content": prompt},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Signal {direction_text}. Automated explanation unavailable: {e}"


def detect_drift(previous, current, extra_context: str = ""):
    """
    Compare two IntelligenceObjects and return a SignalDrift if the signal
    changed meaningfully, or None if it remained stable.

    Args:
        previous: The cached IntelligenceObject from before the refresh
        current:  The freshly generated IntelligenceObject
        extra_context: Recent headlines / filing text for the explanation

    Returns:
        SignalDrift or None
    """
    from pipeline.schema import SignalDrift

    direction = _direction(
        previous.composite_signal, current.composite_signal,
        previous.confidence,       current.confidence,
    )
    if direction is None:
        return None

    explanation = _explain(
        company=current.company,
        ticker=current.ticker,
        prev_signal=previous.composite_signal,
        prev_conf=previous.confidence,
        new_signal=current.composite_signal,
        new_conf=current.confidence,
        direction=direction,
        current_headlines=current.signals.news_sentiment.top_headlines,
        extra_context=extra_context,
    )

    return SignalDrift(
        previous_signal=previous.composite_signal,
        previous_confidence=previous.confidence,
        direction=direction,
        explanation=explanation,
        detected_at=datetime.now(timezone.utc).isoformat(),
    )
