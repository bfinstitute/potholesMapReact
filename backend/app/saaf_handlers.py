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
        get_citations_mapping,
        get_funding_summary_and_map_data,
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
        get_citations_mapping,
        get_funding_summary_and_map_data,
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

def _get_source(key: str) -> str:
    mapping = get_citations_mapping()
    # Map old hardcoded keys to new dynamic names as fallback bridging
    if key == "demographics":
        return mapping.get("Census Demographics", mapping.get("78207_Master_Dataset_Percentage", SOURCE_NAMES.get(key, key)))
    if key == "health":
        return mapping.get("Health Places", mapping.get("Health_Places", SOURCE_NAMES.get(key, key)))
    if key == "311":
        return mapping.get("311 Service Request", SOURCE_NAMES.get(key, key))
    if key == "unemployment":
        return mapping.get("Unemployment Rate", mapping.get("Unemployment_Rate", SOURCE_NAMES.get(key, key)))
    if key == "funding":
        return mapping.get("San Antonio 78207", "[City of San Antonio Bond Projects](https://data.sanantonio.gov/)")
    
    return mapping.get(key, key)


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


def _community_need_response() -> Tuple[str, Optional[dict], pd.DataFrame]:
    top_health = get_top_health_issues(limit=5)
    mh = get_mental_health_indicator_trend()
    unemployment = get_unemployment_summary()
    context = get_context_metrics()
    domain_signals = get_need_signals_by_domain()

    if not top_health:
        return _strict_not_available_response("community need")

    sources_used = []
    lines = ["ZIP 78207 community need signals (data-backed):"]
    lines.append("Top public health burdens from `clean/health_places.csv`:")
    for name, val in top_health[:3]:
        lines.append(f"- {name}: {val:.1f}%")
    sources_used.append(_get_source("health"))

    if mh:
        lines.append(
            f"- Mental health burden proxy (Depression + Frequent Mental Distress): average {mh['average_percent']:.1f}%"
        )
    if unemployment:
        lines.append(f"- Unemployment (latest): {unemployment['latest_rate']:.2f}%")
        sources_used.append(_get_source("unemployment"))
    if context.get("poverty_rate") is not None:
        lines.append(f"- Poverty rate from `clean/master_dataset.csv`: {float(context['poverty_rate']):.1f}%")
        sources_used.append(_get_source("demographics"))
    if context.get("uninsured_rate") is not None:
        lines.append(f"- Uninsured rate proxy from `clean/master_dataset.csv`: {float(context['uninsured_rate']):.1f}%")
        if _get_source("demographics") not in sources_used:
            sources_used.append(_get_source("demographics"))
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

    chart_data = {
        "type": "bar",
        "title": "Top Health Burdens in ZIP 78207 (%)",
        "xKey": "value",
        "yKey": "name",
        "xLabel": "Prevalence (%)",
        "data": [{"name": name, "value": round(val, 1)} for name, val in top_health],
    }

    text = _append_sources("\n".join(lines), sources_used)
    return text, chart_data, zip_centroid_marker("78207", label="ZIP 78207 (SAAF)", color="#9370DB")


def _community_conditions_311_response() -> Tuple[str, Optional[dict], pd.DataFrame]:
    top_types = get_top_311_categories(limit=6)
    hazard = get_environmental_hazard_summary()
    if not top_types:
        return _strict_not_available_response("311 conditions")

    sources_used = [_get_source("311")]
    lines = ["ZIP 78207 community conditions (311 health-related signals):"]
    lines.append("Most common request types from `clean/service_requests_78207.csv`:")
    for name, count in top_types[:4]:
        lines.append(f"- {name}: {count} cases")

    if hazard:
        lines.append("Hazard signal counts (keyword grouped):")
        lines.append(f"- Mold/sanitation/pests: {hazard.get('mold_sanitation_pests', 0)}")
        lines.append(f"- Vector hazards: {hazard.get('vector_hazards', 0)}")
        lines.append(f"- Homeless encampment/outreach: {hazard.get('homeless_encampment', 0)}")

    lines.append("Ask a follow-up for month-wise or neighborhood-level summary.")

    chart_data = {
        "type": "bar",
        "title": "Top 311 Service Request Categories in ZIP 78207",
        "xKey": "count",
        "yKey": "category",
        "xLabel": "Number of Requests",
        "data": [{"category": name, "count": int(count)} for name, count in top_types],
    }

    text = _append_sources("\n".join(lines), sources_used)
    return text, chart_data, zip_centroid_marker("78207", label="ZIP 78207 (SAAF)", color="#9370DB")


def _service_landscape_response() -> Tuple[str, Optional[dict], pd.DataFrame]:
    service_summary = get_service_landscape_summary()
    if not service_summary:
        return _strict_not_available_response("service landscape")

    sources_used = [_get_source("311")]
    top_items = list(service_summary.items())[:6]
    lines = [
        "Service landscape proxy for ZIP 78207 (from 311 departmental activity in `clean/service_requests_78207.csv`):"
    ]
    for dept, count in top_items[:5]:
        lines.append(f"- {dept}: {count} service requests")
    lines.append(
        "Note: this is operational service-request activity, not a complete provider capacity inventory."
    )

    chart_data = {
        "type": "bar",
        "title": "Service Activity by Department in ZIP 78207",
        "xKey": "requests",
        "yKey": "department",
        "xLabel": "Service Requests",
        "data": [{"department": dept, "requests": int(count)} for dept, count in top_items],
    }

    text = _append_sources("\n".join(lines), sources_used)
    return text, chart_data, zip_centroid_marker("78207", label="ZIP 78207 (SAAF)", color="#9370DB")


def _need_service_gap_response() -> Tuple[str, Optional[dict], pd.DataFrame]:
    gap = get_gap_summary()
    # Gap analysis uses health, 311, and demographics data
    sources_used = [_get_source("health"), _get_source("311"), _get_source("demographics")]
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

    chart_data = {
        "type": "bar",
        "title": "Need vs. Service Gap Analysis — ZIP 78207",
        "xKey": "score",
        "yKey": "metric",
        "xLabel": "Score",
        "data": [
            {"metric": "Need Score", "score": float(gap["need_score"])},
            {"metric": "Service Score", "score": float(gap["service_score"])},
            {"metric": "Gap Score", "score": float(gap["gap_score"])},
        ],
    }

    text = _append_sources("\n".join(lines), sources_used)
    return text, chart_data, zip_centroid_marker("78207", label="ZIP 78207 (SAAF)", color="#9370DB")


def _context_demographics_response() -> Tuple[str, Optional[dict], pd.DataFrame]:
    context = get_context_metrics()
    if all(v is None for v in context.values()):
        return _strict_not_available_response("context demographics")

    sources_used = [_get_source("demographics")]
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

    chart_rows = []
    if context["poverty_rate"] is not None:
        chart_rows.append({"indicator": "Poverty Rate (%)", "value": round(float(context["poverty_rate"]), 1)})
    if context["uninsured_rate"] is not None:
        chart_rows.append({"indicator": "Uninsured Rate (%)", "value": round(float(context["uninsured_rate"]), 1)})
    if context["hispanic_share"] is not None:
        chart_rows.append({"indicator": "Hispanic/Latino Share (%)", "value": round(100 * float(context["hispanic_share"]), 1)})
    if context["median_age"] is not None:
        chart_rows.append({"indicator": "Median Age", "value": round(float(context["median_age"]), 1)})
    if context["persons_per_household"] is not None:
        chart_rows.append({"indicator": "Persons per Household", "value": round(float(context["persons_per_household"]), 2)})

    chart_data = {
        "type": "bar",
        "title": "Demographic Context — ZIP 78207",
        "xKey": "value",
        "yKey": "indicator",
        "xLabel": "Value",
        "data": chart_rows,
    } if chart_rows else None

    text = _append_sources("\n".join(lines), sources_used)
    return text, chart_data, zip_centroid_marker("78207", label="ZIP 78207 (SAAF)", color="#9370DB")


def _funding_intelligence_response() -> Tuple[str, Optional[dict], pd.DataFrame]:
    summary, map_df = get_funding_summary_and_map_data()
    if not summary:
        return _strict_not_available_response("funding/investment")

    sources = [_get_source("funding")]
    lines = ["ZIP 78207 funding and intervention intelligence (data-backed):"]
    lines.append(f"Total Bond Budget Investment: ${summary['total_budget']:,.2f}")
    lines.append(f"Number of Active Projects: {summary['project_count']}")

    lines.append("\nInvestment by Category (Bond Propositions):")
    for cat, amount in summary["by_category"].items():
        if amount > 0:
            lines.append(f"- {cat}: ${amount:,.2f}")

    lines.append("\nThe attached map layer highlights precise geographical points for these funded interventions.")

    output_df = map_df if map_df is not None else zip_centroid_marker("78207", label="ZIP 78207 (SAAF)", color="#9370DB")

    chart_rows = [
        {"category": cat, "amount": round(float(amt), 0)}
        for cat, amt in summary["by_category"].items()
        if amt > 0
    ]
    chart_data = {
        "type": "bar",
        "title": "Bond Investment by Category — ZIP 78207",
        "xKey": "amount",
        "yKey": "category",
        "xLabel": "Investment ($)",
        "data": chart_rows,
    } if chart_rows else None

    text = _append_sources("\n".join(lines), sources)
    return text, chart_data, output_df

def _mental_health_needs_response() -> Tuple[str, Optional[dict], pd.DataFrame]:
    """Detailed breakdown of mental health indicators for ZIP 78207."""
    top_health = get_top_health_issues(limit=10)
    mh = get_mental_health_indicator_trend()
    context = get_context_metrics()

    sources_used = [_get_source("health"), _get_source("demographics")]
    lines = ["Mental health need signals in ZIP 78207 (data-backed):"]

    # Filter for mental-health-related indicators from health_places
    mh_indicators = [
        (name, val) for name, val in top_health
        if any(kw in name.lower() for kw in ["mental", "depression", "distress", "sleep", "anxiety", "cognit"])
    ]
    if not mh_indicators:
        mh_indicators = top_health[:5]

    lines.append("Key mental and behavioral health indicators:")
    for name, val in mh_indicators:
        lines.append(f"- {name}: {val:.1f}%")

    if mh:
        lines.append(f"\nAggregate mental health burden (Depression + Frequent Mental Distress): avg {mh['average_percent']:.1f}%")

    if context.get("poverty_rate") is not None:
        lines.append(f"\nContext: Poverty rate {float(context['poverty_rate']):.1f}% — poverty is a strong driver of mental health need.")
    if context.get("uninsured_rate") is not None:
        lines.append(f"Context: Uninsured rate {float(context['uninsured_rate']):.1f}% — limits access to mental health services.")

    lines.append("\nRecommendation: Prioritize ZIP 78207 for expanded mental health service access given compounding risk factors.")

    chart_data = {
        "type": "bar",
        "title": "Mental Health & Behavioral Health Indicators — ZIP 78207 (%)",
        "xKey": "value",
        "yKey": "indicator",
        "xLabel": "Prevalence (%)",
        "data": [{"indicator": name, "value": round(val, 1)} for name, val in mh_indicators],
    }

    text = _append_sources("\n".join(lines), sources_used)
    return text, chart_data, zip_centroid_marker("78207", label="ZIP 78207 — Mental Health", color="#8B3FC8")


def _housing_concentration_response() -> Tuple[str, Optional[dict], pd.DataFrame]:
    """Housing issues in ZIP 78207 via 311 complaint categories."""
    top_types = get_top_311_categories(limit=10)
    hazard = get_environmental_hazard_summary()

    if not top_types:
        return _strict_not_available_response("311 housing conditions")

    housing_types = [
        (name, count) for name, count in top_types
        if any(kw in name.lower() for kw in ["housing", "animal", "code", "mold", "sanit", "unsafe", "blight", "vacant", "pest"])
    ]
    if not housing_types:
        housing_types = top_types[:5]

    sources_used = [_get_source("311")]
    lines = [
        "Housing-related community conditions in ZIP 78207 (via 311 service requests):",
        "These signals indicate where housing issues are concentrated:",
    ]
    for name, count in housing_types:
        lines.append(f"- {name}: {count} cases")

    if hazard:
        env_total = hazard.get("mold_sanitation_pests", 0) + hazard.get("vector_hazards", 0)
        lines.append(f"\nEnvironmental hazard complaints (mold/sanitation/pests + vector): {env_total} total")

    lines.append("\nNote: For neighborhood-level breakdown, a geographic join on complaint addresses is needed.")

    chart_data = {
        "type": "bar",
        "title": "Housing-Related 311 Complaints — ZIP 78207",
        "xKey": "count",
        "yKey": "category",
        "xLabel": "Number of Cases",
        "data": [{"category": name, "count": int(count)} for name, count in housing_types],
    }

    text = _append_sources("\n".join(lines), sources_used)
    return text, chart_data, zip_centroid_marker("78207", label="ZIP 78207 — Housing", color="#E05A2B")


def _sdh_comprehensive_response() -> Tuple[str, Optional[dict], pd.DataFrame]:
    """All Social Determinants of Health domain signals for ZIP 78207."""
    domain_signals = get_need_signals_by_domain()
    context = get_context_metrics()
    mh = get_mental_health_indicator_trend()
    unemployment = get_unemployment_summary()

    sources_used = [_get_source("health"), _get_source("demographics"), _get_source("311"), _get_source("unemployment")]
    lines = [
        "Social Determinants of Health (SDH) overview for ZIP 78207:",
        "All available domain signals across the five SDH pillars:",
    ]

    chart_rows = []

    mh_signal = domain_signals.get("mental_health", {}).get("signal")
    if mh_signal is not None:
        lines.append(f"\nMental Health: avg burden {mh_signal:.1f}%")
        chart_rows.append({"domain": "Mental Health", "signal": round(float(mh_signal), 1)})

    ph_signal = domain_signals.get("public_health", {}).get("signal")
    if ph_signal is not None:
        lines.append(f"Public Health: avg indicator {ph_signal:.1f}%")
        chart_rows.append({"domain": "Public Health", "signal": round(float(ph_signal), 1)})

    housing_signal = domain_signals.get("housing_environment", {}).get("signal")
    if housing_signal is not None:
        lines.append(f"Housing & Environment: {int(housing_signal)} hazard-related complaints (311 data)")
        # Excluded from chart — raw complaint count is not comparable to % signals

    eco_signal = domain_signals.get("economic_mobility", {}).get("signal")
    if eco_signal is not None:
        lines.append(f"Economic Mobility: composite score {eco_signal:.1f}%")
        chart_rows.append({"domain": "Economic Mobility", "signal": round(float(eco_signal), 1)})

    if unemployment:
        lines.append(f"Employment: unemployment rate {unemployment['latest_rate']:.2f}%")
        chart_rows.append({"domain": "Employment", "signal": round(float(unemployment["latest_rate"]), 2)})

    if context.get("uninsured_rate") is not None:
        lines.append(f"Healthcare Access: uninsured rate {float(context['uninsured_rate']):.1f}%")
        chart_rows.append({"domain": "Healthcare Access", "signal": round(float(context["uninsured_rate"]), 1)})

    lines.append("\nHigher signals indicate greater unmet need in that domain.")
    lines.append("Recommendation: Use this multi-domain view to allocate funding across all SDH pillars, not just one.")

    chart_data = {
        "type": "bar",
        "title": "Social Determinants of Health — ZIP 78207 Domain Signals",
        "xKey": "signal",
        "yKey": "domain",
        "xLabel": "Signal Strength",
        "data": chart_rows,
    } if chart_rows else None

    text = _append_sources("\n".join(lines), sources_used)
    return text, chart_data, zip_centroid_marker("78207", label="ZIP 78207 — SDH", color="#2D7FC1")


def _funding_decision_response() -> Tuple[str, Optional[dict], pd.DataFrame]:
    """Decision-making framework focused on mental health: connect needs data to funding priorities."""
    gap = get_gap_summary()
    domain_signals = get_need_signals_by_domain()
    mh = get_mental_health_indicator_trend()
    top_health = get_top_health_issues(limit=10)
    summary, map_df = get_funding_summary_and_map_data()

    sources_used = [_get_source("health"), _get_source("311"), _get_source("demographics"), _get_source("funding")]

    # Filter mental health specific indicators for % chart (same unit)
    mh_indicators = [
        (name, val) for name, val in top_health
        if any(kw in name.lower() for kw in ["mental", "depression", "distress", "sleep", "anxiety", "cognit"])
    ]
    if not mh_indicators:
        mh_indicators = top_health[:3]

    mh_signal = domain_signals.get("mental_health", {}).get("signal")
    eco_signal = domain_signals.get("economic_mobility", {}).get("signal")

    lines = [
        "Data-driven mental health funding decision framework for ZIP 78207:",
        "",
        "Step 1 — Quantify the mental health need:",
    ]
    for name, val in mh_indicators:
        lines.append(f"  • {name}: {val:.1f}%")
    if mh:
        lines.append(f"  • Aggregate mental health burden (Depression + Distress): avg {mh['average_percent']:.1f}%")

    lines += [
        "",
        "Step 2 — Assess the service gap:",
        f"  • Overall need score: {gap['need_score']} | Service score: {gap['service_score']} | Gap: {gap['gap_score']} ({gap['gap_level']})",
        "  • High gap score signals that mental health service supply is not meeting documented need.",
        "",
        "Step 3 — Review existing investment:",
    ]
    if summary:
        lines.append(f"  • Current total bond investment: ${summary['total_budget']:,.2f} across {summary['project_count']} projects")
        lines.append("  • Assess whether these projects fund behavioral health services specifically.")
    else:
        lines.append("  • No bond project data ingested yet — manual review of current mental health funding required.")

    lines += [
        "",
        "Recommendation: Prioritize funding for depression/mental distress intervention programs and behavioral health access in ZIP 78207, targeting the highest-prevalence indicators above.",
    ]

    # Chart uses only %-based indicators so units are comparable
    chart_rows = [{"indicator": name, "value": round(val, 1)} for name, val in mh_indicators]
    if eco_signal is not None:
        chart_rows.append({"indicator": "Economic Mobility Need (%)", "value": round(float(eco_signal), 1)})

    chart_data = {
        "type": "bar",
        "title": "Mental Health Funding Priorities — ZIP 78207 Need Signals (%)",
        "xKey": "value",
        "yKey": "indicator",
        "xLabel": "Prevalence / Signal (%)",
        "data": chart_rows,
    } if chart_rows else None

    output_df = map_df if map_df is not None else zip_centroid_marker("78207", label="ZIP 78207 — Funding", color="#2D7FC1")
    text = _append_sources("\n".join(lines), sources_used)
    return text, chart_data, output_df


def _critical_issues_response() -> Tuple[str, Optional[dict], pd.DataFrame]:
    """Most critical issues affecting residents in ZIP 78207 across all domains."""
    top_health = get_top_health_issues(limit=5)
    top_311 = get_top_311_categories(limit=4)
    context = get_context_metrics()
    gap = get_gap_summary()

    sources_used = [_get_source("health"), _get_source("311"), _get_source("demographics")]
    lines = [
        "Most critical issues affecting residents of ZIP 78207 (multi-domain analysis):",
        "",
        "Health Burdens (CDC PLACES — prevalence %):",
    ]
    for name, val in top_health:
        lines.append(f"  • {name}: {val:.1f}%")

    lines.append("\nCommunity Conditions (311 service requests — case counts):")
    for name, count in top_311:
        lines.append(f"  • {name}: {count} cases")

    if context.get("poverty_rate") is not None:
        lines.append(f"\nEconomic Stress: Poverty rate {float(context['poverty_rate']):.1f}%")
    if context.get("uninsured_rate") is not None:
        lines.append(f"Healthcare Access Gap: Uninsured rate {float(context['uninsured_rate']):.1f}%")

    lines.append(f"\nOverall need-service gap: {gap['gap_level']} (score: {gap['gap_score']})")

    # Derive top issue from data rather than hardcoding
    top_issue_name = top_health[0][0] if top_health else "health burdens"
    lines.append(f"\nConclusion: {top_issue_name}, poverty ({float(context['poverty_rate']):.0f}% rate), and a {gap['gap_level']} service gap are the most critical compounding issues in ZIP 78207.")

    # Chart shows health indicators (%) + key economic indicators on same % scale
    chart_rows = [{"issue": name, "value": round(val, 1)} for name, val in top_health]
    if context.get("poverty_rate") is not None:
        chart_rows.append({"issue": "Poverty Rate", "value": round(float(context["poverty_rate"]), 1)})
    if context.get("uninsured_rate") is not None:
        chart_rows.append({"issue": "Uninsured Rate", "value": round(float(context["uninsured_rate"]), 1)})

    chart_data = {
        "type": "bar",
        "title": "Critical Issues — ZIP 78207 (Health & Economic Indicators, %)",
        "xKey": "value",
        "yKey": "issue",
        "xLabel": "Prevalence (%)",
        "data": chart_rows,
    }

    text = _append_sources("\n".join(lines), sources_used)
    return text, chart_data, zip_centroid_marker("78207", label="ZIP 78207 — Critical Issues", color="#C72B2B")


def _underserved_response() -> Tuple[str, Optional[dict], pd.DataFrame]:
    """Which communities in ZIP 78207 are underserved based on available data."""
    gap = get_gap_summary()
    domain_signals = get_need_signals_by_domain()
    context = get_context_metrics()

    sources_used = [_get_source("health"), _get_source("311"), _get_source("demographics")]
    lines = [
        "Underserved community assessment for ZIP 78207 (data-driven):",
        "",
        f"Overall service gap level: {gap['gap_level']} (gap score: {gap['gap_score']})",
        "",
        "Evidence of underservice:",
    ]
    for item in gap["need_evidence"]:
        lines.append(f"  • {item}")

    chart_rows = []
    mh = domain_signals.get("mental_health", {}).get("signal")
    if mh is not None:
        lines.append(f"\nMental health need ({mh:.1f}%) vs. limited specialty behavioral health providers → underserved")
        chart_rows.append({"dimension": "Mental Health Need", "score": round(float(mh), 1)})

    eco = domain_signals.get("economic_mobility", {}).get("signal")
    if eco is not None:
        chart_rows.append({"dimension": "Economic Mobility Need", "score": round(float(eco), 1)})

    chart_rows.append({"dimension": "Service Coverage", "score": float(gap["service_score"])})

    if context.get("uninsured_rate") is not None:
        lines.append(f"Healthcare access: {float(context['uninsured_rate']):.1f}% uninsured → significant underservice in primary care")
        chart_rows.append({"dimension": "Uninsured Rate (%)", "score": round(float(context["uninsured_rate"]), 1)})

    lines.append("\nConclusion: ZIP 78207 residents are underserved, particularly in mental health, economic support, and primary healthcare access.")

    chart_data = {
        "type": "bar",
        "title": "Underserved Dimensions — ZIP 78207",
        "xKey": "score",
        "yKey": "dimension",
        "xLabel": "Need Score / Rate",
        "data": chart_rows,
    }

    text = _append_sources("\n".join(lines), sources_used)
    return text, chart_data, zip_centroid_marker("78207", label="ZIP 78207 — Underserved", color="#C72B2B")


def _hyperlocal_assessment_response() -> Tuple[str, Optional[dict], pd.DataFrame]:
    """Explain how to build a hyperlocal community needs assessment for ZIP 78207 replicable citywide."""
    domain_signals = get_need_signals_by_domain()
    context = get_context_metrics()
    mh = get_mental_health_indicator_trend()
    unemployment = get_unemployment_summary()

    sources_used = [_get_source("health"), _get_source("311"), _get_source("demographics")]
    lines = [
        "Hyperlocal Community Needs Assessment — ZIP 78207 Framework",
        "",
        "Yes — this can be built and replicated citywide. Here is the methodology:",
        "",
        "**Layer 1 — Demographic baseline** (currently available for 78207):",
    ]
    if context.get("population") is not None:
        lines.append(f"  • Population: {int(context['population']):,}")
    if context.get("poverty_rate") is not None:
        lines.append(f"  • Poverty rate: {float(context['poverty_rate']):.1f}%")
    if context.get("uninsured_rate") is not None:
        lines.append(f"  • Uninsured rate: {float(context['uninsured_rate']):.1f}%")

    lines.append("\n**Layer 2 — Health indicator signals** (currently available):")
    mh_signal = domain_signals.get("mental_health", {}).get("signal")
    ph_signal = domain_signals.get("public_health", {}).get("signal")
    if mh_signal is not None:
        lines.append(f"  • Mental health burden: {mh_signal:.1f}%")
    if ph_signal is not None:
        lines.append(f"  • Public health avg indicator: {ph_signal:.1f}%")
    if mh:
        lines.append(f"  • Depression + Distress avg: {mh['average_percent']:.1f}%")

    lines.append("\n**Layer 3 — Service request activity** (currently available via 311):")
    eco_signal = domain_signals.get("economic_mobility", {}).get("signal")
    if eco_signal is not None:
        lines.append(f"  • Economic mobility signal: {eco_signal:.1f}%")
    if unemployment:
        lines.append(f"  • Unemployment rate: {unemployment['latest_rate']:.2f}%")

    lines += [
        "",
        "**To replicate citywide, each ZIP would need:**",
        "  1. Census tract–level demographic data (ACS 5-year estimates)",
        "  2. CDC PLACES health indicators aggregated to that ZIP",
        "  3. 311 service requests filtered by ZIP",
        "  4. A consistent scoring formula (e.g., composite need index) applied uniformly",
        "",
        "**Current 78207 composite signal (available now):**",
    ]

    chart_rows = []
    if mh_signal is not None:
        chart_rows.append({"layer": "Mental Health Need (%)", "value": round(float(mh_signal), 1)})
    if ph_signal is not None:
        chart_rows.append({"layer": "Public Health Avg (%)", "value": round(float(ph_signal), 1)})
    if eco_signal is not None:
        chart_rows.append({"layer": "Economic Mobility (%)", "value": round(float(eco_signal), 1)})
    if context.get("poverty_rate") is not None:
        chart_rows.append({"layer": "Poverty Rate (%)", "value": round(float(context["poverty_rate"]), 1)})
    if context.get("uninsured_rate") is not None:
        chart_rows.append({"layer": "Uninsured Rate (%)", "value": round(float(context["uninsured_rate"]), 1)})

    for row in chart_rows:
        lines.append(f"  • {row['layer']}: {row['value']}")

    lines.append("\nThis ZIP 78207 profile is the template. Ingest the same datasets for other ZIPs to replicate the assessment citywide.")

    chart_data = {
        "type": "bar",
        "title": "Hyperlocal Assessment Template — ZIP 78207 Need Signals (%)",
        "xKey": "value",
        "yKey": "layer",
        "xLabel": "Signal Strength (%)",
        "data": chart_rows,
    } if chart_rows else None

    text = _append_sources("\n".join(lines), sources_used)
    return text, chart_data, zip_centroid_marker("78207", label="ZIP 78207 — Needs Assessment", color="#2D7FC1")


def try_handle_saaf_question(prompt: str) -> Optional[Tuple[str, Optional[dict], pd.DataFrame]]:
    intent = detect_intent(prompt)
    if intent is None:
        return None

    if intent == "missing_sensitive_data":
        return _strict_not_available_response("ER/crisis/substance-use")
    if intent == "housing_concentration":
        return _housing_concentration_response()
    if intent == "mental_health_needs":
        return _mental_health_needs_response()
    if intent == "funding_decision":
        return _funding_decision_response()
    if intent == "sdh_comprehensive":
        return _sdh_comprehensive_response()
    if intent == "connect_needs_services":
        return _need_service_gap_response()
    if intent == "critical_issues":
        return _critical_issues_response()
    if intent == "hyperlocal_assessment":
        return _hyperlocal_assessment_response()
    if intent == "underserved":
        return _underserved_response()
    if intent == "funding_intelligence":
        return _funding_intelligence_response()
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
