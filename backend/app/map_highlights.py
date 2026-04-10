"""
Lightweight map payloads for the React map (Latitude, Longitude, MSAG_Name, color, marker_radius).
Uses geocoding for ZIP / city context when point-level data is unavailable.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Optional

import pandas as pd


@lru_cache(maxsize=256)
def _geocode_pair(query: str):
    try:
        from .integrated import geocode_address
    except ImportError:
        from integrated import geocode_address

    return geocode_address(query)


def zip_centroid_marker(
    zipcode: str,
    label: Optional[str] = None,
    color: str = "#4169E1",
    marker_radius: int = 18,
) -> pd.DataFrame:
    z = str(zipcode).strip()
    lat, lon = _geocode_pair(f"{z}, San Antonio, TX")
    if lat is None or lon is None:
        return pd.DataFrame()
    return pd.DataFrame(
        [
            {
                "Latitude": float(lat),
                "Longitude": float(lon),
                "MSAG_Name": label or f"ZIP {z} (approx. center)",
                "color": color,
                "marker_radius": marker_radius,
            }
        ]
    )


def san_antonio_center_marker(
    label: str = "San Antonio (city context)",
    color: str = "#2E8B57",
    marker_radius: int = 16,
) -> pd.DataFrame:
    lat, lon = _geocode_pair("San Antonio, TX")
    if lat is None or lon is None:
        return pd.DataFrame()
    return pd.DataFrame(
        [
            {
                "Latitude": float(lat),
                "Longitude": float(lon),
                "MSAG_Name": label,
                "color": color,
                "marker_radius": marker_radius,
            }
        ]
    )


def sacrd_analytics_context_marker() -> pd.DataFrame:
    """Non-geographic analytics answers still get a downtown context pin."""
    return san_antonio_center_marker(
        label="SACRD / portal analytics (city context)",
        color="#6A5ACD",
        marker_radius=14,
    )


def rag_map_highlight_for_prompt(prompt: str) -> pd.DataFrame:
    """
    Best-effort map context for get_rag_response() text-only answers.
    """
    text = (prompt or "").strip()
    if not text:
        return pd.DataFrame()
    low = text.lower()

    if re.search(r"pageview|sacrd", low):
        return sacrd_analytics_context_marker()

    if "78207" in low or re.search(r"zip\s*78207", low):
        return zip_centroid_marker("78207", label="ZIP 78207 context", color="#9370DB", marker_radius=17)

    zips = re.findall(r"\b(\d{5})\b", text)
    if zips:
        z = zips[0]
        return zip_centroid_marker(z, label=f"ZIP {z} context", color="#4169E1", marker_radius=17)

    citywide = any(
        phrase in low
        for phrase in (
            "san antonio",
            "san antonians",
            "city-wide",
            "citywide",
            "your district",
        )
    )
    if citywide:
        return san_antonio_center_marker()

    # Pavement / 311 / VIA / history-style RAG answers often have no ZIP in the text
    if re.search(
        r"pothole|reported on|complaint|pci\b|pavement|via\b|route\b|street|ave\b|boulevard|history of repeated",
        low,
    ):
        return san_antonio_center_marker(label="San Antonio (infrastructure context)", color="#2E8B57")

    return pd.DataFrame()
