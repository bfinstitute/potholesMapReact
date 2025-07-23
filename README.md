# Potholes Map & Chatbot

This project is a full-stack application for visualizing pothole data and interacting with a chatbot that can answer questions about potholes, streets, and districts in San Antonio.

---

## Backend (FastAPI)

### **Requirements**
- Python 3.9+
- See `backend/app/requirements.txt` for dependencies

### **Installation**
```bash
cd backend/app
pip install -r requirements.txt
```

### **Running the Backend (Data-Only Mode, No Groq LLM)**
You can run the backend without a Groq API key. In this mode, the chatbot will only answer questions that match your local data logic (e.g., pothole counts, street queries, map highlights). LLM fallback will be disabled or return a default message.

```bash
cd backend/app
uvicorn main:app --reload --host 127.0.0.1 --port 5005
```
- Do **not** set the `GROQ_API_KEY` environment variable.
- The bot will answer only data-driven questions. LLM/generic questions will return a fallback message.

### **Running the Backend (With Groq LLM)**
If you want LLM fallback for generic questions:
```powershell
$env:GROQ_API_KEY="your_actual_groq_api_key"
uvicorn main:app --reload --host 127.0.0.1 --port 5005
```

---

## Frontend (React)

### **Requirements**
- Node.js 18+
- See `frontend/package.json` for dependencies

### **Installation**
```bash
cd frontend
npm install
```

### **Running the Frontend**
```bash
npm start
```
- The app will be available at [http://localhost:3000](http://localhost:3000) or [http://localhost:3001](http://localhost:3001).

---

## **Usage**
- Open the frontend in your browser.
- Ask the chatbot questions about potholes, streets, or districts.
- The map will update with highlights for data-driven answers.
- If running without Groq, only data-driven questions will be answered.

---

## **Troubleshooting**
- If the bot hangs or does not respond, check the backend terminal for errors.
- If you see a 401 error, your Groq API key is missing or invalid.
- If you want to run in data-only mode, do not set the Groq API key.

---

## **Project Structure**
- `backend/app/` — FastAPI backend and data logic
- `frontend/` — React frontend and map UI

---

For more help, open an issue or contact the maintainer. 