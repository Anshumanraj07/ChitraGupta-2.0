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