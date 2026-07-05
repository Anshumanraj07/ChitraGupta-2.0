"""
ChitraGupta 2.0 — Tasks API Endpoints
Task management with quality engine integration.
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime

from core.task_quality_engine import task_quality_engine, TaskGenerationRequest
from core.schemas.task import QualityTask, TaskType, TaskPriority, TaskDifficulty, TaskStatus
from core.confidence_tracker import confidence_tracker
from core.identity_model import identity_model
from core.behavioral_inference import behavioral_inference
from core.coaching_planner import coaching_planner
import core.engine_shifter as engine_shifter

logger = logging.getLogger("chitragupta.tasks_endpoint")

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskCreateRequest(BaseModel):
    user_id: str = "default_user"
    title: str
    description: str = ""
    task_type: TaskType = TaskType.MICRO
    priority: TaskPriority = TaskPriority.MEDIUM
    difficulty: TaskDifficulty = TaskDifficulty.EASY
    goal_area: str = ""
    estimated_duration_minutes: int = 15
    micro_steps: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)


class TaskUpdateRequest(BaseModel):
    status: Optional[TaskStatus] = None
    completed: Optional[bool] = None
    difficulty_rating: Optional[int] = Field(None, ge=1, le=5)
    value_rating: Optional[int] = Field(None, ge=1, le=5)
    notes: str = ""


class TaskReviewRequest(BaseModel):
    user_id: str = "default_user"
    task_id: str
    completed: bool
    difficulty_rating: Optional[int] = Field(None, ge=1, le=5)
    value_rating: Optional[int] = Field(None, ge=1, le=5)
    notes: str = ""


@router.post("/generate")
async def generate_tasks(request: TaskGenerationRequest):
    """Generate high-quality tasks using the task quality engine."""
    try:
        # Auto-populate goal_area from goal if not explicitly provided
        if not request.goal_area and request.goal:
            request.goal_area = request.goal
        result = task_quality_engine.generate_tasks(request)
        return {
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "task_type": t.task_type.value,
                    "priority": t.priority.value,
                    "difficulty": t.difficulty.value,
                    "reason": t.reason,
                    "expected_outcome": t.expected_outcome,
                    "success_criteria": t.success_criteria,
                    "estimated_duration_minutes": t.estimated_duration_minutes,
                    "micro_steps": t.micro_steps,
                    "dependencies": t.dependencies,
                    "review_condition": t.review_condition,
                    "adaptation_strategy": t.adaptation_strategy,
                    "goal_area": t.goal_area,
                    "coaching_strategy": t.coaching_strategy,
                    "generated_confidence": t.generated_confidence,
                    "alignment_score": t.alignment_score,
                }
                for t in result.tasks
            ],
            "reasoning": result.reasoning,
            "strategy_used": result.strategy_used,
            "confidence": result.confidence,
            "rejected_candidates": result.rejected_candidates,
        }
    except Exception as e:
        logger.error(f"Task generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/review")
async def review_task(task_id: str, request: TaskReviewRequest):
    """Review a completed/failed task and get adaptation recommendations."""
    try:
        # Get the task (in real implementation, fetch from DB)
        # For now, create a mock task for review
        task = QualityTask(
            id=task_id,
            user_id=request.user_id,
            title="Task",
            task_type=TaskType.MICRO,
            difficulty=TaskDifficulty.EASY,
            estimated_duration_minutes=15,
            adaptation_strategy="extend_time",
            max_retries=2,
            retry_count=0,
        )
        
        outcome = {
            "completed": request.completed,
            "difficulty_rating": request.difficulty_rating,
            "value_rating": request.value_rating,
            "notes": request.notes,
        }
        
        review_result = task_quality_engine.review_task(task, outcome)
        
        # Update confidence based on outcome
        confidence_evidence = confidence_tracker.infer_from_task_outcome(outcome)
        confidence_tracker.add_evidence_batch(confidence_evidence)
        
        # Update behavioral inference if completed
        if request.completed:
            # Would update behavioral profile from task history
            pass
        
        return {
            "task_id": review_result.task_id,
            "action": review_result.action,
            "reasoning": review_result.reasoning,
            "modifications": review_result.modifications,
            "new_tasks": [
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
                for t in review_result.new_tasks
            ],
        }
    except Exception as e:
        logger.error(f"Task review failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active")
async def get_active_tasks(user_id: str = "default_user"):
    """Get active tasks for user."""
    try:
        from core.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if supabase:
            response = supabase.table("tasks").select("*").eq("user_id", user_id).neq("status", "completed").neq("status", "archived").execute()
            return {"tasks": response.data}
        return {"tasks": []}
    except Exception as e:
        logger.error(f"Failed to get active tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_task_history(user_id: str = "default_user", limit: int = 50):
    """Get task history for user."""
    try:
        from core.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if supabase:
            response = supabase.table("tasks").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
            return {"tasks": response.data}
        return {"tasks": []}
    except Exception as e:
        logger.error(f"Failed to get task history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/complete")
async def complete_task(task_id: str, request: TaskUpdateRequest):
    """Mark a task as completed."""
    try:
        from core.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if supabase:
            update_data = {
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat(),
                "completed": True,
            }
            if request.difficulty_rating:
                update_data["difficulty_rating"] = request.difficulty_rating
            if request.value_rating:
                update_data["value_rating"] = request.value_rating
            if request.notes:
                update_data["completion_notes"] = request.notes
            
            supabase.table("tasks").update(update_data).eq("id", task_id).execute()
            
            # Record in adaptive memory
            from core.adaptive_memory import adaptive_memory
            adaptive_memory.record_task_outcome(
                task_id=task_id,
                outcome=request.notes or "Completed",
                success=True,
            )
            
            return {"success": True, "task_id": task_id}
        raise HTTPException(status_code=500, detail="Database not available")
    except Exception as e:
        logger.error(f"Failed to complete task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/fail")
async def fail_task(task_id: str, request: TaskUpdateRequest):
    """Mark a task as failed/blocked."""
    try:
        from core.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if supabase:
            update_data = {
                "status": "blocked" if request.status == TaskStatus.BLOCKED else "abandoned",
                "blocked_reason": request.notes,
            }
            
            supabase.table("tasks").update(update_data).eq("id", task_id).execute()
            
            # Record in adaptive memory
            from core.adaptive_memory import adaptive_memory
            adaptive_memory.record_task_outcome(
                task_id=task_id,
                outcome=request.notes or "Failed",
                success=False,
            )
            
            return {"success": True, "task_id": task_id}
        raise HTTPException(status_code=500, detail="Database not available")
    except Exception as e:
        logger.error(f"Failed to mark task failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))