"""
ChitraGupta 2.0 — Karma/Summary API Endpoint
Real data from Supabase, no mock data.
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Header
from datetime import datetime, timedelta

from core.utils.supabase_client import get_supabase_client
from core.user_registry import DEFAULT_USER_ID

logger = logging.getLogger("chitragupta.karma_endpoint")

router = APIRouter(prefix="/api", tags=["karma"])


def _resolve_user_id(user_id: Optional[str], x_user_id: Optional[str]) -> str:
    uid = (user_id or "").strip() or (x_user_id or "").strip() or DEFAULT_USER_ID
    return uid


@router.get("/karma")
async def get_karma(user_id: Optional[str] = None, x_user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    """Get comprehensive karma analytics (user-scoped)."""
    try:
        user_id = _resolve_user_id(user_id, x_user_id)
        supabase = get_supabase_client()
        if not supabase:
            return _empty_karma()
        
        # Get daily summaries from last 90 days
        cutoff = (datetime.utcnow() - timedelta(days=90)).isoformat()
        response = supabase.table("daily_summaries").select("*").eq("user_id", user_id).gte("date", cutoff).order("date", desc=True).execute()
        
        daily_summaries = response.data
        
        if not daily_summaries:
            return _empty_karma()
        
        # Calculate comprehensive metrics
        total_days = len(daily_summaries)
        total_karma = sum(d.get("karma", 0) for d in daily_summaries)
        avg_karma = total_karma / total_days if total_days > 0 else 0
        
        # Completion rates
        total_tasks = sum(d.get("tasks_completed", 0) + d.get("tasks_missed", 0) for d in daily_summaries)
        completed_tasks = sum(d.get("tasks_completed", 0) for d in daily_summaries)
        completion_rate = completed_tasks / total_tasks if total_tasks > 0 else 0
        
        # Streaks
        current_streak = _calculate_current_streak(daily_summaries)
        longest_streak = _calculate_longest_streak(daily_summaries)
        
        # Weekly trend (last 12 weeks)
        weekly_data = _calculate_weekly_trends(daily_summaries)
        
        # Monthly trend
        monthly_data = _calculate_monthly_trends(daily_summaries)
        
        # Completion heatmap data
        heatmap = _calculate_heatmap(daily_summaries)
        
        # Goal area breakdown
        goal_areas = {}
        for d in daily_summaries:
            for goal in d.get("goals_addressed", []):
                goal_areas[goal] = goal_areas.get(goal, 0) + 1
        
        # Habit evolution
        habit_evolution = _calculate_habit_evolution(daily_summaries)
        
        # Behavior evolution
        behavior_evolution = _calculate_behavior_evolution(daily_summaries)
        
        return {
            "user_id": user_id,
            "overview": {
                "total_karma": total_karma,
                "average_daily_karma": round(avg_karma, 1),
                "current_streak_days": current_streak,
                "longest_streak_days": longest_streak,
                "completion_rate": round(completion_rate * 100, 1),
                "total_tasks_completed": completed_tasks,
                "total_tasks_attempted": total_tasks,
                "days_tracked": total_days,
            },
            "weekly_trends": weekly_data,
            "monthly_trends": monthly_data,
            "completion_heatmap": heatmap,
            "goal_areas": goal_areas,
            "habit_evolution": habit_evolution,
            "behavior_evolution": behavior_evolution,
            "last_updated": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get karma: {e}")
        return _empty_karma()


@router.get("/karma-summary")
async def get_karma_summary(user_id: Optional[str] = None, x_user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    """Get karma summary with real data from Supabase (user-scoped)."""
    try:
        user_id = _resolve_user_id(user_id, x_user_id)
        supabase = get_supabase_client()
        if not supabase:
            return _empty_summary()
        
        # Get daily summaries from last 30 days
        cutoff = (datetime.utcnow() - timedelta(days=30)).isoformat()
        response = supabase.table("daily_summaries").select("*").eq("user_id", user_id).gte("date", cutoff).order("date", desc=True).execute()
        
        daily_summaries = response.data
        
        if not daily_summaries:
            return _empty_summary()
        
        # Calculate metrics
        total_days = len(daily_summaries)
        total_karma = sum(d.get("karma", 0) for d in daily_summaries)
        avg_karma = total_karma / total_days if total_days > 0 else 0
        
        # Completion rates
        total_tasks = sum(d.get("tasks_completed", 0) + d.get("tasks_missed", 0) for d in daily_summaries)
        completed_tasks = sum(d.get("tasks_completed", 0) for d in daily_summaries)
        completion_rate = completed_tasks / total_tasks if total_tasks > 0 else 0
        
        # Streaks
        current_streak = _calculate_current_streak(daily_summaries)
        longest_streak = _calculate_longest_streak(daily_summaries)
        
        # Recent trend (last 7 days)
        recent = daily_summaries[:7]
        recent_karma = sum(d.get("karma", 0) for d in recent) / len(recent) if recent else 0
        previous_karma = sum(d.get("karma", 0) for d in daily_summaries[7:14]) / 7 if len(daily_summaries) > 7 else recent_karma
        trend = "up" if recent_karma > previous_karma else "down" if recent_karma < previous_karma else "stable"
        
        # Goal area breakdown
        goal_areas = {}
        for d in daily_summaries:
            for goal in d.get("goals_addressed", []):
                goal_areas[goal] = goal_areas.get(goal, 0) + 1
        
        return {
            "user_id": user_id,
            "total_karma": total_karma,
            "average_daily_karma": round(avg_karma, 1),
            "current_streak_days": current_streak,
            "longest_streak_days": longest_streak,
            "completion_rate": round(completion_rate * 100, 1),
            "total_tasks_completed": completed_tasks,
            "total_tasks_attempted": total_tasks,
            "recent_trend": trend,
            "recent_avg_karma": round(recent_karma, 1),
            "goal_areas": goal_areas,
            "days_tracked": total_days,
            "last_updated": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get karma summary: {e}")
        return _empty_summary()


@router.get("/daily-summaries")
async def get_daily_summaries(user_id: Optional[str] = None, days: int = 30, x_user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    """Get daily summaries for the specified period (user-scoped)."""
    try:
        user_id = _resolve_user_id(user_id, x_user_id)
        supabase = get_supabase_client()
        if not supabase:
            return {"summaries": []}
        
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        response = supabase.table("daily_summaries").select("*").eq("user_id", user_id).gte("date", cutoff).order("date", desc=True).execute()
        
        return {"summaries": response.data, "user_id": user_id}
    except Exception as e:
        logger.error(f"Failed to get daily summaries: {e}")
        return {"summaries": []}


@router.get("/weekly-summary")
async def get_weekly_summary(user_id: Optional[str] = None, x_user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    """Get aggregated weekly summary (user-scoped)."""
    try:
        user_id = _resolve_user_id(user_id, x_user_id)
        supabase = get_supabase_client()
        if not supabase:
            return _empty_weekly()
        
        cutoff = (datetime.utcnow() - timedelta(weeks=4)).isoformat()
        response = supabase.table("daily_summaries").select("*").eq("user_id", user_id).gte("date", cutoff).order("date").execute()
        
        daily_summaries = response.data
        
        if not daily_summaries:
            return _empty_weekly()
        
        # Group by week
        weeks = {}
        for d in daily_summaries:
            date_obj = datetime.fromisoformat(d["date"])
            week_start = date_obj - timedelta(days=date_obj.weekday())
            week_key = week_start.date().isoformat()
            
            if week_key not in weeks:
                weeks[week_key] = {
                    "week_start": week_key,
                    "days": 0,
                    "karma": 0,
                    "completed": 0,
                    "attempted": 0,
                }
            
            weeks[week_key]["days"] += 1
            weeks[week_key]["karma"] += d.get("karma", 0)
            weeks[week_key]["completed"] += d.get("tasks_completed", 0)
            weeks[week_key]["attempted"] += d.get("tasks_completed", 0) + d.get("tasks_missed", 0)
        
        week_list = list(weeks.values())
        week_list.sort(key=lambda x: x["week_start"])
        
        return {
            "weeks": week_list,
            "total_weeks": len(week_list),
        }
    except Exception as e:
        logger.error(f"Failed to get weekly summary: {e}")
        return _empty_weekly()


def _calculate_current_streak(summaries: List[Dict]) -> int:
    """Calculate current completion streak."""
    streak = 0
    for d in summaries:
        if d.get("tasks_completed", 0) > 0:
            streak += 1
        else:
            break
    return streak


def _calculate_longest_streak(summaries: List[Dict]) -> int:
    """Calculate longest completion streak."""
    longest = 0
    current = 0
    for d in reversed(summaries):  # Oldest first
        if d.get("tasks_completed", 0) > 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _empty_summary() -> Dict[str, Any]:
    return {
        "user_id": DEFAULT_USER_ID,
        "total_karma": 0,
        "average_daily_karma": 0,
        "current_streak_days": 0,
        "longest_streak_days": 0,
        "completion_rate": 0,
        "total_tasks_completed": 0,
        "total_tasks_attempted": 0,
        "recent_trend": "stable",
        "recent_avg_karma": 0,
        "goal_areas": {},
        "days_tracked": 0,
        "last_updated": datetime.utcnow().isoformat(),
    }


def _empty_weekly() -> Dict[str, Any]:
    return {
        "weeks": [],
        "total_weeks": 0,
    }


def _empty_karma() -> Dict[str, Any]:
    return {
        "user_id": DEFAULT_USER_ID,
        "overview": {
            "total_karma": 0,
            "average_daily_karma": 0,
            "current_streak_days": 0,
            "longest_streak_days": 0,
            "completion_rate": 0,
            "total_tasks_completed": 0,
            "total_tasks_attempted": 0,
            "days_tracked": 0,
        },
        "weekly_trends": [],
        "monthly_trends": [],
        "completion_heatmap": {},
        "goal_areas": {},
        "habit_evolution": [],
        "behavior_evolution": [],
        "last_updated": datetime.utcnow().isoformat(),
    }


def _calculate_weekly_trends(summaries: List[Dict]) -> List[Dict]:
    """Calculate weekly karma trends for last 12 weeks."""
    from collections import defaultdict
    weeks = defaultdict(lambda: {"karma": 0, "completed": 0, "attempted": 0, "days": 0})
    
    for d in summaries:
        date_obj = datetime.fromisoformat(d["date"])
        week_start = date_obj - timedelta(days=date_obj.weekday())
        week_key = week_start.date().isoformat()
        
        weeks[week_key]["karma"] += d.get("karma", 0)
        weeks[week_key]["completed"] += d.get("tasks_completed", 0)
        weeks[week_key]["attempted"] += d.get("tasks_completed", 0) + d.get("tasks_missed", 0)
        weeks[week_key]["days"] += 1
    
    # Get last 12 weeks
    sorted_weeks = sorted(weeks.items(), key=lambda x: x[0], reverse=True)[:12]
    return [
        {
            "week_start": week,
            "karma": data["karma"],
            "completed": data["completed"],
            "attempted": data["attempted"],
            "completion_rate": round(data["completed"] / data["attempted"] * 100, 1) if data["attempted"] > 0 else 0,
        }
        for week, data in reversed(sorted_weeks)
    ]


def _calculate_monthly_trends(summaries: List[Dict]) -> List[Dict]:
    """Calculate monthly karma trends."""
    from collections import defaultdict
    months = defaultdict(lambda: {"karma": 0, "completed": 0, "attempted": 0, "days": 0})
    
    for d in summaries:
        date_obj = datetime.fromisoformat(d["date"])
        month_key = date_obj.strftime("%Y-%m")
        
        months[month_key]["karma"] += d.get("karma", 0)
        months[month_key]["completed"] += d.get("tasks_completed", 0)
        months[month_key]["attempted"] += d.get("tasks_completed", 0) + d.get("tasks_missed", 0)
        months[month_key]["days"] += 1
    
    sorted_months = sorted(months.items(), key=lambda x: x[0])
    return [
        {
            "month": month,
            "karma": data["karma"],
            "completed": data["completed"],
            "attempted": data["attempted"],
            "avg_daily_karma": round(data["karma"] / data["days"], 1) if data["days"] > 0 else 0,
        }
        for month, data in sorted_months
    ]


def _calculate_heatmap(summaries: List[Dict]) -> Dict[str, int]:
    """Generate completion heatmap data (date -> completed count)."""
    heatmap = {}
    for d in summaries:
        date_str = d.get("date", "")
        if date_str:
            heatmap[date_str] = d.get("tasks_completed", 0)
    return heatmap


def _calculate_habit_evolution(summaries: List[Dict]) -> List[Dict]:
    """Track habit evolution over time."""
    from collections import defaultdict
    habit_counts = defaultdict(lambda: defaultdict(int))
    
    for d in summaries:
        date_obj = datetime.fromisoformat(d["date"])
        week_key = (date_obj - timedelta(days=date_obj.weekday())).date().isoformat()
        
        for goal in d.get("goals_addressed", []):
            habit_counts[week_key][goal] += 1
    
    # Convert to evolution format
    sorted_weeks = sorted(habit_counts.keys())
    evolution = []
    for week in sorted_weeks:
        for habit, count in habit_counts[week].items():
            evolution.append({
                "week": week,
                "habit": habit,
                "count": count,
            })
    return evolution


def _calculate_behavior_evolution(summaries: List[Dict]) -> List[Dict]:
    """Track behavior pattern evolution over time."""
    from collections import defaultdict
    behavior_counts = defaultdict(lambda: defaultdict(int))
    
    for d in summaries:
        date_obj = datetime.fromisoformat(d["date"])
        week_key = (date_obj - timedelta(days=date_obj.weekday())).date().isoformat()
        
        # Track behavioral patterns from metadata
        for pattern in d.get("behavior_patterns", []):
            behavior_counts[week_key][pattern] += 1
    
    sorted_weeks = sorted(behavior_counts.keys())
    evolution = []
    for week in sorted_weeks:
        for behavior, count in behavior_counts[week].items():
            evolution.append({
                "week": week,
                "behavior": behavior,
                "count": count,
            })
    return evolution
