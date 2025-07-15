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
    # get_groq_response returns (response, plot_object, highlight_data_df)
    if isinstance(response_tuple, tuple):
        response = response_tuple[0]
    else:
        response = response_tuple
    return {"response": response}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5005) 