import os
import json
import requests
import re

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
    Output ONLY valid JSON. No extra text, no markdown.
    If task format: {{"type": "task", "task_title": "Title", "category": "Dev", "priority": "Medium", "sub_tasks": [{{"title": "Step 1", "is_completed": false}}], "chitragupt_wisdom": "Tip"}}
    If journal format: {{"type": "journal", "mood": "Focused", "summary": "Insight"}}
    
    User Input: {user_input}
    """

    payload = {
        "model": "llama3-70b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            text = response.json()["choices"][0]["message"]["content"].strip()
            match = re.search(r'\{.*\}', text, re.DOTALL)
            clean_json = match.group(0) if match else text
            return json.loads(clean_json)
        else:
            # Agar Groq API ka koi error hai (jaise 401 ya 429) toh wo title me dikhega
            return {
                "type": "task", 
                "task_title": f"API FAILED: Code {response.status_code}", 
                "chitragupt_wisdom": response.text[:150]
            }
            
    except Exception as e:
        # Agar JSON decode ya timeout error hai, toh wo yahan dikhega
        return {
            "type": "task", 
            "task_title": f"PYTHON CRASH: {str(e)}", 
            "category": "Error"
        }