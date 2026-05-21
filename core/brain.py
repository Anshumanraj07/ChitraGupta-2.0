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

    system_prompt = "You are a precise data extraction agent. You output ONLY raw valid JSON. No markdown codeblocks, no conversational text."
    
    # Prompt ko instructions-based banaya taaki AI copy-paste na kare
    user_prompt = f"""
    Analyze the USER INPUT provided below and categorize it into either a 'task' or a 'journal'.
    
    USER INPUT: "{user_input}"
    
    Instructions for routing:
    1. If the input contains an action item, plan, reminder, or to-do, treat it as a 'task'.
    2. If the input is just a thought, rant, log, or emotion with no immediate action, treat it as a 'journal'.

    Strict Output Schema Requirements:
    
    If it is a 'task', generate a JSON object where you must replace the instruction strings with real data from the user input:
    {{
        "type": "task",
        "task_title": "Write a short, clear objective title based on the user input",
        "category": "Classify into Action, Dev, Routine, or Life",
        "priority": "High, Medium, or Low based on urgency",
        "sub_tasks": [
            {{"title": "Create a small, bite-sized actionable sub-task broken down from the main input", "is_completed": false}}
        ],
        "chitragupt_wisdom": "Write one sharp, unique technical execution tip specific to this task"
    }}

    If it is a 'journal', generate a JSON object where you analyze the user input:
    {{
        "type": "journal",
        "mood": "Identify the objective mood from the text (e.g., Focused, Overwhelmed, Idle)",
        "summary": "Provide a sharp, development-focused analytical or R&D insight about this entry. Do not write philosophy or fluff."
    }}
    
    Generate only the final JSON object. Do not wrap in ```json.
    """

    payload = {
        "model": "llama-3.1-8b-instant", 
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
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