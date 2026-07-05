"""
ChitraGupta 2.0 — Daily Review Loop
Day-start review for progress assessment and adaptation.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, date, timedelta
from collections import defaultdict

from core.schemas.daily_review import (
    DailyReviewInput, DailyReviewOutput, DailyTaskReview, TaskReviewStatus, ReviewFocus
)
from core.schemas.identity import IdentityProfile
from core.schemas.behavior import BehavioralProfile
from core.schemas.confidence import ConfidenceProfile
from core.task_quality_engine import task_quality_engine, TaskGenerationRequest
from core.schemas.task import TaskType, TaskPriority, TaskDifficulty

logger = logging.getLogger("chitragupta.daily_review")


class DailyReview:
    """
    Conducts daily review at session start and end.
    Reviews yesterday's progress, infers patterns, adapts strategy.
    """
    
    def __init__(self, user_id: str = "default_user"):
        self.user_id = user_id
    
    def conduct_review(self, input_data: DailyReviewInput) -> DailyReviewOutput:
        """Conduct daily review and produce actionable output."""
        output = DailyReviewOutput(
            review_date=input_data.review_date,
            focus=input_data.focus
        )
        
        if input_data.focus == ReviewFocus.DAILY_START:
            output = self._daily_start_review(input_data, output)
        elif input_data.focus == ReviewFocus.DAILY_END:
            output = self._daily_end_review(input_data, output)
        elif input_data.focus == ReviewFocus.WEEKLY:
            output = self._weekly_review(input_data, output)
        else:
            output = self._on_demand_review(input_data, output)
        
        # Save review to Supabase
        self._save_review(input_data, output)
        
        logger.info(f"Daily review completed for {self.user_id} on {input_data.review_date} ({input_data.focus.value})")
        return output
    
    def _daily_start_review(self, input_data: DailyReviewInput, output: DailyReviewOutput) -> DailyReviewOutput:
        """Morning review: assess yesterday, plan today."""
        prev_tasks = input_data.previous_tasks
        
        if not prev_tasks:
            output.overall_assessment = "Fresh start - no previous tasks to review"
            output.completion_rate = 0.0
            output.encouragement = "New day, new opportunity. Let's start small."
            return output
        
        # Calculate completion rate
        completed = sum(1 for t in prev_tasks if t.status in [TaskReviewStatus.COMPLETED, TaskReviewStatus.PARTIAL])
        total = len(prev_tasks)
        output.completion_rate = completed / total if total > 0 else 0.0
        
        # Analyze each task
        for task in prev_tasks:
            decision = self._analyze_task(task, input_data)
            output.task_decisions.append(decision)
        
        # Generate insights
        output.key_insights = self._generate_insights(prev_tasks, input_data)
        output.patterns_noticed = self._detect_patterns(prev_tasks, input_data)
        
        # Overall assessment
        output.overall_assessment = self._generate_assessment(output.completion_rate, output.patterns_noticed)
        
        # Coaching adaptation
        output.coaching_strategy_adjustment = self._determine_strategy_adjustment(output, input_data)
        output.pacing_recommendation = self._determine_pacing(output, input_data)
        output.focus_areas = self._determine_focus_areas(output, input_data)
        output.avoid_areas = self._determine_avoid_areas(output, input_data)
        
        # Generate new tasks for today
        output.new_tasks = self._generate_todays_tasks(input_data, output)
        
        # Identity/behavior updates
        output.identity_updates = self._generate_identity_updates(output, input_data)
        output.behavioral_updates = self._generate_behavioral_updates(output, input_data)
        output.confidence_adjustments = self._generate_confidence_adjustments(output, input_data)
        
        # Encouragement
        output.encouragement = self._generate_encouragement(output.completion_rate, output.patterns_noticed)
        output.warning_signals = self._generate_warnings(output, input_data)
        
        return output
    
    def _analyze_task(self, task: DailyTaskReview, input_data: DailyReviewInput) -> Dict[str, Any]:
        """Analyze a single task and decide what to do with it."""
        if task.status == TaskReviewStatus.COMPLETED:
            return {
                "task_id": task.task_id,
                "action": "continue",
                "modifications": {},
                "reason": "Completed successfully"
            }
        
        elif task.status == TaskReviewStatus.PARTIAL:
            if task.should_retry:
                return {
                    "task_id": task.task_id,
                    "action": "retry",
                    "modifications": {"retry_modification": task.retry_modification or "reduce_scope"},
                    "reason": f"Partial completion ({task.completion_percentage:.0f}%) - retry with adjustment"
                }
            else:
                return {
                    "task_id": task.task_id,
                    "action": "modify",
                    "modifications": {"difficulty": "easier"},
                    "reason": f"Partial completion - making easier"
                }
        
        elif task.status == TaskReviewStatus.MISSED:
            # Check pattern - if missed multiple times, reduce or archive
            missed_count = sum(1 for t in input_data.previous_tasks 
                             if t.task_id == task.task_id and t.status == TaskReviewStatus.MISSED)
            if missed_count >= 3:
                return {
                    "task_id": task.task_id,
                    "action": "archive",
                    "modifications": {},
                    "reason": f"Missed {missed_count} times - archiving"
                }
            else:
                return {
                    "task_id": task.task_id,
                    "action": "retry",
                    "modifications": {"retry_modification": "reduce_scope"},
                    "reason": f"Missed - retry with reduced scope"
                }
        
        elif task.status == TaskReviewStatus.BLOCKED:
            if task.blocker:
                return {
                    "task_id": task.task_id,
                    "action": "modify",
                    "modifications": {"blocker_addressed": task.blocker},
                    "reason": f"Blocked by: {task.blocker}"
                }
            return {
                "task_id": task.task_id,
                "action": "retry",
                "modifications": {},
                "reason": "Was blocked - retry"
            }
        
        else:  # NOT_ATTEMPTED
            return {
                "task_id": task.task_id,
                "action": "modify",
                "modifications": {"difficulty": "easier", "estimated_duration": 5},
                "reason": "Not attempted - reducing to micro-task"
            }
    
    def _generate_insights(self, tasks: List[DailyTaskReview], input_data: DailyReviewInput) -> List[str]:
        """Generate key insights from task review."""
        insights = []
        
        completed = [t for t in tasks if t.status == TaskReviewStatus.COMPLETED]
        missed = [t for t in tasks if t.status == TaskReviewStatus.MISSED]
        blocked = [t for t in tasks if t.status == TaskReviewStatus.BLOCKED]
        
        if completed:
            insights.append(f"Completed {len(completed)} task(s) - momentum building")
            
            # What worked
            worked = [t.what_worked for t in completed if t.what_worked]
            if worked:
                insights.append(f"What worked: {'; '.join(worked[:2])}")
        
        if missed:
            insights.append(f"Missed {len(missed)} task(s) - review needed")
            
            # Common blockers
            blockers = [t.blocker for t in missed if t.blocker]
            if blockers:
                from collections import Counter
                common = Counter(blockers).most_common(1)
                if common:
                    insights.append(f"Common blocker: {common[0][0]}")
        
        if blocked:
            insights.append(f"{len(blocked)} task(s) blocked - address obstacles")
        
        # Time analysis
        timed_tasks = [t for t in tasks if t.time_spent_minutes]
        if timed_tasks:
            avg_time = sum(t.time_spent_minutes for t in timed_tasks) / len(timed_tasks)
            insights.append(f"Average task time: {avg_time:.0f} min")
        
        # Streak
        if input_data.streak_days > 0:
            insights.append(f"Current streak: {input_data.streak_days} days")
        
        return insights[:5]  # Limit
    
    def _detect_patterns(self, tasks: List[DailyTaskReview], input_data: DailyReviewInput) -> List[str]:
        """Detect patterns from task review."""
        patterns = []
        
        # Morning vs evening completion
        morning_done = 0
        evening_done = 0
        for t in tasks:
            if t.status == TaskReviewStatus.COMPLETED:
                # Would need time data - placeholder
                pass
        
        # Consistent missing
        missed_ids = [t.task_id for t in tasks if t.status == TaskReviewStatus.MISSED]
        if len(missed_ids) >= 2:
            patterns.append("Repeated missed tasks - possible avoidance")
        
        # Consistent blocking
        blocked_reasons = [t.blocker for t in tasks if t.blocker]
        if len(blocked_reasons) >= 2:
            patterns.append("Recurring blockers - environment/structure issue")
        
        # Low completion with high planning
        planned_not_done = [t for t in tasks if t.status in [TaskReviewStatus.NOT_ATTEMPTED, TaskReviewStatus.MISSED] 
                           and t.completion_percentage == 0]
        if len(planned_not_done) >= 2:
            patterns.append("Planning but not executing - perfectionism or overwhelm")
        
        return patterns[:3]
    
    def _generate_assessment(self, completion_rate: float, patterns: List[str]) -> str:
        """Generate overall assessment."""
        if completion_rate >= 0.8:
            base = "Excellent day - strong execution"
        elif completion_rate >= 0.5:
            base = "Good progress - some tasks completed"
        elif completion_rate > 0:
            base = "Partial progress - room for improvement"
        else:
            base = "No tasks completed - reset needed"
        
        if patterns:
            base += f". Patterns: {'; '.join(patterns)}"
        
        return base
    
    def _determine_strategy_adjustment(self, output: DailyReviewOutput, input_data: DailyReviewInput) -> str:
        """Determine coaching strategy adjustment."""
        if output.completion_rate >= 0.8:
            return "Maintain current strategy - user in flow"
        elif output.completion_rate >= 0.5:
            return "Slightly increase challenge - user ready for more"
        elif output.completion_rate > 0:
            return "Reduce difficulty, increase support - user struggling"
        else:
            return "Shift to SUPPORT strategy - rebuild trust and momentum"
    
    def _determine_pacing(self, output: DailyReviewOutput, input_data: DailyReviewInput) -> str:
        """Determine pacing recommendation."""
        if input_data.behavioral_profile:
            burnout = input_data.behavioral_profile.get("burnout_risk", 0)
            if burnout > 0.6:
                return "slow"
        
        if output.completion_rate >= 0.7:
            return "fast"
        elif output.completion_rate >= 0.4:
            return "moderate"
        return "slow"
    
    def _determine_focus_areas(self, output: DailyReviewOutput, input_data: DailyReviewInput) -> List[str]:
        """Determine focus areas for today."""
        areas = []
        
        if output.completion_rate < 0.5:
            areas.append("task_execution")
        
        if input_data.behavioral_profile:
            proc = input_data.behavioral_profile.get("procrastination_score", 0)
            if proc > 0.5:
                areas.append("procrastination_reduction")
            
            friction = input_data.behavioral_profile.get("task_friction_sensitivity_score", 0)
            if friction > 0.5:
                areas.append("friction_reduction")
        
        if input_data.confidence_scores.get("goal_clarity", 0) < 0.4:
            areas.append("goal_clarification")
        
        if not areas:
            areas = ["maintain_momentum"]
        
        return areas[:3]
    
    def _determine_avoid_areas(self, output: DailyReviewOutput, input_data: DailyReviewInput) -> List[str]:
        """Determine areas to avoid today."""
        avoid = []
        
        if input_data.behavioral_profile:
            burnout = input_data.behavioral_profile.get("burnout_risk", 0)
            if burnout > 0.5:
                avoid.append("high_effort_tasks")
            
            perfectionism = input_data.behavioral_profile.get("perfectionism_score", 0)
            if perfectionism > 0.6:
                avoid.append("open_ended_tasks")
        
        return avoid
    
    def _generate_todays_tasks(self, input_data: DailyReviewInput, output: DailyReviewOutput) -> List[Dict[str, Any]]:
        """Generate new tasks for today based on review."""
        # Determine how many tasks
        if output.pacing_recommendation == "fast":
            max_tasks = 3
        elif output.pacing_recommendation == "moderate":
            max_tasks = 2
        else:
            max_tasks = 1
        
        # Filter out avoided areas
        avoid_areas = set(output.avoid_areas)
        
        # Create task generation request
        request = TaskGenerationRequest(
            user_id=self.user_id,
            goal=input_data.identity_profile.get("goals", [""])[0] if input_data.identity_profile else "",
            struggle="; ".join(output.patterns_noticed) if output.patterns_noticed else None,
            identity_profile=input_data.identity_profile,
            behavioral_profile=input_data.behavioral_profile,
            confidence_scores=input_data.confidence_scores,
            active_tasks=input_data.active_tasks,
            completed_today=0,
            missed_today=0,
            energy_level=input_data.energy_level,
            time_available_minutes=30 if output.pacing_recommendation == "slow" else 60,
            coaching_strategy=output.coaching_strategy_adjustment.split(" ")[-1].lower() if "strategy" in output.coaching_strategy_adjustment.lower() else "balanced",
            max_tasks_to_generate=max_tasks,
            avoid_goal_areas=list(avoid_areas),
        )
        
        result = task_quality_engine.generate_tasks(request)
        
        # Convert to dict format
        return [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "reason": t.reason,
                "expected_outcome": t.expected_outcome,
                "success_criteria": t.success_criteria,
                "estimated_duration_minutes": t.estimated_duration_minutes,
                "micro_steps": t.micro_steps,
                "difficulty": t.difficulty.value,
                "goal_area": t.goal_area,
                "review_condition": t.review_condition,
                "adaptation_strategy": t.adaptation_strategy,
            }
            for t in result.tasks
        ]
    
    def _generate_identity_updates(self, output: DailyReviewOutput, input_data: DailyReviewInput) -> List[Dict[str, Any]]:
        """Generate identity model updates from review."""
        updates = []
        
        if output.completion_rate >= 0.7:
            updates.append({
                "category": "strengths",
                "field": "consistency",
                "proposed_value": "Consistently follows through on commitments",
                "confidence": 0.7,
                "reasoning": f"High completion rate: {output.completion_rate:.0%}"
            })
        
        if "procrastination" in " ".join(output.patterns_noticed).lower():
            updates.append({
                "category": "weaknesses",
                "field": "procrastination",
                "proposed_value": "Struggles with task initiation",
                "confidence": 0.6,
                "reasoning": "Pattern of missed/delayed tasks"
            })
        
        return updates
    
    def _generate_behavioral_updates(self, output: DailyReviewOutput, input_data: DailyReviewInput) -> List[Dict[str, Any]]:
        """Generate behavioral profile updates from review."""
        updates = []
        
        if output.completion_rate < 0.3 and len(input_data.previous_tasks) > 2:
            updates.append({
                "pattern": "procrastination",
                "confidence_adjustment": 0.1,
                "reasoning": "Low completion rate with multiple tasks"
            })
        
        if output.completion_rate >= 0.8:
            updates.append({
                "pattern": "momentum",
                "confidence_adjustment": 0.1,
                "reasoning": "High completion rate suggests building momentum"
            })
        
        return updates
    
    def _generate_confidence_adjustments(self, output: DailyReviewOutput, input_data: DailyReviewInput) -> Dict[str, float]:
        """Generate confidence score adjustments from review."""
        adjustments = {}
        
        if output.completion_rate >= 0.7:
            adjustments["readiness_for_action"] = 0.1
            adjustments["goal_clarity"] = 0.05
        elif output.completion_rate < 0.3:
            adjustments["readiness_for_action"] = -0.15
            adjustments["constraint_clarity"] = -0.1
        
        if output.patterns_noticed:
            if any("procrastinat" in p.lower() for p in output.patterns_noticed):
                adjustments["readiness_for_action"] = adjustments.get("readiness_for_action", 0) - 0.1
        
        return adjustments
    
    def _generate_encouragement(self, completion_rate: float, patterns: List[str]) -> str:
        """Generate encouraging message."""
        if completion_rate >= 0.8:
            return "Fantastic progress! You're building real momentum. Keep it up."
        elif completion_rate >= 0.5:
            return "Good work yesterday. Let's build on that foundation today."
        elif completion_rate > 0:
            return "Every step counts. Today's a fresh start - let's make it count."
        else:
            return "Yesterday was tough, but today is new. Let's start with something tiny and build from there."
    
    def _generate_warnings(self, output: DailyReviewOutput, input_data: DailyReviewInput) -> List[str]:
        """Generate warning signals."""
        warnings = []
        
        if input_data.behavioral_profile:
            burnout = input_data.behavioral_profile.get("burnout_risk", 0)
            if burnout > 0.6:
                warnings.append("Burnout risk elevated - prioritize rest")
            
            procrastination = input_data.behavioral_profile.get("procrastination_score", 0)
            if procrastination > 0.7:
                warnings.append("High procrastination pattern - consider micro-steps only")
        
        if output.completion_rate == 0 and len(input_data.previous_tasks) > 3:
            warnings.append("Multiple days of zero completion - strategy change needed")
        
        if input_data.streak_days > 14 and output.completion_rate < 0.5:
            warnings.append("Long streak at risk - protect consistency")
        
        return warnings
    
    def _daily_end_review(self, input_data: DailyReviewInput, output: DailyReviewOutput) -> DailyReviewOutput:
        """End-of-day review: reflect on today, prepare tomorrow."""
        output.overall_assessment = "End-of-day reflection completed"
        output.encouragement = "Good reflection. Rest well, tomorrow is a new day."
        return output
    
    def _weekly_review(self, input_data: DailyReviewInput, output: DailyReviewOutput) -> DailyReviewOutput:
        """Weekly review: aggregate patterns, adjust strategy."""
        output.overall_assessment = "Weekly review completed"
        output.encouragement = "Week complete. Patterns clear, strategy adjusted."
        return output
    
    def _on_demand_review(self, input_data: DailyReviewInput, output: DailyReviewOutput) -> DailyReviewOutput:
        """On-demand review."""
        output.overall_assessment = "On-demand review completed"
        return output
    
    def _save_review(self, input_data: DailyReviewInput, output: DailyReviewOutput):
        """Save review to Supabase."""
        try:
            from core.utils.supabase_client import get_supabase_client
            supabase = get_supabase_client()
            if supabase:
                data = {
                    "user_id": self.user_id,
                    "review_date": input_data.review_date.isoformat(),
                    "focus": input_data.focus.value,
                    "completion_rate": output.completion_rate,
                    "overall_assessment": output.overall_assessment,
                    "key_insights": output.key_insights,
                    "patterns_noticed": output.patterns_noticed,
                    "task_decisions": output.task_decisions,
                    "new_tasks": output.new_tasks,
                    "coaching_strategy_adjustment": output.coaching_strategy_adjustment,
                    "pacing_recommendation": output.pacing_recommendation,
                    "focus_areas": output.focus_areas,
                    "avoid_areas": output.avoid_areas,
                    "encouragement": output.encouragement,
                    "warning_signals": output.warning_signals,
                    "created_at": datetime.utcnow().isoformat(),
                }
                supabase.table("daily_reviews").upsert(data, on_conflict="user_id,review_date,focus").execute()
        except Exception as e:
            logger.error(f"Failed to save daily review: {e}")


# Global instance
daily_review = DailyReview()