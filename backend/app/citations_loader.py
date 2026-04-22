"""
Loads Citations.csv and maps each chatbot intent to its relevant data sources.
"""
import csv
import os
from typing import List, Dict, Optional
from functools import lru_cache

_CITATIONS_PATH = os.path.join(os.path.dirname(__file__), "..", "Data", "Citations.csv")

# Maps each SAAF intent to the dataset keys that power its response
INTENT_DATASETS: Dict[str, List[str]] = {
    "mental_health_needs":       ["health_places", "Health_Data ", "311 Service Request", "Track data"],
    "funding_decision":          ["78207_master_dataset_percentage - ", "health_places", "Health_Data ", "Interventions"],
    "sdh_comprehensive":         ["78207_master_dataset_percentage - ", "health_places", "Housing 78207", "Health_Data ", "Track data"],
    "housing_concentration":     ["Housing 78207", "311 Service Request", "Service_Request-78207"],
    "connect_needs_services":    ["health_places", "Interventions", "311 Service Request"],
    "critical_issues":           ["311 Service Request", "health_places", "Health_Data "],
    "hyperlocal_assessment":     ["78207_master_dataset_percentage - ", "Track data", "census_demographics"],
    "underserved":               ["Track data", "census_economics", "unemployment_rate"],
    "funding_intelligence":      ["Interventions", "78207_master_dataset_percentage - ", "health_places"],
    "community_need":            ["78207_master_dataset_percentage - ", "health_places", "Track data"],
    "community_conditions_311":  ["311 Service Request", "Service_Request-78207"],
    "service_landscape":         ["health_places", "Interventions", "311 Service Request"],
    "need_service_gap":          ["health_places", "Interventions", "Track data"],
    "context_demographics":      ["census_demographics", "census_economics", "age_by_race", "age_group"],
}


@lru_cache(maxsize=1)
def _load_all() -> Dict[str, dict]:
    """Return a dict keyed by stripped DataSets name → row dict."""
    lookup: Dict[str, dict] = {}
    path = os.path.normpath(_CITATIONS_PATH)
    try:
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                key = row.get("DataSets", "").strip()
                if key:
                    lookup[key] = {
                        "dataset":  key,
                        "url":      row.get("Citation", "").strip(),
                        "data_link": row.get("Data Link", "").strip(),
                        "source":   row.get("Partners/Sources", "").strip(),
                    }
    except Exception as e:
        print(f"[citations] Could not load Citations.csv: {e}")
    return lookup


def get_citations_for_intent(intent: Optional[str]) -> List[dict]:
    """Return citation dicts for all datasets used by the given intent."""
    if not intent:
        return []
    all_citations = _load_all()
    datasets = INTENT_DATASETS.get(intent, [])
    results = []
    for ds in datasets:
        entry = all_citations.get(ds) or all_citations.get(ds.strip())
        if entry:
            results.append(entry)
    return results
