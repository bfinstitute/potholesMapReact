"""
Structured chat response schema for the civic decision-support assistant.

Phase 1: used as the contract between backend synthesis and the frontend.
Phase 2+: metrics (need_score, gap_score, etc.) will be added alongside deterministic compute.
"""

from __future__ import annotations

from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field


class MapAction(BaseModel):
    """Optional map UI hint; deterministic geography logic can populate this in Phase 2."""

    show_map: bool = False
    layer: str = ""
    geography: str = ""


class CivicStructuredResponse(BaseModel):
    """
    JSON shape returned to the client. Facts and numbers should originate from
    retrieved_context / metrics in synthesis; the LLM fills narrative fields only.
    """

    answer: str = Field(..., description="Primary user-facing answer (Markdown allowed).")
    reasoning_summary: str = Field(
        default="",
        description="Short explanation of how the answer relates to the evidence.",
    )
    recommendations: List[str] = Field(default_factory=list)
    follow_up_question: str = Field(default="")
    confidence: Literal["low", "medium", "high"] = "medium"
    limitations: List[str] = Field(
        default_factory=list,
        description="Data gaps, uncertainty, or caveats.",
    )
    map_action: MapAction = Field(default_factory=MapAction)

    # Extension hook for Phase 2 (deterministic scores passed through to UI)
    metrics: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional structured metrics from backend (filled in Phase 2).",
    )


def fallback_structured_from_text(answer_text: str) -> CivicStructuredResponse:
    """When synthesis is disabled or the LLM fails, still return a valid schema."""
    return CivicStructuredResponse(
        answer=answer_text or "",
        reasoning_summary="",
        recommendations=[],
        follow_up_question="",
        confidence="medium",
        limitations=["Automated narrative synthesis was skipped or unavailable."],
        map_action=MapAction(),
        metrics=None,
    )
