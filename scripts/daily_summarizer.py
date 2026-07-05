#!/usr/bin/env python3
"""
ChitraGupta 2.0 — Daily Rolling Summarizer
============================================
Standalone cron script that compresses raw chat messages from the last 24 hours
into a dense daily summary and stores it in the `daily_summaries` Supabase table.

Designed to run via:
  - Local cron / Windows Task Scheduler
  - GitHub Actions / Vercel Cron / Render Cron Job

Usage:
  python scripts/daily_summarizer.py

Environment Variables (required):
  SUPABASE_URL, SUPABASE_KEY, GOOGLE_API_KEY (or OPENROUTER_API_KEY as fallback)

Supabase Tables Required:
  - chats(id, user_id, role, content, created_at)
  - daily_summaries(id, user_id, summary_date, summary, dominant_emotion,
                     task_count, discipline_mental, discipline_physical,
                     key_topics, created_at)
"""

import json
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Bootstrap: add project root to sys.path so `core.` imports work
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from pydantic import BaseModel

from core.engine_shifter import ProviderRole, invoke_structured, AllProvidersExhaustedError

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("chitragupta.daily_summarizer")

# ---------------------------------------------------------------------------
# Pydantic Schema for Gemini output
# ---------------------------------------------------------------------------


class DailySummarySchema(BaseModel):
    """Structured output from the summarizer LLM call."""
    summary: str = ""
    dominant_emotion: str = "neutral"
    task_count: int = 0
    discipline_mental: float = 50.0
    discipline_physical: float = 50.0
    key_topics: list[str] = []


# ---------------------------------------------------------------------------
# Supabase Client
# ---------------------------------------------------------------------------

def _get_supabase():
    """Initialize and return a Supabase client."""
    from supabase import create_client, Client
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        logger.error("SUPABASE_URL or SUPABASE_KEY not set")
        return None
    return create_client(url, key)


# ---------------------------------------------------------------------------
# Summarizer Prompt
# ---------------------------------------------------------------------------

SUMMARIZER_SYSTEM_PROMPT = """You are the Daily Summarizer for ChitraGupta — a journal compression engine. You receive a full day's conversation between a user and an AI coach, and must produce a dense, structured summary.

Output a single JSON object with this EXACT schema:
{
  "summary": "<50-word dense summary of the day's conversations — key topics, emotional tone, decisions made>",
  "dominant_emotion": "<single word: anxious, ambitious, calm, frustrated, reflective, motivated, sad, neutral>",
  "task_count": <integer — number of distinct actionable tasks or goals discussed>,
  "discipline_mental": <float 0-100 — how disciplined mentally was the user today based on their messages>,
  "discipline_physical": <float 0-100 — how disciplined physically was the user today based on their messages>,
  "key_topics": ["<topic1>", "<topic2>", "<topic3>"]
}

RULES:
1. summary must be 50 words MAX — dense and information-rich.
2. dominant_emotion: pick the single most prevalent emotional tone.
3. task_count: count ONLY explicit actionable items discussed (not casual mentions).
4. discipline scores: 0 = no discipline at all, 100 = perfect discipline. Be realistic — most days are 40-70.
5. key_topics: 2-3 most recurring themes from the day's conversations.
6. Don't fabricate — only summarize what you can actually observe in the chat logs.
7. If the chat is very short or trivial, still produce a valid summary (even if brief).
"""


# ---------------------------------------------------------------------------
# Core Logic
# ---------------------------------------------------------------------------


def fetch_chats(supabase, user_id: str = "master", hours: int = 24) -> list[dict]:
    """Fetch raw chat messages from the last N hours for a given user."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    try:
        response = (
            supabase.table("chats")
            .select("role, content, created_at")
            .eq("user_id", user_id)
            .gte("created_at", cutoff)
            .order("created_at", desc=False)
            .execute()
        )
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Failed to fetch chats: {e}")
        return []


def format_chats_for_prompt(chats: list[dict]) -> str:
    """Format chat messages into a readable prompt block."""
    if not chats:
        return ""
    lines = []
    for chat in chats:
        role = "User" if chat.get("role") == "user" else "AI"
        content = chat.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def generate_summary(chat_text: str) -> DailySummarySchema:
    """Use EngineShifter (MEMORY role = Gemini) to compress chat into summary."""
    messages = [
        {"role": "system", "content": SUMMARIZER_SYSTEM_PROMPT},
        {"role": "user", "content": f"DAY'S CONVERSATION LOG:\n{chat_text}\n\nProduce the daily summary."},
    ]
    result = invoke_structured(ProviderRole.MEMORY, messages, DailySummarySchema)
    return result


def upsert_summary(supabase, summary: DailySummarySchema, user_id: str = "master") -> bool:
    """Insert or update the daily summary (idempotent via UPSERT)."""
    today = date.today().isoformat()
    row = {
        "user_id": user_id,
        "summary_date": today,
        "summary": summary.summary,
        "dominant_emotion": summary.dominant_emotion,
        "task_count": summary.task_count,
        "discipline_mental": summary.discipline_mental,
        "discipline_physical": summary.discipline_physical,
        "key_topics": summary.key_topics,
    }
    try:
        # UPSERT: insert on conflict (user_id, summary_date) update
        response = (
            supabase.table("daily_summaries")
            .upsert(row, on_conflict="user_id,summary_date")
            .execute()
        )
        logger.info(f"Upserted daily summary for {today}: emotion={summary.dominant_emotion}, tasks={summary.task_count}")
        return True
    except Exception as e:
        logger.error(f"Failed to upsert daily summary: {e}")
        return False


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------


def main():
    """Run the daily summarizer — intended for cron execution."""
    logger.info("=== ChitraGupta Daily Summarizer ===")

    supabase = _get_supabase()
    if not supabase:
        logger.error("Supabase client not available. Exiting.")
        sys.exit(1)

    # Step 1: Fetch raw chats from last 24 hours
    chats = fetch_chats(supabase, hours=24)
    if not chats:
        logger.warning("No chats found in the last 24 hours. Nothing to summarize.")
        sys.exit(0)

    logger.info(f"Fetched {len(chats)} chat messages from last 24 hours")

    # Step 2: Format chats for LLM prompt
    chat_text = format_chats_for_prompt(chats)
    if not chat_text.strip():
        logger.warning("Chat text is empty after formatting. Exiting.")
        sys.exit(0)

    # Step 3: Generate summary using EngineShifter (Gemini)
    try:
        summary = generate_summary(chat_text)
    except AllProvidersExhaustedError as e:
        logger.error(f"All providers exhausted for summary generation: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        sys.exit(1)

    # Step 4: Upsert summary into Supabase
    success = upsert_summary(supabase, summary)
    if success:
        logger.info(f"Daily summary complete: {summary.summary[:80]}...")
    else:
        logger.error("Failed to store daily summary")
        sys.exit(1)


if __name__ == "__main__":
    main()