import os
from dotenv import load_dotenv

# Load environment variables before any other imports
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

"""
Chat API entrypoint.

Flow: guardrail → integrated.get_groq_response (retrieval / handlers / RAG) →
civic_synthesis.synthesize_civic_structured_response (LLM JSON narrative).

See CHAT_ARCHITECTURE.md and civic_synthesis.py.
"""
import re
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

try:
    from .chat_format import formal_guardrail_reply
    from .integrated import get_groq_response
    from .civic_synthesis import synthesize_civic_structured_response
except ImportError:
    # Running as `uvicorn main:app` from `backend/app` (not as package `app.main`)
    from chat_format import formal_guardrail_reply
    from integrated import get_groq_response
    from civic_synthesis import synthesize_civic_structured_response


def _geography_hint_from_message(text: str) -> Optional[str]:
    """Lightweight hint for synthesis (Phase 2 will replace with real geo resolution)."""
    if not text:
        return None
    m = re.search(r"\b(\d{5})\b", text)
    return f"ZIP {m.group(1)}" if m else None


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all. Restrict in production.
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_message = (data.get("message") or "").strip()
    blocked = formal_guardrail_reply(user_message)
    if blocked:
        return {"response": blocked, "structured": None, "highlight_data": None}

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

    # 2) LLM synthesis: narrative JSON grounded in retrieved_context (Phase 1)
    structured = synthesize_civic_structured_response(
        user_query=user_message,
        retrieved_context=str(raw_text),
        metrics=metrics or None,
        geography_hint=_geography_hint_from_message(user_message),
    )
    payload = structured.model_dump()

    return {
        "response": structured.answer,
        "structured": payload,
        "highlight_data": highlight_data,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5005)
