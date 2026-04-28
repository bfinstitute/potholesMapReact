"""
Alamo-Intelligence-Hub API endpoints, ported from the standalone Flask backend.

Mounted under the FastAPI app at the `/api` prefix so a single backend serves
both the civic chatbot (`/chat`, `/health`, `/cache/*`) and the Hub
(`/api/login`, `/api/upload`, `/api/analyze`, ...).

The original Flask implementation lives in
`Alamo-Intelligence-Hub/backend/app.py`; this module preserves its public
behavior (request/response shapes) so the existing frontend `services/api.js`
keeps working without changes.
"""

from __future__ import annotations

import csv
import io
import json
import os
from typing import Any, List, Optional

import pandas as pd
import requests
from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel


router = APIRouter(prefix="/api", tags=["hub"])

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Hub historically used GOOGLE_API_KEY; the chatbot uses GEMINI_API_KEY.
# Accept either so a single backend env can drive both.
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash-exp:generateContent"
)

# Hub auth: intentionally hardcoded (demo auth).
HUB_ADMIN_EMAIL = os.environ.get("HUB_ADMIN_EMAIL", "admin@bfinstitute.org")
HUB_ADMIN_PASSWORD = os.environ.get("HUB_ADMIN_PASSWORD", "admin123")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_nan_values(obj: Any) -> Any:
    """Recursively replace NaN-like values with None so JSON serialization works."""
    if isinstance(obj, dict):
        return {k: _clean_nan_values(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_nan_values(v) for v in obj]
    try:
        if pd.isna(obj):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(obj, str) and obj.strip().lower() == "nan":
        return None
    return obj


def _gemini_text(prompt: str) -> Optional[str]:
    """Call Gemini and return the raw text part, or None on any failure."""
    if not GEMINI_API_KEY:
        return None
    try:
        r = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        if r.status_code != 200:
            return None
        result = r.json()
        candidates = result.get("candidates") or []
        if not candidates:
            return None
        return candidates[0]["content"]["parts"][0]["text"]
    except Exception:
        return None


def _strip_code_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def human_column_description(col: str) -> str:
    """Deterministic fallback descriptions for common civic / transit columns."""
    col = (col or "").lower()

    # Transit / transportation
    if "route_id" in col or "route" in col:
        return "Unique identifier for the transit route or bus/train line."
    if "trip_id" in col or "trip" in col:
        return "Unique identifier for a specific transit trip or journey."
    if "trip_headsign" in col or "headsign" in col:
        return "Destination display name shown on the transit vehicle."
    if "block_id" in col or "block" in col:
        return "Vehicle block identifier for transit scheduling."
    if "service_id" in col or "service" in col:
        return "Service schedule identifier for transit operations."
    if "shape_id" in col or "shape" in col:
        return "Geographic route shape identifier for mapping."
    if "stop_id" in col or "stop" in col:
        return "Unique identifier for a transit stop or station."
    if "agency_id" in col or "agency" in col:
        return "Transit agency identifier."
    if "vehicle_id" in col or "vehicle" in col:
        return "Unique identifier for a transit vehicle."

    # Generic ID
    if "id" in col and "client" in col:
        return "Unique identifier for the client or requester."
    if "id" in col and "case" in col:
        return "Unique identifier for each case or service request."
    if "id" in col:
        return "Unique identifier for this record."

    # Date / time
    if "date" in col and "open" in col:
        return "Date when the case was opened."
    if "date" in col and "close" in col:
        return "Date when the case was closed."
    if "date" in col:
        return "Date information for this record."
    if "time" in col:
        return "Time information for this record."

    # Service / SLA
    if "sla" in col:
        return "Service Level Agreement (SLA) related date or days."
    if "late" in col:
        return "Indicates if the case was resolved late."
    if "subject" in col:
        return "Department or subject area handling the case."
    if "source" in col:
        return "Source of the case (e.g., phone, web, app)."
    if "desc" in col:
        return "Description or address related to the case."

    # Location
    if "district" in col:
        return "City council district where the case occurred."
    if "coord" in col:
        return "Coordinate for the case location."
    if "lat" in col:
        return "Latitude coordinate of the case location."
    if "long" in col:
        return "Longitude coordinate of the case location."

    # Time / duration
    if "duration" in col:
        return "Duration of the case."
    if "day" in col:
        return "Day related to the case."
    if "month" in col:
        return "Month related to the case."
    if "year" in col:
        return "Year related to the case."
    if "hour" in col:
        return "Hour related to the case."
    if "fiscal" in col:
        return "Fiscal year in which the case was opened."

    # Weather
    if "week" in col:
        return "Weekly weather or environmental data."
    if "prcp" in col:
        return "Precipitation (rainfall) data."
    if "snow" in col:
        return "Snowfall data."
    if "tfrz" in col:
        return "Number of freezing temperature days."
    if "tmax" in col:
        return "Maximum temperature."
    if "tmin" in col:
        return "Minimum temperature."
    if "tavg" in col:
        return "Average temperature."
    if "tdif" in col:
        return "Temperature difference."

    # Counts
    if col == "cases":
        return "Number of cases."
    if "count" in col:
        return "Count or quantity measurement."

    return "No description available."


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class LoginIn(BaseModel):
    email: str = ""
    password: str = ""


class TokenIn(BaseModel):
    token: str = ""


class CsvDataIn(BaseModel):
    csvData: List[dict] = []
    filename: Optional[str] = "processed_data.csv"


class ColumnDescriptionIn(BaseModel):
    column_name: str = ""
    sample_data: List[dict] = []


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/health")
async def hub_health():
    return {"status": "healthy", "message": "CSV Analyzer Backend is running"}


@router.post("/login")
async def hub_login(payload: LoginIn):
    if payload.email == HUB_ADMIN_EMAIL and payload.password == HUB_ADMIN_PASSWORD:
        return {
            "success": True,
            "message": "Login successful",
            "token": "demo-token",
            "user": {"email": payload.email, "name": "Admin"},
        }
    return JSONResponse(
        status_code=401,
        content={"success": False, "message": "Invalid credentials"},
    )


@router.post("/verify-token")
async def hub_verify_token(payload: TokenIn):
    if not payload.token:
        return JSONResponse(status_code=400, content={"error": "Token is required"})
    if payload.token == "demo-token":
        return {"success": True, "user": {"email": HUB_ADMIN_EMAIL, "name": "Admin"}}

    return JSONResponse(status_code=401, content={"success": False, "message": "Invalid token"})


@router.post("/upload")
async def hub_upload(file: UploadFile = File(...)):
    if not file or not file.filename:
        return JSONResponse(status_code=400, content={"error": "No selected file"})

    safe_name = os.path.basename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, safe_name)
    contents = await file.read()
    with open(filepath, "wb") as f:
        f.write(contents)

    try:
        df = pd.read_csv(filepath)
        df_clean = df.where(pd.notnull(df), None)
        sample = df_clean.head(5).to_dict(orient="records")
        summary = {
            "filename": safe_name,
            "num_rows": len(df),
            "num_columns": len(df.columns),
            "columns": list(df.columns),
            "sample": sample,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to process CSV: {e}"},
        )

    cols = list(df.columns)
    sample_text = "\n".join(
        f"Row {i + 1}: {json.dumps(row, default=str)}"
        for i, row in enumerate(df_clean.head(3).to_dict(orient="records"))
    )

    prompt = (
        "You are a data expert. The following CSV file has these column headers:\n\n"
        f"{', '.join(cols)}\n\n"
        f"Here are a few sample rows:\n\n{sample_text}\n\n"
        "Please analyze the column names and give a description of what each one likely refers to or means.\n"
        "Output your answer as a JSON object where keys are column names and values are descriptions.\n"
        'Example format: {"column1": "description1", "column2": "description2"}\n\n'
        "Only return the JSON object, no other text.\n"
    )

    annotations = {col: human_column_description(col) for col in cols}
    ai = _gemini_text(prompt)
    if ai:
        try:
            parsed = json.loads(_strip_code_fence(ai))
            if isinstance(parsed, dict):
                # LLM annotations win when present, fallback otherwise.
                for k, v in parsed.items():
                    if isinstance(v, str) and v.strip():
                        annotations[k] = v
        except Exception:
            pass

    response_data = {
        "success": True,
        "message": "File uploaded successfully",
        "summary": summary,
        "annotations": annotations,
        "filename": safe_name,
        "data": df_clean.head(5).to_dict(orient="records"),
        "stats": summary,
        "column_descriptions": annotations,
    }

    return _clean_nan_values(response_data)


@router.post("/get_column_description")
async def hub_get_column_description(payload: ColumnDescriptionIn):
    if not payload.column_name:
        return JSONResponse(
            status_code=400,
            content={"error": "Column name is required"},
        )

    sample_text = "\n".join(
        f"Row {i + 1}: {json.dumps(row, default=str)}"
        for i, row in enumerate(payload.sample_data[:3])
    )
    prompt = (
        f'You are a data expert. I have a CSV column named "{payload.column_name}".\n\n'
        f"Here are a few sample rows from the dataset:\n\n{sample_text}\n\n"
        "Please provide a clear, concise description of what this column likely represents or contains.\n"
        "Focus on the business meaning and purpose of this data field.\n"
    )

    description = _gemini_text(prompt) or human_column_description(payload.column_name)
    return {"description": description}


@router.post("/analyze")
async def hub_analyze(payload: CsvDataIn):
    csv_data = payload.csvData
    if not csv_data:
        return JSONResponse(
            status_code=400, content={"error": "No CSV data provided"},
        )
    return {
        "success": True,
        "analysis": {
            "total_rows": len(csv_data),
            "total_columns": len(csv_data[0]) if csv_data else 0,
            "message": "Analysis completed",
        },
    }


@router.post("/validate")
async def hub_validate(payload: CsvDataIn):
    csv_data = payload.csvData
    if not csv_data:
        return JSONResponse(
            status_code=400, content={"error": "No CSV data provided"},
        )
    return {
        "success": True,
        "validation": {
            "has_data": len(csv_data) > 0,
            "total_rows": len(csv_data),
            "total_columns": len(csv_data[0]) if csv_data else 0,
            "message": "Validation completed",
        },
    }


@router.post("/download")
async def hub_download(payload: CsvDataIn):
    csv_data = payload.csvData
    if not csv_data:
        return JSONResponse(
            status_code=400, content={"error": "No CSV data provided"},
        )

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(csv_data[0].keys()))
    writer.writeheader()
    writer.writerows(csv_data)

    filename = payload.filename or "processed_data.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/feedback")
async def hub_feedback(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = None
    print("Feedback received:", data)
    return {"success": True, "message": "Feedback submitted successfully"}


@router.get("/files")
async def hub_list_files():
    try:
        files = []
        if os.path.exists(UPLOAD_FOLDER):
            for filename in os.listdir(UPLOAD_FOLDER):
                if filename.endswith(".csv"):
                    p = os.path.join(UPLOAD_FOLDER, filename)
                    st = os.stat(p)
                    files.append(
                        {
                            "filename": filename,
                            "size": st.st_size,
                            "uploaded_at": st.st_mtime,
                        }
                    )
        return {"success": True, "files": files}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error listing files: {e}"},
        )


@router.get("/files/{filename}")
async def hub_get_file_info(filename: str):
    try:
        safe_name = os.path.basename(filename)
        p = os.path.join(UPLOAD_FOLDER, safe_name)
        if not os.path.exists(p):
            return JSONResponse(status_code=404, content={"error": "File not found"})
        df = pd.read_csv(p)
        st = os.stat(p)
        return {
            "success": True,
            "file_info": {
                "filename": safe_name,
                "size": st.st_size,
                "uploaded_at": st.st_mtime,
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "columns": list(df.columns),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error getting file info: {e}"},
        )
