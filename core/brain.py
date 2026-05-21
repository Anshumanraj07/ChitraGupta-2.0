import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def parse_user_input(user_input: str) -> dict:
    """
    Parses raw user input using Groq's Llama-3 model and returns a structured dictionary.
    Accurately routes the input as either an actionable 'task' or a reflective 'journal'.
    """
    if not GROQ_API_KEY:
        print("Error: GROQ_API_KEY not found in environment variables.")
        return {
            "type": "task", 
            "task_title": user_input, 
            "category": "General", 
            "priority": "Medium", 
            "sub_tasks": [], 
            "chitragupt_wisdom": "API key missing. Logged as raw task."
        }

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    You are the core intelligence engine for ChitraGupta.
    Analyze the user input and return a STRICT JSON output. 
    Do not include any conversational text or markdown code block wrappers (like ```json). Just raw JSON.

    If the input is an actionable task, reminder, or to-do:
    {{
        "type": "task",
        "task_title": "Clear and concise title explaining the core objective",
        "category": "Development/Life/Academic/Routine",
        "priority": "High/Medium/Low",
        "sub_tasks": [
            {{"title": "Sub task 1", "is_completed": false}},
            {{"title": "Sub task 2", "is_completed": false}}
        ],
        "chitragupt_wisdom": "One sharp, practical line about this task's execution or a technical tip."
    }}

    If the input is a thought, rant, feeling, or reflection (Journal):
    {{
        "type": "journal",
        "mood": "Objective assessment of mood (e.g., Focused, Anxious, Reflective, Idle)",
        "summary": "Provide a sharp, R&D or analytical insight based on the input. Look for engineering patterns, data points, logical gaps, behavior trends, or development opportunities. Strictly NO philosophical fluff."
    }}

    User Input: {user_input}
    """

    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {
                "role": "system", 
                "content": "You are a precise backend AI agent that outputs ONLY valid raw JSON objects matching the requested schema. No conversational filler, no markdown formatting."
            },
            {
                "role": "user", 
                "content": prompt
            }
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=12)
        if response.status_code == 200:
            result_json = response.json()["choices"][0]["message"]["content"]
            return json.loads(result_json)
        else:
            print(f"Groq API Error: {response.status_code} - {response.text}")
            return {
                "type": "task", 
                "task_title": user_input, 
                "category": "General", 
                "priority": "Medium", 
                "sub_tasks": [], 
                "chitragupt_wisdom": "AI parsing failed due to API status error."
            }
    except Exception as e:
        print(f"Exception during ChitraGupta AI parsing: {str(e)}")
        return {
            "type": "task", 
            "task_title": user_input, 
            "category": "General", 
            "priority": "Medium", 
            "sub_tasks": [], 
            "chitragupt_wisdom": "AI parsing failed due to internal exception."
        }