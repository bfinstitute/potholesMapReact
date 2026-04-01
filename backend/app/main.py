from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
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
    response_tuple = get_groq_response(user_message)
    # get_groq_response returns (response, chart_data_or_plot, highlight_data_df)
    if isinstance(response_tuple, tuple):
        response = response_tuple[0]
        chart_data = None
        highlight_data = None
        # Second element: chart_data dict (or legacy matplotlib figure, which we ignore)
        if len(response_tuple) > 1 and isinstance(response_tuple[1], dict):
            chart_data = response_tuple[1]
        # Third element: highlight DataFrame for the map
        if len(response_tuple) > 2 and response_tuple[2] is not None:
            try:
                highlight_data = response_tuple[2].to_dict('records')
                if not highlight_data:
                    highlight_data = None
            except Exception:
                highlight_data = None
    else:
        response = response_tuple
        chart_data = None
        highlight_data = None
    return {"response": response, "highlight_data": highlight_data, "chart_data": chart_data}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5005) 