import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Test SERP API — checks your SERP credentials
from pipeline.scrapers.serp import fetch_ticker_news
articles = fetch_ticker_news("AAPL", "Apple Inc.", days_back=7)
print(f"Got {len(articles)} articles")
if articles:
    print(articles[0])
else:
    print("No articles returned — check HTML preview above for diagnosis")