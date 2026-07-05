"""
ChitraGupta 2.0 — Adaptive Memory Schemas
Smart memory recall prioritizing coaching effectiveness.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class MemoryType(str, Enum):
    CONVERSATION = "conversation"
    TASK_OUTCOME = "task_outcome"
    INSIGHT = "insight"
    PATTERN = "pattern"
    PREFERENCE = "preference"
    INTERVENTION = "intervention"
    IDENTITY = "identity"
    GOAL = "goal"
    STRUGGLE = "struggle"
    SUCCESS = "success"
    FAILURE = "failure"


class MemoryPriority(str, Enum):
    CRITICAL = "critical"      # Must include
    HIGH = "high"              # Strongly relevant
    MEDIUM = "medium"          # Moderately relevant
    LOW = "low"                # Weakly relevant
    ARCHIVAL = "archival"      # Historical only


class MemoryEntry(BaseModel):
    """Single memory entry with coaching relevance."""
    id: str
    user_id: str
    memory_type: MemoryType
    priority: MemoryPriority
    content: str
    summary: str  # One-line summary for quick scanning
    
    # Context
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None
    related_task_id: Optional[str] = None
    related_goal: Optional[str] = None
    
    # Coaching metadata
    coaching_effectiveness: float = Field(default=0.0, ge=0.0, le=1.0)
    # How effective was the intervention related to this memory
    
    user_response: str = ""  # How user responded (positive, negative, neutral)
    intervention_type: Optional[str] = None  # What coaching move was made
    
    # Behavioral tags
    behavioral_patterns: List[str] = Field(default_factory=list)
    emotional_tone: Optional[str] = None
    
    # Retrieval metadata
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    retrieval_contexts: List[str] = Field(default_factory=list)
    # What queries/contexts this was retrieved for
    
    # Decay
    decay_rate: float = 0.1  # Per week
    relevance_score: float = Field(default=1.0, ge=0.0, le=1.0)


class MemoryQuery(BaseModel):
    """Query for adaptive memory retrieval."""
    user_id: str
    current_context: str = ""  # What's happening now
    goal: Optional[str] = None
    struggle: Optional[str] = None
    active_task: Optional[str] = None
    behavioral_patterns: List[str] = Field(default_factory=list)
    coaching_strategy: Optional[str] = None
    max_entries: int = 10
    min_relevance: float = 0.3
    include_types: Optional[List[MemoryType]] = None
    exclude_types: Optional[List[MemoryType]] = None
    time_window_days: Optional[int] = None


class MemoryRetrievalResult(BaseModel):
    """Result of memory retrieval."""
    entries: List[MemoryEntry] = Field(default_factory=list)
    total_available: int = 0
    retrieval_strategy: str = ""
    coverage: Dict[str, int] = Field(default_factory=dict)
    # memory_type -> count


class MemoryConsolidationRule(BaseModel):
    """Rules for memory consolidation (30-day compaction)."""
    source_types: List[MemoryType]
    target_type: MemoryType
    condition: str  # Python expression
    consolidation_fn: str  # Name of consolidation function
    priority: MemoryPriority = MemoryPriority.MEDIUM


# Default consolidation rules
DEFAULT_CONSOLIDATION_RULES = [
    MemoryConsolidationRule(
        source_types=[MemoryType.CONVERSATION, MemoryType.INSIGHT],
        target_type=MemoryType.PATTERN,
        condition="frequency > 3 and coaching_effectiveness > 0.5",
        consolidation_fn="consolidate_recurring_insights",
        priority=MemoryPriority.HIGH
    ),
    MemoryConsolidationRule(
        source_types=[MemoryType.TASK_OUTCOME, MemoryType.SUCCESS, MemoryType.FAILURE],
        target_type=MemoryType.INTERVENTION,
        condition="task_type_consistent and outcome_clear",
        consolidation_fn="consolidate_task_interventions",
        priority=MemoryPriority.HIGH
    ),
    MemoryConsolidationRule(
        source_types=[MemoryType.GOAL, MemoryType.STRUGGLE, MemoryType.IDENTITY],
        target_type=MemoryType.PATTERN,
        condition="themes_stable_over_30_days",
        consolidation_fn="consolidate_identity_patterns",
        priority=MemoryPriority.MEDIUM
    ),
]