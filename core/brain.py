import os
import json
import requests
import re
from dotenv import load_dotenv

load_dotenv()

def parse_user_input(user_input: str) -> dict:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

    if not GROQ_API_KEY:
        return {
            "type": "task", 
            "task_title": "ERROR: Render pe GROQ_API_KEY missing hai", 
            "category": "Error", 
            "priority": "High"
        }

    url = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    Output ONLY a valid JSON object. Do not add any markdown formatting.
    If task format: {{"type": "task", "task_title": "Title", "category": "Dev", "priority": "Medium", "sub_tasks": [{{"title": "Step 1", "is_completed": false}}], "chitragupt_wisdom": "Tip"}}
    If journal format: {{"type": "journal", "mood": "Focused", "summary": "Insight"}}
    
    User Input: {user_input}
    """

    payload = {
        # Llama 3 ka naya aur zyada fast model jo error nahi deta
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": "You are a JSON-only processor. Output strictly JSON formatting."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            text = response.json()["choices"][0]["message"]["content"].strip()
            match = re.search(r'\{.*\}', text, re.DOTALL)
            clean_json = match.group(0) if match else text
            return json.loads(clean_json)
        else:
            # Error reason nikal kar bhej rahe hain taaki exactly pata chale
            try:
                err_msg = response.json().get("error", {}).get("message", response.text)
            except:
                err_msg = response.text
                
            return {
                "type": "task", 
                "task_title": f"API FAILED: Code {response.status_code}", 
                "chitragupt_wisdom": err_msg[:200]
            }
            
    except Exception as e:
        return {
            "type": "task", 
            "task_title": f"PYTHON CRASH", 
            "category": "Error",
            "chitragupt_wisdom": str(e)[:200]
        }