from typing import Optional, Tuple, List

import pandas as pd

try:
    from .map_highlights import zip_centroid_marker
except ImportError:
    from map_highlights import zip_centroid_marker

try:
    from saaf_data import (
        get_available_data_sources,
        get_context_metrics,
        get_environmental_hazard_summary,
        get_mental_health_indicator_trend,
        get_need_signals_by_domain,
        get_percent_estimate_consistency_issues,
        get_service_landscape_summary,
        get_top_311_categories,
        get_top_health_issues,
        get_unemployment_summary,
    )
    from saaf_gap_engine import get_gap_summary
    from saaf_intents import detect_intent
except ModuleNotFoundError:
    from .saaf_data import (
        get_available_data_sources,
        get_context_metrics,
        get_environmental_hazard_summary,
        get_mental_health_indicator_trend,
        get_need_signals_by_domain,
        get_percent_estimate_consistency_issues,
        get_service_landscape_summary,
        get_top_311_categories,
        get_top_health_issues,
        get_unemployment_summary,
    )
    from .saaf_gap_engine import get_gap_summary
    from .saaf_intents import detect_intent


# Define user-friendly source names with clickable links
# TODO: Replace placeholder URLs with actual data source links
SOURCE_NAMES = {
    "demographics": "[U.S. Census Bureau - American Community Survey](https://data.census.gov/)",
    "health": "[CDC PLACES - Local Health Data](https://www.cdc.gov/places/)",
    "311": "[San Antonio 311 Service Requests](https://www.sanantonio.gov/311)",
    "unemployment": "[Bureau of Labor Statistics - Employment Data](https://www.bls.gov/)"
}


def _append_sources(text: str, sources: List[str]) -> str:
    """Append clickable source links to response text."""
    if not sources:
        return text

    # Remove duplicates while preserving order
    unique_sources = []
    for source in sources:
        if source not in unique_sources:
            unique_sources.append(source)

    # Format sources with markdown links
    sources_section = "\n\n---\n\n**Data Sources:**\n" + "\n".join([f"• {source}" for source in unique_sources])
    return text + sources_section


def _strict_not_available_response(topic: str) -> Tuple[str, None, pd.DataFrame]:
    top_sources = get_available_data_sources()[:5]
    sources = "\n".join([f"- {s}" for s in top_sources])
    text = (
        f"I do not have ingested {topic} data for ZIP 78207 yet, so I cannot provide a data-backed answer.\n\n"
        f"Currently available datasets I can use are:\n{sources}\n\n"
        "If you want this answered, we need to ingest that source first."
    )
    return text, None, zip_centroid_marker("78207", label="ZIP 78207 (SAAF)", color="#9370DB")


def _community_need_response() -> Tuple[str, None, pd.DataFrame]:
    top_health = get_top_health_issues(limit=3)
    mh = get_mental_health_indicator_trend()
    unemployment = get_unemployment_summary()
    context = get_context_metrics()
    domain_signals = get_need_signals_by_domain()

    if not top_health:
        return _strict_not_available_response("community need")

    sources_used = []
    lines = ["ZIP 78207 community need signals (data-backed):"]
    lines.append("Top public health burdens from `clean/health_places.csv`:")
    for name, val in top_health:
        lines.append(f"- {name}: {val:.1f}%")
    sources_used.append(SOURCE_NAMES["health"])

    if mh:
        lines.append(
            f"- Mental health burden proxy (Depression + Frequent Mental Distress): average {mh['average_percent']:.1f}%"
        )
    if unemployment:
        lines.append(f"- Unemployment (latest): {unemployment['latest_rate']:.2f}%")
        sources_used.append(SOURCE_NAMES["unemployment"])
    if context.get("poverty_rate") is not None:
        lines.append(f"- Poverty rate from `clean/master_dataset.csv`: {float(context['poverty_rate']):.1f}%")
        sources_used.append(SOURCE_NAMES["demographics"])
    if context.get("uninsured_rate") is not None:
        lines.append(f"- Uninsured rate proxy from `clean/master_dataset.csv`: {float(context['uninsured_rate']):.1f}%")
        if SOURCE_NAMES["demographics"] not in sources_used:
            sources_used.append(SOURCE_NAMES["demographics"])
    mh_signal = domain_signals.get("mental_health", {}).get("signal")
    if mh_signal is not None:
        lines.append(f"- Domain signal (mental health): {float(mh_signal):.1f}")
    ph_signal = domain_signals.get("public_health", {}).get("signal")
    if ph_signal is not None:
        lines.append(f"- Domain signal (public health): {float(ph_signal):.1f}")
    consistency_issues = get_percent_estimate_consistency_issues()
    if consistency_issues:
        lines.append(f"- Data quality note: {len(consistency_issues)} consistency flag(s) in economic tables.")

    lines.append("Ask a follow-up for detailed breakdown by indicator.")

    text = _append_sources("\n".join(lines), sources_used)
    return text, None, zip_centroid_marker("78207", label="ZIP 78207 (SAAF)", color="#9370DB")


def _community_conditions_311_response() -> Tuple[str, None, pd.DataFrame]:
    top_types = get_top_311_categories(limit=4)
    hazard = get_environmental_hazard_summary()
    if not top_types:
        return _strict_not_available_response("311 conditions")

    sources_used = [SOURCE_NAMES["311"]]
    lines = ["ZIP 78207 community conditions (311 health-related signals):"]
    lines.append("Most common request types from `clean/service_requests_78207.csv`:")
    for name, count in top_types:
        lines.append(f"- {name}: {count} cases")

    if hazard:
        lines.append("Hazard signal counts (keyword grouped):")
        lines.append(f"- Mold/sanitation/pests: {hazard.get('mold_sanitation_pests', 0)}")
        lines.append(f"- Vector hazards: {hazard.get('vector_hazards', 0)}")
        lines.append(f"- Homeless encampment/outreach: {hazard.get('homeless_encampment', 0)}")

    lines.append("Ask a follow-up for month-wise or neighborhood-level summary.")

    text = _append_sources("\n".join(lines), sources_used)
    return text, None, zip_centroid_marker("78207", label="ZIP 78207 (SAAF)", color="#9370DB")


def _service_landscape_response() -> Tuple[str, None, pd.DataFrame]:
    service_summary = get_service_landscape_summary()
    if not service_summary:
        return _strict_not_available_response("service landscape")

    sources_used = [SOURCE_NAMES["311"]]
    lines = [
        "Service landscape proxy for ZIP 78207 (from 311 departmental activity in `clean/service_requests_78207.csv`):"
    ]
    for dept, count in list(service_summary.items())[:5]:
        lines.append(f"- {dept}: {count} service requests")
    lines.append(
        "Note: this is operational service-request activity, not a complete provider capacity inventory."
    )
    text = _append_sources("\n".join(lines), sources_used)
    return text, None, zip_centroid_marker("78207", label="ZIP 78207 (SAAF)", color="#9370DB")


def _need_service_gap_response() -> Tuple[str, None, pd.DataFrame]:
    gap = get_gap_summary()
    # Gap analysis uses health, 311, and demographics data
    sources_used = [SOURCE_NAMES["health"], SOURCE_NAMES["311"], SOURCE_NAMES["demographics"]]
    lines = [
        "Need-vs-service gap assessment for ZIP 78207 (rule-based, explainable):",
        f"- Need score: {gap['need_score']}",
        f"- Service score: {gap['service_score']}",
        f"- Gap score (need - service): {gap['gap_score']} => {gap['gap_level']}",
        "",
        "Need evidence:",
    ]
    for item in gap["need_evidence"][:3]:
        lines.append(f"- {item}")
    lines.append("Service evidence:")
    for item in gap["service_evidence"][:3]:
        lines.append(f"- {item}")
    lines.append("Interpretation: higher positive gap score means stronger unmet need signal.")
    text = _append_sources("\n".join(lines), sources_used)
    return text, None, zip_centroid_marker("78207", label="ZIP 78207 (SAAF)", color="#9370DB")


def _context_demographics_response() -> Tuple[str, None, pd.DataFrame]:
    context = get_context_metrics()
    if all(v is None for v in context.values()):
        return _strict_not_available_response("context demographics")

    sources_used = [SOURCE_NAMES["demographics"]]
    lines = ["ZIP 78207 context metrics (from `clean/master_dataset.csv`):"]
    if context["population"] is not None:
        lines.append(f"- Population: {int(context['population']):,}")
    if context["median_income"] is not None:
        lines.append(f"- Median household income: ${int(context['median_income']):,}")
    if context["poverty_rate"] is not None:
        lines.append(f"- Poverty rate: {float(context['poverty_rate']):.1f}%")
    if context["median_age"] is not None:
        lines.append(f"- Median age: {float(context['median_age']):.1f}")
    if context["uninsured_rate"] is not None:
        lines.append(f"- Uninsured rate: {float(context['uninsured_rate']):.1f}%")
    if context["hispanic_share"] is not None:
        lines.append(f"- Hispanic/Latino share: {100 * float(context['hispanic_share']):.1f}%")
    if context["persons_per_household"] is not None:
        lines.append(f"- Persons per household: {float(context['persons_per_household']):.2f}")
    lines.append("Ask a follow-up for deeper context on age/race/economic metrics.")
    text = _append_sources("\n".join(lines), sources_used)
    return text, None, zip_centroid_marker("78207", label="ZIP 78207 (SAAF)", color="#9370DB")


def try_handle_saaf_question(prompt: str) -> Optional[Tuple[str, None, pd.DataFrame]]:
    intent = detect_intent(prompt)
    if intent is None:
        return None

    if intent == "missing_sensitive_data":
        return _strict_not_available_response("ER/crisis/substance-use")
    if intent == "funding_intelligence":
        return _strict_not_available_response("funding/investment")
    if intent == "community_need":
        return _community_need_response()
    if intent == "community_conditions_311":
        return _community_conditions_311_response()
    if intent == "service_landscape":
        return _service_landscape_response()
    if intent == "need_service_gap":
        return _need_service_gap_response()
    if intent == "context_demographics":
        return _context_demographics_response()
    return None
