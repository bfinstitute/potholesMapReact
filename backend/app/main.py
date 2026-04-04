import os
import time
import hashlib
from dotenv import load_dotenv

# Load environment variables before any other imports
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

"""
Chat API entrypoint.

Flow: guardrail → MongoDB cache check → integrated.get_groq_response (retrieval / handlers / RAG) →
civic_synthesis.synthesize_civic_structured_response (LLM JSON narrative) → MongoDB logging/caching.

See CHAT_ARCHITECTURE.md, civic_synthesis.py, and MONGODB_INTEGRATION_SUMMARY.md.
"""
import re
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

try:
    from .chat_format import formal_guardrail_reply
    from .integrated import get_groq_response
    from .civic_synthesis import synthesize_civic_structured_response
    from .mongodb_client import (
        get_mongo_client,
        log_query,
        get_cached_response,
        cache_response,
        log_groq_response,
    )
except ImportError:
    # Running as `uvicorn main:app` from `backend/app` (not as package `app.main`)
    from chat_format import formal_guardrail_reply
    from integrated import get_groq_response
    from civic_synthesis import synthesize_civic_structured_response
    from mongodb_client import (
        get_mongo_client,
        log_query,
        get_cached_response,
        cache_response,
        log_groq_response,
    )


def _geography_hint_from_message(text: str) -> Optional[str]:
    """Lightweight hint for synthesis (Phase 2 will replace with real geo resolution)."""
    if not text:
        return None
    m = re.search(r"\b(\d{5})\b", text)
    return f"ZIP {m.group(1)}" if m else None


def _get_context_signature() -> str:
    """Generate a signature representing the current data context state.

    Uses daily granularity to group queries from the same day with same data.
    This allows cache reuse while ensuring fresh data is used each day.
    """
    from datetime import datetime
    day_str = datetime.utcnow().strftime("%Y-%m-%d")
    return hashlib.md5(day_str.encode()).hexdigest()


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all. Restrict in production.
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/chat")
async def chat(request: Request):
    start_time = time.time()

    data = await request.json()
    user_message = (data.get("message") or "").strip()

    # Check guardrails first
    blocked = formal_guardrail_reply(user_message)
    if blocked:
        return {"response": blocked, "structured": None, "highlight_data": None}

    # Generate context signature for MongoDB caching
    context_sig = _get_context_signature()

    # Try to get cached response from MongoDB
    mongo_client = get_mongo_client()
    cached = None
    if mongo_client.enabled:
        cached = get_cached_response(user_message, context_sig)

    if cached:
        # Return cached response with structured data
        response_time_ms = int((time.time() - start_time) * 1000)

        # Log query with cache hit
        if mongo_client.enabled:
            log_query(
                question=user_message,
                intent_detected="cached",
                data_sources_used=["cache"],
                response_time_ms=response_time_ms,
                groq_called=False,
            )

        return {
            "response": cached["response"],
            "structured": cached.get("structured"),
            "highlight_data": cached.get("highlight_data"),
        }

    # No cache hit - proceed with full pipeline:
    # 1) Deterministic retrieval + handlers (facts embedded in response text / highlight_df)
    response_tuple = get_groq_response(user_message)
    raw_text = ""
    highlight_data = None

    if isinstance(response_tuple, tuple):
        raw_text = response_tuple[0] if response_tuple[0] is not None else ""
        if len(response_tuple) > 2 and response_tuple[2] is not None:
            try:
                highlight_data = response_tuple[2].to_dict("records")
            except Exception:
                highlight_data = None
    else:
        raw_text = response_tuple if response_tuple is not None else ""

    metrics = {}
    if highlight_data:
        metrics["map_point_count"] = len(highlight_data)

    # 2) LLM synthesis: narrative JSON grounded in retrieved_context
    structured = synthesize_civic_structured_response(
        user_query=user_message,
        retrieved_context=str(raw_text),
        metrics=metrics or None,
        geography_hint=_geography_hint_from_message(user_message),
    )
    payload = structured.model_dump()

    # Calculate total response time
    response_time_ms = int((time.time() - start_time) * 1000)

    # Log query to MongoDB
    if mongo_client.enabled:
        # Detect if Groq was called (response contains data sources section)
        groq_called = "**Data Sources:**" in raw_text or structured.answer

        log_query(
            question=user_message,
            intent_detected="civic_synthesis",
            data_sources_used=["groq", "civic_synthesis"] if groq_called else ["local", "civic_synthesis"],
            response_time_ms=response_time_ms,
            groq_called=groq_called,
        )

        # Cache the complete response (including structured data) for future use
        cache_response(
            question=user_message,
            context_signature=context_sig,
            response=structured.answer,
            highlight_data=highlight_data,
        )

        # Note: We could also cache the structured payload separately if needed
        # For now, we're just caching the answer text and highlight_data

    return {
        "response": structured.answer,
        "structured": payload,
        "highlight_data": highlight_data,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5005)
