"""ChitraGupta 2.0 — Core Package"""

from core import engine_shifter
from core.conversation_manager import conversation_manager
from core.goal_discovery import goal_discovery
from core.memory_manager import memory_manager
from core.session_manager import session_manager
from core.task_generator import task_generator
import scripts.daily_summarizer as daily_summarizer_module
daily_summarizer = daily_summarizer_module

# Intelligence Layers (NEW)
from core.policy_engine import policy_engine, PolicyEngine
from core.confidence_tracker import confidence_tracker, ConfidenceTracker
from core.identity_model import identity_model, IdentityModel
from core.behavioral_inference import behavioral_inference, BehavioralInference
from core.coaching_planner import coaching_planner, CoachingPlanner
from core.task_quality_engine import task_quality_engine, TaskQualityEngine
from core.daily_review import daily_review, DailyReview
from core.adaptive_memory import adaptive_memory, AdaptiveMemory

__all__ = [
    # Original modules
    "engine_shifter",
    "conversation_manager",
    "goal_discovery",
    "memory_manager",
    "session_manager",
    "task_generator",
    "daily_summarizer",
    # Intelligence layers
    "policy_engine",
    "PolicyEngine",
    "confidence_tracker",
    "ConfidenceTracker",
    "identity_model",
    "IdentityModel",
    "behavioral_inference",
    "BehavioralInference",
    "coaching_planner",
    "CoachingPlanner",
    "task_quality_engine",
    "TaskQualityEngine",
    "daily_review",
    "DailyReview",
    "adaptive_memory",
    "AdaptiveMemory",
]
