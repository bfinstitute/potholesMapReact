"""Compact response formatting and guardrails for the chat API."""
from __future__ import annotations

import re
from typing import List, Optional


def _clean_text(text: Optional[str]) -> str:
    t = (text or "").strip()
    if not t:
        return ""
    replacements = (
        ("\U0001f6a7", ""),
        ("\U0001f4c5", ""),
        ("\U0001f4cd", ""),
        ("\U0001f5d3", ""),
        ("\u2705", ""),
        ("\u26a0\ufe0f", ""),
        ("\u26a0", ""),
        ("\U0001f50d", ""),
        ("\u2022", ""),
        ("Ã¢â‚¬Â¢", ""),
        ("Ã°Å¸â€”â€œÃ¯Â¸Â", ""),
        ("Ã°Å¸â€œÂ", ""),
        ("Ã°Å¸Å¡Â§", ""),
    )
    for old, new in replacements:
        t = t.replace(old, new)
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"(?m)^#+\s*", "", t)
    return t.strip()


def _normalize_items(items: Optional[List[str]]) -> List[str]:
    out: List[str] = []
    for item in items or []:
        s = _clean_text(item)
        s = re.sub(r"^[-*]\s*", "", s)
        if s:
            out.append(s)
    return out


def format_compact_response(
    lead: str,
    breakdown: Optional[List[str]] = None,
    notes: Optional[List[str]] = None,
) -> str:
    lead = _clean_text(lead) or "No response."
    breakdown_items = _normalize_items(breakdown)
    note_items = _normalize_items(notes)

    lines: List[str] = [lead]
    if breakdown_items:
        lines.extend(["", "Breakdown:"])
        lines.extend(breakdown_items)
    if note_items:
        lines.extend(["", "Notes:"])
        lines.extend(note_items)
    return "\n".join(lines).strip()


def format_buffi_response(lead: str, bullets: Optional[List[str]] = None) -> str:
    """Backward-compatible alias used by older backend code."""
    return format_compact_response(lead, breakdown=bullets)


def _parse_sectioned_text(text: str) -> str:
    lines = text.splitlines()
    summary_lines: List[str] = []
    findings: List[str] = []
    notes: List[str] = []
    section = "lead"

    for raw_line in lines:
        s = _clean_text(raw_line)
        if not s:
            continue
        lowered = s.lower()
        if lowered == "summary":
            section = "summary"
            continue
        if lowered in ("findings", "breakdown"):
            section = "findings"
            continue
        if lowered in (
            "data basis",
            "limitations",
            "supporting source",
            "supporting sources",
            "limitation",
            "source",
            "sources",
            "notes",
        ):
            section = "notes"
            continue

        s = re.sub(r"^[-*]\s*", "", s)
        if section == "summary":
            summary_lines.append(s)
        elif section == "findings":
            findings.append(s)
        elif section == "notes":
            notes.append(s)
        else:
            if not summary_lines:
                summary_lines.append(s)
            else:
                findings.append(s)

    lead = " ".join(summary_lines).strip() if summary_lines else _clean_text(text)
    return format_compact_response(lead, findings or None, notes or None)


def finalize_chat_response_text(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    if not isinstance(text, str):
        return text

    t = text.strip()
    if not t:
        return t

    if re.search(r"(?im)^summary\s*$", t):
        return _parse_sectioned_text(t)

    if re.search(r"(?im)^(breakdown|notes):\s*$", t):
        return _parse_sectioned_text(t)

    lines = [line.rstrip() for line in t.splitlines()]
    non_empty = [line for line in lines if line.strip()]
    bullet_pattern = r"^\s*(?:\u2022|Ã¢â‚¬Â¢|-|\*)\s+"
    bullet_lines = [line for line in non_empty[1:] if re.match(bullet_pattern, line)]
    if len(non_empty) >= 2 and bullet_lines:
        lead = _clean_text(non_empty[0])
        breakdown = [_clean_text(re.sub(bullet_pattern, "", line)) for line in bullet_lines]
        trailing = [
            _clean_text(line) for line in non_empty[1 + len(bullet_lines):] if _clean_text(line)
        ]
        return format_compact_response(lead, breakdown or None, trailing or None)

    return _clean_text(t)


def buffi_guardrail_reply(prompt: str) -> Optional[str]:
    p = (prompt or "").lower()

    if re.search(r"diagnos\w*\s+(?:my\s+)?(?:illness|condition|disease)", p) or "diagnose my" in p:
        return format_compact_response(
            "Medical diagnosis is not available in this assistant.",
            notes=[
                "Clinical diagnosis requires a licensed health care professional.",
                "Open data and facility lists here cannot evaluate individual health conditions.",
            ],
        )

    if (
        "specific individuals" in p
        or "specific families" in p
        or "specific households" in p
    ) and (
        "struggling" in p
        or "where do they live" in p
        or re.search(r"\bidentify\b.*\b(individuals|families|households)\b", p)
    ):
        return format_compact_response(
            "This request cannot be answered.",
            notes=[
                "Datasets used are aggregated or de-identified.",
                "Naming or locating individuals or families is declined for privacy and ethics reasons.",
            ],
        )

    if "can you identify specific individuals" in p or "identify specific individuals" in p:
        return format_compact_response(
            "Identification of specific individuals is not supported.",
            notes=["No consent-based identity linkage is exposed through this tool."],
        )

    if "who made each" in p and "service request" in p:
        return format_compact_response(
            "Requester identity for individual service requests is not provided here.",
            notes=["Data emphasize categories, geography, and volume rather than named residents behind tickets."],
        )

    if ("predict who" in p or "who might lose" in p) and "job" in p:
        return format_compact_response(
            "Individual job-loss prediction is not supported.",
            notes=["Person-level employment records are not available for such forecasts."],
        )

    if "predict who will need" in p and "service" in p:
        return format_compact_response(
            "Predicting which specific persons will need services is not supported.",
            notes=["Only aggregate or geographic analysis is appropriate from these datasets."],
        )

    if re.search(r"guarantee.*\b100%\s*accurate\b", p) or re.search(
        r"\b100%\s*accurate\b.*\breal life\b", p
    ):
        return format_compact_response(
            "A guarantee of perfect real-world accuracy cannot be given.",
            notes=["All figures depend on collection timing, definitions, and reporting error."],
        )

    if "what values need to be changed" in p and "look better" in p:
        return format_compact_response(
            "The assistant will not advise changing data values to alter appearances.",
            notes=["Reported values should match source records and integrity standards."],
        )

    return None


formal_guardrail_reply = buffi_guardrail_reply


def humanize_source_line(rel_path: str) -> str:
    p = (rel_path or "").strip().replace("\\", "/")
    return p if p else "local data file"
