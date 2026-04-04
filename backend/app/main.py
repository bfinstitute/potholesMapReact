import os
from dotenv import load_dotenv

# Load environment variables before any other imports
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

try:
    from .chat_format import formal_guardrail_reply
    from .integrated import get_groq_response
except ImportError:
    # Running as `uvicorn main:app` from `backend/app` (not as package `app.main`)
    from chat_format import formal_guardrail_reply
    from integrated import get_groq_response


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
    user_message = data.get("message", "")
    blocked = formal_guardrail_reply(user_message)
    if blocked:
        return {"response": blocked, "highlight_data": None}
    response_tuple = get_groq_response(user_message)
    # get_groq_response returns (response, plot_object, highlight_data_df)
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
    return {"response": response, "highlight_data": highlight_data}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5005) 
