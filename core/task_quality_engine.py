"""
ChitraGupta 2.0 — Task Quality Engine
Reasoning-driven task generation with full justification.
"""

import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from core.schemas.task import (
    QualityTask, TaskType, TaskPriority, TaskDifficulty, TaskStatus,
    TaskGenerationRequest, TaskGenerationResult, TaskReviewResult
)
from core.schemas.identity import IdentityProfile
from core.schemas.behavior import BehavioralProfile
from core.schemas.confidence import ConfidenceProfile, ConfidenceDimension

logger = logging.getLogger("chitragupta.task_quality_engine")


class TaskQualityEngine:
    """
    Generates high-quality, reasoning-driven tasks.
    Replaces template-spam with tasks that have clear rationale, success criteria, and adaptation strategies.
    """
    
    def __init__(self, user_id: str = "default_user"):
        self.user_id = user_id
        self._task_templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, List[Dict]]:
        """Load task templates organized by goal area and pattern."""
        return {
            "fitness": {
                "micro": [
                    {"title": "5-minute walk", "duration": 5, "difficulty": "trivial", "steps": ["Put on shoes", "Walk outside", "Return"]},
                    {"title": "10 bodyweight squats", "duration": 3, "difficulty": "easy", "steps": ["Stand feet shoulder-width", "Squat 10 times", "Rest"]},
                    {"title": "Stretch for 5 minutes", "duration": 5, "difficulty": "trivial", "steps": ["Neck rolls", "Shoulder rolls", "Hamstring stretch", "Quad stretch"]},
                    {"title": "Drink a glass of water", "duration": 1, "difficulty": "trivial", "steps": ["Fill glass", "Drink"]},
                ],
                "habit": [
                    {"title": "Daily 15-min walk", "duration": 15, "difficulty": "easy", "steps": ["Schedule time", "Walk", "Log"]},
                    {"title": "Morning stretch routine", "duration": 10, "difficulty": "easy", "steps": ["5 stretches x 30 sec each"]},
                ],
                "project": [
                    {"title": "Create weekly workout plan", "duration": 30, "difficulty": "moderate", "steps": ["Assess schedule", "Pick 3 workouts", "Set reminders"]},
                ],
            },
            "career": {
                "micro": [
                    {"title": "Update one LinkedIn section", "duration": 10, "difficulty": "easy", "steps": ["Log in", "Edit headline", "Save"]},
                    {"title": "Send one networking message", "duration": 5, "difficulty": "easy", "steps": ["Identify contact", "Write message", "Send"]},
                    {"title": "Read one industry article", "duration": 10, "difficulty": "trivial", "steps": ["Find article", "Read", "Note insight"]},
                ],
                "habit": [
                    {"title": "Daily 15-min skill practice", "duration": 15, "difficulty": "easy", "steps": ["Pick skill", "Practice", "Log"]},
                ],
                "project": [
                    {"title": "Build portfolio project", "duration": 120, "difficulty": "challenging", "steps": ["Define scope", "Set milestones", "Start coding"]},
                ],
            },
            "mental_health": {
                "micro": [
                    {"title": "3-minute breathing exercise", "duration": 3, "difficulty": "trivial", "steps": ["Sit comfortably", "Breathe 4-7-8 x 4"]},
                    {"title": "Write 3 gratitudes", "duration": 5, "difficulty": "trivial", "steps": ["Open journal", "Write 3 things", "Close"]},
                    {"title": "Step outside for fresh air", "duration": 2, "difficulty": "trivial", "steps": ["Open door", "Breathe", "Return"]},
                ],
                "habit": [
                    {"title": "Daily 10-min meditation", "duration": 10, "difficulty": "easy", "steps": ["Set timer", "Meditate", "Note state"]},
                ],
                "project": [
                    {"title": "Create anxiety coping toolkit", "duration": 45, "difficulty": "moderate", "steps": ["List triggers", "Match strategies", "Print card"]},
                ],
            },
            "learning": {
                "micro": [
                    {"title": "Watch 10-min tutorial", "duration": 10, "difficulty": "easy", "steps": ["Find video", "Watch", "Note key point"]},
                    {"title": "Read 5 pages", "duration": 15, "difficulty": "easy", "steps": ["Open book", "Read", "Summarize"]},
                ],
                "habit": [
                    {"title": "Daily 20-min study", "duration": 20, "difficulty": "moderate", "steps": ["Set topic", "Study", "Recall"]},
                ],
                "project": [
                    {"title": "Complete online course module", "duration": 60, "difficulty": "moderate", "steps": ["Start module", "Take notes", "Do exercises"]},
                ],
            },
            "productivity": {
                "micro": [
                    {"title": "Clear email inbox", "duration": 10, "difficulty": "easy", "steps": ["Open email", "Archive/delete", "Flag important"]},
                    {"title": "Plan tomorrow's top 3", "duration": 5, "difficulty": "trivial", "steps": ["Review goals", "Pick 3 tasks", "Schedule"]},
                ],
                "habit": [
                    {"title": "Daily planning ritual", "duration": 10, "difficulty": "easy", "steps": ["Review calendar", "Set priorities", "Block time"]},
                ],
                "project": [
                    {"title": "Build personal task system", "duration": 60, "difficulty": "moderate", "steps": ["Choose tool", "Set up projects", "Create templates"]},
                ],
            },
        }
    
    def generate_tasks(self, request: TaskGenerationRequest) -> TaskGenerationResult:
        """
        Generate high-quality tasks based on full context.
        Every task includes: reason, expected_outcome, success_criteria, micro_steps, adaptation_strategy.
        """
        # Determine task type based on context
        task_type = self._determine_task_type(request)
        
        # Get relevant templates
        templates = self._get_templates(request.goal_area, task_type)
        
        # Filter and score templates
        scored_templates = self._score_templates(templates, request)
        
        # Select top candidates
        selected = scored_templates[:request.max_tasks_to_generate]
        
        # Generate full quality tasks
        tasks = []
        rejected = []
        
        for template, score in selected:
            if score < 0.4:  # Quality threshold
                rejected.append({"title": template["title"], "reason_rejected": f"Low quality score: {score:.2f}"})
                continue
            
            task = self._create_quality_task(template, request, score)
            tasks.append(task)
        
        # Apply global constraints
        tasks = self._apply_constraints(tasks, request)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(request, tasks, task_type)
        
        return TaskGenerationResult(
            tasks=tasks,
            reasoning=reasoning,
            strategy_used=request.coaching_strategy,
            confidence=sum(t.generated_confidence for t in tasks) / len(tasks) if tasks else 0.0,
            rejected_candidates=rejected
        )
    
    def _determine_task_type(self, request: TaskGenerationRequest) -> TaskType:
        """Determine appropriate task type based on context."""
        if request.preferred_task_type:
            return request.preferred_task_type
        
        # Based on confidence and behavioral profile
        readiness = request.confidence_scores.get("readiness_for_action", 0.0)
        goal_clarity = request.confidence_scores.get("goal_clarity", 0.0)
        procrastination = request.behavioral_profile.get("procrastination_score", 0.0) if request.behavioral_profile else 0.0
        friction = request.behavioral_profile.get("task_friction_sensitivity_score", 0.0) if request.behavioral_profile else 0.0
        
        if readiness > 0.7 and goal_clarity > 0.7:
            if len(request.active_tasks) == 0:
                return TaskType.HABIT  # Ready for recurring
            return TaskType.MICRO
        
        if procrastination > 0.6 or friction > 0.6:
            return TaskType.MICRO  # Tiny steps
        
        if goal_clarity < 0.4:
            return TaskType.EXPERIMENT  # Exploration
        
        return TaskType.MICRO
    
    def _get_templates(self, goal_area: str, task_type: TaskType) -> List[Dict]:
        """Get templates for goal area and task type."""
        area_templates = self._task_templates.get(goal_area.lower(), self._task_templates.get("productivity", {}))
        return area_templates.get(task_type.value, area_templates.get("micro", []))
    
    def _score_templates(self, templates: List[Dict], request: TaskGenerationRequest) -> List[tuple]:
        """Score templates based on context fit."""
        scored = []
        
        for template in templates:
            score = 0.5  # Base score
            
            # Difficulty match
            max_diff = request.max_difficulty or TaskDifficulty.MODERATE
            template_diff = TaskDifficulty(template.get("difficulty", "easy"))
            if self._difficulty_value(template_diff) <= self._difficulty_value(max_diff):
                score += 0.2
            else:
                score -= 0.3
            
            # Energy level match
            if request.energy_level == "low" and template_diff in [TaskDifficulty.TRIVIAL, TaskDifficulty.EASY]:
                score += 0.2
            elif request.energy_level == "high" and template_diff in [TaskDifficulty.MODERATE, TaskDifficulty.CHALLENGING]:
                score += 0.1
            
            # Time available match
            if request.time_available_minutes:
                if template.get("duration", 15) <= request.time_available_minutes:
                    score += 0.15
                else:
                    score -= 0.2
            
            # Behavioral fit
            if request.behavioral_profile:
                procrastination = request.behavioral_profile.get("procrastination_score", 0)
                if procrastination > 0.5 and template_diff == TaskDifficulty.TRIVIAL:
                    score += 0.15
                
                perfectionism = request.behavioral_profile.get("perfectionism_score", 0)
                if perfectionism > 0.5 and "exact" not in template.get("title", "").lower():
                    score += 0.1  # Avoid "perfect" framing
            
            # Identity alignment
            if request.identity_profile:
                values = request.identity_profile.get("values", [])
                if "health" in values and request.goal_area == "fitness":
                    score += 0.1
                if "growth" in values and request.goal_area == "learning":
                    score += 0.1
            
            # Avoid duplicates with active tasks
            active_titles = [t.title.lower() for t in request.active_tasks]
            if template["title"].lower() in active_titles:
                score -= 0.5
            
            scored.append((template, max(0, min(1, score))))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
    
    def _difficulty_value(self, diff: TaskDifficulty) -> int:
        values = {
            TaskDifficulty.TRIVIAL: 1,
            TaskDifficulty.EASY: 2,
            TaskDifficulty.MODERATE: 3,
            TaskDifficulty.CHALLENGING: 4,
            TaskDifficulty.DIFFICULT: 5,
        }
        return values.get(diff, 3)
    
    def _create_quality_task(self, template: Dict, request: TaskGenerationRequest, score: float) -> QualityTask:
        """Create a full QualityTask from template."""
        task_id = str(uuid.uuid4())[:8]
        difficulty = TaskDifficulty(template.get("difficulty", "easy"))
        duration = template.get("duration", 15)
        
        # Generate reason based on context
        reason = self._generate_task_reason(template, request)
        expected_outcome = self._generate_expected_outcome(template, request)
        success_criteria = self._generate_success_criteria(template, request)
        micro_steps = template.get("steps", [template["title"]])
        adaptation = self._generate_adaptation_strategy(request)
        
        # Calculate alignment score
        alignment = self._calculate_alignment(template, request)
        
        # Determine review condition
        review_condition = self._determine_review_condition(request)
        execution_tips = self._generate_execution_tips(template, request)
        energy = self._energy_for(difficulty, request)
        objective = self._generate_objective(template, request)

        # Mirror micro_steps into sub_tasks for frontend compatibility (P7)
        sub_tasks = list(micro_steps)

        task = QualityTask(
            id=task_id,
            user_id=self.user_id,
            title=template["title"],
            description=f"{reason} Expected: {expected_outcome}",
            task_type=request.preferred_task_type or TaskType.MICRO,
            priority=TaskPriority.MEDIUM,
            difficulty=difficulty,
            reason=reason,
            expected_outcome=expected_outcome,
            success_criteria=success_criteria,
            estimated_duration_minutes=duration,
            micro_steps=micro_steps,
            sub_tasks=sub_tasks,
            execution_tips=execution_tips,
            energy_requirement=energy,
            objective=objective,
            review_condition=review_condition,
            adaptation_strategy=adaptation,
            goal_area=request.goal_area,
            coaching_strategy=request.coaching_strategy,
            generated_confidence=score,
            alignment_score=alignment,
            user_commitment_level=request.confidence_scores.get("readiness_for_action", 0.5),
        )

        return task

    def _energy_for(self, difficulty: TaskDifficulty, request: TaskGenerationRequest) -> str:
        """Map difficulty + reported energy level to a task energy requirement."""
        diff_val = self._difficulty_value(difficulty)
        # If the user reports low energy, never prescribe a high-energy task
        reported = (request.energy_level or "").lower()
        if reported == "low":
            return "low"
        if diff_val >= 4:
            return "high"
        if diff_val == 3:
            return "medium"
        return "low"

    def _generate_objective(self, template: Dict, request: TaskGenerationRequest) -> str:
        """One-line objective of the task."""
        title = template.get("title", "this task")
        if request.goal:
            return f"Make concrete progress toward: {request.goal} via '{title}'."
        return f"Complete '{title}' to build momentum and a small win."

    def _generate_execution_tips(self, template: Dict, request: TaskGenerationRequest) -> List[str]:
        """Practical how-to guidance, tailored to the user's behavioral profile."""
        tips = []
        title = template.get("title", "").lower()
        steps = template.get("steps", [])

        # Generic, always-useful tips
        if len(steps) >= 2:
            tips.append("Do not skip step 1 — it's the anchor that makes the rest easy.")
        tips.append("Start within the next 2 hours; momentum decays fast.")

        # Behavioral tips
        if request.behavioral_profile:
            proc = request.behavioral_profile.get("procrastination_score", 0)
            if proc > 0.5:
                tips.append("Use a 2-minute rule: commit to just starting, not finishing.")
            friction = request.behavioral_profile.get("task_friction_sensitivity_score", 0)
            if friction > 0.5:
                tips.append("Prep everything you need before you start — remove friction.")
            perfection = request.behavioral_profile.get("perfectionism_score", 0)
            if perfection > 0.5:
                tips.append("Aim for 'done', not 'perfect'. Good enough counts.")

        # Task-specific tips
        if "walk" in title:
            tips.append("No phone. Treat it as a reset, not exercise.")
        if "read" in title:
            tips.append("Read aloud one sentence — it doubles retention.")
        if "message" in title or "email" in title:
            tips.append("Keep it under 3 sentences. Send, then close the app.")
        if "meditat" in title or "breath" in title:
            tips.append("Phone on airplane mode. Eyes closed before you start the timer.")
        if "plan" in title:
            tips.append("Write it on paper. Digital planning turns into research rabbit holes.")

        return tips[:5]  # keep concise
    
    def _generate_task_reason(self, template: Dict, request: TaskGenerationRequest) -> str:
        """Generate the 'why' for this task."""
        reasons = []
        
        # Goal alignment
        if request.goal:
            reasons.append(f"Moves toward '{request.goal}'")
        
        # Address struggle
        if request.struggle:
            reasons.append(f"Addresses: {request.struggle}")
        
        # Behavioral targeting
        if request.behavioral_profile:
            procrastination = request.behavioral_profile.get("procrastination_score", 0)
            if procrastination > 0.5:
                reasons.append("Micro-step to bypass procrastination trigger")
            
            friction = request.behavioral_profile.get("task_friction_sensitivity_score", 0)
            if friction > 0.5:
                reasons.append("Low-friction task to build momentum")
        
        # Confidence building
        readiness = request.confidence_scores.get("readiness_for_action", 0)
        if readiness < 0.5:
            reasons.append("Builds readiness through easy win")
        
        # Habit building
        if request.habit:
            reasons.append(f"Builds habit: {request.habit}")
        
        return "; ".join(reasons) if reasons else "General progress task"
    
    def _generate_expected_outcome(self, template: Dict, request: TaskGenerationRequest) -> str:
        """Generate expected outcome."""
        outcomes = [
            f"Complete '{template['title']}'",
            f"Gain momentum in {request.goal_area}",
        ]
        
        if request.behavioral_profile:
            if request.behavioral_profile.get("procrastination_score", 0) > 0.5:
                outcomes.append("Break inertia with immediate action")
            if request.behavioral_profile.get("momentum_score", 0) > 0.5:
                outcomes.append("Extend positive streak")
        
        return "; ".join(outcomes)
    
    def _generate_success_criteria(self, template: Dict, request: TaskGenerationRequest) -> List[str]:
        """Generate measurable success criteria."""
        criteria = [
            f"Task marked complete",
            f"Time spent: ~{template.get('duration', 15)} minutes",
        ]
        
        # Add specific criteria based on task
        if "walk" in template["title"].lower():
            criteria.append("Steps recorded or route completed")
        if "read" in template["title"].lower():
            criteria.append("Key insight noted")
        if "message" in template["title"].lower() or "email" in template["title"].lower():
            criteria.append("Sent and logged")
        if "plan" in template["title"].lower():
            criteria.append("Plan written down")
        
        return criteria
    
    def _generate_adaptation_strategy(self, request: TaskGenerationRequest) -> str:
        """Generate adaptation strategy for if task fails."""
        if request.behavioral_profile:
            procrastination = request.behavioral_profile.get("procrastination_score", 0)
            if procrastination > 0.5:
                return "reduce_scope"
            
            friction = request.behavioral_profile.get("task_friction_sensitivity_score", 0)
            if friction > 0.5:
                return "extend_time"
            
            perfectionism = request.behavioral_profile.get("perfectionism_score", 0)
            if perfectionism > 0.5:
                return "change_approach"
        
        # Default strategies
        if request.confidence_scores.get("readiness_for_action", 0) < 0.4:
            return "reduce_scope"
        
        return "extend_time"
    
    def _calculate_alignment(self, template: Dict, request: TaskGenerationRequest) -> float:
        """Calculate alignment with goals, identity, behavior."""
        alignment = 0.5
        
        # Goal area match
        if template.get("goal_area", "").lower() == request.goal_area.lower():
            alignment += 0.2
        
        # Identity values match
        if request.identity_profile:
            values = request.identity_profile.get("values", [])
            goal_area = request.goal_area.lower()
            if goal_area in ["fitness", "health"] and "health" in values:
                alignment += 0.15
            if goal_area in ["career", "learning"] and "growth" in values:
                alignment += 0.15
        
        # Behavioral fit
        if request.behavioral_profile:
            if request.behavioral_profile.get("follow_through_score", 0) > 0.7:
                alignment += 0.1
        
        return min(1.0, alignment)
    
    def _determine_review_condition(self, request: TaskGenerationRequest) -> str:
        """Determine when to review this task."""
        if request.coaching_strategy in ["execute", "challenge"]:
            return "end_of_day"
        elif request.coaching_strategy in ["understand", "reflect"]:
            return "after_completion"
        else:
            return "if_blocked"
    
    def _apply_constraints(self, tasks: List[QualityTask], request: TaskGenerationRequest) -> List[QualityTask]:
        """Apply global constraints: max active, merge duplicates, etc."""
        # Limit active tasks
        max_active = 10
        current_active = len(request.active_tasks)
        
        if current_active + len(tasks) > max_active:
            # Keep highest alignment tasks
            tasks.sort(key=lambda t: t.alignment_score, reverse=True)
            tasks = tasks[:max_active - current_active]
        
        # Merge similar tasks (same goal area, similar title)
        merged = []
        for task in tasks:
            similar = [m for m in merged if m.goal_area == task.goal_area and 
                      self._similarity(m.title, task.title) > 0.7]
            if similar:
                # Merge into existing
                similar[0].micro_steps.extend(task.micro_steps)
                similar[0].estimated_duration_minutes += task.estimated_duration_minutes
                similar[0].reason += f"; {task.reason}"
            else:
                merged.append(task)
        
        return merged
    
    def _similarity(self, a: str, b: str) -> float:
        """Simple string similarity."""
        a_words = set(a.lower().split())
        b_words = set(b.lower().split())
        if not a_words or not b_words:
            return 0
        return len(a_words & b_words) / len(a_words | b_words)
    
    def _generate_reasoning(self, request: TaskGenerationRequest, tasks: List[QualityTask], task_type: TaskType) -> str:
        """Generate overall reasoning for task selection."""
        parts = [
            f"Generated {len(tasks)} {task_type.value} task(s) for {request.goal_area}",
            f"Strategy: {request.coaching_strategy}",
            f"Readiness: {request.confidence_scores.get('readiness_for_action', 0):.0%}",
        ]
        
        if request.behavioral_profile:
            proc = request.behavioral_profile.get("procrastination_score", 0)
            if proc > 0.5:
                parts.append(f"Targeting procrastination ({proc:.0%}) with micro-steps")
        
        if tasks:
            avg_alignment = sum(t.alignment_score for t in tasks) / len(tasks)
            parts.append(f"Average goal alignment: {avg_alignment:.0%}")
        
        return ". ".join(parts)
    
    def review_task(self, task: QualityTask, outcome: Dict[str, Any]) -> TaskReviewResult:
        """Review a completed/failed task and decide next action."""
        completed = outcome.get("completed", False)
        difficulty_rating = outcome.get("difficulty_rating")
        value_rating = outcome.get("value_rating")
        notes = outcome.get("notes", "")
        
        if completed:
            # Check if we should continue, increase, or create follow-up
            if value_rating and value_rating >= 4:
                return TaskReviewResult(
                    task_id=task.id,
                    action="continue",
                    reasoning="High value rating, continue similar tasks",
                    modifications={},
                    new_tasks=[]
                )
            elif difficulty_rating and difficulty_rating <= 2:
                # Too easy, increase difficulty
                return TaskReviewResult(
                    task_id=task.id,
                    action="modify",
                    reasoning="Task too easy, increase challenge",
                    modifications={"difficulty": self._next_difficulty(task.difficulty).value},
                    new_tasks=[]
                )
            else:
                return TaskReviewResult(
                    task_id=task.id,
                    action="continue",
                    reasoning="Completed successfully, maintain level",
                    modifications={},
                    new_tasks=[]
                )
        else:
            # Task not completed - adapt
            retry_count = task.retry_count + 1
            if retry_count >= task.max_retries:
                return TaskReviewResult(
                    task_id=task.id,
                    action="archive",
                    reasoning=f"Failed {task.max_retries} times, archiving",
                    modifications={},
                    new_tasks=[]
                )
            
            # Apply adaptation strategy
            strategy = task.adaptation_strategy
            if strategy == "reduce_scope":
                return TaskReviewResult(
                    task_id=task.id,
                    action="retry",
                    reasoning="Reducing scope for retry",
                    modifications={
                        "difficulty": self._prev_difficulty(task.difficulty).value,
                        "estimated_duration_minutes": max(5, task.estimated_duration_minutes // 2),
                        "micro_steps": task.micro_steps[:max(1, len(task.micro_steps) // 2)]
                    },
                    new_tasks=[]
                )
            elif strategy == "extend_time":
                return TaskReviewResult(
                    task_id=task.id,
                    action="retry",
                    reasoning="Extending time allowance",
                    modifications={
                        "estimated_duration_minutes": int(task.estimated_duration_minutes * 1.5),
                        "review_condition": "end_of_day"
                    },
                    new_tasks=[]
                )
            elif strategy == "change_approach":
                return TaskReviewResult(
                    task_id=task.id,
                    action="modify",
                    reasoning="Changing approach for retry",
                    modifications={
                        "micro_steps": self._alternative_steps(task),
                        "adaptation_strategy": "reduce_scope"  # Next time reduce
                    },
                    new_tasks=[]
                )
            else:
                return TaskReviewResult(
                    task_id=task.id,
                    action="retry",
                    reasoning="Retrying with same parameters",
                    modifications={},
                    new_tasks=[]
                )
    
    def _next_difficulty(self, current: TaskDifficulty) -> TaskDifficulty:
        order = [TaskDifficulty.TRIVIAL, TaskDifficulty.EASY, TaskDifficulty.MODERATE, 
                 TaskDifficulty.CHALLENGING, TaskDifficulty.DIFFICULT]
        idx = order.index(current)
        return order[min(idx + 1, len(order) - 1)]
    
    def _prev_difficulty(self, current: TaskDifficulty) -> TaskDifficulty:
        order = [TaskDifficulty.TRIVIAL, TaskDifficulty.EASY, TaskDifficulty.MODERATE, 
                 TaskDifficulty.CHALLENGING, TaskDifficulty.DIFFICULT]
        idx = order.index(current)
        return order[max(idx - 1, 0)]
    
    def _alternative_steps(self, task: QualityTask) -> List[str]:
        """Generate alternative micro-steps for a task."""
        # Simplified - in practice would be more sophisticated
        if len(task.micro_steps) > 1:
            return task.micro_steps[1:] + [task.micro_steps[0]]
        return [f"Alternative: {task.micro_steps[0]}"]


# Global instance
task_quality_engine = TaskQualityEngine()