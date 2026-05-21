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
            "task_title": "ERROR: GROQ_API_KEY missing", 
            "category": "Error", 
            "priority": "High",
            "sub_tasks": [],
            "chitragupt_wisdom": "Check Render environment variables."
        }

    url = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    # System prompt ko aur strict banaya
    system_prompt = "You are a strict data router. You output ONLY JSON. No explanations, no markdown."
    
    # 8B Model ke liye naya dumb-proof prompt
    user_prompt = f"""
    You must categorize the following user input into EXACTLY ONE of two types: 'task' OR 'journal'.
    
    USER INPUT: "{user_input}"
    
    RULE 1: If the input contains ANY action item, to-do, reminder, or plan, you MUST format it as a task:
    {{
        "type": "task",
        "task_title": "Clear action title",
        "category": "Action",
        "priority": "Medium",
        "sub_tasks": [{{"title": "Step 1", "is_completed": false}}],
        "chitragupt_wisdom": "Execution tip"
    }}
    
    RULE 2: ONLY if the input is a pure thought, emotion, or rant with NO action required, format it as a journal:
    {{
        "type": "journal",
        "mood": "Objective Mood",
        "summary": "Analytical insight"
    }}
    
    Return exactly ONE JSON object based on the rules. Do not merge them.
    """

    payload = {
        "model": "llama-3.1-8b-instant", 
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,  # Temperature kam kiya taaki hallucinate na kare
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
            return {
                "type": "task", 
                "task_title": f"API ERROR {response.status_code}", 
                "category": "Error",
                "priority": "High",
                "sub_tasks": [],
                "chitragupt_wisdom": f"Groq Error: {response.text[:150]}"
            }
    except Exception as e:
        return {
            "type": "task", 
            "task_title": "SYSTEM CRASH", 
            "category": "Error",
            "priority": "High",
            "sub_tasks": [],
            "chitragupt_wisdom": f"Python Error: {str(e)[:150]}"
        }