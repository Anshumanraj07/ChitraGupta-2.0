import os
import json
import requests
import re
from dotenv import load_dotenv

load_dotenv()

def parse_user_input(user_input: str) -> dict:
    # Function ke andar load kar rahe hain taaki hamesha fresh API key pick ho
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

    fallback_response = {
        "type": "task", 
        "task_title": f"[AI FAILED] {user_input}", 
        "category": "General", 
        "priority": "Medium", 
        "sub_tasks": [], 
        "chitragupt_wisdom": "System bypassed AI to save your data."
    }

    if not GROQ_API_KEY:
        print("Error: GROQ_API_KEY not found.")
        return fallback_response

    url = "[https://api.groq.com/openai/v1/chat/completions](https://api.groq.com/openai/v1/chat/completions)"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    You are the core intelligence engine for ChitraGupta.
    Analyze the user input and return STRICTLY a valid JSON object. 
    DO NOT wrap the output in markdown block quotes (like ```json). Just start with {{ and end with }}.

    If the input is an actionable task, reminder, or to-do:
    {{
        "type": "task",
        "task_title": "Clear title of the action",
        "category": "Development",
        "priority": "Medium",
        "sub_tasks": [
            {{"title": "Step 1", "is_completed": false}}
        ],
        "chitragupt_wisdom": "One practical execution tip."
    }}

    If the input is a thought, feeling, or reflection (Journal):
    {{
        "type": "journal",
        "mood": "Objective Mood",
        "summary": "Provide a sharp, R&D or analytical insight based on the input. Strictly NO philosophical fluff."
    }}

    User Input: {user_input}
    """

    payload = {
        "model": "llama3-70b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            result_text = response.json()["choices"][0]["message"]["content"].strip()
            
            # Regex to extract only the JSON part, ignoring any AI bakchodi
            match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if match:
                clean_json = match.group(0)
                return json.loads(clean_json)
            else:
                return json.loads(result_text)
                
        else:
            print(f"Groq API Error {response.status_code}: {response.text}")
            return fallback_response
            
    except Exception as e:
        print(f"Exception parsing ChitraGupta AI: {str(e)}")
        return fallback_response