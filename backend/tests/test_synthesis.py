import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Test Claude synthesis — checks your CMU gateway
from pipeline.schema import Signals, NewsSentimentSignal, HiringTrendSignal, FilingLanguageSignal, PricingSignal
from pipeline.synthesis.agent import synthesise

# Build a fake signals object with dummy data
signals = Signals(
    news_sentiment=NewsSentimentSignal(score=0.5, label="BULLISH", articles_analyzed=10, top_headlines=["Apple beats estimates"]),
    hiring_trend=HiringTrendSignal(jobs_30d=50, signal="BULLISH"),
    filing_language=FilingLanguageSignal(guidance_tone="positive", signal="BULLISH"),
    pricing=PricingSignal(signal="NEUTRAL"),
)

result = synthesise("AAPL", "Apple Inc.", signals)
print(result)