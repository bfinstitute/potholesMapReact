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
    "mental_health_needs":       ["health_places", "Health_Data ", "311 Service Request", "Track data",
                                  "Medical_Expenditure_78207_San_Antonio"],
    "funding_decision":          ["78207_master_dataset_percentage - ", "health_places", "Health_Data ", "Interventions",
                                  "Market_profile_Population_Consumer_Spending", "Medical_Expenditure_78207_San_Antonio"],
    "sdh_comprehensive":         ["78207_master_dataset_percentage - ", "health_places", "Housing 78207", "Health_Data ", "Track data",
                                  "san_antonio_78207", "Market_profile_Population_Consumer_Summary"],
    "housing_concentration":     ["Housing 78207", "311 Service Request", "Service_Request-78207",
                                  "san_antonio_78207"],
    "connect_needs_services":    ["health_places", "Interventions", "311 Service Request",
                                  "san_antonio_78207"],
    "critical_issues":           ["311 Service Request", "health_places", "Health_Data ",
                                  "san_antonio_78207"],
    "hyperlocal_assessment":     ["78207_master_dataset_percentage - ", "Track data", "census_demographics",
                                  "san_antonio_78207"],
    "underserved":               ["Track data", "census_economics", "unemployment_rate",
                                  "Market_profile_Population_Income", "san_antonio_78207"],
    "funding_intelligence":      ["Interventions", "78207_master_dataset_percentage - ", "health_places",
                                  "Market_profile_Population_Consumer_Spending", "Market_profile_Population_Consumer_Industry",
                                  "Market_profile_Population_Consumer_Summary"],
    "community_need":            ["78207_master_dataset_percentage - ", "health_places", "Track data",
                                  "san_antonio_78207", "Health_and _Beauty_Market_Potential_Demographic",
                                  "Market_profile_Population_Consumer_Summary", "Medical_Expenditure_78207_San_Antonio"],
    "community_conditions_311":  ["311 Service Request", "Service_Request-78207",
                                  "san_antonio_78207"],
    "service_landscape":         ["health_places", "Interventions", "311 Service Request",
                                  "Health_and _Beauty_Market_Potential_Behavior"],
    "need_service_gap":          ["health_places", "Interventions", "Track data",
                                  "Medical_Expenditure_78207_San_Antonio", "Market_profile_Population_Income"],
    "context_demographics":      ["census_demographics", "census_economics", "age_by_race", "age_group",
                                  "Health_and _Beauty_Market_Potential_Demographic", "Health_and _Beauty_Market_Potential_Behavior",
                                  "Market_profile_Population_Income", "Market_profile_Population_Consumer_Summary",
                                  "san_antonio_78207"],
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
