"""
ChitraGupta 2.0 — Coaching Planner Schemas
Long-term interaction strategy and pacing control.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class CoachingStrategy(str, Enum):
    """High-level coaching strategies."""
    UNDERSTAND = "understand"      # Deep listening, exploration
    REFLECT = "reflect"            # Mirror back, synthesize
    CHALLENGE = "challenge"        # Push boundaries, question assumptions
    CLARIFY = "clarify"            # Reduce ambiguity, define specifics
    PLAN = "plan"                  # Create structure, roadmap
    EXECUTE = "execute"            # Drive action, accountability
    REVIEW = "review"              # Assess progress, learn
    ADAPT = "adapt"                # Adjust approach based on failures, change course
    SUPPORT = "support"            # Encourage, validate
    EDUCATE = "educate"            # Teach concepts, frameworks


class CoachingPacing(str, Enum):
    SLOW = "slow"          # More reflection, less action
    MODERATE = "moderate"  # Balanced
    FAST = "fast"          # More action, less reflection


class CoachingFocus(str, Enum):
    GOALS = "goals"
    HABITS = "habits"
    MINDSET = "mindset"
    SKILLS = "skills"
    ENVIRONMENT = "environment"
    IDENTITY = "identity"
    EMOTIONS = "emotions"
    RELATIONSHIPS = "relationships"
    CAREER = "career"
    HEALTH = "health"
    LEARNING = "learning"
    CREATIVITY = "creativity"


class StrategyRule(BaseModel):
    """Rule for selecting coaching strategy."""
    name: str
    condition: str  # Python expression
    strategy: CoachingStrategy
    pacing: CoachingPacing
    priority: int = 0
    focus_areas: List[CoachingFocus] = Field(default_factory=list)
    avoid_areas: List[CoachingFocus] = Field(default_factory=list)
    max_duration_sessions: Optional[int] = None
    min_duration_sessions: int = 1
    transition_triggers: List[str] = Field(default_factory=list)


class CoachingPlan(BaseModel):
    """Active coaching plan for a user."""
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Current strategy
    primary_strategy: CoachingStrategy = CoachingStrategy.UNDERSTAND
    secondary_strategies: List[CoachingStrategy] = Field(default_factory=list)
    pacing: CoachingPacing = CoachingPacing.MODERATE
    focus_areas: List[CoachingFocus] = Field(default_factory=list)
    
    # Strategy metadata
    strategy_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    sessions_in_current_strategy: int = 0
    strategy_start_date: Optional[datetime] = None
    
    # Constraints
    max_tasks_per_session: int = 1
    min_reflection_ratio: float = 0.3  # Reflection vs action balance
    challenge_level: float = 0.5  # 0 = supportive, 1 = challenging
    
    # Adaptation
    adaptation_triggers: List[str] = Field(default_factory=list)
    last_adaptation: Optional[datetime] = None
    adaptation_count: int = 0
    
    # History
    strategy_history: List[Dict[str, Any]] = Field(default_factory=list)
    # Each: {"strategy": "...", "start": "...", "end": "...", "reason": "...", "outcome": "..."}


class CoachingDecision(BaseModel):
    """Decision from coaching planner."""
    strategy: CoachingStrategy
    pacing: CoachingPacing
    focus_areas: List[CoachingFocus] = Field(default_factory=list)
    avoid_areas: List[CoachingFocus] = Field(default_factory=list)
    max_tasks: int = 1
    reflection_ratio: float = 0.3
    challenge_level: float = 0.5
    reasoning: str = ""
    confidence: float = Field(ge=0.0, le=1.0)
    adaptation_needed: bool = False
    adaptation_reason: str = ""


# Default strategy selection rules
DEFAULT_STRATEGY_RULES = [
    # New user: understand first
    StrategyRule(
        name="new_user_understand",
        condition="conversation_count < 3 and not has_identity_profile",
        strategy=CoachingStrategy.UNDERSTAND,
        pacing=CoachingPacing.SLOW,
        priority=100,
        focus_areas=[CoachingFocus.GOALS, CoachingFocus.IDENTITY, CoachingFocus.MINDSET],
        min_duration_sessions=3
    ),
    
    # Low trust: build rapport
    StrategyRule(
        name="low_trust_support",
        condition="trust_rapport < 0.4",
        strategy=CoachingStrategy.SUPPORT,
        pacing=CoachingPacing.SLOW,
        priority=95,
        focus_areas=[CoachingFocus.EMOTIONS, CoachingFocus.MINDSET],
        min_duration_sessions=2
    ),
    
    # Burnout risk: support and slow down
    StrategyRule(
        name="burnout_risk_support",
        condition="burnout_risk > 0.6",
        strategy=CoachingStrategy.SUPPORT,
        pacing=CoachingPacing.SLOW,
        priority=90,
        focus_areas=[CoachingFocus.HEALTH, CoachingFocus.EMOTIONS, CoachingFocus.ENVIRONMENT],
        avoid_areas=[CoachingFocus.CAREER, CoachingFocus.SKILLS],
        min_duration_sessions=3
    ),
    
    # High procrastination: challenge + structure
    StrategyRule(
        name="procrastination_challenge_plan",
        condition="procrastination_score > 0.6 and readiness_for_action > 0.4",
        strategy=CoachingStrategy.CHALLENGE,
        pacing=CoachingPacing.MODERATE,
        priority=85,
        focus_areas=[CoachingFocus.HABITS, CoachingFocus.GOALS, CoachingFocus.MINDSET],
        secondary_strategies=[CoachingStrategy.PLAN],
        min_duration_sessions=2
    ),
    
    # High avoidance: understand then clarify
    StrategyRule(
        name="avoidance_understand_clarify",
        condition="avoidance_score > 0.6",
        strategy=CoachingStrategy.UNDERSTAND,
        pacing=CoachingPacing.SLOW,
        priority=80,
        focus_areas=[CoachingFocus.EMOTIONS, CoachingFocus.MINDSET, CoachingFocus.IDENTITY],
        secondary_strategies=[CoachingStrategy.CLARIFY],
        min_duration_sessions=3
    ),
    
    # Perfectionism: reflect + adapt
    StrategyRule(
        name="perfectionism_reflect_adapt",
        condition="perfectionism_score > 0.6",
        strategy=CoachingStrategy.REFLECT,
        pacing=CoachingPacing.MODERATE,
        priority=75,
        focus_areas=[CoachingFocus.MINDSET, CoachingFocus.HABITS],
        secondary_strategies=[CoachingStrategy.ADAPT],
        min_duration_sessions=2
    ),
    
    # High momentum: execute + challenge
    StrategyRule(
        name="momentum_execute",
        condition="momentum_score > 0.7 and follow_through_score > 0.7",
        strategy=CoachingStrategy.EXECUTE,
        pacing=CoachingPacing.FAST,
        priority=70,
        focus_areas=[CoachingFocus.GOALS, CoachingFocus.SKILLS, CoachingFocus.HABITS],
        secondary_strategies=[CoachingStrategy.CHALLENGE],
        min_duration_sessions=2
    ),
    
    # Goal clarity high but no action: plan
    StrategyRule(
        name="clarity_without_action_plan",
        condition="goal_clarity > 0.7 and active_tasks == 0 and readiness_for_action > 0.5",
        strategy=CoachingStrategy.PLAN,
        pacing=CoachingPacing.MODERATE,
        priority=65,
        focus_areas=[CoachingFocus.GOALS, CoachingFocus.HABITS],
        min_duration_sessions=2
    ),
    
    # Inconsistency: review + adapt
    StrategyRule(
        name="inconsistency_review_adapt",
        condition="consistency_score < 0.4 and conversation_count > 5",
        strategy=CoachingStrategy.REVIEW,
        pacing=CoachingPacing.MODERATE,
        priority=60,
        focus_areas=[CoachingFocus.HABITS, CoachingFocus.ENVIRONMENT, CoachingFocus.MINDSET],
        secondary_strategies=[CoachingStrategy.ADAPT],
        min_duration_sessions=3
    ),
    
    # Overthinking: clarify + execute (small)
    StrategyRule(
        name="overthinking_clarify_execute",
        condition="overthinking_score > 0.6",
        strategy=CoachingStrategy.CLARIFY,
        pacing=CoachingPacing.SLOW,
        priority=55,
        focus_areas=[CoachingFocus.GOALS, CoachingFocus.HABITS],
        secondary_strategies=[CoachingStrategy.EXECUTE],
        min_duration_sessions=2
    ),
    
    # Default: balanced understand/reflect
    StrategyRule(
        name="default_balanced",
        condition="True",
        strategy=CoachingStrategy.UNDERSTAND,
        pacing=CoachingPacing.MODERATE,
        priority=0,
        focus_areas=[CoachingFocus.GOALS, CoachingFocus.HABITS, CoachingFocus.MINDSET],
        secondary_strategies=[CoachingStrategy.REFLECT, CoachingStrategy.CLARIFY],
    ),
]