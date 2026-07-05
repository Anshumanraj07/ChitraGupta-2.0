"""
ChitraGupta 2.0 — Daily Review Schemas
Day-start review loop for progress assessment and adaptation.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, date


class ReviewFocus(str, Enum):
    DAILY_START = "daily_start"
    DAILY_END = "daily_end"
    WEEKLY = "weekly"
    ON_DEMAND = "on_demand"


class TaskReviewStatus(str, Enum):
    COMPLETED = "completed"
    PARTIAL = "partial"
    MISSED = "missed"
    BLOCKED = "blocked"
    NOT_ATTEMPTED = "not_attempted"
    MODIFIED = "modified"


class DailyTaskReview(BaseModel):
    """Review of a single task for the day."""
    task_id: str
    task_title: str
    status: TaskReviewStatus
    completion_percentage: float = Field(ge=0.0, le=100.0, default=0.0)
    time_spent_minutes: Optional[int] = None
    what_worked: str = ""
    what_didnt_work: str = ""
    blocker: Optional[str] = None
    insight: str = ""
    should_retry: bool = False
    retry_modification: Optional[str] = None  # "reduce_scope", "extend_time", "change_approach"


class DailyReviewInput(BaseModel):
    """Input for daily review."""
    user_id: str
    review_date: date
    focus: ReviewFocus = ReviewFocus.DAILY_START
    
    # Previous day's tasks
    previous_tasks: List[DailyTaskReview] = Field(default_factory=list)
    
    # Current state
    active_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    identity_profile: Optional[Dict[str, Any]] = None
    behavioral_profile: Optional[Dict[str, Any]] = None
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    
    # Metrics
    streak_days: int = 0
    weekly_completion_rate: float = 0.0
    monthly_completion_rate: float = 0.0
    
    # Context
    energy_level: Optional[str] = None
    mood: Optional[str] = None
    sleep_quality: Optional[str] = None
    stress_level: Optional[str] = None


class DailyReviewOutput(BaseModel):
    """Output from daily review."""
    review_date: date
    focus: ReviewFocus
    
    # Summary
    overall_assessment: str = ""
    completion_rate: float = 0.0
    key_insights: List[str] = Field(default_factory=list)
    patterns_noticed: List[str] = Field(default_factory=list)
    
    # Task decisions
    task_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    # Each: {"task_id": "...", "action": "retry/modify/archive/continue", "modifications": {...}}
    
    # New tasks for today
    new_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Coaching adaptation
    coaching_strategy_adjustment: str = ""  # How to adapt today
    pacing_recommendation: str = "moderate"
    focus_areas: List[str] = Field(default_factory=list)
    avoid_areas: List[str] = Field(default_factory=list)
    
    # Identity/behavior updates
    identity_updates: List[Dict[str, Any]] = Field(default_factory=list)
    behavioral_updates: List[Dict[str, Any]] = Field(default_factory=list)
    confidence_adjustments: Dict[str, float] = Field(default_factory=dict)
    
    # Encouragement
    encouragement: str = ""
    warning_signals: List[str] = Field(default_factory=list)


class WeeklyReviewOutput(BaseModel):
    """Weekly review output (extends daily)."""
    week_start: date
    week_end: date
    daily_reviews: List[DailyReviewOutput] = Field(default_factory=list)
    
    # Aggregated
    total_tasks_completed: int = 0
    total_tasks_attempted: int = 0
    weekly_completion_rate: float = 0.0
    average_daily_tasks: float = 0.0
    
    # Patterns
    consistent_patterns: List[str] = Field(default_factory=list)
    emerging_patterns: List[str] = Field(default_factory=list)
    resolved_patterns: List[str] = Field(default_factory=list)
    
    # Goal progress
    goal_progress: Dict[str, float] = Field(default_factory=dict)
    # goal_area -> progress 0-1
    
    # Recommendations
    next_week_focus: List[str] = Field(default_factory=list)
    strategy_changes: List[str] = Field(default_factory=list)
    identity_shifts: List[str] = Field(default_factory=list)