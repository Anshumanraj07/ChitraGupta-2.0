"""
ChitraGupta 2.0 — Task Quality Engine Schemas
Reasoning-driven task generation with full justification.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta


class TaskType(str, Enum):
    MICRO = "micro"           # < 15 min, single action
    HABIT = "habit"           # Recurring, behavior-building
    PROJECT = "project"       # Multi-step, > 1 hour
    REVIEW = "review"         # Reflection, assessment
    EXPERIMENT = "experiment" # Try something new, low stakes
    RECOVERY = "recovery"     # After failure/setback


class TaskPriority(str, Enum):
    CRITICAL = "critical"     # Must do today
    HIGH = "high"             # Important, soon
    MEDIUM = "medium"         # Normal priority
    LOW = "low"               # When time permits
    OPTIONAL = "optional"     # Nice to have


class TaskDifficulty(str, Enum):
    TRIVIAL = "trivial"       # Almost no effort
    EASY = "easy"             # Low effort
    MODERATE = "moderate"     # Some effort
    CHALLENGING = "challenging" # Significant effort
    DIFFICULT = "difficult"   # High effort


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    ABANDONED = "abandoned"
    ARCHIVED = "archived"


class QualityTask(BaseModel):
    """A high-quality, reasoning-driven task."""
    id: Optional[str] = None
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Core task
    title: str
    description: str = ""
    task_type: TaskType = TaskType.MICRO
    priority: TaskPriority = TaskPriority.MEDIUM
    difficulty: TaskDifficulty = TaskDifficulty.EASY
    
    # Reasoning (REQUIRED - no template spam)
    reason: str  # Why this task, why now, what it addresses
    expected_outcome: str  # What changes if completed
    success_criteria: List[str] = Field(default_factory=list)  # Measurable completion signals
    
    # Execution details
    estimated_duration_minutes: int = Field(ge=1, le=480)
    micro_steps: List[str] = Field(default_factory=list)  # Atomic steps
    dependencies: List[str] = Field(default_factory=list)  # Other task IDs
    
    # Adaptive fields
    review_condition: str = ""  # When to review: "end_of_day", "after_completion", "if_blocked"
    adaptation_strategy: str = ""  # What to do if failed: "reduce_scope", "extend_time", "change_approach", "archive"
    max_retries: int = 2
    retry_count: int = 0
    
    # Context
    goal_area: str = ""  # fitness, career, mental_health, learning, etc.
    discipline: str = "mental"  # mental, physical, both
    coaching_strategy: str = ""  # Which strategy generated this
    
    # State
    status: TaskStatus = TaskStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    blocked_reason: Optional[str] = None
    actual_duration_minutes: Optional[int] = None
    
    # Quality signals
    user_commitment_level: float = Field(default=0.5, ge=0.0, le=1.0)
    generated_confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    alignment_score: float = Field(default=0.0, ge=0.0, le=1.0)  # Aligns with goals/identity
    
    # Feedback
    completion_notes: str = ""
    difficulty_rating: Optional[int] = Field(default=None, ge=1, le=5)
    value_rating: Optional[int] = Field(default=None, ge=1, le=5)


class TaskGenerationRequest(BaseModel):
    """Request for task generation with full context."""
    user_id: str
    goal: str
    goal_area: str = ""
    struggle: Optional[str] = None
    habit: Optional[str] = None
    routine: Optional[str] = None
    roadmap: Optional[str] = None
    
    # Identity & behavior context
    identity_profile: Optional[Dict[str, Any]] = None
    behavioral_profile: Optional[Dict[str, Any]] = None
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    
    # Current state
    active_tasks: List[QualityTask] = Field(default_factory=list)
    completed_today: int = 0
    missed_today: int = 0
    energy_level: Optional[str] = None  # high, medium, low
    time_available_minutes: Optional[int] = None
    
    # Preferences
    preferred_task_type: Optional[TaskType] = None
    max_difficulty: Optional[TaskDifficulty] = None
    coaching_strategy: str = "balanced"
    
    # Constraints
    max_tasks_to_generate: int = 1
    avoid_goal_areas: List[str] = Field(default_factory=list)


class TaskGenerationResult(BaseModel):
    """Result of task generation."""
    tasks: List[QualityTask] = Field(default_factory=list)
    reasoning: str = ""
    strategy_used: str = ""
    confidence: float = Field(ge=0.0, le=1.0)
    rejected_candidates: List[Dict[str, Any]] = Field(default_factory=list)
    # Each: {"title": "...", "reason_rejected": "..."}


class TaskReviewResult(BaseModel):
    """Result of task review (daily or on-demand)."""
    task_id: str
    action: str  # "continue", "modify", "retry", "archive", "split", "merge"
    reasoning: str
    modifications: Dict[str, Any] = Field(default_factory=dict)
    # e.g., {"difficulty": "easy", "micro_steps": ["..."], "estimated_duration": 10}
    new_tasks: List[QualityTask] = Field(default_factory=list)