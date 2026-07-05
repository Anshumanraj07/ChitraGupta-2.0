"""
ChitraGupta 2.0 — Behavioral Inference Schemas
Deterministic pattern detection from conversation + task history.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta


class BehaviorPattern(str, Enum):
    """Detectable behavioral patterns."""
    PROCRASTINATION = "procrastination"
    AVOIDANCE = "avoidance"
    PERFECTIONISM = "perfectionism"
    BURNOUT = "burnout"
    OVERTHINKING = "overthinking"
    VALIDATION_SEEKING = "validation_seeking"
    INCONSISTENCY = "inconsistency"
    MOMENTUM = "momentum"
    RESISTANCE = "resistance"
    INTRINSIC_MOTIVATION = "intrinsic_motivation"
    EXTRINSIC_MOTIVATION = "extrinsic_motivation"
    FOLLOW_THROUGH_TENDENCY = "follow_through_tendency"
    TASK_FRICTION_SENSITIVITY = "task_friction_sensitivity"
    EMOTIONAL_REGULATION = "emotional_regulation"
    GOAL_SHIFTING = "goal_shifting"
    SCOPE_CREEP = "scope_creep"
    MINIMAL_EFFORT = "minimal_effort"
    ALL_OR_NOTHING = "all_or_nothing"
    SELF_SABOTAGE = "self_sabotage"
    COMPENSATORY = "compensatory"


class PatternEvidence(BaseModel):
    """Evidence for a behavioral pattern."""
    pattern: BehaviorPattern
    source: str  # "task_history", "conversation", "daily_review", "completion_data"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    description: str
    strength: float = Field(ge=0.0, le=1.0)  # How strongly this evidence supports the pattern
    context: Dict[str, Any] = Field(default_factory=dict)


class BehavioralPatternResult(BaseModel):
    """Result of behavioral pattern detection."""
    pattern: BehaviorPattern
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: List[PatternEvidence] = Field(default_factory=list)
    first_detected: Optional[datetime] = None
    last_reinforced: Optional[datetime] = None
    frequency: int = 0  # How many times observed
    trend: str = "stable"  # "increasing", "decreasing", "stable"
    description: str = ""
    # Intervention suggestions
    suggested_interventions: List[str] = Field(default_factory=list)
    coaching_notes: str = ""


class BehavioralProfile(BaseModel):
    """Complete behavioral profile for a user."""
    user_id: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Active patterns with confidence
    patterns: Dict[BehaviorPattern, BehavioralPatternResult] = Field(default_factory=dict)
    
    # Composite scores
    procrastination_score: float = 0.0
    avoidance_score: float = 0.0
    perfectionism_score: float = 0.0
    burnout_risk: float = 0.0
    consistency_score: float = 0.0
    follow_through_score: float = 0.0
    motivation_quality: float = 0.0  # intrinsic vs extrinsic balance
    emotional_stability: float = 0.0
    
    # Derived insights
    primary_pattern: Optional[BehaviorPattern] = None
    secondary_patterns: List[BehaviorPattern] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    protective_factors: List[str] = Field(default_factory=list)
    
    # Coaching implications
    recommended_pacing: str = "moderate"  # "slow", "moderate", "fast"
    recommended_approach: str = "balanced"  # "supportive", "challenging", "balanced", "directive"
    task_difficulty_preference: str = "micro"  # "micro", "small", "medium", "large"
    feedback_style: str = "encouraging"  # "encouraging", "direct", "analytical", "minimal"
    
    # History
    pattern_history: List[Dict[str, Any]] = Field(default_factory=list)
    # Each entry: {"date": "...", "pattern": "...", "confidence": 0.0, "change": "new/increased/decreased/resolved"}


# Detection rules configuration
BEHAVIORAL_DETECTION_RULES = {
    BehaviorPattern.PROCRASTINATION: {
        "task_indicators": [
            "task_created_but_not_started_within_24h",
            "task_repeatedly_rescheduled",
            "high_priority_tasks_consistently_delayed",
            "many_tasks_in_backlog",
        ],
        "conversation_indicators": [
            "mentions_putting_things_off",
            "says_will_do_later",
            "expresses_guilt_about_not_starting",
        ],
        "thresholds": {
            "min_evidence_count": 3,
            "min_confidence": 0.6,
        }
    },
    BehaviorPattern.AVOIDANCE: {
        "task_indicators": [
            "tasks_abandoned_without_completion",
            "difficult_tasks_never_attempted",
            "consistently_chooses_easier_alternatives",
        ],
        "conversation_indicators": [
            "changes_topic_when_difficulty_mentioned",
            "minimizes_challenges",
            "expresses_fear_of_failure",
        ],
        "thresholds": {
            "min_evidence_count": 2,
            "min_confidence": 0.5,
        }
    },
    BehaviorPattern.PERFECTIONISM: {
        "task_indicators": [
            "tasks_marked_incomplete_due_to_not_perfect",
            "excessive_planning_before_starting",
            "repeatedly_revises_same_task",
        ],
        "conversation_indicators": [
            "uses_language_like_perfect_right_exact",
            "expresses_frustration_with_imperfection",
            "sets_unrealistic_standards",
        ],
        "thresholds": {
            "min_evidence_count": 3,
            "min_confidence": 0.6,
        }
    },
    BehaviorPattern.BURNOUT: {
        "task_indicators": [
            "sudden_drop_in_completion_rate",
            "previously_consistent_user_stops_engaging",
            "tasks_take_much_longer_than_estimated",
        ],
        "conversation_indicators": [
            "expresses_exhaustion_overwhelmed",
            "mentions_no_energy_motivation",
            "cynical_about_progress",
        ],
        "thresholds": {
            "min_evidence_count": 2,
            "min_confidence": 0.7,
        }
    },
    BehaviorPattern.OVERTHINKING: {
        "task_indicators": [
            "long_deliberation_before_simple_tasks",
            "asks_many_clarifying_questions",
            "creates_complex_plans_for_simple_goals",
        ],
        "conversation_indicators": [
            "analyzes_multiple_scenarios",
            "struggles_to_decide",
            "seeks_excessive_information",
        ],
        "thresholds": {
            "min_evidence_count": 3,
            "min_confidence": 0.5,
        }
    },
    BehaviorPattern.VALIDATION_SEEKING: {
        "task_indicators": [
            "only_completes_tasks_when_acknowledged",
            "shares_progress_excessively",
        ],
        "conversation_indicators": [
            "asks_am_i_doing_this_right",
            "seeks_reassurance_frequently",
            "needs_external_confirmation",
        ],
        "thresholds": {
            "min_evidence_count": 3,
            "min_confidence": 0.5,
        }
    },
    BehaviorPattern.INCONSISTENCY: {
        "task_indicators": [
            "high_variance_in_daily_completion",
            "streaks_broken_frequently",
            "pattern_of_start_stop",
        ],
        "conversation_indicators": [
            "contradicts_previous_statements",
            "changes_goals_frequently",
            "mood_dependent_engagement",
        ],
        "thresholds": {
            "min_evidence_count": 4,
            "min_confidence": 0.5,
        }
    },
    BehaviorPattern.MOMENTUM: {
        "task_indicators": [
            "completion_begets_completion",
            "streaks_building",
            "increasing_task_difficulty_over_time",
        ],
        "conversation_indicators": [
            "expresses_excitement_about_progress",
            "references_past_wins",
            "proactive_about_next_steps",
        ],
        "thresholds": {
            "min_evidence_count": 3,
            "min_confidence": 0.6,
        }
    },
    BehaviorPattern.RESISTANCE: {
        "task_indicators": [
            "rejects_suggested_tasks",
            "modifies_tasks_significantly",
            "pushes_back_on_structure",
        ],
        "conversation_indicators": [
            "says_i_dont_like_being_told",
            "prefers_own_way",
            "questions_authority_structure",
        ],
        "thresholds": {
            "min_evidence_count": 2,
            "min_confidence": 0.5,
        }
    },
    BehaviorPattern.FOLLOW_THROUGH_TENDENCY: {
        "task_indicators": [
            "high_completion_rate_for_committed_tasks",
            "low_abandonment_rate",
        ],
        "conversation_indicators": [
            "uses_commitment_language",
            "follows_up_on_previous_mentions",
        ],
        "thresholds": {
            "min_evidence_count": 3,
            "min_confidence": 0.6,
        }
    },
    BehaviorPattern.TASK_FRICTION_SENSITIVITY: {
        "task_indicators": [
            "completes_easy_tasks_avoids_hard",
            "abandons_when_friction_encountered",
            "needs_very_specific_instructions",
        ],
        "conversation_indicators": [
            "complains_about_complexity",
            "asks_for_exact_steps",
            "overwhelmed_by_ambiguity",
        ],
        "thresholds": {
            "min_evidence_count": 3,
            "min_confidence": 0.5,
        }
    },
}