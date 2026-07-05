"""
ChitraGupta 2.0 — Confidence Tracker Schemas
Multi-dimensional confidence tracking with evidence-based updates.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ConfidenceDimension(str, Enum):
    GOAL_CLARITY = "goal_clarity"
    CONSTRAINT_CLARITY = "constraint_clarity"
    HABIT_CLARITY = "habit_clarity"
    IDENTITY_CLARITY = "identity_clarity"
    MOTIVATION_CLARITY = "motivation_clarity"
    ROUTINE_CLARITY = "routine_clarity"
    READINESS_FOR_ACTION = "readiness_for_action"
    TRUST_RAPPORT = "trust_rapport"
    CONVERSATION_DEPTH = "conversation_depth"


class ConfidenceEvidence(BaseModel):
    """Evidence for a confidence score."""
    dimension: ConfidenceDimension
    source: str  # "conversation", "task_completion", "task_failure", "daily_review", "explicit_statement"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    description: str
    impact: float = Field(ge=-1.0, le=1.0)  # Positive or negative impact
    confidence: float = Field(ge=0.0, le=1.0)  # How confident we are in this evidence
    context: Dict[str, Any] = Field(default_factory=dict)


class ConfidenceScore(BaseModel):
    """Confidence score for a single dimension."""
    dimension: ConfidenceDimension
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_count: int = 0
    positive_evidence: int = 0
    negative_evidence: int = 0
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    trend: str = "stable"  # "increasing", "decreasing", "stable"
    volatility: float = 0.0  # How much score fluctuates
    
    # Thresholds for action
    action_threshold: float = 0.7  # Above this: can act confidently
    question_threshold: float = 0.4  # Below this: need to ask/explore
    critical_threshold: float = 0.2  # Below this: major gap


class ConfidenceProfile(BaseModel):
    """Complete confidence profile for a user."""
    user_id: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Individual dimension scores
    scores: Dict[ConfidenceDimension, ConfidenceScore] = Field(default_factory=dict)
    
    # Composite scores
    overall_clarity: float = 0.0
    overall_readiness: float = 0.0
    trust_level: float = 0.0
    
    # Gaps (dimensions below question_threshold)
    clarity_gaps: List[ConfidenceDimension] = Field(default_factory=list)
    critical_gaps: List[ConfidenceDimension] = Field(default_factory=list)
    
    # Strengths (dimensions above action_threshold)
    clarity_strengths: List[ConfidenceDimension] = Field(default_factory=list)
    
    # History
    score_history: List[Dict[str, Any]] = Field(default_factory=list)
    # Each: {"timestamp": "...", "dimension": "...", "old_score": 0.0, "new_score": 0.0, "evidence": "..."}


# Default confidence thresholds
CONFIDENCE_THRESHOLDS = {
    ConfidenceDimension.GOAL_CLARITY: {"action": 0.7, "question": 0.4, "critical": 0.2},
    ConfidenceDimension.CONSTRAINT_CLARITY: {"action": 0.6, "question": 0.3, "critical": 0.1},
    ConfidenceDimension.HABIT_CLARITY: {"action": 0.6, "question": 0.3, "critical": 0.1},
    ConfidenceDimension.IDENTITY_CLARITY: {"action": 0.7, "question": 0.4, "critical": 0.2},
    ConfidenceDimension.MOTIVATION_CLARITY: {"action": 0.6, "question": 0.3, "critical": 0.1},
    ConfidenceDimension.ROUTINE_CLARITY: {"action": 0.5, "question": 0.3, "critical": 0.1},
    ConfidenceDimension.READINESS_FOR_ACTION: {"action": 0.6, "question": 0.3, "critical": 0.1},
    ConfidenceDimension.TRUST_RAPPORT: {"action": 0.6, "question": 0.4, "critical": 0.2},
    ConfidenceDimension.CONVERSATION_DEPTH: {"action": 0.5, "question": 0.3, "critical": 0.1},
}

# Evidence weights by source
EVIDENCE_WEIGHTS = {
    "explicit_statement": 1.0,
    "task_completion": 0.8,
    "task_failure": 0.6,
    "daily_review": 0.7,
    "conversation": 0.5,
    "behavioral_inference": 0.4,
    "identity_inference": 0.6,
}