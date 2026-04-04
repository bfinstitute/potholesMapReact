from __future__ import annotations

import calendar
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd

try:
    from rag_tool import query_table
    from saaf_data import (
        get_context_metrics,
        get_environmental_hazard_summary,
        get_service_landscape_summary,
        get_top_311_categories,
        get_top_health_issues,
        get_unemployment_summary,
    )
    from saaf_gap_engine import get_gap_summary
except ModuleNotFoundError:
    from .rag_tool import query_table
    from .saaf_data import (
        get_context_metrics,
        get_environmental_hazard_summary,
        get_service_landscape_summary,
        get_top_311_categories,
        get_top_health_issues,
        get_unemployment_summary,
    )
    from .saaf_gap_engine import get_gap_summary


DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Data"))


def _resolve_data_path(*candidates: str) -> str:
    for rel_path in candidates:
        abs_path = os.path.join(DATA_ROOT, rel_path)
        if os.path.exists(abs_path):
            return abs_path
    return os.path.join(DATA_ROOT, candidates[0])


def _render(lead: str, bullets: Optional[List[str]] = None) -> str:
    lines = [(lead or "").strip()]
    if bullets:
        clean = [str(x).strip() for x in bullets if str(x).strip()]
        if clean:
            lines.append("")
            lines.append("Breakdown:")
            lines.extend([f"• {item}" for item in clean])
    return "\n".join(lines).strip()


def _render_lines(lines: List[str]) -> str:
    return "\n".join([str(x).rstrip() for x in lines if str(x).strip()]).strip()


def _to_number(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not pd.isna(value):
        return float(value)
    text = str(value).strip().replace(",", "").replace("$", "").replace("%", "")
    if not text:
        return None
    match = re.search(r"-?\d+(\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _zip_from_question(question: str) -> Optional[str]:
    match = re.search(r"\b(\d{5})\b", question)
    return match.group(1) if match else None


def _street_from_question(question: str, prefix_pattern: str, suffix_pattern: str = r"(?:\?|$)") -> Optional[str]:
    match = re.search(prefix_pattern + r"\s+(.+?)" + suffix_pattern, question, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip().strip("?.!")


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    rel_path: str
    grain: str
    topic: str


DATASET_REGISTRY: List[DatasetSpec] = [
    DatasetSpec("survey", "Survey Data.csv", "response", "survey"),
    DatasetSpec("pci", "COSA_Infrastructure/cleaned_COSA_Pavement_latlon.csv", "segment", "pavement"),
    DatasetSpec("complaints", "COSA_Infrastructure/cleaned_COSA_pavement_311.csv", "request", "complaints"),
    DatasetSpec("via_routes", "VIA/via_routes_cleaned.csv", "route", "transit"),
    DatasetSpec("health_places_78207", "ZIPCODE 78207/clean/health_places.csv", "zip", "health"),
    DatasetSpec("service_requests_78207", "ZIPCODE 78207/clean/service_requests_78207.csv", "zip", "service"),
]


@lru_cache(maxsize=1)
def load_survey() -> pd.DataFrame:
    try:
        return pd.read_csv(_resolve_data_path("Survey Data.csv"))
    except Exception:
        return pd.DataFrame()


@lru_cache(maxsize=1)
def load_pci() -> pd.DataFrame:
    try:
        df = pd.read_csv(
            _resolve_data_path(
                "COSA_Infrastructure/cleaned_COSA_Pavement_latlon.csv",
                "COSA_Infrastructure/cleaned_COSA_Pavement.csv",
                "COSA_Infrastructure/COSA_Pavement.csv",
                "COSA_Pavement.csv",
            )
        )
        if "GoogleMapView" in df.columns and ("Latitude" not in df.columns or "Longitude" not in df.columns):
            def extract_lat_lon(url: str) -> Tuple[Optional[float], Optional[float]]:
                if pd.isna(url):
                    return None, None
                match = re.search(r"place/([0-9.]+)N\s+([0-9.]+)W", str(url))
                if not match:
                    return None, None
                return float(match.group(1)), -float(match.group(2))

            df[["Latitude", "Longitude"]] = df["GoogleMapView"].apply(
                lambda value: pd.Series(extract_lat_lon(value))
            )
        return df
    except Exception:
        return pd.DataFrame()


@lru_cache(maxsize=1)
def load_complaints() -> pd.DataFrame:
    try:
        df = pd.read_csv(
            _resolve_data_path(
                "COSA_Infrastructure/cleaned_COSA_pavement_311.csv",
                "COSA_Infrastructure/COSA_pavement_311.csv",
                "COSA_pavement_311.csv",
            ),
            low_memory=False,
        )
        if "OPENEDDATETIME" in df.columns:
            df["OPENEDDATETIME"] = pd.to_datetime(df["OPENEDDATETIME"], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()


@lru_cache(maxsize=1)
def load_via_routes() -> pd.DataFrame:
    try:
        return pd.read_csv(_resolve_data_path("VIA/via_routes_cleaned.csv"))
    except Exception:
        return pd.DataFrame()


@lru_cache(maxsize=1)
def load_health_places_78207() -> pd.DataFrame:
    try:
        return pd.read_csv(_resolve_data_path("ZIPCODE 78207/clean/health_places.csv"))
    except Exception:
        return pd.DataFrame()


def _local_zip_center(zipcode: str) -> Optional[Tuple[float, float]]:
    if str(zipcode) != "78207":
        return None
    # Local ZCTA file only covers 78207 and gives a stable center point.
    return 29.422124, -98.5259784


def _subset_pci_for_zip(df: pd.DataFrame, zipcode: str) -> pd.DataFrame:
    zip_col = "zipcode" if "zipcode" in df.columns else "ZipCode" if "ZipCode" in df.columns else None
    if zip_col:
        return df[df[zip_col].astype(str) == str(zipcode)].copy()

    center = _local_zip_center(zipcode)
    if center is None or "Latitude" not in df.columns or "Longitude" not in df.columns:
        return pd.DataFrame()

    working = df.copy()
    working["Latitude"] = pd.to_numeric(working["Latitude"], errors="coerce")
    working["Longitude"] = pd.to_numeric(working["Longitude"], errors="coerce")
    working = working.dropna(subset=["Latitude", "Longitude"])
    if working.empty:
        return pd.DataFrame()

    lat, lon = center
    radius_deg = 2000 / 111320.0
    nearby = working[
        ((working["Latitude"] - lat) ** 2 + (working["Longitude"] - lon) ** 2) ** 0.5 <= radius_deg
    ].copy()
    return nearby


def _load_sacrd_pageview(month_key: str) -> pd.DataFrame:
    file_path = _resolve_data_path(f"SACRD analytics-20260401T155025Z-3-001/{month_key} pageview.csv")
    if not os.path.exists(file_path):
        return pd.DataFrame()
    try:
        df = pd.read_csv(file_path, skiprows=5)
        if len(df.columns) >= 3:
            df.columns = ["page_location", "page_referrer", "event_count", *list(df.columns[3:])]
        if "event_count" in df.columns:
            df["event_count"] = pd.to_numeric(df["event_count"], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()


def _latest_health_measure(measure_id: str) -> Optional[Dict[str, object]]:
    df = load_health_places_78207()
    if df.empty or "measure_id" not in df.columns:
        return None
    rows = df[df["measure_id"].astype(str).str.upper() == measure_id.upper()].copy()
    if rows.empty:
        return None
    if "year" in rows.columns:
        rows["year_num"] = pd.to_numeric(rows["year"], errors="coerce")
        rows = rows.sort_values("year_num", ascending=False)
    row = rows.iloc[0]
    value = _to_number(row.get("value"))
    if value is None:
        return None
    return {
        "year": int(_to_number(row.get("year")) or 0),
        "value": value,
        "measure": str(row.get("measure", measure_id)),
    }


def _survey_zip(df: pd.DataFrame, zipcode: str) -> pd.DataFrame:
    if df.empty:
        return df
    return df[df["What ZIP code do you live in?"].astype(str) == str(zipcode)].copy()


def _single_choice_distribution(series: pd.Series) -> List[Tuple[str, float]]:
    counts = series.dropna().astype(str).value_counts()
    total = counts.sum()
    if total == 0:
        return []
    return [(label, 100.0 * count / total) for label, count in counts.items()]


def _multi_choice_distribution(series: pd.Series) -> List[Tuple[str, int]]:
    items: List[str] = []
    for value in series.dropna():
        if isinstance(value, str):
            items.extend([part.strip() for part in value.split(",") if part.strip()])
    if not items:
        return []
    counts = pd.Series(items).value_counts()
    return [(str(label), int(count)) for label, count in counts.items()]


def _business_wishes_column(df: pd.DataFrame) -> Optional[str]:
    for col in df.columns:
        lowered = str(col).lower()
        if ("local business" in lowered or "local businesses" in lowered) and ("wish" in lowered or "existed" in lowered):
            return col
    return None


def _handle_pothole_street_year(question: str) -> Optional[str]:
    match = re.search(r"how many potholes (?:were )?reported on (.+?) in (\d{4})", question, flags=re.IGNORECASE)
    if not match:
        return None
    street = match.group(1).strip()
    year = int(match.group(2))
    rows = query_table(street=street, year=year)
    if not rows:
        return f"No pothole records found for streets containing '{street.lower()}' in {year}."
    df = pd.DataFrame(rows, columns=["latitude", "longitude", "street_name", "year", "council_district"])
    counts = df["street_name"].astype(str).value_counts()
    total = int(counts.sum())
    bullets = []
    for name, count in counts.items():
        report_word = "report" if int(count) == 1 else "reports"
        bullets.append(f"{name}: {int(count)} {report_word}")
    return _render(
        f"Found {total} pothole reports for streets containing '{street.lower()}' in {year}.",
        bullets,
    )


def _handle_pci_zip(question: str) -> Optional[str]:
    if not re.search(r"\bpci\b", question, flags=re.IGNORECASE):
        return None
    zipcode = _zip_from_question(question)
    if not zipcode:
        return None
    df = load_pci()
    if df.empty:
        return "Pavement condition data is not available."
    subset = _subset_pci_for_zip(df, zipcode)
    if subset.empty or "PCI" not in subset.columns:
        return f"No pavement condition records were found for zip code {zipcode}."
    pci_num = pd.to_numeric(subset["PCI"], errors="coerce").dropna()
    if pci_num.empty:
        return f"No pavement condition records were found for zip code {zipcode}."
    avg_pci = pci_num.mean()
    condition = "Good" if avg_pci >= 70 else "Fair" if avg_pci >= 50 else "Poor"
    assessment = (
        "Generally good pavement conditions with minimal pothole risk."
        if avg_pci >= 70
        else "Moderate pavement conditions with some pothole risk."
        if avg_pci >= 50
        else "Poor pavement conditions with elevated pothole risk."
    )
    return _render(
        f"Pavement Condition Index (PCI) for zip code {zipcode}:",
        [
            f"Average PCI: {avg_pci:.1f}",
            f"Range: {pci_num.min():.1f} - {pci_num.max():.1f}",
            f"Number of road segments: {len(pci_num)}",
            f"Overall condition: {condition}",
            f"Assessment: {assessment}",
        ],
    )


def _handle_complaint_history(question: str) -> Optional[str]:
    if not re.search(r"history of repeated pothole complaints", question, flags=re.IGNORECASE):
        return None
    street = _street_from_question(question, r"history of repeated pothole complaints(?:\s+along)?")
    if not street:
        return None
    df = load_complaints()
    if df.empty or "MSAG_Name" not in df.columns or "OPENEDDATETIME" not in df.columns:
        return "Complaint history data is not available."
    subset = df[df["MSAG_Name"].astype(str).str.contains(street, case=False, na=False)].copy()
    subset = subset.dropna(subset=["OPENEDDATETIME"])
    if subset.empty:
        return f"No complaint history was found for {street}."
    trend = subset.groupby(subset["OPENEDDATETIME"].dt.to_period("M")).size()
    groups: Dict[int, List[Tuple[int, int]]] = {}
    for period, count in trend.items():
        year = int(str(period)[:4])
        month = int(str(period)[5:7])
        groups.setdefault(year, []).append((month, int(count)))
    lines = [f"Complaint History for {street.title()}"]
    for year in sorted(groups):
        lines.append("")
        lines.append(f"{year}")
        for month, count in sorted(groups[year]):
            lines.append(f"• {calendar.month_abbr[month]}: {count}")
    return _render_lines(lines)


def _handle_via_routes(question: str) -> Optional[str]:
    if not re.search(r"which via buses? travel most often on pothole[- ]?prone streets?", question, flags=re.IGNORECASE):
        return None
    routes = load_via_routes()
    pavement = load_pci()
    if routes.empty or pavement.empty:
        return "VIA route and pavement data are required for this analysis."
    if "PCI" not in pavement.columns:
        return "Pavement condition data is not available."
    poor = pavement[pd.to_numeric(pavement["PCI"], errors="coerce") < 50].copy()
    if poor.empty:
        return "No pothole-prone streets were found in the pavement condition data."
    street_variations = {
        "san pedro": ["san pedro", "san pedro avenue"],
        "blanco": ["blanco", "blanco road"],
        "fredericksburg": ["fredericksburg", "fredericksburg road"],
        "zarzamora": ["zarzamora", "zarzamora street"],
        "mccullough": ["mccullough", "mccullough avenue"],
        "broadway": ["broadway", "broadway street"],
        "military": ["military", "military drive"],
        "commerce": ["commerce", "commerce street"],
    }
    rankings: List[Tuple[str, int]] = []
    for _, route in routes.iterrows():
        route_name = str(route.get("route_long_name", "")).lower()
        route_short = str(route.get("route_short_name", "")).strip()
        score = 0
        for variants in street_variations.values():
            if any(v in route_name for v in variants):
                score += int(
                    poor["MSAG_Name"].astype(str).str.lower().str.contains(
                        "|".join(re.escape(v) for v in variants), na=False
                    ).sum()
                )
        if score > 0:
            rankings.append((route_short, score))
    if not rankings:
        return "No VIA routes could be matched to pothole-prone streets."
    rankings.sort(key=lambda item: (-item[1], item[0]))
    top = rankings[:5]
    lines = ["Top VIA Routes on Pothole-Prone Streets", ""]
    for idx, (route_short, score) in enumerate(top, start=1):
        lines.append(f"{idx}. Route {route_short} - {score} poor streets")
    lines.append("")
    lines.append(f"Summary: {len(rankings)} total routes affected")
    return _render_lines(lines)


def _handle_survey_transport_sentiment(question: str) -> Optional[str]:
    match = re.search(r"do people in (?:zip code )?(\d{5}) like public transportation", question, flags=re.IGNORECASE)
    if not match:
        return None
    zipcode = match.group(1)
    df = _survey_zip(load_survey(), zipcode)
    col = "How satisfied are you with public transportation in San Antonio?"
    if df.empty or col not in df.columns:
        return f"No survey responses were found for zip code {zipcode}."
    dist = _single_choice_distribution(df[col])
    if not dist:
        return f"No public transportation responses were found for zip code {zipcode}."
    negative = sum(p for label, p in dist if "dissatisfied" in label.lower())
    positive = sum(p for label, p in dist if "satisfied" in label.lower() and "dissatisfied" not in label.lower())
    sentiment = "Negative" if negative > positive else "Positive" if positive > negative else "Mixed"
    bullets = [f"Overall sentiment: {sentiment}"]
    bullets.append(
        "Most residents are dissatisfied with public transportation."
        if sentiment == "Negative"
        else "Most residents report satisfaction with public transportation."
        if sentiment == "Positive"
        else "Resident opinions are mixed."
    )
    for label, pct in dist[:5]:
        bullets.append(f"{label}: {pct:.1f}%")
    return _render(f"Public transportation sentiment in zip code {zipcode}:", bullets)


def _handle_survey_public_transit_satisfaction(question: str) -> Optional[str]:
    match = re.search(r"are people in (?:zip code )?(\d{5}) satisfied with their public transit", question, flags=re.IGNORECASE)
    if not match:
        return None
    zipcode = match.group(1)
    df = _survey_zip(load_survey(), zipcode)
    col = "How satisfied are you with public transportation in San Antonio?"
    if df.empty or col not in df.columns:
        return f"No survey responses were found for zip code {zipcode}."
    dist = _single_choice_distribution(df[col])
    return _render(f"Public transit satisfaction in zip code {zipcode}:", [f"{label}: {pct:.1f}%" for label, pct in dist[:6]])


def _handle_survey_mode(question: str) -> Optional[str]:
    match = re.search(r"what do most citizens in (?:zip code )?(\d{5}) use for their mode of transportation", question, flags=re.IGNORECASE)
    if not match:
        return None
    zipcode = match.group(1)
    df = _survey_zip(load_survey(), zipcode)
    col = "What is your primary mode of transportation?"
    if df.empty or col not in df.columns:
        return f"No survey responses were found for zip code {zipcode}."
    dist = _single_choice_distribution(df[col])
    return _render(f"Primary mode of transportation in zip code {zipcode}:", [f"{label}: {pct:.1f}%" for label, pct in dist[:5]])


def _handle_survey_transport_improvements(question: str) -> Optional[str]:
    if not re.search(r"what do most people in san antonio want to see improved for transportation", question, flags=re.IGNORECASE):
        return None
    df = load_survey()
    col = "Which transportation improvements would most benefit your daily life?  (select all that apply)"
    if df.empty or col not in df.columns:
        return "Transportation improvement survey data is not available."
    dist = _multi_choice_distribution(df[col])
    total = len(df.index) if not df.empty else 1
    bullets = [f"{label}: {100.0 * count / total:.1f}%" for label, count in dist[:5]]
    return _render("Top requested transportation improvements in San Antonio:", bullets)


def _handle_survey_missing_services(question: str) -> Optional[str]:
    match = re.search(r"what public services or resources do people in (?:zip code )?(\d{5}) lack", question, flags=re.IGNORECASE)
    if not match:
        return None
    zipcode = match.group(1)
    df = _survey_zip(load_survey(), zipcode)
    col = "What's a public service or resource your neighborhood is currently lacking? (select all that apply)"
    if df.empty or col not in df.columns:
        return f"No survey responses were found for zip code {zipcode}."
    dist = _multi_choice_distribution(df[col])
    total = len(df.index) if not df.empty else 1
    return _render(f"Most commonly missing services in zip code {zipcode}:", [f"{label}: {100.0 * count / total:.1f}%" for label, count in dist[:5]])


def _handle_survey_investment(question: str) -> Optional[str]:
    if not re.search(r"are there opportunities for investment in san antonio", question, flags=re.IGNORECASE):
        return None
    df = load_survey()
    col = 'Are there opportunities for investment, career growth, and job opportunities in your district? (If possible, please expand on your answer choice in "Other")'
    if df.empty or col not in df.columns:
        return "Investment survey data is not available."
    dist = _single_choice_distribution(df[col])
    return _render("Perceived investment opportunities in San Antonio:", [f"{label}: {pct:.1f}%" for label, pct in dist[:5]])


def _handle_survey_city_satisfaction(question: str) -> Optional[str]:
    if not re.search(r"do san antonians like the city", question, flags=re.IGNORECASE):
        return None
    df = load_survey()
    col = "What perspective do you have about development regarding the San Antonio sports and entertainment district?"
    if df.empty or col not in df.columns:
        return "City sentiment survey data is not available."
    dist = _single_choice_distribution(df[col])
    return _render("Overall sentiment toward San Antonio:", [f"{label}: {pct:.1f}%" for label, pct in dist[:5]])


def _handle_survey_city_attitude(question: str) -> Optional[str]:
    if not re.search(r"is san antonio cool", question, flags=re.IGNORECASE):
        return None
    df = load_survey()
    col = "Feel free to share any other experiences or opinions as a citizen of your district and San Antonio: (Free Response)"
    if df.empty or col not in df.columns:
        return "Free-response survey data is not available."
    positive_keywords = ["good", "great", "love", "optimistic", "better", "improve"]
    negative_keywords = ["bad", "worse", "hate", "unsafe", "expensive", "frustrated"]
    positive = 0
    negative = 0
    total = 0
    for value in df[col].dropna():
        if not isinstance(value, str):
            continue
        text = value.lower()
        pos = sum(1 for word in positive_keywords if word in text)
        neg = sum(1 for word in negative_keywords if word in text)
        if pos > neg:
            positive += 1
        elif neg > pos:
            negative += 1
        total += 1
    if total == 0:
        return "Free-response survey data is not available."
    neutral = total - positive - negative
    return _render(
        "San Antonio sentiment based on free-response comments:",
        [
            f"Positive sentiment: {100.0 * positive / total:.1f}%",
            f"Negative sentiment: {100.0 * negative / total:.1f}%",
            f"Neutral sentiment: {100.0 * neutral / total:.1f}%",
        ],
    )


def _handle_survey_spaces(question: str) -> Optional[str]:
    zip_match = re.search(r"how accessible are public community spaces in (?:zip code )?(\d{5})", question, flags=re.IGNORECASE)
    city_match = re.search(r"how accessible are public community spaces in san antonio", question, flags=re.IGNORECASE)
    if not zip_match and not city_match:
        return None
    df = load_survey()
    col = "How accessible are public community spaces in your district? (ex. Parks, Libraries, Community Centers, etc.)"
    if df.empty or col not in df.columns:
        return "Community spaces survey data is not available."
    scope_df = _survey_zip(df, zip_match.group(1)) if zip_match else df
    if scope_df.empty:
        return f"No survey responses were found for zip code {zip_match.group(1)}."
    dist = _single_choice_distribution(scope_df[col])
    ratings = pd.to_numeric(scope_df[col], errors="coerce").dropna()
    bullets = [f"Rating {label}/10: {pct:.1f}%" for label, pct in dist[:5]]
    if not ratings.empty:
        bullets.append(f"Average accessibility rating: {ratings.mean():.1f}/10")
        bullets.append(
            "Assessment: Community spaces are generally accessible across the city."
            if ratings.mean() >= 7 and city_match
            else "Assessment: Community spaces are generally accessible."
            if ratings.mean() >= 7
            else "Assessment: Community spaces have moderate accessibility."
            if ratings.mean() >= 4
            else "Assessment: Community spaces have limited accessibility."
        )
    lead = "Community spaces accessibility in San Antonio:" if city_match else f"Community spaces accessibility in zip code {zip_match.group(1)}:"
    return _render(lead, bullets)


def _handle_survey_affordability(question: str) -> Optional[str]:
    zip_match = re.search(r"how affordable is housing in (?:zip code )?(\d{5})", question, flags=re.IGNORECASE)
    city_match = re.search(r"how affordable is housing in san antonio", question, flags=re.IGNORECASE)
    if not zip_match and not city_match:
        return None
    df = load_survey()
    col = "How would you rate the affordability of housing in your area?"
    if df.empty or col not in df.columns:
        return "Housing affordability survey data is not available."
    scope_df = _survey_zip(df, zip_match.group(1)) if zip_match else df
    if scope_df.empty:
        return f"No survey responses were found for zip code {zip_match.group(1)}."
    dist = _single_choice_distribution(scope_df[col])
    ratings = pd.to_numeric(scope_df[col], errors="coerce").dropna()
    bullets = [f"Rating {label}/5: {pct:.1f}%" for label, pct in dist[:5]]
    if not ratings.empty:
        bullets.append(f"Average affordability rating: {ratings.mean():.1f}/5")
    lead = "Housing affordability in San Antonio:" if city_match else f"Housing affordability in zip code {zip_match.group(1)}:"
    return _render(lead, bullets)


def _handle_survey_housing_types(question: str) -> Optional[str]:
    if not re.search(r"what type of housing do san antonio", question, flags=re.IGNORECASE):
        return None
    df = load_survey()
    col = "What type of dwelling do you currently live in? (select all that apply)"
    if df.empty or col not in df.columns:
        return "Housing type survey data is not available."
    dist = _multi_choice_distribution(df[col])
    total = len(df.index) if not df.empty else 1
    return _render("Housing types in San Antonio:", [f"{label}: {100.0 * count / total:.1f}%" for label, count in dist[:6]])


def _handle_survey_living_arrangements(question: str) -> Optional[str]:
    if not re.search(r"do most people live by themselves or with others", question, flags=re.IGNORECASE):
        return None
    df = load_survey()
    col = "What is your current housing situation? (select all that apply)"
    if df.empty or col not in df.columns:
        return "Living arrangement survey data is not available."
    items = _multi_choice_distribution(df[col])
    alone = 0
    with_others = 0
    for label, count in items:
        lowered = label.lower()
        if any(token in lowered for token in ["family", "friends", "roommates", "partner", "spouse"]):
            with_others += count
        if any(token in lowered for token in ["alone", "myself", "single"]):
            alone += count
    total = max(alone + with_others, 1)
    return _render(
        "Living arrangements in San Antonio:",
        [
            f"Living with others: {100.0 * with_others / total:.1f}%",
            f"Living alone: {100.0 * alone / total:.1f}%",
        ],
    )


def _handle_survey_business_wishes(question: str) -> Optional[str]:
    zip_match = re.search(r"what type(?:s)? of local businesses do citizens in (?:zip code )?(\d{5}) wish they had", question, flags=re.IGNORECASE)
    city_match = re.search(r"what type(?:s)? of local businesses do citizens in san antonio wish they had", question, flags=re.IGNORECASE)
    if not zip_match and not city_match:
        return None
    df = load_survey()
    col = _business_wishes_column(df)
    if df.empty or not col:
        return "Desired business survey data is not available."
    scope_df = _survey_zip(df, zip_match.group(1)) if zip_match else df
    if scope_df.empty:
        return f"No survey responses were found for zip code {zip_match.group(1)}."
    dist = _multi_choice_distribution(scope_df[col])
    total = len(scope_df.index) if not scope_df.empty else 1
    bullets = [f"{label}: {count} mention(s) ({100.0 * count / total:.1f}% of respondents)" for label, count in dist[:7]]
    lead = f"Desired local businesses or services in zip code {zip_match.group(1)}:" if zip_match else "Desired local businesses or services in San Antonio:"
    return _render(lead, bullets)


def _handle_78207_health_medications(question: str) -> Optional[str]:
    lowered = question.lower()
    if not ("78207" in lowered and "zip-level" in lowered and any(token in lowered for token in ["anxiety", "depression", "sleep medication", "sleep medications"])):
        return None
    depression = _latest_health_measure("DEPRESSION")
    distress = _latest_health_measure("MHLTH")
    sleep = _latest_health_measure("SLEEP")
    bullets: List[str] = []
    if depression:
        bullets.append(f"Depression among adults: {depression['value']:.1f}% ({depression['year']})")
    if distress:
        bullets.append(f"Frequent mental distress among adults: {distress['value']:.1f}% ({distress['year']})")
    if sleep:
        bullets.append(f"Short sleep duration among adults: {sleep['value']:.1f}% ({sleep['year']})")
    bullets.append("Source: ZIPCODE 78207/clean/health_places.csv")
    return _render(
        "The available ZIP-level data for 78207 does not report anxiety, depression, or sleep medication usage. It only includes related health indicators.",
        bullets,
    )


def _handle_78207_health_national(question: str) -> Optional[str]:
    lowered = question.lower()
    if not ("78207" in lowered and "national" in lowered and "mental health" in lowered):
        return None
    depression = _latest_health_measure("DEPRESSION")
    distress = _latest_health_measure("MHLTH")
    sleep = _latest_health_measure("SLEEP")
    bullets: List[str] = []
    if depression:
        bullets.append(f"Depression among adults: {depression['value']:.1f}% ({depression['year']})")
    if distress:
        bullets.append(f"Frequent mental distress among adults: {distress['value']:.1f}% ({distress['year']})")
    if sleep:
        bullets.append(f"Short sleep duration among adults: {sleep['value']:.1f}% ({sleep['year']})")
    bullets.append("Supporting source: ZIPCODE 78207/clean/health_places.csv")
    bullets.append("Data source label: BRFSS / PLACES local estimates")
    bullets.append("Limitation: no national benchmark table or direct treatment-usage measure is loaded.")
    return _render(
        "The loaded 78207 data supports local mental-health indicators, but not a true comparison to national averages for treatment usage.",
        bullets,
    )


def _handle_sacrd_pageview(question: str) -> Optional[str]:
    match = re.search(r"what are the top pageview rows for (\d{4}\s\d{2}) pageview", question, flags=re.IGNORECASE)
    if not match:
        return None
    month_key = match.group(1)
    df = _load_sacrd_pageview(month_key)
    if df.empty or "page_location" not in df.columns or "event_count" not in df.columns:
        return f"No pageview data was found for {month_key}."
    working = df.dropna(subset=["event_count"]).copy()
    working = working[working["page_location"].astype(str).str.lower() != "page location"]
    working = working[~working["page_location"].astype(str).str.contains("grand total", case=False, na=False)]
    working = working.sort_values("event_count", ascending=False).head(5)
    if working.empty:
        return f"No pageview data was found for {month_key}."
    bullets = [f"{str(row['page_location']).strip()}: {int(row['event_count'])} pageviews" for _, row in working.iterrows()]
    return _render(f"Top pageview rows for {month_key} pageview:", bullets)


def _handle_78207_common_health(question: str) -> Optional[str]:
    if not re.search(r"what are the most common health issues in zip 78207", question, flags=re.IGNORECASE):
        return None
    top = get_top_health_issues(limit=5)
    if not top:
        return "Health indicator data is not available for ZIP code 78207."
    bullets = [f"{name}: {value:.1f}%" for name, value in top]
    summary = get_unemployment_summary()
    context = get_context_metrics()
    if summary:
        bullets.append(f"Unemployment (latest): {summary['latest_rate']:.2f}%")
    if context.get("poverty_rate") is not None:
        bullets.append(f"Poverty rate: {float(context['poverty_rate']):.1f}%")
    return _render("Most common health issues in ZIP code 78207:", bullets)


def _handle_78207_services(question: str) -> Optional[str]:
    if not re.search(r"what mental health services are available in zip 78207", question, flags=re.IGNORECASE):
        return None
    summary = get_service_landscape_summary()
    if not summary:
        return "Service landscape data is not available for ZIP code 78207."
    bullets = [f"{dept}: {count} service requests" for dept, count in list(summary.items())[:5]]
    bullets.append("This is a service-request proxy, not a full provider inventory.")
    return _render("Mental health-related service landscape in ZIP code 78207:", bullets)


def _handle_78207_gap(question: str) -> Optional[str]:
    if not re.search(r"where are community needs highest but services limited in 78207", question, flags=re.IGNORECASE):
        return None
    gap = get_gap_summary()
    bullets = [
        f"Need score: {gap['need_score']}",
        f"Service score: {gap['service_score']}",
        f"Gap score: {gap['gap_score']} ({gap['gap_level']})",
    ]
    bullets.extend(gap["need_evidence"][:3])
    bullets.extend(gap["service_evidence"][:3])
    return _render("Need-vs-service gap assessment for ZIP code 78207:", bullets)


def _handle_78207_demographics(question: str) -> Optional[str]:
    if not re.search(r"what are the demographics of zip 78207", question, flags=re.IGNORECASE):
        return None
    context = get_context_metrics()
    bullets: List[str] = []
    if context["population"] is not None:
        bullets.append(f"Population: {int(context['population']):,}")
    if context["median_income"] is not None:
        bullets.append(f"Median household income: ${int(context['median_income']):,}")
    if context["poverty_rate"] is not None:
        bullets.append(f"Poverty rate: {float(context['poverty_rate']):.1f}%")
    if context["median_age"] is not None:
        bullets.append(f"Median age: {float(context['median_age']):.1f}")
    if context["uninsured_rate"] is not None:
        bullets.append(f"Uninsured rate: {float(context['uninsured_rate']):.1f}%")
    if context["hispanic_share"] is not None:
        bullets.append(f"Hispanic/Latino share: {100.0 * float(context['hispanic_share']):.1f}%")
    if context["persons_per_household"] is not None:
        bullets.append(f"Persons per household: {float(context['persons_per_household']):.2f}")
    return _render("Demographics for ZIP code 78207:", bullets)


def _handle_78207_conditions(question: str) -> Optional[str]:
    lowered = question.lower()
    if "78207" not in lowered or not re.search(r"mold|pests?|sanitation", lowered):
        return None
    hazard = get_environmental_hazard_summary()
    service_path = _resolve_data_path("ZIPCODE 78207/clean/service_requests_78207.csv")
    try:
        df = pd.read_csv(service_path)
    except Exception:
        df = pd.DataFrame()
    bullets: List[str] = []
    if not df.empty and "type" in df.columns:
        relevant = df[df["type"].astype(str).str.contains(r"mold|pest|sanitation|hygienic|vector", case=False, na=False)].copy()
        if not relevant.empty:
            top_relevant = relevant["type"].astype(str).value_counts().head(5)
            bullets.extend([f"{name}: {int(count)} cases" for name, count in top_relevant.items()])
    if hazard:
        bullets.append(f"Mold/sanitation/pests: {hazard.get('mold_sanitation_pests', 0)}")
        bullets.append(f"Vector hazards: {hazard.get('vector_hazards', 0)}")
    if not bullets:
        top = get_top_311_categories(limit=4)
        bullets.extend([f"{name}: {count} cases" for name, count in top])
    return _render("311 health-related conditions in ZIP code 78207:", bullets)


INTENT_HANDLERS: List[Callable[[str], Optional[str]]] = [
    _handle_pothole_street_year,
    _handle_pci_zip,
    _handle_complaint_history,
    _handle_via_routes,
    _handle_sacrd_pageview,
    _handle_survey_transport_sentiment,
    _handle_survey_public_transit_satisfaction,
    _handle_survey_mode,
    _handle_survey_transport_improvements,
    _handle_survey_missing_services,
    _handle_survey_investment,
    _handle_survey_city_satisfaction,
    _handle_survey_city_attitude,
    _handle_survey_spaces,
    _handle_survey_affordability,
    _handle_survey_housing_types,
    _handle_survey_living_arrangements,
    _handle_survey_business_wishes,
    _handle_78207_health_medications,
    _handle_78207_health_national,
    _handle_78207_common_health,
    _handle_78207_services,
    _handle_78207_gap,
    _handle_78207_demographics,
    _handle_78207_conditions,
]


def get_rag_response(question: str) -> Optional[str]:
    text = (question or "").strip()
    if not text:
        return None
    for handler in INTENT_HANDLERS:
        try:
            result = handler(text)
        except Exception:
            result = None
        if result:
            return result
    return None
