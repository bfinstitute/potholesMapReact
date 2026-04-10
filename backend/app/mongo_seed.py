"""
MongoDB Seed Script for SAAF Chatbot.

Populates the saaf_chatbot MongoDB database with structured civic data
derived from local CSVs and live API sources. Run this once to initialize
the database, then the application handles ongoing updates.

Usage:
    cd backend/app
    python mongo_seed.py                     # Full seed
    python mongo_seed.py --test-connection   # Just test the connection
    python mongo_seed.py --collection civic_data  # Seed only one collection

Collections populated:
    civic_data   - Structured ZIP 78207 facts (demographics, health, 311, etc.)
    data_sources - Registry of all data sources with freshness metadata
    api_cache    - Pre-warmed cache from live API calls (CDC, Census, SA Open Data)

Collections auto-populated at runtime (not seeded here):
    queries         - Chat query analytics
    response_cache  - LLM response cache
    groq_responses  - Groq API call logs
"""

import os
import sys
import json
import argparse
import certifi
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Bootstrap: load env first
# ---------------------------------------------------------------------------
from dotenv import load_dotenv
_env_path = Path(__file__).parent / ".env"
load_dotenv(_env_path)

from pymongo import MongoClient, ASCENDING, DESCENDING


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_client() -> tuple:
    """Connect to MongoDB, return (client, db)."""
    uri = os.getenv("MONGODB_URI")
    if not uri:
        print("[Seed] ERROR: MONGODB_URI not set in .env")
        sys.exit(1)
    print(f"[Seed] Connecting to MongoDB...")
    client = MongoClient(uri, serverSelectionTimeoutMS=10000, tlsCAFile=certifi.where())
    client.server_info()  # Raises if cannot connect
    db_name = os.getenv("MONGODB_DB_NAME", "saaf_chatbot")
    db = client[db_name]
    print(f"[Seed] Connected to database: {db_name}")
    return client, db


def _data_path(*parts: str) -> Optional[Path]:
    """Resolve path relative to backend/Data/ZIPCODE 78207/clean/."""
    base = Path(__file__).parent.parent  # backend/
    p = base / "Data" / "ZIPCODE 78207" / "clean" / Path(*parts)
    return p if p.exists() else None


def _read_csv_safe(path: Optional[Path], label: str) -> Optional[pd.DataFrame]:
    """Read a CSV file, return None on failure."""
    if not path:
        print(f"  [!] File not found: {label}")
        return None
    try:
        df = pd.read_csv(path)
        print(f"  [+] Loaded {label}: {len(df)} rows, {len(df.columns)} cols")
        return df
    except Exception as e:
        print(f"  [!] Failed to read {label}: {e}")
        return None


def _safe_value(val):
    """Convert numpy/pandas types to native Python for MongoDB."""
    if pd.isna(val) if not isinstance(val, (list, dict)) else False:
        return None
    if hasattr(val, "item"):
        return val.item()
    return val


# ---------------------------------------------------------------------------
# Seed: civic_data
# ---------------------------------------------------------------------------

def _df_to_docs(df: pd.DataFrame, zip_code: str, category: str, subcategory: str, source: str, now) -> list:
    """Convert a full DataFrame to MongoDB documents — one doc per row."""
    docs = []
    for _, row in df.iterrows():
        doc = {
            "zip_code": zip_code,
            "category": category,
            "subcategory": subcategory,
            "source": source,
            "updated_at": now,
        }
        # Merge all row data at top level for easy querying
        for k, v in row.items():
            doc[str(k)] = _safe_value(v)
        docs.append(doc)
    return docs


def seed_civic_data(db) -> int:
    """Seed civic_data collection with ALL full rows from every dataset."""
    mongo_col = db.civic_data
    mongo_col.drop()  # Fresh seed
    print("\n[civic_data] Seeding (full rows)...")

    mongo_col.create_index([("zip_code", ASCENDING)])
    mongo_col.create_index([("category", ASCENDING)])
    mongo_col.create_index([("subcategory", ASCENDING)])
    mongo_col.create_index([("updated_at", DESCENDING)])

    all_docs = []
    now = datetime.utcnow()

    # --- Health Places (CDC PLACES local export) ---
    df = _read_csv_safe(_data_path("health_places.csv"), "health_places.csv")
    if df is not None:
        all_docs.extend(_df_to_docs(df, "78207", "health", "cdc_places", "CDC PLACES 2025", now))

    # --- Service Requests 311 (summarized — full file is 30MB) ---
    df_311 = _read_csv_safe(_data_path("service_requests_78207.csv"), "service_requests_78207.csv")
    if df_311 is not None:
        # Store all 167 rows from the cleaned/reduced version
        all_docs.extend(_df_to_docs(df_311, "78207", "service_requests", "311_requests", "SA 311 Data", now))

    # --- Unemployment (full historical series) ---
    df_unemp = _read_csv_safe(_data_path("unemployment_rate.csv"), "unemployment_rate.csv")
    if df_unemp is not None:
        all_docs.extend(_df_to_docs(df_unemp, "78207", "economic", "unemployment", "BLS via local dataset", now))

    # --- Census Demographics (all 685 rows) ---
    df_demo = _read_csv_safe(_data_path("census_demographics.csv"), "census_demographics.csv")
    if df_demo is not None:
        all_docs.extend(_df_to_docs(df_demo, "78207", "demographics", "census_demographics", "US Census Bureau ACS", now))

    # --- Census Economic (all 137 rows) ---
    df_econ = _read_csv_safe(_data_path("census_economic.csv"), "census_economic.csv")
    if df_econ is not None:
        all_docs.extend(_df_to_docs(df_econ, "78207", "economic", "census_economic", "US Census Bureau ACS", now))

    # --- Master Dataset (all 98 rows) ---
    df_master = _read_csv_safe(_data_path("master_dataset.csv"), "master_dataset.csv")
    if df_master is not None:
        all_docs.extend(_df_to_docs(df_master, "78207", "overview", "master_dataset", "Aggregated local dataset", now))

    # --- Age Groups (all 20 rows) ---
    df_age = _read_csv_safe(_data_path("age_groups.csv"), "age_groups.csv")
    if df_age is not None:
        all_docs.extend(_df_to_docs(df_age, "78207", "demographics", "age_groups", "Census Bureau", now))

    # --- Age by Race ---
    df_race = _read_csv_safe(_data_path("age_by_race.csv"), "age_by_race.csv")
    if df_race is not None:
        all_docs.extend(_df_to_docs(df_race, "78207", "demographics", "age_by_race", "Census Bureau", now))

    # --- Master Percentage ---
    df_pct = _read_csv_safe(_data_path("78207_master_dataset_percentage.csv"), "78207_master_dataset_percentage.csv")
    if df_pct is not None:
        all_docs.extend(_df_to_docs(df_pct, "78207", "overview", "master_percentage", "Aggregated local dataset", now))

    # --- Master Value ---
    df_val = _read_csv_safe(_data_path("78207_master_dataset_value.csv"), "78207_master_dataset_value.csv")
    if df_val is not None:
        all_docs.extend(_df_to_docs(df_val, "78207", "overview", "master_value", "Aggregated local dataset", now))

    # --- Portal Entity Counts ---
    df_portal = _read_csv_safe(_data_path("portal_entity_counts_78207.csv"), "portal_entity_counts_78207.csv")
    if df_portal is not None:
        all_docs.extend(_df_to_docs(df_portal, "78207", "overview", "portal_entity_counts", "SA Open Data Portal", now))

    # --- Health & Beauty Market Potential (all rows) ---
    hb_dir = _data_path("Health_and_Beauty_Market_Potential_78207")
    if hb_dir and hb_dir.exists():
        for hb_file in hb_dir.glob("*.csv"):
            df_hb = _read_csv_safe(hb_file, hb_file.name)
            if df_hb is not None:
                all_docs.extend(_df_to_docs(df_hb, "78207", "health_behavior", "market_potential",
                                             f"Health & Beauty Market Data", now))

    # --- Medical Expenditures (all rows) ---
    med_dir = _data_path("Medical_Expenditures_78207")
    if med_dir and med_dir.exists():
        for med_file in med_dir.glob("*.csv"):
            df_med = _read_csv_safe(med_file, med_file.name)
            if df_med is not None:
                all_docs.extend(_df_to_docs(df_med, "78207", "health_spending", "medical_expenditures",
                                             f"Medical Expenditures Data", now))

    # --- Market Profile (all rows) ---
    mp_dir = _data_path("Market_Profile_78207")
    if mp_dir and mp_dir.exists():
        for mp_file in mp_dir.glob("*.csv"):
            df_mp = _read_csv_safe(mp_file, mp_file.name)
            if df_mp is not None:
                subcat = mp_file.stem.replace("Market_Profile_Population_", "").lower()
                all_docs.extend(_df_to_docs(df_mp, "78207", "market", f"market_{subcat}",
                                             f"Market Profile", now))

    # --- Survey Data ---
    survey_path = Path(__file__).parent.parent / "Data" / "Survey Data.csv"
    if survey_path.exists():
        df_survey = _read_csv_safe(survey_path, "Survey Data.csv")
        if df_survey is not None:
            all_docs.extend(_df_to_docs(df_survey, "78207", "citizen_feedback", "survey",
                                         "Citizen Survey 2025", now))

    if all_docs:
        # Insert in batches to avoid hitting MongoDB 16MB document limit
        BATCH = 500
        total_inserted = 0
        for i in range(0, len(all_docs), BATCH):
            batch = all_docs[i:i + BATCH]
            result = mongo_col.insert_many(batch)
            total_inserted += len(result.inserted_ids)
        print(f"[civic_data] ✓ Inserted {total_inserted} documents ({len(all_docs)} total rows across all datasets)")
        return total_inserted
    else:
        print("[civic_data] No documents to insert")
        return 0


# ---------------------------------------------------------------------------
# Seed: data_sources
# ---------------------------------------------------------------------------

def seed_data_sources(db) -> int:
    """Seed data_sources registry with all known data sources."""
    col = db.data_sources
    col.drop()
    print("\n[data_sources] Seeding registry...")

    col.create_index([("source_name", ASCENDING)], unique=True)
    col.create_index([("source_type", ASCENDING)])

    now = datetime.utcnow()
    sources = [
        {
            "source_name": "health_places_csv",
            "source_type": "local_csv",
            "description": "CDC PLACES 2025 health indicators for ZIP 78207",
            "file_path": "backend/Data/ZIPCODE 78207/clean/health_places.csv",
            "update_frequency": "annual",
            "last_updated": now,
            "status": "active",
            "categories": ["health", "chronic_disease"],
        },
        {
            "source_name": "cdc_places_api",
            "source_type": "api",
            "description": "Live CDC PLACES health data via Socrata API",
            "api_endpoint": "https://data.cdc.gov/resource/swc5-untb.json",
            "api_key_required": False,
            "cache_ttl_days": 30,
            "update_frequency": "monthly",
            "last_fetched": None,
            "status": "configured",
            "categories": ["health", "chronic_disease"],
        },
        {
            "source_name": "service_requests_78207_csv",
            "source_type": "local_csv",
            "description": "311 service requests for ZIP 78207",
            "file_path": "backend/Data/ZIPCODE 78207/clean/service_requests_78207.csv",
            "update_frequency": "as_available",
            "last_updated": now,
            "status": "active",
            "categories": ["service_requests", "311"],
        },
        {
            "source_name": "sa_open_data_311_api",
            "source_type": "api",
            "description": "Live San Antonio 311 service requests via Open Data Portal",
            "api_endpoint": "https://data.sanantonio.gov/resource/7jde-fmbd.json",
            "api_key_required": False,
            "cache_ttl_hours": 24,
            "update_frequency": "daily",
            "last_fetched": None,
            "status": "configured",
            "categories": ["service_requests", "311"],
        },
        {
            "source_name": "census_demographics_csv",
            "source_type": "local_csv",
            "description": "US Census Bureau demographic data for ZIP 78207",
            "file_path": "backend/Data/ZIPCODE 78207/clean/census_demographics.csv",
            "update_frequency": "annual",
            "last_updated": now,
            "status": "active",
            "categories": ["demographics", "census"],
        },
        {
            "source_name": "census_economic_csv",
            "source_type": "local_csv",
            "description": "US Census Bureau economic data for ZIP 78207",
            "file_path": "backend/Data/ZIPCODE 78207/clean/census_economic.csv",
            "update_frequency": "annual",
            "last_updated": now,
            "status": "active",
            "categories": ["economic", "census"],
        },
        {
            "source_name": "census_acs5_api",
            "source_type": "api",
            "description": "US Census Bureau ACS 5-Year Estimates",
            "api_endpoint": "https://api.census.gov/data/2022/acs/acs5",
            "api_key_required": False,
            "cache_ttl_days": 30,
            "update_frequency": "annual",
            "last_fetched": None,
            "status": "configured",
            "categories": ["demographics", "economic", "housing"],
        },
        {
            "source_name": "unemployment_rate_csv",
            "source_type": "local_csv",
            "description": "Historical unemployment rate data",
            "file_path": "backend/Data/ZIPCODE 78207/clean/unemployment_rate.csv",
            "update_frequency": "monthly",
            "last_updated": now,
            "status": "active",
            "categories": ["economic", "employment"],
        },
        {
            "source_name": "health_behavior_market_csv",
            "source_type": "local_csv",
            "description": "Health & Beauty Market Potential — exercise, diet, monitoring data",
            "file_path": "backend/Data/ZIPCODE 78207/clean/Health_and_Beauty_Market_Potential_78207/",
            "update_frequency": "as_available",
            "last_updated": now,
            "status": "active",
            "categories": ["health_behavior", "lifestyle"],
        },
        {
            "source_name": "medical_expenditures_csv",
            "source_type": "local_csv",
            "description": "Medical expenditure data — insurance, prescriptions, dental, hospital",
            "file_path": "backend/Data/ZIPCODE 78207/clean/Medical_Expenditures_78207/",
            "update_frequency": "as_available",
            "last_updated": now,
            "status": "active",
            "categories": ["health_spending", "insurance"],
        },
        {
            "source_name": "potholes_geopackage",
            "source_type": "local_geopackage",
            "description": "Primary geospatial potholes dataset (15MB GeoPackage)",
            "file_path": "backend/app/potholes_data.gpkg",
            "update_frequency": "as_available",
            "last_updated": now,
            "status": "active",
            "categories": ["geospatial", "infrastructure"],
        },
        {
            "source_name": "survey_data_csv",
            "source_type": "local_csv",
            "description": "Citizen survey responses (113 responses)",
            "file_path": "backend/Data/Survey Data.csv",
            "update_frequency": "as_available",
            "last_updated": now,
            "status": "active",
            "categories": ["citizen_feedback", "survey"],
        },
        {
            "source_name": "groq_llm",
            "source_type": "api",
            "description": "Groq LLM API for civic synthesis and question answering",
            "api_endpoint": "https://api.groq.com/openai/v1/chat/completions",
            "api_key_required": True,
            "update_frequency": "realtime",
            "status": "active",
            "categories": ["llm", "synthesis"],
        },
    ]

    result = col.insert_many(sources)
    print(f"[data_sources] ✓ Inserted {len(result.inserted_ids)} source registry entries")
    return len(result.inserted_ids)


# ---------------------------------------------------------------------------
# Seed: api_cache (pre-warm with live API calls)
# ---------------------------------------------------------------------------

def seed_api_cache(db) -> int:
    """Pre-warm api_cache collection with live API data."""
    print("\n[api_cache] Pre-warming cache from live APIs...")
    count = 0

    # Import API loaders (they handle their own MongoDB writes)
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from api_loaders.cdc_places import fetch_cdc_places
        from api_loaders.census_api import fetch_census_acs
        from api_loaders.sa_open_data import fetch_sa_311
    except ImportError as e:
        print(f"  [!] Could not import api_loaders: {e}")
        return 0

    # CDC PLACES
    try:
        print("  Fetching CDC PLACES data...")
        cdc_data = fetch_cdc_places(force_refresh=True)
        if cdc_data:
            print(f"  [+] CDC PLACES: {len(cdc_data)} records cached")
            count += 1
        else:
            print("  [!] CDC PLACES: No data returned (API may be down, check later)")
    except Exception as e:
        print(f"  [!] CDC PLACES fetch error: {e}")

    # Census ACS
    try:
        print("  Fetching Census ACS data...")
        census_data = fetch_census_acs(force_refresh=True)
        if census_data and not census_data.get("error"):
            print(f"  [+] Census ACS: {len(census_data)} variables cached")
            count += 1
        else:
            print("  [!] Census ACS: No data returned")
    except Exception as e:
        print(f"  [!] Census ACS fetch error: {e}")

    # SA 311 (live API may differ from local CSV)
    try:
        print("  Fetching SA 311 data...")
        sa_311_data = fetch_sa_311(force_refresh=True)
        if sa_311_data:
            print(f"  [+] SA 311: {len(sa_311_data)} records cached")
            count += 1
        else:
            print("  [!] SA 311: No data returned")
    except Exception as e:
        print(f"  [!] SA 311 fetch error: {e}")

    # Update data_sources with last_fetched timestamp
    try:
        now = datetime.utcnow()
        db.data_sources.update_many(
            {"source_type": "api"},
            {"$set": {"last_fetched": now, "status": "active"}},
        )
    except Exception:
        pass

    print(f"[api_cache] ✓ Pre-warmed {count}/3 API sources")
    return count


# ---------------------------------------------------------------------------
# Create indexes on runtime collections
# ---------------------------------------------------------------------------

def ensure_indexes(db) -> None:
    """Ensure indexes exist on all collections (idempotent)."""
    print("\n[indexes] Ensuring indexes...")

    # queries
    db.queries.create_index([("timestamp", DESCENDING)])
    db.queries.create_index([("question_hash", ASCENDING)])
    db.queries.create_index([("intent_detected", ASCENDING)])

    # response_cache
    db.response_cache.create_index([("question_hash", ASCENDING)])
    db.response_cache.create_index([("created_at", DESCENDING)])
    try:
        db.response_cache.create_index(
            [("created_at", ASCENDING)], expireAfterSeconds=7 * 24 * 60 * 60, name="cache_ttl"
        )
    except Exception:
        pass  # Index may already exist

    # groq_responses
    db.groq_responses.create_index([("created_at", DESCENDING)])
    db.groq_responses.create_index([("question_hash", ASCENDING)])

    # civic_data
    db.civic_data.create_index([("zip_code", ASCENDING)])
    db.civic_data.create_index([("category", ASCENDING)])

    # api_cache
    db.api_cache.create_index([("cache_key", ASCENDING)], unique=True)
    try:
        db.api_cache.create_index(
            [("expires_at", ASCENDING)], expireAfterSeconds=0, name="api_cache_ttl"
        )
    except Exception:
        pass

    print("[indexes] ✓ All indexes ensured")


# ---------------------------------------------------------------------------
# Print collection summary
# ---------------------------------------------------------------------------

def print_summary(db) -> None:
    """Print summary of all collections in the database."""
    print("\n" + "=" * 55)
    print("  MongoDB Database Summary")
    print("=" * 55)
    for col_name in sorted(db.list_collection_names()):
        count = db[col_name].count_documents({})
        print(f"  {col_name:<25} {count:>6} documents")
    print("=" * 55)


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="SAAF MongoDB seed script")
    parser.add_argument("--test-connection", action="store_true", help="Only test MongoDB connection")
    parser.add_argument("--collection", help="Seed only a specific collection (civic_data, data_sources, api_cache)")
    parser.add_argument("--skip-api", action="store_true", help="Skip live API calls (only seed from CSVs)")
    args = parser.parse_args()

    # Connect
    try:
        client, db = get_client()
    except Exception as e:
        print(f"[Seed] Connection failed: {e}")
        print("[Seed] Check MONGODB_URI in .env and ensure Atlas IP whitelist includes your IP")
        sys.exit(1)

    if args.test_connection:
        print(f"[Seed] ✓ Connection successful!")
        print(f"[Seed] Existing collections: {db.list_collection_names()}")
        client.close()
        return

    print(f"\n{'='*55}")
    print(f"  SAAF MongoDB Seeder")
    print(f"  Database: {db.name}")
    print(f"  Time: {datetime.utcnow().isoformat()}Z")
    print(f"{'='*55}\n")

    total = 0

    if not args.collection or args.collection == "civic_data":
        total += seed_civic_data(db)

    if not args.collection or args.collection == "data_sources":
        total += seed_data_sources(db)

    if not args.skip_api and (not args.collection or args.collection == "api_cache"):
        seed_api_cache(db)

    ensure_indexes(db)
    print_summary(db)

    print(f"\n[Seed] ✓ Complete! {total} documents inserted into civic collections.")
    print("[Seed] Runtime collections (queries, response_cache, groq_responses) populate automatically.\n")

    client.close()


if __name__ == "__main__":
    main()
