import os
import requests
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from core.brain import parse_user_input

load_dotenv()

app = FastAPI(title="ChitraGupt 2.0 API")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Base headers for Supabase REST API
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

class UserInput(BaseModel):
    user_input: str

class TaskUpdate(BaseModel):
    is_completed: bool = None
    sub_tasks: list = None


@app.get("/")
def serve_frontend():
    return FileResponse("index.html")

# 1. Fetch Tasks (Ab sirf logged-in user ka data aayega)
@app.get("/api/tasks")
def get_tasks(user_id: str = Header(...)):
    url = f"{SUPABASE_URL}/rest/v1/tasks?user_id=eq.{user_id}&order=created_at.desc"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return {"status": "success", "data": response.json()}
    raise HTTPException(status_code=response.status_code, detail=response.text)

# 2. Fetch Journals (Ab sirf logged-in user ka data aayega)
@app.get("/api/journals")
def get_journals(user_id: str = Header(...)):
    url = f"{SUPABASE_URL}/rest/v1/journals?user_id=eq.{user_id}&order=created_at.desc"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return {"status": "success", "data": response.json()}
    raise HTTPException(status_code=response.status_code, detail=response.text)

# 3. Smart Parser & Router (Sath me user_id save karega)
@app.post("/api/parse-task")
def parse_and_save_task(data: UserInput, user_id: str = Header(...)):
    ai_data = parse_user_input(data.user_input)
    data_type = ai_data.get("type", "task") 
    
    if data_type == "task":
        payload = {
            "user_id": user_id,  # <-- Har entry ke sath User ID attach hogi
            "raw_input": data.user_input,
            "task_title": ai_data.get("task_title"),
            "category": ai_data.get("category"),
            "priority": ai_data.get("priority"),
            "estimated_time": ai_data.get("estimated_time"),
            "chitragupt_wisdom": ai_data.get("chitragupt_wisdom"),
            "sub_tasks": ai_data.get("sub_tasks", [])
        }
        url = f"{SUPABASE_URL}/rest/v1/tasks"
        response = requests.post(url, headers=headers, json=payload)
        message = "Action logged in the ledger."
        
    else:
        payload = {
            "user_id": user_id,  # <-- Har entry ke sath User ID attach hogi
            "raw_input": data.user_input,
            "mood": ai_data.get("mood"),
            "summary": ai_data.get("summary"),
            "philosophical_insight": ai_data.get("philosophical_insight")
        }
        url = f"{SUPABASE_URL}/rest/v1/journals"
        response = requests.post(url, headers=headers, json=payload)
        message = "Thought recorded in the journal."

    if response.status_code in [200, 201]:
        return {"status": "success", "message": message, "type": data_type, "data": response.json()}
    raise HTTPException(status_code=response.status_code, detail=response.text)

# 4. Task Update (Security: Sirf apna task update kar sakega)
@app.patch("/api/tasks/{task_id}")
def update_task(task_id: str, update_data: TaskUpdate, user_id: str = Header(...)):
    url = f"{SUPABASE_URL}/rest/v1/tasks?id=eq.{task_id}&user_id=eq.{user_id}"
    payload = {}
    if update_data.is_completed is not None:
        payload["is_completed"] = update_data.is_completed
    if update_data.sub_tasks is not None:
        payload["sub_tasks"] = update_data.sub_tasks

    response = requests.patch(url, headers=headers, json=payload)
    if response.status_code in [200, 204]:
        return {"status": "success"}
    raise HTTPException(status_code=response.status_code, detail=response.text)

# 5. Delete Task
@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str, user_id: str = Header(...)):
    url = f"{SUPABASE_URL}/rest/v1/tasks?id=eq.{task_id}&user_id=eq.{user_id}"
    response = requests.delete(url, headers=headers)
    if response.status_code in [200, 204]:
        return {"status": "success"}
    raise HTTPException(status_code=response.status_code, detail=response.text)

# 6. Delete Journal
@app.delete("/api/journals/{journal_id}")
def delete_journal(journal_id: str, user_id: str = Header(...)):
    url = f"{SUPABASE_URL}/rest/v1/journals?id=eq.{journal_id}&user_id=eq.{user_id}"
    response = requests.delete(url, headers=headers)
    if response.status_code in [200, 204]:
        return {"status": "success"}
    raise HTTPException(status_code=response.status_code, detail=response.text)


# 7. Analyze Karma (Weekly Summary)
@app.get("/api/analyze")
def analyze_karma(user_id: str = Header(...)):
    # Fetch recent tasks and journals
    tasks_url = f"{SUPABASE_URL}/rest/v1/tasks?user_id=eq.{user_id}&order=created_at.desc&limit=15"
    journals_url = f"{SUPABASE_URL}/rest/v1/journals?user_id=eq.{user_id}&order=created_at.desc&limit=10"
    
    tasks_req = requests.get(tasks_url, headers=headers)
    journals_req = requests.get(journals_url, headers=headers)
    
    tasks_data = tasks_req.json() if tasks_req.status_code == 200 else []
    journals_data = journals_req.json() if journals_req.status_code == 200 else []
    
    # Prepare data for AI
    task_strings = [f"- {t.get('task_title')} (Status: {'Done' if t.get('is_completed') else 'Pending'})" for t in tasks_data]
    journal_strings = [f"- Mood: {j.get('mood')} | {j.get('summary')}" for j in journals_data]
    
    user_context = f"Recent Tasks:\n{chr(10).join(task_strings)}\n\nRecent Journals:\n{chr(10).join(journal_strings)}"
    
    # Groq AI Call
    groq_api_key = os.getenv("GROQ_API_KEY")
    groq_headers = {"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}
    
    prompt = f"""
    Analyze the user's recent tasks and journal entries below.
    Provide a simple, clear, and highly objective summary of their recent focus areas, productivity, and state of mind.
    Rule 1: Keep the tone practical and direct. Do NOT use any forced personas.
    Rule 2: At the very end, provide exactly ONE highly relevant quote from a renowned philosopher that perfectly matches their current situation or subject matter.
    
    Data:
    {user_context}
    """
    
    payload = {
        "model": "llama3-70b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5
    }
    
    groq_res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=groq_headers, json=payload)
    
    if groq_res.status_code == 200:
        analysis = groq_res.json()["choices"][0]["message"]["content"]
        return {"status": "success", "analysis": analysis}
    else:
        raise HTTPException(status_code=500, detail="Failed to analyze karma.")