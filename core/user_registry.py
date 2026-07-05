"""
ChitraGupta 2.0 — User Registry
Per-user instances of all intelligence modules.

This is the central mechanism for proper multi-user support. Instead of using
module-level singletons (which are bound to "default_user"), the endpoints and
the request path request a per-user bundle of modules via this registry. The
bundle is cached so repeated requests for the same user are cheap; each user
gets isolated in-memory state + Supabase-persisted state scoped by user_id.

Backward compatibility: the legacy module-level singletons remain importable
and remain bound to "default_user" for any code that has not yet migrated.
"""

import logging
import threading
from typing import Dict, Any, Optional

logger = logging.getLogger("chitragupta.user_registry")

# Default anonymous user id when none is provided by the caller.
# This preserves backward compatibility with the previous behaviour while
# making the user id explicit and consistent across the interface.
DEFAULT_USER_ID = "default_user"

_lock = threading.Lock()
_user_bundles: Dict[str, "_UserBundle"] = {}


class _UserBundle:
    """Holds per-user instances of all intelligence modules."""

    __slots__ = (
        "user_id",
        "identity_model",
        "behavioral_inference",
        "coaching_planner",
        "confidence_tracker",
        "adaptive_memory",
        "daily_review",
        "task_quality_engine",
    )

    def __init__(self, user_id: str):
        # Import lazily to avoid circular imports during module init.
        from core.identity_model import IdentityModel
        from core.behavioral_inference import BehavioralInference
        from core.coaching_planner import CoachingPlanner
        from core.confidence_tracker import ConfidenceTracker
        from core.adaptive_memory import AdaptiveMemory
        from core.daily_review import DailyReview
        from core.task_quality_engine import TaskQualityEngine

        self.user_id = user_id
        self.identity_model = IdentityModel(user_id=user_id)
        self.behavioral_inference = BehavioralInference(user_id=user_id)
        self.coaching_planner = CoachingPlanner(user_id=user_id)
        self.confidence_tracker = ConfidenceTracker(user_id=user_id)
        self.adaptive_memory = AdaptiveMemory(user_id=user_id)
        # DailyReview and TaskQualityEngine currently don't carry per-user
        # state internally, but instantiate with user_id for forward compat.
        self.daily_review = DailyReview()
        self.task_quality_engine = TaskQualityEngine(user_id=user_id)

    def summary(self) -> Dict[str, Any]:
        """Lightweight summary for diagnostics."""
        return {
            "user_id": self.user_id,
            "modules": [
                "identity_model",
                "behavioral_inference",
                "coaching_planner",
                "confidence_tracker",
                "adaptive_memory",
                "daily_review",
                "task_quality_engine",
            ],
        }


def get_user_bundle(user_id: Optional[str] = None) -> _UserBundle:
    """
    Get (or create) the per-user bundle of intelligence modules.

    Falls back to DEFAULT_USER_ID when user_id is empty/None so that callers
    without an explicit user identity keep working without crashing.
    """
    resolved = (user_id or "").strip() or DEFAULT_USER_ID
    # Bundle already cached?
    bundle = _user_bundles.get(resolved)
    if bundle is not None:
        return bundle

    with _lock:
        # Double-check after acquiring lock
        bundle = _user_bundles.get(resolved)
        if bundle is None:
            logger.debug(f"Creating intelligence bundle for user_id='{resolved}'")
            bundle = _UserBundle(resolved)
            _user_bundles[resolved] = bundle
        return bundle


def reset_user_bundle(user_id: str):
    """Drop the cached bundle for a user (testing / cache invalidation)."""
    with _lock:
        _user_bundles.pop(user_id, None)


def clear_all_bundles():
    """Clear every cached bundle (testing)."""
    with _lock:
        _user_bundles.clear()


def active_user_ids():
    """List user ids that currently have cached bundles."""
    with _lock:
        return list(_user_bundles.keys())