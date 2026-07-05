"""
ChitraGupta 2.0 — Coaching Planner
Long-term interaction strategy and pacing control.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from core.schemas.coaching import (
    CoachingStrategy, CoachingPacing, CoachingFocus, StrategyRule, CoachingPlan, CoachingDecision,
    DEFAULT_STRATEGY_RULES
)
from core.schemas.behavior import BehavioralProfile
from core.schemas.identity import IdentityProfile
from core.schemas.confidence import ConfidenceProfile

logger = logging.getLogger("chitragupta.coaching_planner")


class CoachingPlanner:
    """
    Determines long-term coaching strategy and pacing.
    Controls: don't generate tasks too early, don't rush advice, don't bounce topics.
    """
    
    def __init__(self, user_id: str = "default_user"):
        self.user_id = user_id
        self.rules = DEFAULT_STRATEGY_RULES
        self.plan: Optional[CoachingPlan] = None
        self._load_plan()
    
    def _load_plan(self):
        """Load coaching plan from Supabase."""
        try:
            from core.utils.supabase_client import get_supabase_client
            supabase = get_supabase_client()
            if supabase:
                response = supabase.table("coaching_plans").select("*").eq("user_id", self.user_id).execute()
                if response.data:
                    data = response.data[0]
                    self.plan = CoachingPlan(user_id=self.user_id)
                    self.plan.created_at = datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat()))
                    self.plan.updated_at = datetime.fromisoformat(data.get("updated_at", datetime.utcnow().isoformat()))
                    
                    self.plan.primary_strategy = CoachingStrategy(data.get("primary_strategy", "understand"))
                    self.plan.secondary_strategies = [CoachingStrategy(s) for s in data.get("secondary_strategies", [])]
                    self.plan.pacing = CoachingPacing(data.get("pacing", "moderate"))
                    self.plan.focus_areas = [CoachingFocus(f) for f in data.get("focus_areas", [])]
                    
                    self.plan.strategy_confidence = data.get("strategy_confidence", 0.5)
                    self.plan.sessions_in_current_strategy = data.get("sessions_in_current_strategy", 0)
                    self.plan.strategy_start_date = datetime.fromisoformat(data["strategy_start_date"]) if data.get("strategy_start_date") else None
                    
                    self.plan.max_tasks_per_session = data.get("max_tasks_per_session", 1)
                    self.plan.min_reflection_ratio = data.get("min_reflection_ratio", 0.3)
                    self.plan.challenge_level = data.get("challenge_level", 0.5)
                    
                    self.plan.adaptation_triggers = data.get("adaptation_triggers", [])
                    self.plan.last_adaptation = datetime.fromisoformat(data["last_adaptation"]) if data.get("last_adaptation") else None
                    self.plan.adaptation_count = data.get("adaptation_count", 0)
                    
                    self.plan.strategy_history = data.get("strategy_history", [])
                    
                    logger.info(f"Loaded coaching plan for {self.user_id}: {self.plan.primary_strategy.value}")
                    return
        except Exception as e:
            logger.warning(f"Failed to load coaching plan: {e}")
        
        # Create new plan
        self.plan = CoachingPlan(user_id=self.user_id)
        logger.info(f"Created new coaching plan for {self.user_id}")
    
    def _save_plan(self):
        """Save coaching plan to Supabase."""
        try:
            from core.utils.supabase_client import get_supabase_client
            supabase = get_supabase_client()
            if supabase and self.plan:
                self.plan.updated_at = datetime.utcnow()
                
                data = {
                    "user_id": self.user_id,
                    "created_at": self.plan.created_at.isoformat(),
                    "updated_at": self.plan.updated_at.isoformat(),
                    "primary_strategy": self.plan.primary_strategy.value,
                    "secondary_strategies": [s.value for s in self.plan.secondary_strategies],
                    "pacing": self.plan.pacing.value,
                    "focus_areas": [f.value for f in self.plan.focus_areas],
                    "strategy_confidence": self.plan.strategy_confidence,
                    "sessions_in_current_strategy": self.plan.sessions_in_current_strategy,
                    "strategy_start_date": self.plan.strategy_start_date.isoformat() if self.plan.strategy_start_date else None,
                    "max_tasks_per_session": self.plan.max_tasks_per_session,
                    "min_reflection_ratio": self.plan.min_reflection_ratio,
                    "challenge_level": self.plan.challenge_level,
                    "adaptation_triggers": self.plan.adaptation_triggers,
                    "last_adaptation": self.plan.last_adaptation.isoformat() if self.plan.last_adaptation else None,
                    "adaptation_count": self.plan.adaptation_count,
                    "strategy_history": self.plan.strategy_history[-20:],
                }
                
                supabase.table("coaching_plans").upsert(data, on_conflict="user_id").execute()
                logger.debug(f"Saved coaching plan for {self.user_id}")
        except Exception as e:
            logger.error(f"Failed to save coaching plan: {e}")
    
    def decide_strategy(self, context: Dict[str, Any]) -> CoachingDecision:
        """
        Select coaching strategy based on current context.
        Context includes: conversation_count, confidence scores, behavioral profile, etc.
        """
        if not self.plan:
            self._load_plan()
        
        # Enrich context with plan state
        enriched_context = {**context}
        enriched_context.update({
            "conversation_count": context.get("conversation_count", 0),
            "has_identity_profile": context.get("has_identity_profile", False),
            "trust_rapport": context.get("trust_rapport", 0.0),
            "burnout_risk": context.get("burnout_risk", 0.0),
            "procrastination_score": context.get("procrastination_score", 0.0),
            "readiness_for_action": context.get("readiness_for_action", 0.0),
            "goal_clarity": context.get("goal_clarity", 0.0),
            "active_tasks": context.get("active_tasks", 0),
            "avoidance_score": context.get("avoidance_score", 0.0),
            "perfectionism_score": context.get("perfectionism_score", 0.0),
            "momentum_score": context.get("momentum_score", 0.0),
            "follow_through_score": context.get("follow_through_score", 0.0),
            "consistency_score": context.get("consistency_score", 0.0),
            "overthinking_score": context.get("overthinking_score", 0.0),
        })
        
        # Evaluate rules in priority order
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)
        
        for rule in sorted_rules:
            try:
                if self._evaluate_condition(rule.condition, enriched_context):
                    # Check minimum duration
                    if self.plan.sessions_in_current_strategy < rule.min_duration_sessions:
                        # Continue current strategy but log that transition is pending
                        logger.debug(f"Rule {rule.name} matched but min duration not met")
                        continue
                    
                    # Check if this is a strategy change
                    is_new_strategy = rule.strategy != self.plan.primary_strategy
                    
                    decision = CoachingDecision(
                        strategy=rule.strategy,
                        pacing=rule.pacing,
                        focus_areas=rule.focus_areas,
                        avoid_areas=rule.avoid_areas,
                        max_tasks=rule.max_duration_sessions or 1,
                        reflection_ratio=0.5 if rule.pacing == CoachingPacing.SLOW else 0.3,
                        challenge_level=0.7 if rule.strategy == CoachingStrategy.CHALLENGE else 0.3,
                        reasoning=f"Rule '{rule.name}' matched: {rule.condition}",
                        confidence=0.8,
                        adaptation_needed=is_new_strategy,
                        adaptation_reason=rule.name if is_new_strategy else ""
                    )
                    
                    # Apply strategy if changed
                    if is_new_strategy:
                        self._transition_to_strategy(rule.strategy, rule.pacing, rule.focus_areas, rule.name)
                    
                    # Update session count
                    self.plan.sessions_in_current_strategy += 1
                    self._save_plan()
                    
                    logger.info(f"Coaching decision: {decision.strategy.value} (pacing: {decision.pacing.value})")
                    return decision
                    
            except Exception as e:
                logger.warning(f"Error evaluating rule '{rule.name}': {e}")
                continue
        
        # Default decision
        return CoachingDecision(
            strategy=self.plan.primary_strategy,
            pacing=self.plan.pacing,
            focus_areas=self.plan.focus_areas,
            max_tasks=self.plan.max_tasks_per_session,
            reflection_ratio=self.plan.min_reflection_ratio,
            challenge_level=self.plan.challenge_level,
            reasoning="Default: continuing current strategy",
            confidence=0.5
        )
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Safely evaluate a Python expression against context."""
        namespace = {
            **context,
            'True': True, 'False': False, 'None': None,
            'and': 'and', 'or': 'or', 'not': 'not',
        }
        try:
            result = eval(condition, {"__builtins__": {}}, namespace)
            return bool(result)
        except Exception as e:
            logger.warning(f"Condition evaluation failed: {condition} - {e}")
            return False
    
    def _transition_to_strategy(self, strategy: CoachingStrategy, pacing: CoachingPacing, 
                                focus_areas: List[CoachingFocus], trigger: str):
        """Transition to a new coaching strategy."""
        if not self.plan:
            return
        
        # Record history
        self.plan.strategy_history.append({
            "strategy": self.plan.primary_strategy.value,
            "start": self.plan.strategy_start_date.isoformat() if self.plan.strategy_start_date else None,
            "end": datetime.utcnow().isoformat(),
            "reason": f"Transitioned to {strategy.value}",
            "outcome": "pending",
            "sessions": self.plan.sessions_in_current_strategy
        })
        
        # Update plan
        self.plan.primary_strategy = strategy
        self.plan.pacing = pacing
        self.plan.focus_areas = focus_areas
        self.plan.strategy_confidence = 0.7
        self.plan.sessions_in_current_strategy = 0
        self.plan.strategy_start_date = datetime.utcnow()
        self.plan.last_adaptation = datetime.utcnow()
        self.plan.adaptation_count += 1
        self.plan.adaptation_triggers.append(trigger)
        
        # Adjust constraints based on strategy
        self._adjust_constraints_for_strategy(strategy)
        
        self._save_plan()
        logger.info(f"Strategy transition: {strategy.value} (trigger: {trigger})")
    
    def _adjust_constraints_for_strategy(self, strategy: CoachingStrategy):
        """Adjust plan constraints based on active strategy."""
        if strategy == CoachingStrategy.UNDERSTAND:
            self.plan.max_tasks_per_session = 0
            self.plan.min_reflection_ratio = 0.6
            self.plan.challenge_level = 0.1
        elif strategy == CoachingStrategy.REFLECT:
            self.plan.max_tasks_per_session = 0
            self.plan.min_reflection_ratio = 0.7
            self.plan.challenge_level = 0.2
        elif strategy == CoachingStrategy.CHALLENGE:
            self.plan.max_tasks_per_session = 1
            self.plan.min_reflection_ratio = 0.2
            self.plan.challenge_level = 0.8
        elif strategy == CoachingStrategy.CLARIFY:
            self.plan.max_tasks_per_session = 0
            self.plan.min_reflection_ratio = 0.4
            self.plan.challenge_level = 0.4
        elif strategy == CoachingStrategy.PLAN:
            self.plan.max_tasks_per_session = 2
            self.plan.min_reflection_ratio = 0.3
            self.plan.challenge_level = 0.5
        elif strategy == CoachingStrategy.EXECUTE:
            self.plan.max_tasks_per_session = 2
            self.plan.min_reflection_ratio = 0.1
            self.plan.challenge_level = 0.6
        elif strategy == CoachingStrategy.REVIEW:
            self.plan.max_tasks_per_session = 1
            self.plan.min_reflection_ratio = 0.5
            self.plan.challenge_level = 0.3
        elif strategy == CoachingStrategy.ADAPT:
            self.plan.max_tasks_per_session = 1
            self.plan.min_reflection_ratio = 0.4
            self.plan.challenge_level = 0.4
        elif strategy == CoachingStrategy.SUPPORT:
            self.plan.max_tasks_per_session = 0
            self.plan.min_reflection_ratio = 0.5
            self.plan.challenge_level = 0.1
        elif strategy == CoachingStrategy.EDUCATE:
            self.plan.max_tasks_per_session = 1
            self.plan.min_reflection_ratio = 0.3
            self.plan.challenge_level = 0.3
    
    def record_session_outcome(self, outcome: str, details: Dict[str, Any] = None):
        """Record outcome of a coaching session for learning."""
        if not self.plan or not self.plan.strategy_history:
            return
        
        # Update last strategy history entry
        last_entry = self.plan.strategy_history[-1]
        last_entry["outcome"] = outcome
        last_entry["details"] = details or {}
        
        self._save_plan()
    
    def get_current_strategy(self) -> CoachingStrategy:
        return self.plan.primary_strategy if self.plan else CoachingStrategy.UNDERSTAND
    
    def get_plan_summary(self) -> Dict[str, Any]:
        if not self.plan:
            return {}
        return {
            "primary_strategy": self.plan.primary_strategy.value,
            "secondary_strategies": [s.value for s in self.plan.secondary_strategies],
            "pacing": self.plan.pacing.value,
            "focus_areas": [f.value for f in self.plan.focus_areas],
            "sessions_in_current": self.plan.sessions_in_current_strategy,
            "max_tasks_per_session": self.plan.max_tasks_per_session,
            "min_reflection_ratio": self.plan.min_reflection_ratio,
            "challenge_level": self.plan.challenge_level,
            "adaptation_count": self.plan.adaptation_count,
        }
    
    def get_context_for_prompt(self) -> str:
        """Get formatted coaching context for LLM prompts."""
        if not self.plan:
            return ""
        
        parts = [
            f"COACHING STRATEGY: {self.plan.primary_strategy.value}",
            f"PACING: {self.plan.pacing.value}",
            f"FOCUS: {', '.join(f.value for f in self.plan.focus_areas)}" if self.plan.focus_areas else "",
            f"MAX TASKS THIS SESSION: {self.plan.max_tasks_per_session}",
            f"REFLECTION RATIO: {self.plan.min_reflection_ratio:.0%}",
            f"CHALLENGE LEVEL: {self.plan.challenge_level:.1f}",
        ]
        return "\n".join(p for p in parts if p)


# Global instance
coaching_planner = CoachingPlanner()