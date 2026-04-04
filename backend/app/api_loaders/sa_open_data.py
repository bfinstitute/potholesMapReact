"""
San Antonio Open Data Portal Loader.

Fetches live 311 service request data from the San Antonio Open Data Portal.
No API key required. Free and unlimited.

Data is cached in MongoDB with a 24-hour TTL.
Falls back to local service_requests_78207.csv if the API is unavailable.

SA Open Data: https://data.sanantonio.gov/
CKAN API: https://data.sanantonio.gov/api/3/action/
"""

import os
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List


try:
    from mongodb_client import get_mongo_client
except ImportError:
    try:
        from ..mongodb_client import get_mongo_client
    except ImportError:
        get_mongo_client = None


# San Antonio Open Data API endpoints
SA_OPEN_DATA_BASE = "https://data.sanantonio.gov/api/3/action"

# 311 Service Requests (Socrata dataset via CKAN)
# Publicly available, updated nightly
SA_311_RESOURCE_ID = "7jde-fmbd"  # Service Calls dataset
SA_311_URL = f"https://data.sanantonio.gov/resource/{SA_311_RESOURCE_ID}.json"

CACHE_KEY_311 = "sa_311_78207"
CACHE_TTL_HOURS = 24


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _resolve_data_path(*parts: str) -> Optional[str]:
    """Resolve a path relative to backend/Data/ZIPCODE 78207/clean/."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidate = os.path.join(base, "Data", "ZIPCODE 78207", "clean", *parts)
    if os.path.exists(candidate):
        return candidate
    return None


# ---------------------------------------------------------------------------
# MongoDB cache helpers
# ---------------------------------------------------------------------------

def _get_from_mongo_cache(cache_key: str, ttl_hours: int = 24) -> Optional[List[Dict]]:
    """Try to get data from MongoDB api_cache."""
    if get_mongo_client is None:
        return None
    try:
        client = get_mongo_client()
        if not client.enabled or client._db is None:
            return None
        col = client._db.api_cache
        doc = col.find_one({"cache_key": cache_key})
        if doc and doc.get("data"):
            age = datetime.utcnow() - doc.get("fetched_at", datetime.min)
            if age < timedelta(hours=ttl_hours):
                print(f"[SA Open Data] Cache hit: {cache_key} (age: {int(age.total_seconds()/3600)}h)")
                return doc["data"]
    except Exception as e:
        print(f"[SA Open Data] MongoDB cache read error: {e}")
    return None


def _save_to_mongo_cache(cache_key: str, data: List[Dict], source: str, ttl_hours: int = 24) -> None:
    """Save data to MongoDB api_cache."""
    if get_mongo_client is None:
        return
    try:
        client = get_mongo_client()
        if not client.enabled or client._db is None:
            return
        col = client._db.api_cache
        col.update_one(
            {"cache_key": cache_key},
            {
                "$set": {
                    "cache_key": cache_key,
                    "source": source,
                    "zipcode": "78207",
                    "record_count": len(data),
                    "data": data[:500],  # Store up to 500 records in Mongo
                    "full_count": len(data),
                    "fetched_at": datetime.utcnow(),
                    "expires_at": datetime.utcnow() + timedelta(hours=ttl_hours),
                }
            },
            upsert=True,
        )
        print(f"[SA Open Data] Saved {len(data)} records to MongoDB ({cache_key})")
    except Exception as e:
        print(f"[SA Open Data] MongoDB cache write error: {e}")


# ---------------------------------------------------------------------------
# Fetch 311 data
# ---------------------------------------------------------------------------

def fetch_sa_311(zip_code: str = "78207", limit: int = 2000, force_refresh: bool = False) -> List[Dict]:
    """
    Fetch SA 311 service requests for a ZIP code.

    Priority:
    1. MongoDB cache (< 24 hours old)
    2. San Antonio Open Data Socrata API
    3. Local service_requests_78207.csv fallback

    Returns list of dicts with 311 request data.
    """
    if not force_refresh:
        cached = _get_from_mongo_cache(CACHE_KEY_311)
        if cached:
            return cached

    # Try Socrata API
    try:
        print(f"[SA 311] Fetching live data for ZIP {zip_code}...")
        t0 = time.time()
        response = requests.get(
            SA_311_URL,
            params={
                "$where": f"xcoord IS NOT NULL",
                "$limit": limit,
                "$order": "openeddatetime DESC",
            },
            timeout=20,
            headers={"Accept": "application/json"},
        )
        if response.status_code == 200:
            data = response.json()
            if data:
                elapsed = int((time.time() - t0) * 1000)
                print(f"[SA 311] Fetched {len(data)} records in {elapsed}ms")
                _save_to_mongo_cache(CACHE_KEY_311, data, "SA Open Data - 311 Service Requests")
                return data
    except Exception as e:
        print(f"[SA 311] API fetch failed: {e}")

    # Fallback to local CSV
    return _load_311_local_fallback()


def _load_311_local_fallback() -> List[Dict]:
    """Load local service_requests_78207.csv as fallback."""
    path = _resolve_data_path("service_requests_78207.csv")
    if path:
        try:
            df = pd.read_csv(path)
            records = df.head(2000).to_dict("records")
            print(f"[SA 311] Loaded {len(records)} records from local CSV fallback")
            return records
        except Exception as e:
            print(f"[SA 311] Local CSV fallback failed: {e}")
    return []


# ---------------------------------------------------------------------------
# Summary builder
# ---------------------------------------------------------------------------

def get_sa_311_summary(zip_code: str = "78207") -> Dict[str, Any]:
    """
    Get a structured summary of 311 service requests.

    Returns dict with top categories, response times, open vs closed counts.
    """
    records = fetch_sa_311(zip_code)
    if not records:
        return {"error": "No 311 data available", "zip_code": zip_code}

    df = pd.DataFrame(records)
    summary: Dict[str, Any] = {
        "zip_code": zip_code,
        "source": "SA Open Data Portal",
        "total_records": len(records),
        "fetched_at": datetime.utcnow().isoformat(),
    }

    # Top categories
    category_col = next((c for c in ["reasonname", "category", "servicename", "description"] if c in df.columns), None)
    if category_col:
        top = df[category_col].value_counts().head(10).to_dict()
        summary["top_categories"] = top

    # Status breakdown
    status_col = next((c for c in ["status", "casestatus", "servicestatus"] if c in df.columns), None)
    if status_col:
        summary["status_breakdown"] = df[status_col].value_counts().to_dict()

    # Council district breakdown
    if "council_district" in df.columns:
        summary["by_council_district"] = df["council_district"].value_counts().head(10).to_dict()

    return summary


if __name__ == "__main__":
    import json
    summary = get_sa_311_summary()
    print(json.dumps(summary, indent=2, default=str))
