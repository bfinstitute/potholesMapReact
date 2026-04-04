import os
import re
from typing import List, Optional

import duckdb

APP_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(APP_DIR, ".."))

DB_PATH = os.path.join(APP_DIR, "potholess.db")
PARQUET_PATH = os.path.join(BACKEND_DIR, "potholes.parquet")


def _get_connection():
    return duckdb.connect(DB_PATH)


def _street_variants(street: str) -> List[str]:
    street = (street or "").strip().lower()
    if not street:
        return []

    variants = {street}
    replacements = [
        (r"\bavenue\b", ["ave", "av"]),
        (r"\bave\b", ["avenue", "av"]),
        (r"\bav\b", ["avenue", "ave"]),
        (r"\broad\b", ["rd"]),
        (r"\brd\b", ["road"]),
        (r"\bstreet\b", ["st"]),
        (r"\bst\b", ["street"]),
        (r"\bdrive\b", ["dr"]),
        (r"\bdr\b", ["drive"]),
        (r"\bboulevard\b", ["blvd"]),
        (r"\bblvd\b", ["boulevard"]),
    ]

    changed = True
    while changed:
        changed = False
        current = list(variants)
        for value in current:
            for pattern, replacements_list in replacements:
                if re.search(pattern, value):
                    for replacement in replacements_list:
                        candidate = re.sub(pattern, replacement, value)
                        if candidate not in variants:
                            variants.add(candidate)
                            changed = True

    cleaned = []
    for value in variants:
        normalized = re.sub(r"\s+", " ", value).strip()
        if normalized:
            cleaned.append(normalized)
    return sorted(set(cleaned))


def _ensure_potholes_table(conn):
    if os.path.exists(PARQUET_PATH):
        conn.execute(
            """
            CREATE OR REPLACE TABLE potholes AS
            SELECT * FROM read_parquet(?)
            """,
            [PARQUET_PATH],
        )
    else:
        print("Warning: potholes.parquet not found. Skipping RAG data load.")


def query_table(
    street: Optional[str] = None,
    year: Optional[int] = None,
    zipcode: Optional[int] = None,
    district: Optional[int] = None,
):
    conn = _get_connection()
    _ensure_potholes_table(conn)
    tables = conn.execute("SHOW TABLES").fetchall()
    if not any("potholes" in t for t in tables):
        print("Warning: potholes table does not exist. Returning empty result.")
        conn.close()
        return []

    base_query = """
        SELECT latitude, longitude, street_name, year, council_district
        FROM potholes WHERE 1=1
    """
    params = []

    if isinstance(street, str):
        variants = _street_variants(street)
        if variants:
            clauses = []
            for variant in variants:
                safe_street = variant.replace("'", "''")
                clauses.append(f"street_name ILIKE '%{safe_street}%'")
            base_query += " AND (" + " OR ".join(clauses) + ")"

    if isinstance(year, int):
        base_query += " AND year = ?"
        params.append(year)
    elif year in ("historical", None):
        pass  # no year filter
    else:
        raise ValueError("Year must be an integer, 'historical', or None")

    if isinstance(zipcode, int):
        base_query += " AND zipcode = ?"
        params.append(zipcode)

    if isinstance(district, int):
        base_query += " AND council_district = ?"
        params.append(district)

    print("QUERY:", base_query)
    print("PARAMS:", params)

    results = conn.execute(base_query, params).fetchall()
    conn.close()
    return results
