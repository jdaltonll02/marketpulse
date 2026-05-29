import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# LinkedIn datasets require minimum purchase on Bright Data.
# Hiring signals are sourced via SERP API (fetch_hiring_via_serp) instead.
from pipeline.scrapers.serp import fetch_hiring_via_serp

articles = fetch_hiring_via_serp("Apple Inc.", days_back=30)
print(f"Got {len(articles)} hiring articles")
if articles:
    print(articles[0])
else:
    print("No hiring articles returned")