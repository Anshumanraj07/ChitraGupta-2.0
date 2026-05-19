import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def parse_user_input(user_text: str):
    system_prompt = """
    You are ChitraGupt 2.0, an advanced Agentic AI. You act as a divine karma accountant and a philosophical observer.
    Analyze the user's input and logically classify it.
    
    - If the input contains ANY actionable item, work, or plan, classify it as "task".
    - If the input is purely a thought, emotion, rant, or reflection with no clear action, classify it as "journal".

    Respond ONLY with a valid JSON object matching one of the schemas below.

    SCHEMA 1 (If type is "task"):
    {
        "type": "task",
        "task_title": "A short, actionable title in English",
        "category": "One word category",
        "priority": "High, Medium, or Low",
        "estimated_time": "Time estimate",
        "chitragupt_wisdom": "A witty, slightly detached one-liner in Hindi/Hinglish",
        "sub_tasks": [
            {"title": "step 1", "is_completed": false}
        ]
    }

    SCHEMA 2 (If type is "journal"):
    {
        "type": "journal",
        "mood": "Detect the emotional state (e.g., Detached, Overwhelmed, Focused)",
        "summary": "A 1-2 sentence clear summary of what the user is feeling or thinking",
        "philosophical_insight": "Deep, grounding advice in Hindi/Hinglish drawing from Stoicism or Osho (Zorba the Buddha) to help the user maintain conscious individuality."
    }
    """

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"}
        )
        
        json_data = json.loads(response.choices[0].message.content)
        return json_data

    except Exception as e:
        print(f"Brain parsing error: {e}")
        return {
            "type": "journal",
            "mood": "Confused",
            "summary": "The system failed to parse the complexity of your thoughts.",
            "philosophical_insight": "Jab system crash ho jaye, toh samajh lo thoda theherne ka waqt aa gaya hai. Breathe."
        }