"""
ChitraGupta 2.0 — Policy Engine
Deterministic action selection before LLM calls.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from core.schemas.policy import (
    PolicyContext, PolicyDecision, PolicyAction, PolicyRule, DEFAULT_POLICY_RULES
)
from core.schemas.confidence import ConfidenceProfile, ConfidenceDimension
from core.schemas.behavior import BehavioralProfile
from core.schemas.identity import IdentityProfile
from core.schemas.coaching import CoachingPlan

logger = logging.getLogger("chitragupta.policy_engine")


class PolicyEngine:
    """
    Deterministic policy engine that decides what action to take
    before any LLM is invoked. Pure Python logic, no LLM calls.

    Anti-repetition (P3): keeps a per-user action streak so the same action is
    not repeated more than twice in a row. On the third consecutive repeat it
    injects a `wait`/`reflect` cooldown so the conversation does not loop.
    """
    
    def __init__(self, rules: Optional[List[PolicyRule]] = None):
        self.rules = rules or DEFAULT_POLICY_RULES
        self._last_decision: Optional[PolicyDecision] = None
        self._decision_history: List[PolicyDecision] = []
        # user_id -> list of recent actions (most recent last)
        self._user_action_streak: Dict[str, List[str]] = {}
        self._MAX_STREAK = 2  # after this many identical actions in a row, vary it
    
    def decide(self, context: PolicyContext) -> PolicyDecision:
        """
        Evaluate rules in priority order and return the first matching action.
        Applies an anti-repetition constraint so coaching does not become repetitive.
        """
        # Update context with derived values
        self._enrich_context(context)
        
        # Sort rules by priority (highest first)
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)
        
        for rule in sorted_rules:
            try:
                if self._evaluate_condition(rule.condition, context):
                    decision = PolicyDecision(
                        action=rule.action,
                        confidence=self._calculate_rule_confidence(rule, context),
                        reasoning=f"Rule '{rule.name}' matched: {rule.condition}",
                        parameters=rule.parameters.copy()
                    )
                    
                    # Add coaching strategy context if available
                    if hasattr(context, 'coaching_strategy') and context.coaching_strategy:
                        decision.coaching_strategy = context.coaching_strategy
                    if hasattr(context, 'pacing') and context.pacing:
                        decision.pacing = context.pacing

                    # Anti-repetition: vary the action if it's been the same too often
                    streak = self._user_action_streak.setdefault(context.user_id, [])
                    if (
                        rule.action == PolicyAction.ASK_QUESTION
                        and len(streak) >= self._MAX_STREAK
                        and all(a == PolicyAction.ASK_QUESTION.value for a in streak[-self._MAX_STREAK:])
                    ):
                        # Too many questions in a row -> reflect instead to break the loop
                        decision = PolicyDecision(
                            action=PolicyAction.REFLECT,
                            confidence=max(0.6, decision.confidence - 0.1),
                            reasoning=f"Rule '{rule.name}' matched, but switched to REFLECT to avoid repetitive questioning.",
                            parameters=rule.parameters.copy(),
                        )
                        decision.coaching_strategy = getattr(context, "coaching_strategy", None)
                        decision.pacing = getattr(context, "pacing", None)
                    elif streak and streak[-1] == rule.action.value and len(set(streak[-3:])) == 1 and len(streak) >= 3:
                        # Any action repeated 3x in a row -> wait to let the user speak
                        decision = PolicyDecision(
                            action=PolicyAction.WAIT,
                            confidence=0.5,
                            reasoning=f"Action '{rule.action.value}' repeated 3x - WAIT to let the user lead.",
                            parameters={},
                        )
                        decision.coaching_strategy = getattr(context, "coaching_strategy", None)
                        decision.pacing = getattr(context, "pacing", None)

                    self._last_decision = decision
                    self._decision_history.append(decision)

                    # Track action streak (bounded)
                    streak.append(decision.action.value)
                    if len(streak) > 10:
                        self._user_action_streak[context.user_id] = streak[-6:]
                    
                    # Keep history bounded
                    if len(self._decision_history) > 100:
                        self._decision_history = self._decision_history[-50:]
                    
                    logger.debug(f"Policy decision: {decision.action.value} (confidence: {decision.confidence:.2f})")
                    return decision
                    
            except Exception as e:
                logger.warning(f"Error evaluating rule '{rule.name}': {e}")
                continue
        
        # Fallback (should never reach here with default rules)
        return PolicyDecision(
            action=PolicyAction.WAIT,
            confidence=0.1,
            reasoning="No rules matched, defaulting to WAIT"
        )
    
    def _enrich_context(self, context: PolicyContext):
        """Add derived fields to context for rule evaluation."""
        # Add coaching strategy if available
        if not hasattr(context, 'coaching_strategy'):
            context.coaching_strategy = None
        if not hasattr(context, 'pacing'):
            context.pacing = None
        
        # Add behavioral scores as individual fields for rule access
        if context.behavioral_confidences:
            for pattern, conf in context.behavioral_confidences.items():
                # Only add _score suffix if not already ending with _score or _risk
                if pattern.endswith('_score') or pattern.endswith('_risk'):
                    setattr(context, pattern, conf)
                else:
                    setattr(context, f"{pattern}_score", conf)
        
        # Add identity profile flag
        if not hasattr(context, 'has_identity_profile'):
            context.has_identity_profile = context.identity_version > 0
    
    def _evaluate_condition(self, condition: str, context: PolicyContext) -> bool:
        """Safely evaluate a Python expression against context."""
        # Build evaluation namespace
        namespace = {
            **context.model_dump(),
            'True': True,
            'False': False,
            'None': None,
            'and': 'and',
            'or': 'or',
            'not': 'not',
        }
        
        # Add any missing attributes as False/0
        for key in ['procrastination_score', 'avoidance_score', 'perfectionism_score', 
                    'burnout_risk', 'momentum_score', 'follow_through_score',
                    'overthinking_score', 'consistency_score']:
            if key not in namespace:
                namespace[key] = 0.0
        
        try:
            result = eval(condition, {"__builtins__": {}}, namespace)
            return bool(result)
        except Exception as e:
            logger.warning(f"Condition evaluation failed: {condition} - {e}")
            return False
    
    def _calculate_rule_confidence(self, rule: PolicyRule, context: PolicyContext) -> float:
        """Calculate confidence in this rule's decision."""
        base_confidence = 0.7
        
        # Higher priority rules get slight confidence boost
        priority_boost = min(rule.priority / 200, 0.2)
        
        # Context richness boost
        richness = min(context.conversation_count / 20, 0.1)
        
        return min(base_confidence + priority_boost + richness, 0.95)
    
    def get_last_decision(self) -> Optional[PolicyDecision]:
        return self._last_decision
    
    def get_decision_history(self, limit: int = 10) -> List[PolicyDecision]:
        return self._decision_history[-limit:]
    
    def add_custom_rule(self, rule: PolicyRule):
        """Add a custom rule to the engine."""
        self.rules.append(rule)
        # Re-sort by priority
        self.rules.sort(key=lambda r: r.priority, reverse=True)
    
    def remove_rule(self, rule_name: str) -> bool:
        """Remove a rule by name."""
        for i, rule in enumerate(self.rules):
            if rule.name == rule_name:
                self.rules.pop(i)
                return True
        return False


# Global instance
policy_engine = PolicyEngine()