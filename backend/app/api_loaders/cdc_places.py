"""
CDC PLACES API Loader — ZIP 78207 Health Data.

Fetches 36 chronic disease / health outcome measures for ZIP code 78207
from the CDC PLACES dataset (Socrata open data, no API key required).

Data is cached in MongoDB with a 30-day TTL.
Falls back to local health_places.csv if the API is unavailable.

CDC PLACES API: https://data.cdc.gov/resource/swc5-untb.json
"""

import os
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# MongoDB integration (optional — gracefully disabled if not connected)
try:
    from mongodb_client import get_mongo_client
except ImportError:
    try:
        from ..mongodb_client import get_mongo_client
    except ImportError:
        get_mongo_client = None


CDC_PLACES_URL = "https://data.cdc.gov/resource/qnzd-25i4.json"  # PLACES ZCTA 2025 release
CACHE_KEY = "cdc_places_78207"
CACHE_TTL_DAYS = 30


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _resolve_data_path(*parts: str) -> Optional[str]:
    """Resolve a path relative to backend/Data/ZIPCODE 78207/clean/."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
    candidate = os.path.join(base, "Data", "ZIPCODE 78207", "clean", *parts)
    if os.path.exists(candidate):
        return candidate
    return None


# ---------------------------------------------------------------------------
# MongoDB cache helpers
# ---------------------------------------------------------------------------

def _get_from_mongo_cache() -> Optional[List[Dict]]:
    """Try to get CDC PLACES data from MongoDB api_cache."""
    if get_mongo_client is None:
        return None
    try:
        client = get_mongo_client()
        if not client.enabled or client._db is None:
            return None
        col = client._db.api_cache
        doc = col.find_one({"cache_key": CACHE_KEY})
        if doc and doc.get("data"):
            age = datetime.utcnow() - doc.get("fetched_at", datetime.min)
            if age < timedelta(days=CACHE_TTL_DAYS):
                print(f"[CDC PLACES] Cache hit from MongoDB (age: {age.days}d)")
                return doc["data"]
    except Exception as e:
        print(f"[CDC PLACES] MongoDB cache read error: {e}")
    return None


def _save_to_mongo_cache(data: List[Dict]) -> None:
    """Save CDC PLACES data to MongoDB api_cache."""
    if get_mongo_client is None:
        return
    try:
        client = get_mongo_client()
        if not client.enabled or client._db is None:
            return
        col = client._db.api_cache
        col.update_one(
            {"cache_key": CACHE_KEY},
            {
                "$set": {
                    "cache_key": CACHE_KEY,
                    "source": "CDC PLACES API",
                    "endpoint": CDC_PLACES_URL,
                    "zipcode": "78207",
                    "record_count": len(data),
                    "data": data,
                    "fetched_at": datetime.utcnow(),
                    "expires_at": datetime.utcnow() + timedelta(days=CACHE_TTL_DAYS),
                }
            },
            upsert=True,
        )
        print(f"[CDC PLACES] Saved {len(data)} records to MongoDB api_cache")
    except Exception as e:
        print(f"[CDC PLACES] MongoDB cache write error: {e}")


# ---------------------------------------------------------------------------
# Fetch from API
# ---------------------------------------------------------------------------

def fetch_cdc_places(zip_code: str = "78207", force_refresh: bool = False) -> List[Dict]:
    """
    Fetch CDC PLACES health data for a ZIP code.

    Priority:
    1. MongoDB cache (if < 30 days old and not force_refresh)
    2. CDC PLACES API
    3. Local health_places.csv fallback

    Returns list of dicts with health measure data.
    """
    if not force_refresh:
        cached = _get_from_mongo_cache()
        if cached:
            return cached

    # Try the live API
    try:
        print(f"[CDC PLACES] Fetching live data for ZIP {zip_code}...")
        t0 = time.time()
        response = requests.get(
            CDC_PLACES_URL,
            params={"locationname": zip_code, "$limit": 500},
            timeout=15,
        )
        if response.status_code == 200:
            data = response.json()
            if data:
                elapsed = int((time.time() - t0) * 1000)
                print(f"[CDC PLACES] Fetched {len(data)} records in {elapsed}ms")
                _save_to_mongo_cache(data)
                return data
    except Exception as e:
        print(f"[CDC PLACES] API fetch failed: {e}")

    # Fallback to local CSV
    return _load_local_fallback()


def _load_local_fallback() -> List[Dict]:
    """Load local health_places.csv as fallback."""
    path = _resolve_data_path("health_places.csv")
    if path:
        try:
            df = pd.read_csv(path)
            records = df.to_dict("records")
            print(f"[CDC PLACES] Loaded {len(records)} records from local CSV fallback")
            return records
        except Exception as e:
            print(f"[CDC PLACES] Local CSV fallback failed: {e}")
    return []


# ---------------------------------------------------------------------------
# Summary builder
# ---------------------------------------------------------------------------

def get_cdc_health_summary(zip_code: str = "78207") -> Dict[str, Any]:
    """
    Get a structured summary of CDC PLACES health data for a ZIP code.

    Returns dict with key health metrics grouped by category.
    """
    records = fetch_cdc_places(zip_code)
    if not records:
        return {"error": "No CDC PLACES data available", "zip_code": zip_code}

    summary: Dict[str, Any] = {
        "zip_code": zip_code,
        "source": "CDC PLACES API",
        "total_measures": len(records),
        "fetched_at": datetime.utcnow().isoformat(),
        "measures": {},
    }

    # Group by measure category
    for record in records:
        measure = record.get("measure") or record.get("measureid") or record.get("short_question_text", "unknown")
        value = record.get("data_value") or record.get("datavalue")
        unit = record.get("data_value_unit", "%")
        category = record.get("category") or record.get("categoryid", "General")

        if measure and value is not None:
            summary["measures"][measure] = {
                "value": value,
                "unit": unit,
                "category": category,
            }

    return summary


if __name__ == "__main__":
    import json
    summary = get_cdc_health_summary()
    print(json.dumps(summary, indent=2, default=str))
