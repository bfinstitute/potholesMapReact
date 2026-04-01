import os
from typing import Optional

import duckdb

DB_PATH = os.path.join(os.path.dirname(__file__), "potholess.db")
PARQUET_PATH = os.path.join(os.path.dirname(__file__), "potholes.parquet")


def _get_connection():
    return duckdb.connect(DB_PATH)


def _ensure_potholes_table(conn):
    tables = conn.execute("SHOW TABLES").fetchall()
    if any("potholes" in t for t in tables):
        return

    if os.path.exists(PARQUET_PATH):
        conn.execute(
            """
            CREATE TABLE potholes AS
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
        safe_street = street.replace("'", "''")
        base_query += f" AND street_name ILIKE '%{safe_street}%'"

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