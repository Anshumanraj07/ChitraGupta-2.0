"""
ChitraGupta 2.0 — Daily Review API Endpoint
Trigger and retrieve daily reviews.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from datetime import date

from core.daily_review import daily_review, DailyReviewInput, ReviewFocus, DailyTaskReview
from core.identity_model import identity_model
from core.behavioral_inference import behavioral_inference
from core.confidence_tracker import confidence_tracker
from core.utils.supabase_client import get_supabase_client
from datetime import timedelta
from typing import List

logger = logging.getLogger("chitragupta.review_endpoint")

router = APIRouter(prefix="/api/review", tags=["review"])


class ReviewRequest(BaseModel):
    user_id: str = "default_user"
    review_date: Optional[str] = None  # YYYY-MM-DD, defaults to today
    focus: ReviewFocus = ReviewFocus.DAILY_START


@router.post("/daily")
async def trigger_daily_review(request: ReviewRequest):
    """Trigger a daily review for the user."""
    try:
        review_date = date.fromisoformat(request.review_date) if request.review_date else date.today()
        
        # Get required context data
        identity_summary = identity_model.get_profile_summary()
        behavioral_summary = behavioral_inference.get_profile_summary()
        confidence_scores = confidence_tracker.get_all_scores()
        
        # Get active tasks and previous day tasks from Supabase
        active_tasks = await _get_active_tasks(request.user_id)
        previous_tasks = await _get_previous_day_tasks(request.user_id, review_date)
        streak_days = await _get_streak_days(request.user_id)
        
        input_data = DailyReviewInput(
            user_id=request.user_id,
            review_date=review_date,
            focus=request.focus,
            previous_tasks=[DailyTaskReview(**t) for t in previous_tasks],
            active_tasks=active_tasks,
            identity_profile=identity_summary,
            behavioral_profile=behavioral_summary,
            confidence_scores=confidence_scores,
            streak_days=streak_days,
        )
        
        output = daily_review.conduct_review(input_data)
        
        return {
            "review_date": output.review_date.isoformat(),
            "focus": output.focus.value,
            "completion_rate": output.completion_rate,
            "overall_assessment": output.overall_assessment,
            "key_insights": output.key_insights,
            "patterns_noticed": output.patterns_noticed,
            "task_decisions": output.task_decisions,
            "new_tasks": output.new_tasks,
            "coaching_strategy_adjustment": output.coaching_strategy_adjustment,
            "pacing_recommendation": output.pacing_recommendation,
            "focus_areas": output.focus_areas,
            "avoid_areas": output.avoid_areas,
            "identity_updates": output.identity_updates,
            "behavioral_updates": output.behavioral_updates,
            "confidence_adjustments": output.confidence_adjustments,
            "encouragement": output.encouragement,
            "warning_signals": output.warning_signals,
        }
    except Exception as e:
        logger.error(f"Daily review failed: {e}")
        return {"error": str(e)}


@router.get("/history")
async def get_review_history(user_id: str = "default_user", days: int = 30):
    """Get review history for the user."""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return {"reviews": []}
        
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        response = supabase.table("daily_reviews").select("*").eq("user_id", user_id).gte("review_date", cutoff).order("review_date", desc=True).execute()
        
        return {"reviews": response.data}
    except Exception as e:
        logger.error(f"Failed to get review history: {e}")
        return {"reviews": []}


async def _get_active_tasks(user_id: str) -> List[Dict[str, Any]]:
    """Get active tasks from Supabase."""
    try:
        supabase = get_supabase_client()
        if supabase:
            response = supabase.table("tasks").select("*").eq("user_id", user_id).neq("status", "completed").neq("status", "archived").execute()
            return response.data
    except Exception as e:
        logger.warning(f"Failed to get active tasks: {e}")
    return []


async def _get_previous_day_tasks(user_id: str, review_date: date) -> List[Dict[str, Any]]:
    """Get previous day's tasks from Supabase."""
    try:
        supabase = get_supabase_client()
        if supabase:
            prev_date = (review_date - timedelta(days=1)).isoformat()
            response = supabase.table("tasks").select("*").eq("user_id", user_id).eq("date", prev_date).execute()
            return response.data
    except Exception as e:
        logger.warning(f"Failed to get previous day tasks: {e}")
    return []


async def _get_streak_days(user_id: str) -> int:
    """Get current streak from Supabase."""
    try:
        supabase = get_supabase_client()
        if supabase:
            response = supabase.table("streaks").select("current_streak").eq("user_id", user_id).execute()
            if response.data:
                return response.data[0].get("current_streak", 0)
    except Exception as e:
        logger.warning(f"Failed to get streak: {e}")
    return 0