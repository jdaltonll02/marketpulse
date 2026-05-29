"""
scrapers/linkedin.py — Hiring signal via Bright Data Web Scraper API.

Fetches job postings for a company and returns raw records.
The signal analyser (signals/hiring.py) interprets these records.
"""
import time
import requests
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from config import BRIGHTDATA_API_KEY

# LinkedIn Jobs dataset ID — from the Bright Data dataset catalogue
LINKEDIN_JOBS_DATASET_ID = "gd_lpfll7v5hce8dqdj"
BASE_URL = "https://api.brightdata.com/datasets/v3"

HEADERS = {
    "Authorization": f"Bearer {BRIGHTDATA_API_KEY}",
    "Content-Type": "application/json",
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=30))
def _trigger_collection(payload: list) -> str:
    """Trigger a dataset collection and return the snapshot_id."""
    resp = requests.post(
        f"{BASE_URL}/trigger",
        headers=HEADERS,
        json={
            "dataset_id": LINKEDIN_JOBS_DATASET_ID,
            "include_errors": True,
            "data": payload,
        },
        timeout=30,
    )
    if resp.status_code == 402:
        raise RuntimeError("Bright Data credits exhausted — add credits at brightdata.com/billing")
    resp.raise_for_status()
    return resp.json()["snapshot_id"]


def _poll_snapshot(snapshot_id: str, timeout_s: int = 120) -> list[dict]:
    """Poll until the snapshot is ready, then return the data."""
    url = f"{BASE_URL}/snapshot/{snapshot_id}"
    deadline = time.time() + timeout_s

    while time.time() < deadline:
        resp = requests.get(url, headers=HEADERS, params={"format": "json"}, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        status = data.get("status", "")
        if status == "ready":
            return data.get("data", [])
        if status == "failed":
            raise RuntimeError(f"Snapshot {snapshot_id} failed: {data.get('error')}")

        time.sleep(5)

    raise TimeoutError(f"Snapshot {snapshot_id} not ready after {timeout_s}s")


def fetch_linkedin_jobs(company: str, limit: int = 100) -> list[dict]:
    """
    Fetch recent job postings for a company via Bright Data Web Scraper API.

    Args:
        company: Company name as it appears on LinkedIn (e.g. "Apple")
        limit:   Max number of job records to fetch

    Returns:
        List of raw job posting dicts. Empty list if no results or error.
    """
    print(f"  [LinkedIn] Triggering collection for '{company}' (limit={limit})...")

    payload = [{
        "url": f"https://www.linkedin.com/jobs/search/?keywords={requests.utils.quote(company)}",
        "location": "United States",
        "count": limit,
    }]

    try:
        snapshot_id = _trigger_collection(payload)
        print(f"  [LinkedIn] snapshot_id={snapshot_id} — polling...")
        records = _poll_snapshot(snapshot_id)
        print(f"  [LinkedIn] Retrieved {len(records)} job records")
        return records

    except Exception as e:
        print(f"  [LinkedIn] ERROR: {e}")
        return []


def fetch_linkedin_company(company_linkedin_url: str) -> dict:
    """
    Fetch company-level data (headcount, recent posts).
    Requires the full LinkedIn company URL.
    """
    COMPANY_DATASET_ID = "gd_l1viktl72bvl7bjuj0"
    payload = [{"url": company_linkedin_url}]

    try:
        resp = requests.post(
            f"{BASE_URL}/trigger",
            headers=HEADERS,
            json={"dataset_id": COMPANY_DATASET_ID, "data": payload},
            timeout=30,
        )
        resp.raise_for_status()
        snapshot_id = resp.json()["snapshot_id"]
        records = _poll_snapshot(snapshot_id, timeout_s=90)
        return records[0] if records else {}
    except Exception as e:
        print(f"  [LinkedIn Company] ERROR: {e}")
        return {}
