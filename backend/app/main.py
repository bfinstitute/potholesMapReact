import os
import time
import hashlib
from dotenv import load_dotenv

# Load environment variables before any other imports
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

try:
    from .chat_format import formal_guardrail_reply
    from .integrated import get_groq_response
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
    from mongodb_client import (
        get_mongo_client,
        log_query,
        get_cached_response,
        cache_response,
        log_groq_response,
    )


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all. Restrict in production.
    allow_methods=["*"],
    allow_headers=["*"],
)

def _get_context_signature() -> str:
    """Generate a signature representing the current data context state.

    Uses daily granularity to group queries from the same day with same data.
    This allows cache reuse while ensuring fresh data is used each day.
    """
    from datetime import datetime
    day_str = datetime.utcnow().strftime("%Y-%m-%d")
    return hashlib.md5(day_str.encode()).hexdigest()


@app.post("/chat")
async def chat(request: Request):
    start_time = time.time()

    data = await request.json()
    user_message = data.get("message", "")

    # Check guardrails first
    blocked = formal_guardrail_reply(user_message)
    if blocked:
        return {"response": blocked, "highlight_data": None}

    # Generate context signature for caching
    context_sig = _get_context_signature()

    # Try to get cached response
    mongo_client = get_mongo_client()
    cached = None
    if mongo_client.enabled:
        cached = get_cached_response(user_message, context_sig)

    if cached:
        # Return cached response
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
            "highlight_data": cached.get("highlight_data"),
        }

    # No cache hit - call get_groq_response
    response_tuple = get_groq_response(user_message)
    response_time_ms = int((time.time() - start_time) * 1000)

    # Parse response tuple
    if isinstance(response_tuple, tuple):
        response = response_tuple[0]
        highlight_data = None
        if len(response_tuple) > 2 and response_tuple[2] is not None:
            try:
                # Convert DataFrame to list of dicts for JSON serialization
                highlight_data = response_tuple[2].to_dict('records')
            except Exception:
                highlight_data = None
    else:
        response = response_tuple
        highlight_data = None

    # Log query to MongoDB
    if mongo_client.enabled:
        # Detect if this was a Groq call (response contains markdown sources section)
        groq_called = "**Data Sources:**" in response or "I don't have" not in response

        log_query(
            question=user_message,
            intent_detected="unknown",  # Could enhance this by exposing intent from integrated.py
            data_sources_used=["groq"] if groq_called else ["local"],
            response_time_ms=response_time_ms,
            groq_called=groq_called,
        )

        # Cache the response for future use
        cache_response(
            question=user_message,
            context_signature=context_sig,
            response=response,
            highlight_data=highlight_data,
        )

    return {"response": response, "highlight_data": highlight_data}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5005) 
