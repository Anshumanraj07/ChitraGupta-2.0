"""
ChitraGupta 2.0 — Policy Engine Schemas
Deterministic action selection before LLM calls.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class PolicyAction(str, Enum):
    """Available policy actions the system can take."""
    ASK_QUESTION = "ask_question"
    REFLECT = "reflect"
    SUMMARIZE = "summarize"
    EXPLORE_GOAL = "explore_goal"
    EXPLORE_CONSTRAINT = "explore_constraint"
    EXPLORE_HABIT = "explore_habit"
    EXPLORE_IDENTITY = "explore_identity"
    PLAN = "plan"
    GENERATE_TASK = "generate_task"
    REVIEW_TASK = "review_task"
    CHECK_PROGRESS = "check_progress"
    END_SESSION = "end_session"
    WAIT = "wait"


class ConversationPhase(str, Enum):
    """Conversation phases for policy decisions."""
    ONBOARDING = "onboarding"
    DISCOVERY = "discovery"
    GOAL_CLARIFICATION = "goal_clarification"
    PLANNING = "planning"
    EXECUTION = "execution"
    REVIEW = "review"
    DAILY_REVIEW = "daily_review"
    ADAPTATION = "adaptation"


class PolicyContext(BaseModel):
    """Context passed to policy engine for decision making."""
    user_id: str = "default_user"
    conversation_state: str = "onboarding"
    conversation_count: int = 0
    
    # Confidence scores (0.0 - 1.0)
    goal_clarity: float = 0.0
    constraint_clarity: float = 0.0
    habit_clarity: float = 0.0
    identity_clarity: float = 0.0
    motivation_clarity: float = 0.0
    routine_clarity: float = 0.0
    readiness_for_action: float = 0.0
    trust_rapport: float = 0.0
    conversation_depth: float = 0.0
    
    # Behavioral signals
    behavioral_patterns: List[str] = []
    behavioral_confidences: Dict[str, float] = {}
    
    # Task state
    active_tasks: int = 0
    completed_today: int = 0
    missed_today: int = 0
    blocked_tasks: int = 0
    unresolved_task_count: int = 0
    
    # User progress
    streak_days: int = 0
    recent_completion_rate: float = 0.0
    consistency_score: float = 0.0
    
    # Memory context
    has_relevant_memory: bool = False
    memory_summary: str = ""
    rolling_memory_available: bool = False
    
    # Current session
    session_start_time: Optional[datetime] = None
    last_action: Optional[str] = None
    last_action_time: Optional[datetime] = None
    
    # Identity
    has_identity_profile: bool = False
    identity_version: int = 0
    
    # Coaching
    coaching_strategy: Optional[str] = None
    pacing: Optional[str] = None
    
    # Behavioral scores (for rule evaluation)
    procrastination_score: float = 0.0
    avoidance_score: float = 0.0
    perfectionism_score: float = 0.0
    burnout_risk: float = 0.0
    momentum_score: float = 0.0
    follow_through_score: float = 0.0
    overthinking_score: float = 0.0
    consistency_score: float = 0.0


class PolicyDecision(BaseModel):
    """Decision output from policy engine."""
    action: PolicyAction
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
    # For ASK_QUESTION
    question_focus: Optional[str] = None
    question_type: Optional[str] = None  # open, clarifying, scaling, choice
    
    # For GENERATE_TASK
    task_type: Optional[str] = None  # micro, habit, project, review
    task_goal_area: Optional[str] = None
    estimated_difficulty: Optional[float] = None
    
    # For PLAN
    plan_horizon: Optional[str] = None  # daily, weekly, monthly
    plan_focus: Optional[str] = None
    
    # For REVIEW_TASK
    task_id: Optional[str] = None
    review_focus: Optional[str] = None
    
    # For EXPLORE_*
    exploration_target: Optional[str] = None
    
    # Coaching strategy
    coaching_strategy: Optional[str] = None
    pacing: Optional[str] = None  # slow, moderate, fast


class PolicyRule(BaseModel):
    """Individual policy rule for evaluation."""
    name: str
    condition: str  # Python expression string
    action: PolicyAction
    priority: int = 0
    parameters: Dict[str, Any] = Field(default_factory=dict)


# Default policy rules (evaluated in priority order)
DEFAULT_POLICY_RULES = [
    # Daily review at session start
    PolicyRule(
        name="daily_review_at_start",
        condition="conversation_count == 0 and active_tasks > 0",
        action=PolicyAction.REVIEW_TASK,
        priority=100,
        parameters={"review_focus": "daily_start"}
    ),
    
    # End of day review
    PolicyRule(
        name="daily_review_at_end",
        condition="conversation_count > 10 and active_tasks > 0",
        action=PolicyAction.REVIEW_TASK,
        priority=90,
        parameters={"review_focus": "daily_end"}
    ),
    
    # If user has unresolved tasks and is ready, check progress
    PolicyRule(
        name="check_progress_on_unresolved",
        condition="unresolved_task_count > 0 and readiness_for_action > 0.6 and last_action != 'check_progress'",
        action=PolicyAction.CHECK_PROGRESS,
        priority=80
    ),
    
    # If goal is clear but no task generated yet
    PolicyRule(
        name="generate_task_when_ready",
        condition="goal_clarity > 0.7 and constraint_clarity > 0.5 and readiness_for_action > 0.6 and active_tasks < 3 and last_action != 'generate_task'",
        action=PolicyAction.GENERATE_TASK,
        priority=70,
        parameters={"task_type": "micro"}
    ),
    
    # If goal unclear, explore goal
    PolicyRule(
        name="explore_goal_unclear",
        condition="goal_clarity < 0.4 and conversation_count > 2",
        action=PolicyAction.EXPLORE_GOAL,
        priority=60
    ),
    
    # If constraint unclear but goal clear, explore constraint
    PolicyRule(
        name="explore_constraint_unclear",
        condition="goal_clarity > 0.5 and constraint_clarity < 0.4 and conversation_count > 3",
        action=PolicyAction.EXPLORE_CONSTRAINT,
        priority=55
    ),
    
    # If habit unclear, explore habit
    PolicyRule(
        name="explore_habit_unclear",
        condition="goal_clarity > 0.5 and habit_clarity < 0.4 and conversation_count > 4",
        action=PolicyAction.EXPLORE_HABIT,
        priority=50
    ),
    
    # If identity unclear, explore identity
    PolicyRule(
        name="explore_identity_unclear",
        condition="identity_clarity < 0.3 and conversation_count > 5 and trust_rapport > 0.5",
        action=PolicyAction.EXPLORE_IDENTITY,
        priority=45
    ),
    
    # If ready for action but no clear plan, plan
    PolicyRule(
        name="plan_when_ready",
        condition="readiness_for_action > 0.7 and goal_clarity > 0.6 and active_tasks == 0",
        action=PolicyAction.PLAN,
        priority=65,
        parameters={"plan_horizon": "daily"}
    ),
    
    # If deep conversation, reflect
    PolicyRule(
        name="reflect_on_depth",
        condition="conversation_depth > 0.7 and conversation_count > 5 and last_action not in ['reflect', 'summarize']",
        action=PolicyAction.REFLECT,
        priority=40
    ),
    
    # If user seems stuck, ask clarifying question
    PolicyRule(
        name="ask_question_when_stuck",
        condition="readiness_for_action < 0.3 and conversation_count > 3",
        action=PolicyAction.ASK_QUESTION,
        priority=35,
        parameters={"question_type": "clarifying", "question_focus": "blocker"}
    ),
    
    # If trust low, build rapport
    PolicyRule(
        name="build_rapport",
        condition="trust_rapport < 0.4 and conversation_count < 5",
        action=PolicyAction.ASK_QUESTION,
        priority=30,
        parameters={"question_type": "open", "question_focus": "rapport"}
    ),
    
    # If conversation ending naturally
    PolicyRule(
        name="end_session_naturally",
        condition="conversation_count > 15 and readiness_for_action < 0.3 and last_action in ['reflect', 'summarize']",
        action=PolicyAction.END_SESSION,
        priority=20
    ),
    
    # Default: wait and listen
    PolicyRule(
        name="default_wait",
        condition="True",
        action=PolicyAction.WAIT,
        priority=0
    ),
]