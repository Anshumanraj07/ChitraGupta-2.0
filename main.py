import os
import requests
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from core.brain import parse_user_input

load_dotenv()

app = FastAPI(title="ChitraGupta AI API")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# --- Pydantic Models ---
class UserInput(BaseModel):
    user_input: str

class TaskUpdate(BaseModel):
    is_completed: bool = None
    sub_tasks: list = None
    task_title: str = None  
    raw_input: str = None   

class JournalUpdate(BaseModel):
    raw_input: str = None   

# --- Routes ---

@app.get("/")
def serve_frontend():
    return FileResponse("index.html")

# 1. Fetch Tasks
@app.get("/api/tasks")
def get_tasks(user_id: str = Header(...)):
    url = f"{SUPABASE_URL}/rest/v1/tasks?user_id=eq.{user_id}&order=created_at.desc"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return {"status": "success", "data": response.json()}
    raise HTTPException(status_code=response.status_code, detail=response.text)

# 2. Fetch Journals
@app.get("/api/journals")
def get_journals(user_id: str = Header(...)):
    url = f"{SUPABASE_URL}/rest/v1/journals?user_id=eq.{user_id}&order=created_at.desc"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return {"status": "success", "data": response.json()}
    raise HTTPException(status_code=response.status_code, detail=response.text)

# 3. Smart Parser & Router
@app.post("/api/parse-task")
def parse_and_save_task(data: UserInput, user_id: str = Header(...)):
    ai_data = parse_user_input(data.user_input)
    data_type = ai_data.get("type", "task") 
    
    if data_type == "task":
        payload = {
            "user_id": user_id,
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
            "user_id": user_id,
            "raw_input": data.user_input,
            "mood": ai_data.get("mood", "Neutral"),
            "summary": ai_data.get("summary"),
            "philosophical_insight": ai_data.get("philosophical_insight", "")
        }
        url = f"{SUPABASE_URL}/rest/v1/journals"
        response = requests.post(url, headers=headers, json=payload)
        message = "Thought recorded in the journal."

    if response.status_code in [200, 201]:
        return {"status": "success", "message": message, "type": data_type, "data": response.json()}
    raise HTTPException(status_code=response.status_code, detail=response.text)

# 4. Task Update (AI-Powered Text Edit + Checkboxes)
@app.patch("/api/tasks/{task_id}")
def update_task(task_id: str, update_data: TaskUpdate, user_id: str = Header(...)):
    if update_data.task_title:
        ai_data = parse_user_input(update_data.task_title)
        payload = {
            "task_title": ai_data.get("task_title"),
            "raw_input": update_data.task_title,
            "category": ai_data.get("category"),
            "priority": ai_data.get("priority"),
            "sub_tasks": ai_data.get("sub_tasks", []),
            "chitragupt_wisdom": ai_data.get("chitragupt_wisdom")
        }
    else:
        payload = {k: v for k, v in update_data.dict().items() if v is not None}
    
    url = f"{SUPABASE_URL}/rest/v1/tasks?id=eq.{task_id}&user_id=eq.{user_id}"
    response = requests.patch(url, headers=headers, json=payload)
    if response.status_code in [200, 204]:
        return {"status": "success"}
    raise HTTPException(status_code=response.status_code, detail=response.text)

# 5. Journal Update (AI-Powered Insight Regeneration)
@app.patch("/api/journals/{journal_id}")
def update_journal(journal_id: str, update_data: JournalUpdate, user_id: str = Header(...)):
    if update_data.raw_input:
        ai_data = parse_user_input(update_data.raw_input)
        payload = {
            "raw_input": update_data.raw_input,
            "summary": ai_data.get("summary", ""),
            "mood": ai_data.get("mood", "Neutral")
        }
    else:
        payload = {}

    url = f"{SUPABASE_URL}/rest/v1/journals?id=eq.{journal_id}&user_id=eq.{user_id}"
    response = requests.patch(url, headers=headers, json=payload)
    if response.status_code in [200, 204]:
        return {"status": "success"}
    raise HTTPException(status_code=response.status_code, detail=response.text)

# 6. Delete Task
@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str, user_id: str = Header(...)):
    url = f"{SUPABASE_URL}/rest/v1/tasks?id=eq.{task_id}&user_id=eq.{user_id}"
    response = requests.delete(url, headers=headers)
    if response.status_code in [200, 204]:
        return {"status": "success"}
    raise HTTPException(status_code=response.status_code, detail=response.text)

# 7. Delete Journal
@app.delete("/api/journals/{journal_id}")
def delete_journal(journal_id: str, user_id: str = Header(...)):
    url = f"{SUPABASE_URL}/rest/v1/journals?id=eq.{journal_id}&user_id=eq.{user_id}"
    response = requests.delete(url, headers=headers)
    if response.status_code in [200, 204]:
        return {"status": "success"}
    raise HTTPException(status_code=response.status_code, detail=response.text)

# 8. Analyze Karma (Weekly Summary)
@app.get("/api/analyze")
def analyze_karma(user_id: str = Header(...)):
    tasks_url = f"{SUPABASE_URL}/rest/v1/tasks?user_id=eq.{user_id}&order=created_at.desc&limit=15"
    journals_url = f"{SUPABASE_URL}/rest/v1/journals?user_id=eq.{user_id}&order=created_at.desc&limit=10"
    
    tasks_req = requests.get(tasks_url, headers=headers)
    journals_req = requests.get(journals_url, headers=headers)
    
    tasks_data = tasks_req.json() if tasks_req.status_code == 200 else []
    journals_data = journals_req.json() if journals_req.status_code == 200 else []
    
    task_strings = [f"- {t.get('task_title')} (Status: {'Done' if t.get('is_completed') else 'Pending'})" for t in tasks_data]
    journal_strings = [f"- {j.get('summary')}" for j in journals_data]
    
    user_context = f"Recent Tasks:\n{chr(10).join(task_strings)}\n\nRecent Journals:\n{chr(10).join(journal_strings)}"
    
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