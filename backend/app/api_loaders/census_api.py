"""
US Census Bureau ACS 5-Year Estimates Loader — ZIP 78207.

Fetches American Community Survey data for ZIP Code Tabulation Area (ZCTA) 78207.
No API key required for the basic public endpoints used here.

Data is cached in MongoDB with a 30-day TTL.
Falls back to local census_demographics.csv / census_economic.csv.

Census API: https://api.census.gov/data/2022/acs/acs5
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


CENSUS_ACS5_URL = "https://api.census.gov/data/2022/acs/acs5"
CACHE_KEY_CENSUS = "census_acs5_78207"
CACHE_TTL_DAYS = 30

# Variable codes → human-readable labels
# Full list: https://api.census.gov/data/2022/acs/acs5/variables.json
CENSUS_VARIABLES = {
    "B01003_001E": "total_population",
    "B01002_001E": "median_age",
    "B19013_001E": "median_household_income",
    "B17001_002E": "below_poverty_count",
    "B01003_001E": "total_population",
    "B23025_005E": "unemployed_count",
    "B23025_003E": "civilian_labor_force",
    "B25003_001E": "total_housing_units",
    "B25003_002E": "owner_occupied_units",
    "B25003_003E": "renter_occupied_units",
    "B25064_001E": "median_gross_rent",
    "B15003_022E": "bachelors_degree_count",
    "B15003_001E": "educational_attainment_total",
    "B02001_002E": "white_alone",
    "B02001_003E": "black_or_african_american",
    "B03003_003E": "hispanic_or_latino",
    "B27001_001E": "health_insurance_total",
    "C27006_004E": "medicaid_male",
    "C27006_009E": "medicaid_female",
}


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _resolve_data_path(*parts: str) -> Optional[str]:
    """Resolve path relative to backend/Data/ZIPCODE 78207/clean/."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidate = os.path.join(base, "Data", "ZIPCODE 78207", "clean", *parts)
    if os.path.exists(candidate):
        return candidate
    return None


# ---------------------------------------------------------------------------
# MongoDB cache helpers
# ---------------------------------------------------------------------------

def _get_from_mongo_cache() -> Optional[Dict]:
    """Try to get Census data from MongoDB api_cache."""
    if get_mongo_client is None:
        return None
    try:
        client = get_mongo_client()
        if not client.enabled or client._db is None:
            return None
        col = client._db.api_cache
        doc = col.find_one({"cache_key": CACHE_KEY_CENSUS})
        if doc and doc.get("data"):
            age = datetime.utcnow() - doc.get("fetched_at", datetime.min)
            if age < timedelta(days=CACHE_TTL_DAYS):
                print(f"[Census API] Cache hit (age: {age.days}d)")
                return doc["data"]
    except Exception as e:
        print(f"[Census API] MongoDB cache read error: {e}")
    return None


def _save_to_mongo_cache(data: Dict) -> None:
    """Save Census data to MongoDB api_cache."""
    if get_mongo_client is None:
        return
    try:
        client = get_mongo_client()
        if not client.enabled or client._db is None:
            return
        col = client._db.api_cache
        col.update_one(
            {"cache_key": CACHE_KEY_CENSUS},
            {
                "$set": {
                    "cache_key": CACHE_KEY_CENSUS,
                    "source": "Census Bureau ACS 5-Year Estimates (2022)",
                    "zipcode": "78207",
                    "data": data,
                    "fetched_at": datetime.utcnow(),
                    "expires_at": datetime.utcnow() + timedelta(days=CACHE_TTL_DAYS),
                }
            },
            upsert=True,
        )
        print(f"[Census API] Saved to MongoDB api_cache")
    except Exception as e:
        print(f"[Census API] MongoDB cache write error: {e}")


# ---------------------------------------------------------------------------
# Fetch from Census API
# ---------------------------------------------------------------------------

def fetch_census_acs(zip_code: str = "78207", force_refresh: bool = False) -> Dict[str, Any]:
    """
    Fetch ACS 5-Year Estimates for a ZIP Code Tabulation Area.

    Priority:
    1. MongoDB cache (< 30 days old)
    2. Census Bureau API (no key required)
    3. Local census_demographics.csv + census_economic.csv fallback

    Returns dict with census variable name → value.
    """
    if not force_refresh:
        cached = _get_from_mongo_cache()
        if cached:
            return cached

    # Try the Census API
    var_list = ",".join(CENSUS_VARIABLES.keys())
    try:
        print(f"[Census API] Fetching ACS 5-year data for ZCTA {zip_code}...")
        t0 = time.time()
        response = requests.get(
            CENSUS_ACS5_URL,
            params={
                "get": f"NAME,{var_list}",
                "for": f"zip code tabulation area:{zip_code}",
            },
            timeout=15,
        )
        if response.status_code == 200:
            raw = response.json()
            if len(raw) >= 2:
                headers = raw[0]
                values = raw[1]
                data = {}
                for i, header in enumerate(headers):
                    label = CENSUS_VARIABLES.get(header, header)
                    raw_val = values[i]
                    # Convert to int/float where possible
                    try:
                        data[label] = int(raw_val) if raw_val and raw_val != "-666666666" else None
                    except (ValueError, TypeError):
                        data[label] = raw_val

                elapsed = int((time.time() - t0) * 1000)
                print(f"[Census API] Fetched {len(data)} variables in {elapsed}ms")

                # Derived metrics
                if data.get("civilian_labor_force") and data.get("unemployed_count"):
                    lf = data["civilian_labor_force"]
                    unemp = data["unemployed_count"]
                    if lf and lf > 0:
                        data["unemployment_rate_pct"] = round(unemp / lf * 100, 1)

                if data.get("educational_attainment_total") and data.get("bachelors_degree_count"):
                    total = data["educational_attainment_total"]
                    bach = data["bachelors_degree_count"]
                    if total and total > 0:
                        data["bachelors_degree_pct"] = round(bach / total * 100, 1)

                if data.get("total_housing_units"):
                    hu = data["total_housing_units"]
                    owner = data.get("owner_occupied_units") or 0
                    renter = data.get("renter_occupied_units") or 0
                    if hu > 0:
                        data["owner_occupied_pct"] = round(owner / hu * 100, 1)
                        data["renter_occupied_pct"] = round(renter / hu * 100, 1)

                _save_to_mongo_cache(data)
                return data
    except Exception as e:
        print(f"[Census API] Fetch failed: {e}")

    # Fallback to local CSV files
    return _load_census_local_fallback()


def _load_census_local_fallback() -> Dict[str, Any]:
    """Load local census CSV files as fallback."""
    result: Dict[str, Any] = {"source": "local_csv_fallback"}

    demo_path = _resolve_data_path("census_demographics.csv")
    if demo_path:
        try:
            df = pd.read_csv(demo_path)
            result["demographics_records"] = len(df)
            result["demographic_columns"] = list(df.columns[:15])  # sample cols
            print(f"[Census API] Loaded demographics from local CSV ({len(df)} rows)")
        except Exception as e:
            print(f"[Census API] Demographics CSV failed: {e}")

    econ_path = _resolve_data_path("census_economic.csv")
    if econ_path:
        try:
            df = pd.read_csv(econ_path)
            result["economic_records"] = len(df)
            print(f"[Census API] Loaded economic data from local CSV ({len(df)} rows)")
        except Exception as e:
            print(f"[Census API] Economic CSV failed: {e}")

    return result


# ---------------------------------------------------------------------------
# Summary builder
# ---------------------------------------------------------------------------

def get_census_summary(zip_code: str = "78207") -> Dict[str, Any]:
    """
    Get a human-readable summary of census data for a ZIP code.
    """
    data = fetch_census_acs(zip_code)
    if not data:
        return {"error": "No census data available", "zip_code": zip_code}

    summary = {
        "zip_code": zip_code,
        "source": data.get("source", "Census Bureau ACS 2022"),
        "population": data.get("total_population"),
        "median_age": data.get("median_age"),
        "median_household_income_usd": data.get("median_household_income"),
        "below_poverty_count": data.get("below_poverty_count"),
        "unemployment_rate_pct": data.get("unemployment_rate_pct"),
        "bachelors_degree_pct": data.get("bachelors_degree_pct"),
        "owner_occupied_pct": data.get("owner_occupied_pct"),
        "renter_occupied_pct": data.get("renter_occupied_pct"),
        "median_gross_rent_usd": data.get("median_gross_rent"),
        "fetched_at": datetime.utcnow().isoformat(),
    }
    return {k: v for k, v in summary.items() if v is not None}


if __name__ == "__main__":
    import json
    summary = get_census_summary()
    print(json.dumps(summary, indent=2, default=str))
