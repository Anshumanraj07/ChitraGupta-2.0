"""
ChitraGupta 2.0 — Identity Model Schemas
Persistent user identity tracking with incremental updates.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class MotivationStyle(str, Enum):
    INTRINSIC = "intrinsic"
    EXTRINSIC = "extrinsic"
    SOCIAL = "social"
    ACHIEVEMENT = "achievement"
    MASTERY = "mastery"
    AUTONOMY = "autonomy"
    PURPOSE = "purpose"
    UNKNOWN = "unknown"


class DisciplinePattern(str, Enum):
    CONSISTENT = "consistent"
    SPORADIC = "sporadic"
    BURST = "burst"
    PROCRASTINATOR = "procrastinator"
    PERFECTIONIST = "perfectionist"
    ALL_OR_NOTHING = "all_or_nothing"
    GRADUAL = "gradual"
    UNKNOWN = "unknown"


class EnergyPattern(str, Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"
    VARIABLE = "variable"
    UNKNOWN = "unknown"


class LearningStyle(str, Enum):
    VISUAL = "visual"
    AUDITORY = "auditory"
    KINESTHETIC = "kinesthetic"
    READING = "reading"
    EXPERIENTIAL = "experiential"
    REFLECTIVE = "reflective"
    UNKNOWN = "unknown"


class CommunicationPreference(str, Enum):
    DIRECT = "direct"
    GENTLE = "gentle"
    DETAILED = "detailed"
    CONCISE = "concise"
    QUESTIONING = "questioning"
    STORYTELLING = "storytelling"
    HUMOR = "humor"
    UNKNOWN = "unknown"


class CoachingPreference(str, Enum):
    COACH = "coach"
    MENTOR = "mentor"
    PARTNER = "partner"
    ACCOUNTABILITY = "accountability"
    REFLECTIVE = "reflective"
    DIRECTIVE = "directive"
    UNKNOWN = "unknown"


class IdentityProfile(BaseModel):
    """Complete user identity profile stored in Supabase."""
    user_id: str
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Core identity
    values: List[str] = Field(default_factory=list)  # e.g., "health", "family", "growth"
    beliefs: List[str] = Field(default_factory=list)  # e.g., "I can change", "discipline = freedom"
    goals: List[str] = Field(default_factory=list)    # Long-term aspirations
    fears: List[str] = Field(default_factory=list)    # What holds them back
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    
    # Behavioral patterns
    motivation_style: MotivationStyle = MotivationStyle.UNKNOWN
    discipline_pattern: DisciplinePattern = DisciplinePattern.UNKNOWN
    energy_pattern: EnergyPattern = EnergyPattern.UNKNOWN
    
    # Learning & communication
    learning_style: LearningStyle = LearningStyle.UNKNOWN
    communication_preference: CommunicationPreference = CommunicationPreference.UNKNOWN
    coaching_preference: CoachingPreference = CoachingPreference.UNKNOWN
    
    # Self-image trajectory
    self_image_trajectory: List[Dict[str, Any]] = Field(default_factory=list)
    # Each entry: {"date": "...", "self_assessment": "...", "confidence": 0.0}
    
    # Meta
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    # e.g., {"values": 0.8, "goals": 0.6, "motivation_style": 0.7}
    
    evidence_count: Dict[str, int] = Field(default_factory=dict)
    # e.g., {"values": 5, "goals": 3}
    
    # Session context for incremental updates
    last_session_date: Optional[str] = None
    sessions_since_update: int = 0


class IdentityEvidence(BaseModel):
    """Single piece of evidence for identity inference."""
    source: str  # "conversation", "task_completion", "task_failure", "daily_review"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    category: str  # "values", "beliefs", "goals", "fears", "strengths", "weaknesses", "motivation", "discipline", "energy"
    content: str
    confidence: float = Field(ge=0.0, le=1.0)
    session_id: Optional[str] = None


class IdentityUpdate(BaseModel):
    """Proposed identity update from evidence."""
    category: str
    field: str  # e.g., "values", "motivation_style"
    current_value: Any
    proposed_value: Any
    confidence: float
    evidence: List[IdentityEvidence]
    reasoning: str


class SelfImageSnapshot(BaseModel):
    """Point-in-time self-image assessment."""
    date: str  # YYYY-MM-DD
    self_assessment: str  # Free text: "I see myself as someone who..."
    confidence: float = Field(ge=0.0, le=1.0)
    key_themes: List[str] = Field(default_factory=list)