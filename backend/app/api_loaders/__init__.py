"""
API Loaders for SAAF Chatbot.

Each loader fetches live data from a public API, caches in MongoDB,
and falls back to local CSV files if the API is unavailable.

Modules:
    cdc_places   - CDC PLACES health data (36 indicators for ZIP 78207)
    sa_open_data - San Antonio Open Data Portal (311 service requests, code violations)
    census_api   - US Census Bureau ACS 5-Year Estimates (demographics, income, housing)
"""

from .cdc_places import fetch_cdc_places, get_cdc_health_summary
from .sa_open_data import fetch_sa_311, get_sa_311_summary
from .census_api import fetch_census_acs, get_census_summary

__all__ = [
    "fetch_cdc_places",
    "get_cdc_health_summary",
    "fetch_sa_311",
    "get_sa_311_summary",
    "fetch_census_acs",
    "get_census_summary",
]
