from typing import Dict, List, Tuple

try:
    from saaf_data import (
        get_context_metrics,
        get_environmental_hazard_summary,
        get_mental_health_indicator_trend,
        get_service_landscape_summary,
        get_top_311_categories,
    )
except ModuleNotFoundError:
    from .saaf_data import (
        get_context_metrics,
        get_environmental_hazard_summary,
        get_mental_health_indicator_trend,
        get_service_landscape_summary,
        get_top_311_categories,
    )


def _score_need_signals() -> Tuple[float, List[str]]:
    score = 0.0
    evidence: List[str] = []

    context = get_context_metrics()
    if context.get("poverty_rate") is not None:
        poverty = float(context["poverty_rate"])
        if poverty >= 35:
            score += 2.0
            evidence.append(f"High poverty rate: {poverty:.1f}%")

    if context.get("uninsured_rate") is not None:
        uninsured = float(context["uninsured_rate"])
        if uninsured >= 20:
            score += 1.5
            evidence.append(f"High uninsured rate: {uninsured:.1f}%")

    mh = get_mental_health_indicator_trend()
    if mh:
        avg_mh = mh.get("average_percent", 0.0)
        if avg_mh >= 18:
            score += 1.5
            evidence.append(f"Mental health burden indicators average: {avg_mh:.1f}%")

    hazards = get_environmental_hazard_summary()
    env_count = hazards.get("mold_sanitation_pests", 0) + hazards.get("vector_hazards", 0)
    if env_count >= 20:
        score += 1.0
        evidence.append(f"Environmental/sanitation hazard complaints: {env_count}")

    return score, evidence


def _score_service_signals() -> Tuple[float, List[str]]:
    score = 0.0
    evidence: List[str] = []
    landscape = get_service_landscape_summary()
    top_311 = get_top_311_categories(limit=3)

    if landscape:
        if "Metro Health" in landscape:
            score += 1.5
            evidence.append(f"Metro Health service requests observed: {landscape['Metro Health']}")
        if "Human Services" in landscape:
            score += 1.0
            evidence.append(f"Human Services requests observed: {landscape['Human Services']}")
    if top_311:
        score += 0.5
        evidence.append("Multiple active service-request categories detected in 311 records.")

    return score, evidence


def get_gap_summary() -> Dict[str, object]:
    need_score, need_evidence = _score_need_signals()
    service_score, service_evidence = _score_service_signals()
    gap_score = round(need_score - service_score, 2)

    if gap_score >= 1.5:
        level = "high"
    elif gap_score >= 0.5:
        level = "moderate"
    else:
        level = "low_or_balanced"

    return {
        "need_score": round(need_score, 2),
        "service_score": round(service_score, 2),
        "gap_score": gap_score,
        "gap_level": level,
        "need_evidence": need_evidence,
        "service_evidence": service_evidence,
    }
