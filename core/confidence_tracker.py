"""
ChitraGupta 2.0 — Confidence Tracker
Multi-dimensional confidence tracking with evidence-based updates.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict

from core.schemas.confidence import (
    ConfidenceProfile, ConfidenceScore, ConfidenceDimension, ConfidenceEvidence,
    CONFIDENCE_THRESHOLDS, EVIDENCE_WEIGHTS
)

logger = logging.getLogger("chitragupta.confidence_tracker")


class ConfidenceTracker:
    """
    Tracks confidence across multiple dimensions with evidence-based updates.
    Only reduces uncertainty through targeted questioning/inference.
    """
    
    def __init__(self, user_id: str = "default_user"):
        self.user_id = user_id
        self.profile = ConfidenceProfile(user_id=user_id)
        self._initialize_dimensions()
        self._evidence_buffer: List[ConfidenceEvidence] = []
    
    def _initialize_dimensions(self):
        """Initialize all confidence dimensions with defaults."""
        for dim in ConfidenceDimension:
            thresholds = CONFIDENCE_THRESHOLDS.get(dim, {"action": 0.7, "question": 0.4, "critical": 0.2})
            self.profile.scores[dim] = ConfidenceScore(
                dimension=dim,
                score=0.0,
                action_threshold=thresholds["action"],
                question_threshold=thresholds["question"],
                critical_threshold=thresholds["critical"]
            )
        self._recalculate_composites()
    
    def add_evidence(self, evidence: ConfidenceEvidence):
        """Add evidence and update relevant confidence dimension."""
        dim = evidence.dimension
        if dim not in self.profile.scores:
            logger.warning(f"Unknown confidence dimension: {dim}")
            return
        
        score_obj = self.profile.scores[dim]
        old_score = score_obj.score
        
        # Calculate weight
        source_weight = EVIDENCE_WEIGHTS.get(evidence.source, 0.5)
        weighted_impact = evidence.impact * evidence.confidence * source_weight
        
        # Update score with momentum (gradual changes)
        new_score = score_obj.score + weighted_impact * 0.3  # 30% step size
        new_score = max(0.0, min(1.0, new_score))
        
        # Update score object
        score_obj.score = new_score
        score_obj.evidence_count += 1
        if weighted_impact > 0:
            score_obj.positive_evidence += 1
        else:
            score_obj.negative_evidence += 1
        score_obj.last_updated = datetime.utcnow()
        
        # Determine trend
        if new_score > old_score + 0.05:
            score_obj.trend = "increasing"
        elif new_score < old_score - 0.05:
            score_obj.trend = "decreasing"
        else:
            score_obj.trend = "stable"
        
        # Update volatility
        score_obj.volatility = abs(new_score - old_score) * 0.5 + score_obj.volatility * 0.5
        
        # Record history
        self.profile.score_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "dimension": dim.value,
            "old_score": old_score,
            "new_score": new_score,
            "evidence": evidence.description,
            "source": evidence.source
        })
        
        # Keep history bounded
        if len(self.profile.score_history) > 200:
            self.profile.score_history = self.profile.score_history[-100:]
        
        # Update composite scores and gaps
        self._recalculate_composites()
        
        logger.debug(f"Confidence updated: {dim.value} {old_score:.2f} -> {new_score:.2f} (impact: {weighted_impact:.3f})")
    
    def add_evidence_batch(self, evidence_list: List[ConfidenceEvidence]):
        """Add multiple pieces of evidence at once."""
        for evidence in evidence_list:
            self.add_evidence(evidence)
    
    def infer_from_conversation(self, user_input: str, context: Dict[str, Any]) -> List[ConfidenceEvidence]:
        """
        Infer confidence evidence from conversation content.
        Returns list of evidence to add.
        """
        evidence = []
        user_lower = user_input.lower()
        
        # Goal clarity evidence
        goal_indicators = ["want to", "goal is", "aim to", "trying to", "want to achieve"]
        if any(ind in user_lower for ind in goal_indicators):
            evidence.append(ConfidenceEvidence(
                dimension=ConfidenceDimension.GOAL_CLARITY,
                source="conversation",
                description=f"User expressed goal: {user_input[:100]}",
                impact=0.3,
                confidence=0.7,
                context={"input": user_input}
            ))
        
        # Constraint clarity
        constraint_indicators = ["can't", "cannot", "unable to", "limited by", "constraint", "restriction"]
        if any(ind in user_lower for ind in constraint_indicators):
            evidence.append(ConfidenceEvidence(
                dimension=ConfidenceDimension.CONSTRAINT_CLARITY,
                source="conversation",
                description=f"User mentioned constraint: {user_input[:100]}",
                impact=0.25,
                confidence=0.6,
                context={"input": user_input}
            ))
        
        # Habit clarity
        habit_indicators = ["usually", "always", "habit", "routine", "every day", "daily"]
        if any(ind in user_lower for ind in habit_indicators):
            evidence.append(ConfidenceEvidence(
                dimension=ConfidenceDimension.HABIT_CLARITY,
                source="conversation",
                description=f"User described habit/routine: {user_input[:100]}",
                impact=0.2,
                confidence=0.6,
                context={"input": user_input}
            ))
        
        # Identity clarity
        identity_indicators = ["i am", "i see myself", "my identity", "as a person", "who i am"]
        if any(ind in user_lower for ind in identity_indicators):
            evidence.append(ConfidenceEvidence(
                dimension=ConfidenceDimension.IDENTITY_CLARITY,
                source="conversation",
                description=f"User expressed self-identity: {user_input[:100]}",
                impact=0.25,
                confidence=0.7,
                context={"input": user_input}
            ))
        
        # Motivation clarity
        motivation_indicators = ["because", "reason", "why", "motivated by", "driven by", "care about"]
        if any(ind in user_lower for ind in motivation_indicators):
            evidence.append(ConfidenceEvidence(
                dimension=ConfidenceDimension.MOTIVATION_CLARITY,
                source="conversation",
                description=f"User explained motivation: {user_input[:100]}",
                impact=0.2,
                confidence=0.6,
                context={"input": user_input}
            ))
        
        # Readiness for action
        action_indicators = ["ready to", "will do", "going to", "let's do", "start", "begin"]
        if any(ind in user_lower for ind in action_indicators):
            evidence.append(ConfidenceEvidence(
                dimension=ConfidenceDimension.READINESS_FOR_ACTION,
                source="conversation",
                description=f"User expressed readiness: {user_input[:100]}",
                impact=0.3,
                confidence=0.7,
                context={"input": user_input}
            ))
        
        # Trust/rapport (positive engagement)
        trust_indicators = ["thanks", "thank you", "helpful", "makes sense", "agree", "yes", "exactly"]
        if any(ind in user_lower for ind in trust_indicators):
            evidence.append(ConfidenceEvidence(
                dimension=ConfidenceDimension.TRUST_RAPPORT,
                source="conversation",
                description=f"Positive engagement signal: {user_input[:100]}",
                impact=0.1,
                confidence=0.5,
                context={"input": user_input}
            ))
        
        # Conversation depth
        depth_indicators = ["actually", "really", "deep down", "honestly", "vulnerable", "struggle", "fear"]
        if any(ind in user_lower for ind in depth_indicators):
            evidence.append(ConfidenceEvidence(
                dimension=ConfidenceDimension.CONVERSATION_DEPTH,
                source="conversation",
                description=f"Deep/sharing moment: {user_input[:100]}",
                impact=0.15,
                confidence=0.6,
                context={"input": user_input}
            ))
        
        return evidence
    
    def infer_from_task_outcome(self, task_outcome: Dict[str, Any]) -> List[ConfidenceEvidence]:
        """Infer confidence evidence from task completion/failure."""
        evidence = []
        completed = task_outcome.get("completed", False)
        task_type = task_outcome.get("task_type", "unknown")
        difficulty = task_outcome.get("difficulty", "medium")
        
        if completed:
            # Task completion increases readiness and follow-through
            evidence.append(ConfidenceEvidence(
                dimension=ConfidenceDimension.READINESS_FOR_ACTION,
                source="task_completion",
                description=f"Completed {task_type} task ({difficulty})",
                impact=0.2,
                confidence=0.8,
                context=task_outcome
            ))
            
            evidence.append(ConfidenceEvidence(
                dimension=ConfidenceDimension.GOAL_CLARITY,
                source="task_completion",
                description=f"Action aligned with goal via {task_type} task",
                impact=0.1,
                confidence=0.6,
                context=task_outcome
            ))
        else:
            # Task failure may indicate constraint or readiness issues
            evidence.append(ConfidenceEvidence(
                dimension=ConfidenceDimension.READINESS_FOR_ACTION,
                source="task_failure",
                description=f"Failed to complete {task_type} task ({difficulty})",
                impact=-0.15,
                confidence=0.7,
                context=task_outcome
            ))
            
            evidence.append(ConfidenceEvidence(
                dimension=ConfidenceDimension.CONSTRAINT_CLARITY,
                source="task_failure",
                description=f"Possible hidden constraint blocked {task_type} task",
                impact=-0.1,
                confidence=0.5,
                context=task_outcome
            ))
        
        return evidence
    
    def infer_from_daily_review(self, review_data: Dict[str, Any]) -> List[ConfidenceEvidence]:
        """Infer confidence from daily review outcomes."""
        evidence = []
        completion_rate = review_data.get("completion_rate", 0)
        insights = review_data.get("insights", [])
        
        # Overall readiness from completion rate
        if completion_rate > 0.7:
            impact = 0.15
        elif completion_rate > 0.4:
            impact = 0.05
        else:
            impact = -0.1
        
        evidence.append(ConfidenceEvidence(
            dimension=ConfidenceDimension.READINESS_FOR_ACTION,
            source="daily_review",
            description=f"Daily completion rate: {completion_rate:.0%}",
            impact=impact,
            confidence=0.8,
            context={"completion_rate": completion_rate}
        ))
        
        # Pattern insights
        for insight in insights:
            if "procrastinat" in insight.lower():
                evidence.append(ConfidenceEvidence(
                    dimension=ConfidenceDimension.READINESS_FOR_ACTION,
                    source="daily_review",
                    description=f"Procrastination pattern identified: {insight}",
                    impact=-0.2,
                    confidence=0.7,
                    context={"insight": insight}
                ))
            if "avoid" in insight.lower():
                evidence.append(ConfidenceEvidence(
                    dimension=ConfidenceDimension.CONSTRAINT_CLARITY,
                    source="daily_review",
                    description=f"Avoidance pattern: {insight}",
                    impact=-0.15,
                    confidence=0.6,
                    context={"insight": insight}
                ))
        
        return evidence
    
    def _recalculate_composites(self):
        """Recalculate composite scores and gaps."""
        scores = self.profile.scores
        
        # Overall clarity (average of clarity dimensions)
        clarity_dims = [
            ConfidenceDimension.GOAL_CLARITY,
            ConfidenceDimension.CONSTRAINT_CLARITY,
            ConfidenceDimension.HABIT_CLARITY,
            ConfidenceDimension.IDENTITY_CLARITY,
            ConfidenceDimension.MOTIVATION_CLARITY,
            ConfidenceDimension.ROUTINE_CLARITY,
        ]
        clarity_values = [scores[d].score for d in clarity_dims if d in scores]
        self.profile.overall_clarity = sum(clarity_values) / len(clarity_values) if clarity_values else 0
        
        # Overall readiness
        readiness_dims = [
            ConfidenceDimension.READINESS_FOR_ACTION,
            ConfidenceDimension.TRUST_RAPPORT,
            ConfidenceDimension.CONVERSATION_DEPTH,
        ]
        readiness_values = [scores[d].score for d in readiness_dims if d in scores]
        self.profile.overall_readiness = sum(readiness_values) / len(readiness_values) if readiness_values else 0
        
        # Trust level
        self.profile.trust_level = scores.get(ConfidenceDimension.TRUST_RAPPORT, ConfidenceScore(dimension=ConfidenceDimension.TRUST_RAPPORT)).score
        
        # Identify gaps and strengths
        self.profile.clarity_gaps = [
            d for d in clarity_dims 
            if d in scores and scores[d].score < scores[d].question_threshold
        ]
        self.profile.critical_gaps = [
            d for d in clarity_dims
            if d in scores and scores[d].score < scores[d].critical_threshold
        ]
        self.profile.clarity_strengths = [
            d for d in clarity_dims
            if d in scores and scores[d].score > scores[d].action_threshold
        ]
        
        self.profile.updated_at = datetime.utcnow()
    
    def get_score(self, dimension: ConfidenceDimension) -> float:
        """Get current confidence score for a dimension."""
        return self.profile.scores.get(dimension, ConfidenceScore(dimension=dimension)).score
    
    def get_all_scores(self) -> Dict[str, float]:
        """Get all confidence scores as dict."""
        return {dim.value: score.score for dim, score in self.profile.scores.items()}
    
    def should_ask_about(self, dimension: ConfidenceDimension) -> bool:
        """Check if we should ask a question to improve this dimension."""
        score_obj = self.profile.scores.get(dimension)
        if not score_obj:
            return True
        return score_obj.score < score_obj.question_threshold
    
    def can_act_on(self, dimension: ConfidenceDimension) -> bool:
        """Check if we have enough confidence to act on this dimension."""
        score_obj = self.profile.scores.get(dimension)
        if not score_obj:
            return False
        return score_obj.score >= score_obj.action_threshold
    
    def get_top_gaps(self, limit: int = 3) -> List[ConfidenceDimension]:
        """Get top confidence gaps to address."""
        gaps = self.profile.clarity_gaps + self.profile.critical_gaps
        # Sort by severity (critical first, then by score ascending)
        gaps.sort(key=lambda d: (
            0 if d in self.profile.critical_gaps else 1,
            self.profile.scores[d].score
        ))
        return gaps[:limit]
    
    def get_profile_dict(self) -> Dict[str, Any]:
        """Get profile as serializable dict."""
        return {
            "user_id": self.profile.user_id,
            "scores": {dim.value: score.score for dim, score in self.profile.scores.items()},
            "overall_clarity": self.profile.overall_clarity,
            "overall_readiness": self.profile.overall_readiness,
            "trust_level": self.profile.trust_level,
            "clarity_gaps": [d.value for d in self.profile.clarity_gaps],
            "critical_gaps": [d.value for d in self.profile.critical_gaps],
            "clarity_strengths": [d.value for d in self.profile.clarity_strengths],
            "updated_at": self.profile.updated_at.isoformat()
        }


# Global instance
confidence_tracker = ConfidenceTracker()