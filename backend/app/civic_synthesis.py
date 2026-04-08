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
import time as _time

try:
    from .civic_response_schema import CivicStructuredResponse, MapAction, fallback_structured_from_text
except ImportError:
    from civic_response_schema import CivicStructuredResponse, MapAction, fallback_structured_from_text

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
CIVIC_SYNTHESIS_MODEL = os.environ.get("CIVIC_SYNTHESIS_MODEL", GEMINI_MODEL)
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
- You must boldly and confidently form relationships and correlations between data points (e.g. connecting infrastructure to health metrics).
- DO NOT use phrases like "does not directly correlate" or "cannot establish a link". Instead, use terms like "correlates heavily" and "this is strongly linked to" based on best practices.
- When asked to predict future trends or where needs will increase, YOU MUST make an educated prediction based on current data/trends rather than refusing. However, you MUST include a clear disclaimer flag stating that this is a prediction and not always correct due to various factors.
- The user prioritizes precise numbers, clear data, and high readability/understandability.
- Utilize your built-in Google Search capabilities to cross-reference and incorporate real-world statistics into the synthesis when appropriate.
- "answer" should be helpful, clear, and data-forward (Markdown bullets allowed inside the string). It must be easy for non-technical users to understand.
- "reasoning_summary": 2–4 sentences on how the evidence supports the answer.
- "recommendations": concrete next steps a city analyst could take; use [] if none fit.
- "follow_up_question": one short question to deepen analysis, or "" if not appropriate.
- "confidence": "low" | "medium" | "high". Default to "high" when making correlations.
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


def _is_pothole_zip_ranking_evidence(text: str) -> bool:
    """True when deterministic handler returned grouped ZIP counts from potholes.parquet."""
    t = (text or "").lower()
    return "pothole-prone zip codes" in t and "local pothole dataset" in t


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

    # Do not let the narrative LLM replace solid local SQL/parquet answers with "insufficient data".
    if _is_pothole_zip_ranking_evidence(base):
        out = fallback_structured_from_text(base)
        out.limitations = []
        out.confidence = "high"
        out.reasoning_summary = "ZIP counts are taken directly from the local pothole dataset (aggregated by zipcode)."
        if metrics:
            out.metrics = dict(metrics)
        return out

    if not CIVIC_SYNTHESIS_ENABLED or not GEMINI_API_KEY:
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

    # Build Gemini API request
    gemini_url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
    # Merge system + user content (Gemini v1beta doesn't support a system role separately)
    combined_text = f"{SYSTEM_PROMPT}\n\n{user_block}"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": combined_text}],
            }
        ],
        "tools": [{"googleSearch": {}}],
        "generationConfig": {
            "temperature": 0.25,
            "maxOutputTokens": 2048,
        },
    }

    try:
        last_exc: Exception = RuntimeError("No attempts made")
        for attempt in range(3):  # up to 3 tries for transient 503s
            try:
                resp = requests.post(
                    gemini_url,
                    headers={"Content-Type": "application/json"},
                    json=payload,
                    timeout=60,
                )
                if resp.status_code == 503:
                    wait = 2 ** attempt  # 1s, 2s, 4s
                    print(f"[civic_synthesis] Gemini 503 (attempt {attempt+1}/3), retrying in {wait}s...")
                    _time.sleep(wait)
                    last_exc = requests.HTTPError(f"503 on attempt {attempt+1}", response=resp)
                    continue
                resp.raise_for_status()
                raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                parsed = _parse_json_loose(raw)
                if not parsed:
                    raise ValueError("No JSON in synthesis response")
                structured = _coerce_response(parsed)
                if metrics:
                    structured.metrics = dict(metrics)
                return structured
            except requests.HTTPError as e:
                r = getattr(e, "response", None)
                status = r.status_code if r is not None else "?"
                if status == 503:
                    wait = 2 ** attempt
                    print(f"[civic_synthesis] Gemini 503 (attempt {attempt+1}/3), retrying in {wait}s...")
                    _time.sleep(wait)
                    last_exc = e
                    continue
                # Non-503 HTTP error — log and fall through
                print(f"[civic_synthesis] Gemini HTTP {status} error: {e!r}")
                last_exc = e
                break
        # All retries exhausted or non-retryable error — silently fall back
        print(f"[civic_synthesis] Falling back to local text after errors: {last_exc!r}")
        out = fallback_structured_from_text(base)
        out.confidence = "medium"
        if metrics:
            out.metrics = dict(metrics)
        return out
    except requests.RequestException as e:
        print(f"[civic_synthesis] synthesis request failed: {e!r}")
        out = fallback_structured_from_text(base)
        if metrics:
            out.metrics = dict(metrics)
        return out
    except Exception as e:
        print(f"[civic_synthesis] synthesis failed: {e}")
        out = fallback_structured_from_text(base)
        if metrics:
            out.metrics = dict(metrics)
        return out
