import os
import requests
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from core.brain import parse_user_input

load_dotenv()

app = FastAPI(title="ChitraGupta API")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

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
    task_title: str = None  
    raw_input: str = None   

class JournalUpdate(BaseModel):
    raw_input: str = None   

@app.get("/")
def serve_frontend():
    return FileResponse("index.html")

@app.get("/api/tasks")
def get_tasks(user_id: str = Header(...)):
    url = f"{SUPABASE_URL}/rest/v1/tasks?user_id=eq.{user_id}&order=created_at.desc"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return {"status": "success", "data": response.json()}
    raise HTTPException(status_code=response.status_code, detail=response.text)

@app.get("/api/journals")
def get_journals(user_id: str = Header(...)):
    url = f"{SUPABASE_URL}/rest/v1/journals?user_id=eq.{user_id}&order=created_at.desc"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return {"status": "success", "data": response.json()}
    raise HTTPException(status_code=response.status_code, detail=response.text)

@app.post("/api/parse-task")
def parse_and_save_task(data: UserInput, user_id: str = Header(...)):
    ai_data = parse_user_input(data.user_input)
    data_type = ai_data.get("type", "task") 
    
    if data_type == "task":
        payload = {
            "user_id": user_id,
            "raw_input": data.user_input,
            "task_title": ai_data.get("task_title", "Untitled Task"),
            "category": ai_data.get("category", "General"),
            "priority": ai_data.get("priority", "Medium"),
            "chitragupt_wisdom": ai_data.get("chitragupt_wisdom", ""),
            "sub_tasks": ai_data.get("sub_tasks", [])
        }
        url = f"{SUPABASE_URL}/rest/v1/tasks"
        response = requests.post(url, headers=headers, json=payload)
    else:
        payload = {
            "user_id": user_id,
            "raw_input": data.user_input,
            "mood": ai_data.get("mood", "Neutral"),
            "summary": ai_data.get("summary", "")
        }
        url = f"{SUPABASE_URL}/rest/v1/journals"
        response = requests.post(url, headers=headers, json=payload)

    if response.status_code in [200, 201]:
        return {"status": "success", "type": data_type}
    raise HTTPException(status_code=response.status_code, detail=response.text)

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
            "chitragupt_wisdom": ai_data.get("chitragupt_wisdom", "")
        }
    else:
        payload = {k: v for k, v in update_data.dict().items() if v is not None}
    
    url = f"{SUPABASE_URL}/rest/v1/tasks?id=eq.{task_id}&user_id=eq.{user_id}"
    response = requests.patch(url, headers=headers, json=payload)
    if response.status_code in [200, 204]:
        return {"status": "success"}
    raise HTTPException(status_code=response.status_code, detail=response.text)

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

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str, user_id: str = Header(...)):
    url = f"{SUPABASE_URL}/rest/v1/tasks?id=eq.{task_id}&user_id=eq.{user_id}"
    requests.delete(url, headers=headers)
    return {"status": "success"}

@app.delete("/api/journals/{journal_id}")
def delete_journal(journal_id: str, user_id: str = Header(...)):
    url = f"{SUPABASE_URL}/rest/v1/journals?id=eq.{journal_id}&user_id=eq.{user_id}"
    requests.delete(url, headers=headers)
    return {"status": "success"}

@app.get("/api/analyze")
def analyze_karma(user_id: str = Header(...)):
    tasks_req = requests.get(f"{SUPABASE_URL}/rest/v1/tasks?user_id=eq.{user_id}&order=created_at.desc&limit=15", headers=headers)
    journals_req = requests.get(f"{SUPABASE_URL}/rest/v1/journals?user_id=eq.{user_id}&order=created_at.desc&limit=10", headers=headers)
    
    tasks_data = tasks_req.json() if tasks_req.status_code == 200 else []
    journals_data = journals_req.json() if journals_req.status_code == 200 else []
    
    t_str = [f"- {t.get('task_title')} (Done: {t.get('is_completed')})" for t in tasks_data]
    j_str = [f"- {j.get('summary')}" for j in journals_data]
    
    user_context = f"Tasks:\n{chr(10).join(t_str)}\n\nJournals:\n{chr(10).join(j_str)}"
    
    prompt = f"Analyze the user's focus and productivity strictly based on this data. Be objective. No fluff.\n\nData:\n{user_context}"
    
    payload = {
        "model": "llama3-8b-8192",  # NAYA LIVE MODEL YAHAN UPDATE KIYA HAI
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    
    groq_res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}"}, json=payload)
    if groq_res.status_code == 200:
        return {"status": "success", "analysis": groq_res.json()["choices"][0]["message"]["content"]}
    raise HTTPException(status_code=500, detail="Analysis failed")