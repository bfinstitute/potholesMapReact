"""
LLM synthesis layer (Phase 1).

Deterministic pipeline produces `retrieved_context` (and later `metrics`); this module
asks the LLM to return *only* narrative structure as JSON — no new factual claims
beyond the provided evidence.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

import requests

try:
    from .civic_response_schema import CivicStructuredResponse, MapAction, fallback_structured_from_text
except ImportError:
    from civic_response_schema import CivicStructuredResponse, MapAction, fallback_structured_from_text

GROQ_API_URL = os.environ.get("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
CIVIC_SYNTHESIS_MODEL = os.environ.get("CIVIC_SYNTHESIS_MODEL", "llama-3.1-8b-instant")
# Set to 0/false to skip the second LLM call and wrap the handler text in the schema only.
CIVIC_SYNTHESIS_ENABLED = os.environ.get("CIVIC_SYNTHESIS_ENABLED", "1").strip().lower() not in (
    "0",
    "false",
    "no",
    "",
)


SYSTEM_PROMPT = """You are the narrative layer for a civic decision-support assistant (Buffi).
You MUST respond with a single JSON object only — no markdown fences, no commentary outside JSON.

Rules:
- Use ONLY the information in retrieved_context and metrics. Do not invent statistics, organizations, or funding amounts.
- If evidence is missing or insufficient, say so in "limitations" and lower "confidence".
- "answer" should be helpful and readable (Markdown bullets allowed inside the string).
- "reasoning_summary": 2–4 sentences on how the evidence supports the answer.
- "recommendations": concrete next steps a city analyst could take; use [] if none fit.
- "follow_up_question": one short question to deepen analysis, or "" if not appropriate.
- "confidence": "low" | "medium" | "high" based on evidence strength.
- "map_action": set show_map true only if geography is clear and a map would help; otherwise show_map false.

JSON keys (exact names):
answer (string), reasoning_summary (string), recommendations (array of strings),
follow_up_question (string), confidence (string), limitations (array of strings),
map_action (object with show_map boolean, layer string, geography string)
"""


def _parse_json_loose(text: str) -> Optional[dict]:
    text = (text or "").strip()
    if not text:
        return None
    try:
        if text.startswith("{"):
            return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            return None
    m2 = re.search(r"\{[\s\S]*\}", text)
    if m2:
        try:
            return json.loads(m2.group(0))
        except json.JSONDecodeError:
            return None
    return None


def _coerce_response(data: dict) -> CivicStructuredResponse:
    ma = data.get("map_action") or {}
    if not isinstance(ma, dict):
        ma = {}
    return CivicStructuredResponse(
        answer=str(data.get("answer", "") or ""),
        reasoning_summary=str(data.get("reasoning_summary", "") or ""),
        recommendations=list(data.get("recommendations") or []),
        follow_up_question=str(data.get("follow_up_question", "") or ""),
        confidence=data.get("confidence") if data.get("confidence") in ("low", "medium", "high") else "medium",
        limitations=list(data.get("limitations") or []),
        map_action=MapAction(
            show_map=bool(ma.get("show_map", False)),
            layer=str(ma.get("layer", "") or ""),
            geography=str(ma.get("geography", "") or ""),
        ),
        metrics=data.get("metrics") if isinstance(data.get("metrics"), dict) else None,
    )


def synthesize_civic_structured_response(
    user_query: str,
    retrieved_context: str,
    metrics: Optional[dict[str, Any]] = None,
    geography_hint: Optional[str] = None,
) -> CivicStructuredResponse:
    """
    Call the LLM to turn deterministic retrieval output into CivicStructuredResponse.

    - retrieved_context: text produced by RAG, SQL, handlers, etc. (facts live here).
    - metrics: optional small dict from backend math (Phase 1 may pass {} or row counts).
    """
    base = (retrieved_context or "").strip()
    if not CIVIC_SYNTHESIS_ENABLED or not GROQ_API_KEY:
        out = fallback_structured_from_text(base)
        if metrics:
            out.metrics = dict(metrics)
        return out

    metrics = metrics or {}
    geo_line = f"\nGeography hint (if any): {geography_hint}" if geography_hint else ""
    metrics_line = f"\nComputed metrics (trusted; do not contradict): {json.dumps(metrics, default=str)}"

    user_block = f"""User question:
{user_query.strip()}

Retrieved evidence (only source of facts):
{base}
{metrics_line}
{geo_line}
"""

    payload = {
        "model": CIVIC_SYNTHESIS_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_block},
        ],
        "temperature": 0.25,
        "max_tokens": 2048,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]
        parsed = _parse_json_loose(raw)
        if not parsed:
            raise ValueError("No JSON in synthesis response")
        structured = _coerce_response(parsed)
        if metrics:
            structured.metrics = dict(metrics)
        return structured
    except Exception as e:
        print(f"[civic_synthesis] synthesis failed: {e}")
        out = fallback_structured_from_text(base)
        out.limitations = (out.limitations or []) + [f"Synthesis error: {e!s}"]
        out.confidence = "low"
        if metrics:
            out.metrics = dict(metrics)
        return out
