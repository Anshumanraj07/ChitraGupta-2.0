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

    # Fixing the 400 Error: Groq STRICTLY needs the word 'JSON' in the system prompt.
    system_prompt = "You are a data processor. You must output ONLY valid JSON. No conversational text. No markdown blockquotes."
    
    user_prompt = f"""
    Analyze the input and return a JSON object exactly like this:
    
    If the input is an actionable task, to-do, or reminder:
    {{
        "type": "task",
        "task_title": "Clear actionable title",
        "category": "Action",
        "priority": "Medium",
        "sub_tasks": [
            {{"title": "Action step 1", "is_completed": false}}
        ],
        "chitragupt_wisdom": "One sharp execution tip or insight about this task."
    }}

    If the input is a thought, feeling, or reflection (Journal):
    {{
        "type": "journal",
        "mood": "Objective Mood",
        "summary": "Sharp, analytical or R&D insight based on the input. No fluff."
    }}
    
    User Input: {user_input}
    """

    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            text = response.json()["choices"][0]["message"]["content"].strip()
            # Failsafe regex to extract JSON if AI adds extra characters
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