"""
ChitraGupta 2.0 — Behavioral Inference
Deterministic pattern detection from conversation + task history.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter

from core.schemas.behavior import (
    BehaviorPattern, BehavioralProfile, BehavioralPatternResult, PatternEvidence,
    BEHAVIORAL_DETECTION_RULES
)
from core.utils.supabase_client import get_supabase_client

logger = logging.getLogger("chitragupta.behavioral_inference")


class BehavioralInference:
    """
    Detects behavioral patterns from task history and conversation.
    Pure deterministic logic - no LLM calls.
    """
    
    def __init__(self, user_id: str = "default_user"):
        self.user_id = user_id
        self.profile: Optional[BehavioralProfile] = None
        self._load_profile()
    
    def _load_profile(self):
        """Load behavioral profile from Supabase."""
        try:
            supabase = get_supabase_client()
            if supabase:
                response = supabase.table("behavioral_profiles").select("*").eq("user_id", self.user_id).execute()
                if response.data:
                    data = response.data[0]
                    # Reconstruct profile
                    self.profile = BehavioralProfile(user_id=self.user_id)
                    self.profile.updated_at = datetime.fromisoformat(data.get("updated_at", datetime.utcnow().isoformat()))
                    
                    # Load patterns
                    patterns_data = data.get("patterns", {})
                    for pattern_str, pattern_data in patterns_data.items():
                        try:
                            pattern = BehaviorPattern(pattern_str)
                            self.profile.patterns[pattern] = BehavioralPatternResult(**pattern_data)
                        except ValueError:
                            continue
                    
                    # Load composite scores
                    for field in ["procrastination_score", "avoidance_score", "perfectionism_score",
                                 "burnout_risk", "consistency_score", "follow_through_score",
                                 "motivation_quality", "emotional_stability"]:
                        if field in data:
                            setattr(self.profile, field, data[field])
                    
                    # Load derived insights
                    self.profile.primary_pattern = BehaviorPattern(data["primary_pattern"]) if data.get("primary_pattern") else None
                    self.profile.secondary_patterns = [BehaviorPattern(p) for p in data.get("secondary_patterns", [])]
                    self.profile.risk_factors = data.get("risk_factors", [])
                    self.profile.protective_factors = data.get("protective_factors", [])
                    
                    # Load coaching implications
                    self.profile.recommended_pacing = data.get("recommended_pacing", "moderate")
                    self.profile.recommended_approach = data.get("recommended_approach", "balanced")
                    self.profile.task_difficulty_preference = data.get("task_difficulty_preference", "micro")
                    self.profile.feedback_style = data.get("feedback_style", "encouraging")
                    
                    logger.info(f"Loaded behavioral profile for {self.user_id}")
                    return
        except Exception as e:
            logger.warning(f"Failed to load behavioral profile: {e}")
        
        # Create new profile
        self.profile = BehavioralProfile(user_id=self.user_id)
        logger.info(f"Created new behavioral profile for {self.user_id}")
    
    def _save_profile(self):
        """Save behavioral profile to Supabase."""
        try:
            supabase = get_supabase_client()
            if supabase and self.profile:
                self.profile.updated_at = datetime.utcnow()
                
                # Serialize patterns
                patterns_data = {}
                for pattern, result in self.profile.patterns.items():
                    patterns_data[pattern.value] = result.model_dump()
                
                data = {
                    "user_id": self.user_id,
                    "updated_at": self.profile.updated_at.isoformat(),
                    "patterns": patterns_data,
                    "procrastination_score": self.profile.procrastination_score,
                    "avoidance_score": self.profile.avoidance_score,
                    "perfectionism_score": self.profile.perfectionism_score,
                    "burnout_risk": self.profile.burnout_risk,
                    "consistency_score": self.profile.consistency_score,
                    "follow_through_score": self.profile.follow_through_score,
                    "motivation_quality": self.profile.motivation_quality,
                    "emotional_stability": self.profile.emotional_stability,
                    "primary_pattern": self.profile.primary_pattern.value if self.profile.primary_pattern else None,
                    "secondary_patterns": [p.value for p in self.profile.secondary_patterns],
                    "risk_factors": self.profile.risk_factors,
                    "protective_factors": self.profile.protective_factors,
                    "recommended_pacing": self.profile.recommended_pacing,
                    "recommended_approach": self.profile.recommended_approach,
                    "task_difficulty_preference": self.profile.task_difficulty_preference,
                    "feedback_style": self.profile.feedback_style,
                    "pattern_history": self.profile.pattern_history[-50:],  # Keep last 50
                }
                
                supabase.table("behavioral_profiles").upsert(data, on_conflict="user_id").execute()
                logger.debug(f"Saved behavioral profile for {self.user_id}")
        except Exception as e:
            logger.error(f"Failed to save behavioral profile: {e}")
    
    def analyze_task_history(self, tasks: List[Dict[str, Any]]) -> List[BehavioralPatternResult]:
        """Analyze task history for behavioral patterns."""
        if not tasks:
            return []
        
        results = []
        now = datetime.utcnow()
        
        # Prepare task data
        completed_tasks = [t for t in tasks if t.get("status") == "completed" or t.get("completed")]
        pending_tasks = [t for t in tasks if not t.get("completed") and t.get("status") != "completed"]
        all_tasks = tasks
        
        # Calculate basic metrics
        total_tasks = len(all_tasks)
        completion_rate = len(completed_tasks) / total_tasks if total_tasks > 0 else 0
        
        # Check each pattern
        for pattern, rules in BEHAVIORAL_DETECTION_RULES.items():
            evidence = []
            
            # Task-based indicators
            for indicator in rules.get("task_indicators", []):
                ev = self._check_task_indicator(indicator, all_tasks, completed_tasks, pending_tasks)
                if ev:
                    evidence.append(ev)
            
            # Conversation-based indicators (would need conversation history)
            # For now, we'll skip or use placeholder
            
            # Evaluate if pattern is present
            if len(evidence) >= rules["thresholds"]["min_evidence_count"]:
                # Calculate confidence
                avg_strength = sum(e.strength for e in evidence) / len(evidence)
                confidence = min(avg_strength, 1.0)
                
                if confidence >= rules["thresholds"]["min_confidence"]:
                    result = BehavioralPatternResult(
                        pattern=pattern,
                        confidence=confidence,
                        evidence=evidence,
                        first_detected=min(e.timestamp for e in evidence),
                        last_reinforced=max(e.timestamp for e in evidence),
                        frequency=len(evidence),
                        trend=self._calculate_trend(pattern, evidence),
                        description=self._generate_pattern_description(pattern, evidence),
                        suggested_interventions=self._get_interventions(pattern),
                        coaching_notes=self._get_coaching_notes(pattern)
                    )
                    results.append(result)
        
        return results
    
    def _check_task_indicator(self, indicator: str, all_tasks: List[Dict], 
                             completed: List[Dict], pending: List[Dict]) -> Optional[PatternEvidence]:
        """Check a specific task-based behavioral indicator."""
        now = datetime.utcnow()
        
        try:
            if indicator == "task_created_but_not_started_within_24h":
                count = 0
                for task in pending:
                    created = task.get("created_at")
                    if created:
                        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                        if (now - created_dt).total_seconds() > 86400:  # 24 hours
                            count += 1
                if count >= 2:
                    return PatternEvidence(
                        pattern=BehaviorPattern.PROCRASTINATION,
                        source="task_history",
                        description=f"{count} tasks not started within 24 hours",
                        strength=min(0.5 + count * 0.1, 1.0),
                        context={"count": count}
                    )
            
            elif indicator == "task_repeatedly_rescheduled":
                # Check for tasks with multiple updated_at timestamps
                count = 0
                for task in all_tasks:
                    if task.get("reschedule_count", 0) > 1:
                        count += 1
                if count >= 2:
                    return PatternEvidence(
                        pattern=BehaviorPattern.PROCRASTINATION,
                        source="task_history",
                        description=f"{count} tasks rescheduled multiple times",
                        strength=min(0.5 + count * 0.1, 1.0),
                        context={"count": count}
                    )
            
            elif indicator == "high_priority_tasks_consistently_delayed":
                high_priority = [t for t in all_tasks if t.get("priority") in ["high", "critical"]]
                delayed = [t for t in high_priority if not t.get("completed")]
                if len(high_priority) >= 3 and len(delayed) / len(high_priority) > 0.5:
                    return PatternEvidence(
                        pattern=BehaviorPattern.PROCRASTINATION,
                        source="task_history",
                        description=f"{len(delayed)}/{len(high_priority)} high-priority tasks delayed",
                        strength=0.7,
                        context={"delayed": len(delayed), "total_high_priority": len(high_priority)}
                    )
            
            elif indicator == "many_tasks_in_backlog":
                if len(pending) > 10:
                    return PatternEvidence(
                        pattern=BehaviorPattern.PROCRASTINATION,
                        source="task_history",
                        description=f"Large backlog: {len(pending)} pending tasks",
                        strength=min(0.4 + len(pending) * 0.02, 1.0),
                        context={"pending_count": len(pending)}
                    )
            
            elif indicator == "tasks_abandoned_without_completion":
                abandoned = [t for t in all_tasks if t.get("status") == "abandoned"]
                if len(abandoned) >= 2:
                    return PatternEvidence(
                        pattern=BehaviorPattern.AVOIDANCE,
                        source="task_history",
                        description=f"{len(abandoned)} tasks abandoned",
                        strength=min(0.5 + len(abandoned) * 0.1, 1.0),
                        context={"abandoned_count": len(abandoned)}
                    )
            
            elif indicator == "difficult_tasks_never_attempted":
                hard_tasks = [t for t in all_tasks if t.get("difficulty") in ["challenging", "difficult"]]
                unattempted = [t for t in hard_tasks if t.get("status") == "pending"]
                if len(hard_tasks) >= 2 and len(unattempted) == len(hard_tasks):
                    return PatternEvidence(
                        pattern=BehaviorPattern.AVOIDANCE,
                        source="task_history",
                        description=f"All {len(hard_tasks)} difficult tasks unattempted",
                        strength=0.8,
                        context={"difficult_count": len(hard_tasks)}
                    )
            
            elif indicator == "consistently_chooses_easier_alternatives":
                # Check if user creates easy tasks but not hard ones
                easy_completed = len([t for t in completed if t.get("difficulty") in ["trivial", "easy"]])
                hard_completed = len([t for t in completed if t.get("difficulty") in ["challenging", "difficult"]])
                if easy_completed >= 3 and hard_completed == 0:
                    return PatternEvidence(
                        pattern=BehaviorPattern.AVOIDANCE,
                        source="task_history",
                        description=f"Completed {easy_completed} easy tasks, 0 hard tasks",
                        strength=0.7,
                        context={"easy_completed": easy_completed, "hard_completed": hard_completed}
                    )
            
            elif indicator == "tasks_marked_incomplete_due_to_not_perfect":
                # Would need specific tracking - placeholder
                pass
            
            elif indicator == "excessive_planning_before_starting":
                # Check for tasks with many sub_tasks but not started
                planned_not_started = [t for t in pending if len(t.get("sub_tasks", [])) > 5 and not t.get("started_at")]
                if len(planned_not_started) >= 2:
                    return PatternEvidence(
                        pattern=BehaviorPattern.PERFECTIONISM,
                        source="task_history",
                        description=f"{len(planned_not_started)} heavily planned tasks not started",
                        strength=0.6,
                    context={"count": len(planned_not_started)}
                    )
            
            elif indicator == "repeatedly_revises_same_task":
                # Placeholder - would need revision tracking
                pass
            
            elif indicator == "sudden_drop_in_completion_rate":
                # Compare last 7 days vs previous 7 days
                recent_cutoff = now - timedelta(days=7)
                previous_cutoff = now - timedelta(days=14)
                
                recent_tasks = [t for t in all_tasks if t.get("created_at") and 
                               datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")) > recent_cutoff]
                previous_tasks = [t for t in all_tasks if t.get("created_at") and 
                                 previous_cutoff < datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")) <= recent_cutoff]
                
                recent_rate = len([t for t in recent_tasks if t.get("completed")]) / len(recent_tasks) if recent_tasks else 0
                previous_rate = len([t for t in previous_tasks if t.get("completed")]) / len(previous_tasks) if previous_tasks else 0
                
                if previous_rate > 0.5 and recent_rate < previous_rate * 0.5:
                    return PatternEvidence(
                        pattern=BehaviorPattern.BURNOUT,
                        source="task_history",
                        description=f"Completion rate dropped from {previous_rate:.0%} to {recent_rate:.0%}",
                        strength=0.8,
                        context={"previous_rate": previous_rate, "recent_rate": recent_rate}
                    )
            
            elif indicator == "previously_consistent_user_stops_engaging":
                # Check if user had good streak then stopped
                pass
            
            elif indicator == "tasks_take_much_longer_than_estimated":
                overruns = [t for t in completed if t.get("actual_duration_minutes", 0) > t.get("estimated_duration_minutes", 1) * 2]
                if len(overruns) >= 3:
                    return PatternEvidence(
                        pattern=BehaviorPattern.BURNOUT,
                        source="task_history",
                        description=f"{len(overruns)} tasks took 2x+ estimated time",
                        strength=0.7,
                        context={"overrun_count": len(overruns)}
                    )
            
            elif indicator == "long_deliberation_before_simple_tasks":
                # Placeholder - would need timing data
                pass
            
            elif indicator == "asks_many_clarifying_questions":
                # Would need conversation data
                pass
            
            elif indicator == "creates_complex_plans_for_simple_goals":
                # Check for tasks with many subtasks for simple goals
                complex_simple = [t for t in all_tasks if len(t.get("sub_tasks", [])) > 7 and t.get("task_type") == "micro"]
                if len(complex_simple) >= 2:
                    return PatternEvidence(
                        pattern=BehaviorPattern.OVERTHINKING,
                        source="task_history",
                        description=f"{len(complex_simple)} micro-tasks with 7+ subtasks",
                        strength=0.6,
                        context={"count": len(complex_simple)}
                    )
            
            elif indicator == "only_completes_tasks_when_acknowledged":
                # Placeholder - would need social features
                pass
            
            elif indicator == "shares_progress_excessively":
                # Placeholder
                pass
            
            elif indicator == "high_variance_in_daily_completion":
                # Calculate daily completion variance over last 14 days
                daily_completions = defaultdict(int)
                daily_totals = defaultdict(int)
                
                for task in all_tasks:
                    if task.get("created_at"):
                        try:
                            task_date = datetime.fromisoformat(task["created_at"].replace("Z", "+00:00")).date()
                            daily_totals[task_date] += 1
                            if task.get("completed"):
                                daily_completions[task_date] += 1
                        except:
                            continue
                
                rates = []
                for d in daily_totals:
                    if daily_totals[d] > 0:
                        rates.append(daily_completions[d] / daily_totals[d])
                
                if len(rates) >= 5:
                    import statistics
                    variance = statistics.variance(rates) if len(rates) > 1 else 0
                    if variance > 0.15:  # High variance
                        return PatternEvidence(
                            pattern=BehaviorPattern.INCONSISTENCY,
                            source="task_history",
                            description=f"High daily completion variance: {variance:.2f}",
                            strength=min(0.5 + variance, 1.0),
                            context={"variance": variance, "days_tracked": len(rates)}
                        )
            
            elif indicator == "streaks_broken_frequently":
                # Track consecutive completion days
                pass
            
            elif indicator == "pattern_of_start_stop":
                # Check for alternating periods of activity/inactivity
                pass
            
            elif indicator == "completion_begets_completion":
                # Check if completions cluster
                completed_dates = []
                for task in completed:
                    if task.get("completed_at"):
                        try:
                            completed_dates.append(datetime.fromisoformat(task["completed_at"].replace("Z", "+00:00")).date())
                        except:
                            pass
                
                if len(completed_dates) >= 5:
                    completed_dates.sort()
                    streaks = 1
                    max_streak = 1
                    for i in range(1, len(completed_dates)):
                        if (completed_dates[i] - completed_dates[i-1]).days <= 1:
                            streaks += 1
                            max_streak = max(max_streak, streaks)
                        else:
                            streaks = 1
                    
                    if max_streak >= 3:
                        return PatternEvidence(
                            pattern=BehaviorPattern.MOMENTUM,
                            source="task_history",
                            description=f"Longest completion streak: {max_streak} days",
                            strength=min(0.5 + max_streak * 0.1, 1.0),
                            context={"max_streak": max_streak}
                        )
            
            elif indicator == "increasing_task_difficulty_over_time":
                # Check if user takes on harder tasks over time
                pass
            
            elif indicator == "rejects_suggested_tasks":
                # Would need task suggestion tracking
                pass
            
            elif indicator == "modifies_tasks_significantly":
                modified = [t for t in all_tasks if t.get("modified_count", 0) > 2]
                if len(modified) >= 3:
                    return PatternEvidence(
                        pattern=BehaviorPattern.RESISTANCE,
                        source="task_history",
                        description=f"{len(modified)} tasks modified 3+ times",
                        strength=0.7,
                        context={"modified_count": len(modified)}
                    )
            
            elif indicator == "pushes_back_on_structure":
                # Would need conversation data
                pass
            
            elif indicator == "high_completion_rate_for_committed_tasks":
                committed = [t for t in all_tasks if t.get("user_committed", False)]
                committed_completed = [t for t in committed if t.get("completed")]
                if len(committed) >= 3 and len(committed_completed) / len(committed) > 0.8:
                    return PatternEvidence(
                        pattern=BehaviorPattern.FOLLOW_THROUGH_TENDENCY,
                        source="task_history",
                        description=f"Completed {len(committed_completed)}/{len(committed)} committed tasks",
                        strength=0.8,
                        context={"completion_rate": len(committed_completed) / len(committed)}
                    )
            
            elif indicator == "low_abandonment_rate":
                abandoned = [t for t in all_tasks if t.get("status") == "abandoned"]
                if len(all_tasks) >= 5 and len(abandoned) / len(all_tasks) < 0.1:
                    return PatternEvidence(
                        pattern=BehaviorPattern.FOLLOW_THROUGH_TENDENCY,
                        source="task_history",
                        description=f"Low abandonment rate: {len(abandoned)}/{len(all_tasks)}",
                        strength=0.7,
                        context={"abandonment_rate": len(abandoned) / len(all_tasks)}
                    )
            
            elif indicator == "completes_easy_tasks_avoids_hard":
                easy_done = len([t for t in completed if t.get("difficulty") in ["trivial", "easy"]])
                hard_total = len([t for t in all_tasks if t.get("difficulty") in ["challenging", "difficult"]])
                hard_done = len([t for t in completed if t.get("difficulty") in ["challenging", "difficult"]])
                if easy_done >= 3 and hard_total >= 2 and hard_done == 0:
                    return PatternEvidence(
                        pattern=BehaviorPattern.TASK_FRICTION_SENSITIVITY,
                        source="task_history",
                        description=f"Does {easy_done} easy tasks but 0/{hard_total} hard tasks",
                        strength=0.8,
                        context={"easy_done": easy_done, "hard_total": hard_total}
                    )
            
            elif indicator == "abandons_when_friction_encountered":
                # Tasks abandoned after starting
                started_abandoned = [t for t in all_tasks if t.get("started_at") and t.get("status") == "abandoned"]
                if len(started_abandoned) >= 2:
                    return PatternEvidence(
                        pattern=BehaviorPattern.TASK_FRICTION_SENSITIVITY,
                        source="task_history",
                        description=f"{len(started_abandoned)} tasks abandoned after starting",
                        strength=0.7,
                        context={"count": len(started_abandoned)}
                    )
            
            elif indicator == "needs_very_specific_instructions":
                # Tasks with very detailed sub_tasks completed vs vague ones
                pass
        
        except Exception as e:
            logger.warning(f"Error checking indicator {indicator}: {e}")
        
        return None
    
    def analyze_conversation(self, messages: List[Dict[str, Any]]) -> List[BehavioralPatternResult]:
        """Analyze conversation for behavioral patterns (placeholder for NLP)."""
        # This would use NLP/regex in production
        # For now, return empty - patterns from task history are primary
        return []
    
    def _calculate_trend(self, pattern: BehaviorPattern, evidence: List[PatternEvidence]) -> str:
        """Calculate trend for a pattern based on evidence timestamps."""
        if len(evidence) < 2:
            return "stable"
        
        # Sort by timestamp
        sorted_ev = sorted(evidence, key=lambda e: e.timestamp)
        recent = sorted_ev[-3:]  # Last 3 pieces
        older = sorted_ev[:-3] if len(sorted_ev) > 3 else sorted_ev[:1]
        
        recent_avg = sum(e.strength for e in recent) / len(recent)
        older_avg = sum(e.strength for e in older) / len(older) if older else recent_avg
        
        if recent_avg > older_avg + 0.1:
            return "increasing"
        elif recent_avg < older_avg - 0.1:
            return "decreasing"
        return "stable"
    
    def _generate_pattern_description(self, pattern: BehaviorPattern, evidence: List[PatternEvidence]) -> str:
        """Generate human-readable description of pattern."""
        descriptions = {
            BehaviorPattern.PROCRASTINATION: "Tends to delay starting tasks, especially high-priority ones",
            BehaviorPattern.AVOIDANCE: "Avoids difficult or uncomfortable tasks",
            BehaviorPattern.PERFECTIONISM: "Over-plans and delays action until conditions feel perfect",
            BehaviorPattern.BURNOUT: "Shows signs of exhaustion and reduced capacity",
            BehaviorPattern.OVERTHINKING: "Analyzes excessively before taking action",
            BehaviorPattern.VALIDATION_SEEKING: "Needs external confirmation to proceed",
            BehaviorPattern.INCONSISTENCY: "Highly variable engagement and completion patterns",
            BehaviorPattern.MOMENTUM: "Builds positive streaks and compounds progress",
            BehaviorPattern.RESISTANCE: "Pushes back against external structure and suggestions",
            BehaviorPattern.FOLLOW_THROUGH_TENDENCY: "Reliably completes committed tasks",
            BehaviorPattern.TASK_FRICTION_SENSITIVITY: "Struggles with ambiguity and friction in tasks",
        }
        return descriptions.get(pattern, f"Pattern: {pattern.value}")
    
    def _get_interventions(self, pattern: BehaviorPattern) -> List[str]:
        """Get suggested interventions for a pattern."""
        interventions = {
            BehaviorPattern.PROCRASTINATION: [
                "Break tasks into micro-steps (<5 min each)",
                "Use 2-minute rule: if it takes <2 min, do it now",
                "Schedule specific start times, not due dates",
                "Reduce task friction: prepare environment night before"
            ],
            BehaviorPattern.AVOIDANCE: [
                "Identify the fear behind avoidance",
                "Use 'worst case' visualization to reduce anxiety",
                "Start with 1-minute version of avoided task",
                "Pair avoided task with enjoyable activity"
            ],
            BehaviorPattern.PERFECTIONISM: [
                "Define 'good enough' criteria upfront",
                "Set time-boxes for tasks (Pomodoro)",
                "Practice shipping imperfect work",
                "Separate planning from execution phases"
            ],
            BehaviorPattern.BURNOUT: [
                "Reduce daily task load to 1-2 items",
                "Focus on recovery: sleep, nutrition, rest",
                "Remove all 'should' tasks, keep only 'must'",
                "Schedule mandatory non-work time"
            ],
            BehaviorPattern.OVERTHINKING: [
                "Set decision deadlines (5 min for small decisions)",
                "Use 'good enough' threshold: 70% confidence = act",
                "Limit research to 2 sources max",
                "Pre-commit to action before analysis"
            ],
            BehaviorPattern.INCONSISTENCY: [
                "Establish minimum viable daily habit (2 min)",
                "Use implementation intentions: 'If X, then Y'",
                "Track consistency, not intensity",
                "Design environment for default success"
            ],
            BehaviorPattern.MOMENTUM: [
                "Leverage streaks for harder challenges",
                "Gradually increase difficulty",
                "Document winning strategies for reuse",
                "Plan for streak maintenance during disruptions"
            ],
            BehaviorPattern.RESISTANCE: [
                "Offer choices, not directives",
                "Co-create tasks rather than assign",
                "Explain 'why' behind suggestions",
                "Allow autonomy in execution details"
            ],
            BehaviorPattern.FOLLOW_THROUGH_TENDENCY: [
                "Increase task complexity gradually",
                "Add stretch goals",
                "Use as model for other patterns",
                "Maintain trust: don't over-prescribe"
            ],
            BehaviorPattern.TASK_FRICTION_SENSITIVITY: [
                "Provide exact, step-by-step instructions",
                "Reduce decision points in tasks",
                "Prepare all materials in advance",
                "Use templates and checklists"
            ],
        }
        return interventions.get(pattern, ["Observe and gather more evidence"])
    
    def _get_coaching_notes(self, pattern: BehaviorPattern) -> str:
        """Get coaching notes for a pattern."""
        notes = {
            BehaviorPattern.PROCRASTINATION: "Not laziness - usually fear, overwhelm, or unclear next step. Reduce friction, not pressure.",
            BehaviorPattern.AVOIDANCE: "Protective mechanism. Explore what's being avoided emotionally, not just the task.",
            BehaviorPattern.PERFECTIONISM: "High standards masquerading as quality. The cost of perfect is done.",
            BehaviorPattern.BURNOUT: "Physiological, not psychological. Rest is the intervention, not motivation.",
            BehaviorPattern.OVERTHINKING: "Analysis paralysis. Action creates clarity that thinking cannot.",
            BehaviorPattern.INCONSISTENCY: "Life happens. Design for the messy middle, not the perfect week.",
            BehaviorPattern.RESISTANCE: "Autonomy need. Collaborate, don't direct. They'll do their way better than your way.",
            BehaviorPattern.TASK_FRICTION_SENSITIVITY: "Executive function load. Reduce cognitive steps, not task importance.",
        }
        return notes.get(pattern, "")
    
    def update_profile(self, task_history: List[Dict], conversation_history: Optional[List[Dict]] = None):
        """Update behavioral profile with new data."""
        if not self.profile:
            self.profile = BehavioralProfile(user_id=self.user_id)
        
        # Analyze task history
        new_patterns = self.analyze_task_history(task_history)
        
        # Analyze conversation if provided
        if conversation_history:
            conv_patterns = self.analyze_conversation(conversation_history)
            new_patterns.extend(conv_patterns)
        
        # Merge with existing patterns
        for new_pattern in new_patterns:
            existing = self.profile.patterns.get(new_pattern.pattern)
            if existing:
                # Update existing - weighted average
                total_freq = existing.frequency + new_pattern.frequency
                existing.confidence = (existing.confidence * existing.frequency + new_pattern.confidence * new_pattern.frequency) / total_freq
                existing.frequency = total_freq
                existing.evidence.extend(new_pattern.evidence)
                existing.last_reinforced = max(existing.last_reinforced, new_pattern.last_reinforced)
                existing.trend = new_pattern.trend
            else:
                # New pattern
                self.profile.patterns[new_pattern.pattern] = new_pattern
                
                # Record in history
                self.profile.pattern_history.append({
                    "date": datetime.utcnow().date().isoformat(),
                    "pattern": new_pattern.pattern.value,
                    "confidence": new_pattern.confidence,
                    "change": "new"
                })
        
        # Recalculate composite scores
        self._recalculate_composites()
        
        # Update coaching implications
        self._update_coaching_implications()
        
        # Save
        self._save_profile()
    
    def _recalculate_composites(self):
        """Recalculate composite behavioral scores."""
        if not self.profile:
            return
        
        patterns = self.profile.patterns
        
        # Direct pattern scores
        self.profile.procrastination_score = patterns.get(BehaviorPattern.PROCRASTINATION, BehavioralPatternResult(pattern=BehaviorPattern.PROCRASTINATION)).confidence
        self.profile.avoidance_score = patterns.get(BehaviorPattern.AVOIDANCE, BehavioralPatternResult(pattern=BehaviorPattern.AVOIDANCE)).confidence
        self.profile.perfectionism_score = patterns.get(BehaviorPattern.PERFECTIONISM, BehavioralPatternResult(pattern=BehaviorPattern.PERFECTIONISM)).confidence
        self.profile.burnout_risk = patterns.get(BehaviorPattern.BURNOUT, BehavioralPatternResult(pattern=BehaviorPattern.BURNOUT)).confidence
        
        # Derived scores
        follow_through = patterns.get(BehaviorPattern.FOLLOW_THROUGH_TENDENCY, BehavioralPatternResult(pattern=BehaviorPattern.FOLLOW_THROUGH_TENDENCY))
        self.profile.follow_through_score = follow_through.confidence
        
        momentum = patterns.get(BehaviorPattern.MOMENTUM, BehavioralPatternResult(pattern=BehaviorPattern.MOMENTUM))
        inconsistency = patterns.get(BehaviorPattern.INCONSISTENCY, BehavioralPatternResult(pattern=BehaviorPattern.INCONSISTENCY))
        self.profile.consistency_score = max(0, momentum.confidence - inconsistency.confidence)
        
        intrinsic = patterns.get(BehaviorPattern.INTRINSIC_MOTIVATION, BehavioralPatternResult(pattern=BehaviorPattern.INTRINSIC_MOTIVATION))
        extrinsic = patterns.get(BehaviorPattern.EXTRINSIC_MOTIVATION, BehavioralPatternResult(pattern=BehaviorPattern.EXTRINSIC_MOTIVATION))
        self.profile.motivation_quality = intrinsic.confidence - extrinsic.confidence * 0.5
        
        # Emotional stability (inverse of burnout + avoidance + perfectionism)
        self.profile.emotional_stability = 1 - min(1, (self.profile.burnout_risk + self.profile.avoidance_score + self.profile.perfectionism_score) / 3)
        
        # Determine primary and secondary patterns
        scored_patterns = [(p, r.confidence) for p, r in patterns.items() if r.confidence > 0.5]
        scored_patterns.sort(key=lambda x: x[1], reverse=True)
        
        if scored_patterns:
            self.profile.primary_pattern = scored_patterns[0][0]
            self.profile.secondary_patterns = [p for p, _ in scored_patterns[1:4]]
        
        # Risk and protective factors
        self.profile.risk_factors = [p.value for p, c in scored_patterns if p in [
            BehaviorPattern.PROCRASTINATION, BehaviorPattern.AVOIDANCE, 
            BehaviorPattern.PERFECTIONISM, BehaviorPattern.BURNOUT,
            BehaviorPattern.SELF_SABOTAGE, BehaviorPattern.INCONSISTENCY
        ]]
        
        self.profile.protective_factors = [p.value for p, c in scored_patterns if p in [
            BehaviorPattern.MOMENTUM, BehaviorPattern.FOLLOW_THROUGH_TENDENCY,
            BehaviorPattern.INTRINSIC_MOTIVATION
        ]]
    
    def _update_coaching_implications(self):
        """Update coaching recommendations based on profile."""
        if not self.profile:
            return
        
        # Get pattern scores
        patterns = self.profile.patterns
        procrastination = patterns.get(BehaviorPattern.PROCRASTINATION, BehavioralPatternResult(pattern=BehaviorPattern.PROCRASTINATION)).confidence
        avoidance = patterns.get(BehaviorPattern.AVOIDANCE, BehavioralPatternResult(pattern=BehaviorPattern.AVOIDANCE)).confidence
        perfectionism = patterns.get(BehaviorPattern.PERFECTIONISM, BehavioralPatternResult(pattern=BehaviorPattern.PERFECTIONISM)).confidence
        burnout = patterns.get(BehaviorPattern.BURNOUT, BehavioralPatternResult(pattern=BehaviorPattern.BURNOUT)).confidence
        momentum = patterns.get(BehaviorPattern.MOMENTUM, BehavioralPatternResult(pattern=BehaviorPattern.MOMENTUM)).confidence
        follow_through = patterns.get(BehaviorPattern.FOLLOW_THROUGH_TENDENCY, BehavioralPatternResult(pattern=BehaviorPattern.FOLLOW_THROUGH_TENDENCY)).confidence
        resistance = patterns.get(BehaviorPattern.RESISTANCE, BehavioralPatternResult(pattern=BehaviorPattern.RESISTANCE)).confidence
        validation = patterns.get(BehaviorPattern.VALIDATION_SEEKING, BehavioralPatternResult(pattern=BehaviorPattern.VALIDATION_SEEKING)).confidence
        friction = patterns.get(BehaviorPattern.TASK_FRICTION_SENSITIVITY, BehavioralPatternResult(pattern=BehaviorPattern.TASK_FRICTION_SENSITIVITY)).confidence
        
        # Pacing
        if burnout > 0.6 or self.profile.consistency_score < 0.3:
            self.profile.recommended_pacing = "slow"
        elif momentum > 0.7 and follow_through > 0.7:
            self.profile.recommended_pacing = "fast"
        else:
            self.profile.recommended_pacing = "moderate"
        
        # Approach
        if resistance > 0.6:
            self.profile.recommended_approach = "collaborative"
        elif validation > 0.6:
            self.profile.recommended_approach = "supportive"
        elif procrastination > 0.6:
            self.profile.recommended_approach = "directive"
        else:
            self.profile.recommended_approach = "balanced"
        
        # Task difficulty
        if friction > 0.6:
            self.profile.task_difficulty_preference = "micro"
        elif perfectionism > 0.6:
            self.profile.task_difficulty_preference = "small"
        elif follow_through > 0.7:
            self.profile.task_difficulty_preference = "medium"
        else:
            self.profile.task_difficulty_preference = "micro"
        
        # Feedback style
        if burnout > 0.5 or self.profile.emotional_stability < 0.4:
            self.profile.feedback_style = "encouraging"
        elif resistance > 0.6:
            self.profile.feedback_style = "minimal"
        elif perfectionism > 0.6:
            self.profile.feedback_style = "analytical"
        else:
            self.profile.feedback_style = "direct"
    
    def get_profile_summary(self) -> Dict[str, Any]:
        """Get summary for context injection."""
        if not self.profile:
            return {}
        
        return {
            "primary_pattern": self.profile.primary_pattern.value if self.profile.primary_pattern else None,
            "secondary_patterns": [p.value for p in self.profile.secondary_patterns],
            "procrastination_score": self.profile.procrastination_score,
            "avoidance_score": self.profile.avoidance_score,
            "perfectionism_score": self.profile.perfectionism_score,
            "burnout_risk": self.profile.burnout_risk,
            "consistency_score": self.profile.consistency_score,
            "follow_through_score": self.profile.follow_through_score,
            "recommended_pacing": self.profile.recommended_pacing,
            "recommended_approach": self.profile.recommended_approach,
            "task_difficulty_preference": self.profile.task_difficulty_preference,
            "feedback_style": self.profile.feedback_style,
            "risk_factors": self.profile.risk_factors,
            "protective_factors": self.profile.protective_factors,
        }
    
    def get_context_for_prompt(self) -> str:
        """Get formatted behavioral context for LLM prompts."""
        summary = self.get_profile_summary()
        if not summary:
            return ""
        
        parts = []
        if summary.get("primary_pattern"):
            parts.append(f"PRIMARY PATTERN: {summary['primary_pattern']}")
        if summary.get("secondary_patterns"):
            parts.append(f"SECONDARY: {', '.join(summary['secondary_patterns'])}")
        
        # Key scores
        scores = []
        for key in ["procrastination_score", "avoidance_score", "perfectionism_score", "burnout_risk"]:
            val = summary.get(key, 0)
            if val > 0.5:
                scores.append(f"{key}: {val:.1f}")
        if scores:
            parts.append(f"BEHAVIORAL SCORES: {', '.join(scores)}")
        
        # Coaching implications
        parts.append(f"PACING: {summary.get('recommended_pacing', 'moderate')}")
        parts.append(f"APPROACH: {summary.get('recommended_approach', 'balanced')}")
        parts.append(f"TASK SIZE: {summary.get('task_difficulty_preference', 'micro')}")
        parts.append(f"FEEDBACK: {summary.get('feedback_style', 'encouraging')}")
        
        return "\n".join(parts)


# Global instance
behavioral_inference = BehavioralInference()