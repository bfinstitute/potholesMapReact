import os
import re
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

import pandas as pd


def _data_root() -> str:
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "Data", "ZIPCODE 78207")
    )


def _clean_path(filename: str) -> str:
    return os.path.join(_data_root(), "clean", filename)


def _rag_path(filename: str) -> str:
    return os.path.join(_data_root(), "rag", filename)


def _safe_read_csv(path: str) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def _to_number(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", "")
    text = text.replace("$", "")
    text = text.replace("~", "")
    text = text.replace("%", "")
    match = re.search(r"-?\d+(\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _parse_percent(value):
    num = _to_number(value)
    if num is None:
        return None
    if num > 1.0:
        return round(num / 100.0, 4)
    return round(num, 4)


def _normalize_age_file(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    age_col = df.columns[0]
    df = df.copy()
    df[age_col] = df[age_col].astype(str)
    df = df[~df[age_col].str.fullmatch(r"\s*", na=False)]
    df = df[~df[age_col].str.lower().eq("nan")]
    # Drop descriptive header row like: ",,alone,alone,..."
    df = df[~df[age_col].str.lower().eq("alone")]
    if len(df) > 0 and str(df.iloc[0, 0]).strip() == "":
        df = df.iloc[1:]
    return df.reset_index(drop=True)


@lru_cache(maxsize=1)
def load_clean_tables() -> Dict[str, pd.DataFrame]:
    tables = {
        "master_dataset": _safe_read_csv(_clean_path("master_dataset.csv")),
        "service_requests": _safe_read_csv(_clean_path("service_requests_78207.csv")),
        "unemployment_rate": _safe_read_csv(_clean_path("unemployment_rate.csv")),
        "census_demographics": _safe_read_csv(_clean_path("census_demographics.csv")),
        "census_economic": _safe_read_csv(_clean_path("census_economic.csv")),
        "health_places": _safe_read_csv(_clean_path("health_places.csv")),
        "age_groups": _normalize_age_file(_safe_read_csv(_clean_path("age_groups.csv"))),
        "age_by_race": _normalize_age_file(_safe_read_csv(_clean_path("age_by_race.csv"))),
    }
    return tables


@lru_cache(maxsize=1)
def load_rag_tables() -> Dict[str, pd.DataFrame]:
    tables = {
        "metrics_rag": _safe_read_csv(_rag_path("78207_metrics_rag.csv")),
        "service_requests_summary_rag": _safe_read_csv(
            _rag_path("service_requests_78207_summary_rag.csv")
        ),
        "unemployment_summary_rag": _safe_read_csv(
            _rag_path("unemployment_rate_summary_rag.csv")
        ),
    }
    return tables


def get_top_health_issues(limit: int = 5) -> List[Tuple[str, float]]:
    df = load_clean_tables()["health_places"]
    if df.empty:
        return []
    work = df.copy()
    work["value_num"] = work["value"].apply(_to_number)
    work = work.dropna(subset=["value_num"])
    work = work.sort_values("value_num", ascending=False)
    return [
        (str(row.get("short_name", row.get("measure", "Unknown"))), float(row["value_num"]))
        for _, row in work.head(limit).iterrows()
    ]


def get_mental_health_indicator_trend() -> Optional[Dict[str, float]]:
    df = load_clean_tables()["health_places"]
    if df.empty:
        return None
    mh = df[df["short_name"].astype(str).str.contains("Mental Distress|Depression", case=False, na=False)].copy()
    if mh.empty:
        return None
    mh["value_num"] = mh["value"].apply(_to_number)
    mh = mh.dropna(subset=["value_num"])
    if mh.empty:
        return None
    return {
        "average_percent": round(float(mh["value_num"].mean()), 1),
        "max_percent": round(float(mh["value_num"].max()), 1),
        "indicator_count": int(len(mh)),
    }


def get_top_311_categories(limit: int = 5) -> List[Tuple[str, int]]:
    df = load_clean_tables()["service_requests"]
    if df.empty or "type" not in df.columns:
        return []
    counts = df["type"].astype(str).value_counts().head(limit)
    return [(str(k), int(v)) for k, v in counts.items()]


def get_environmental_hazard_summary() -> Dict[str, int]:
    df = load_clean_tables()["service_requests"]
    if df.empty or "type" not in df.columns:
        return {}
    patterns = {
        "mold_sanitation_pests": r"mold|sanitation|pests?",
        "food_contamination": r"food contamination|food illness|food borne",
        "vector_hazards": r"vector",
        "homeless_encampment": r"encampment|homeless",
    }
    out = {}
    type_text = df["type"].astype(str).str.lower()
    for name, pat in patterns.items():
        out[name] = int(type_text.str.contains(pat, regex=True, na=False).sum())
    return out


def get_unemployment_summary() -> Optional[Dict[str, float]]:
    df = load_clean_tables()["unemployment_rate"]
    if df.empty:
        return None
    work = df.copy()
    work["unemployment_rate"] = pd.to_numeric(work["unemployment_rate"], errors="coerce")
    work = work.dropna(subset=["unemployment_rate"])
    if work.empty:
        return None
    latest = work.sort_values("date").iloc[-1]["unemployment_rate"]
    avg = work["unemployment_rate"].mean()
    return {"latest_rate": round(float(latest), 2), "historical_avg_rate": round(float(avg), 2)}


def get_context_metrics() -> Dict[str, Optional[float]]:
    df = load_clean_tables()["master_dataset"]
    out: Dict[str, Optional[float]] = {
        "population": None,
        "median_income": None,
        "poverty_rate": None,
        "median_age": None,
        "uninsured_rate": None,
        "hispanic_share": None,
        "persons_per_household": None,
    }
    if df.empty:
        return out

    metric_idx = {
        str(row["metric"]).strip().lower(): row
        for _, row in df.iterrows()
        if "metric" in row and pd.notna(row["metric"])
    }

    def _row_value(*keys):
        for key in keys:
            row = metric_idx.get(key.lower())
            if row is None:
                continue
            val = _to_number(row.get("value"))
            if val is not None:
                return val
            perc = _to_number(row.get("percentage"))
            if perc is not None:
                return perc
        return None

    out["population"] = _row_value("Population")
    out["median_income"] = _row_value("Median_Household_Income")
    out["poverty_rate"] = _row_value("Poverty_Rate")
    out["median_age"] = _row_value("Median_Age", "Median age")
    out["uninsured_rate"] = _row_value("Uninsured_Rate", "Uninsured Rate (adults)")
    out["persons_per_household"] = _row_value("Persons Per Household", "Total Households")
    out["hispanic_share"] = _parse_percent(
        metric_idx.get("hispanic_latino_percent", {}).get("percentage")
        if "hispanic_latino_percent" in metric_idx
        else None
    )
    if out["hispanic_share"] is None:
        out["hispanic_share"] = _parse_percent(_row_value("Hispanic_Latino_Percent", "Hispanic or Latino"))
    return out


def get_service_landscape_summary() -> Dict[str, int]:
    df = load_clean_tables()["service_requests"]
    if df.empty:
        return {}
    summary = {}
    if "dept" in df.columns:
        for dept, count in df["dept"].astype(str).value_counts().head(8).items():
            summary[dept] = int(count)
    return summary


def get_need_signals_by_domain() -> Dict[str, Dict[str, Optional[float]]]:
    mh = get_mental_health_indicator_trend() or {}
    context = get_context_metrics()
    hazards = get_environmental_hazard_summary()

    mental_health_score = None
    if mh.get("average_percent") is not None:
        mental_health_score = float(mh["average_percent"])

    public_health_score = None
    health_issues = get_top_health_issues(limit=10)
    if health_issues:
        public_health_score = round(sum(v for _, v in health_issues) / len(health_issues), 2)

    housing_env_signal = float(hazards.get("mold_sanitation_pests", 0) + hazards.get("vector_hazards", 0))

    economic_signal = None
    if context.get("poverty_rate") is not None and context.get("uninsured_rate") is not None:
        economic_signal = round(
            (float(context["poverty_rate"]) + float(context["uninsured_rate"])) / 2.0, 2
        )

    return {
        "mental_health": {"signal": mental_health_score},
        "public_health": {"signal": public_health_score},
        "housing_environment": {"signal": housing_env_signal},
        "economic_mobility": {"signal": economic_signal},
    }


def get_percent_estimate_consistency_issues() -> List[str]:
    issues: List[str] = []
    df = load_clean_tables()["census_economic"]
    if df.empty:
        return issues

    required_cols = {"estimate", "percent", "metric_label"}
    if not required_cols.issubset(set(df.columns)):
        return issues

    # Flag rows where percent field appears to be a raw count.
    for _, row in df.iterrows():
        pct = _to_number(row.get("percent"))
        est = _to_number(row.get("estimate"))
        label = str(row.get("metric_label", "metric"))
        if pct is None or est is None:
            continue
        if pct > 100 and est == pct:
            issues.append(f"{label}: percent appears to store an estimate value ({pct}).")
    return issues


def get_available_data_sources() -> List[str]:
    return [
        "ZIP78207 clean/master_dataset.csv",
        "ZIP78207 clean/health_places.csv",
        "ZIP78207 clean/service_requests_78207.csv",
        "ZIP78207 clean/unemployment_rate.csv",
        "ZIP78207 clean/census_demographics.csv",
        "ZIP78207 clean/census_economic.csv",
        "ZIP78207 clean/age_groups.csv",
        "ZIP78207 clean/age_by_race.csv",
        "ZIP78207 rag/78207_metrics_rag.csv",
        "ZIP78207 rag/service_requests_78207_summary_rag.csv",
        "ZIP78207 rag/unemployment_rate_summary_rag.csv",
    ]
