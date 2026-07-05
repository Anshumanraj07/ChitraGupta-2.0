"""
ChitraGupta 2.0 — Chat API Endpoint
Main conversational endpoint with intelligence layers.

Multi-user support: every intelligence module is resolved per-user via the
user registry. The user_id is taken from the request body (or the
X-User-Id header for clients that prefer header-based identity). No more
hardcoded "default_user" in the active request path.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel, Field

from core.user_registry import get_user_bundle, DEFAULT_USER_ID
from core.policy_engine import policy_engine, PolicyContext
from core.schemas.policy import PolicyAction

logger = logging.getLogger("chitragupta.chat_endpoint")

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    response: str
    action: str
    confidence: float
    reasoning: str
    tasks: list = Field(default_factory=list)
    coaching_context: Dict[str, Any] = Field(default_factory=dict)
    memory_context: str = ""
    # Backward-compat fields expected by the frontend
    bias_flag: bool = False
    bias_description: str = ""
    shadow_perspective: str = ""
    ego_score: float = 0.0
    ego_labels: list = Field(default_factory=list)
    tasks_generated: bool = False


def _resolve_user_id(
    body_user_id: Optional[str],
    x_user_id: Optional[str],
    request: Optional[Request],
) -> str:
    """Resolve the effective user id, preferring body → header → default.

    The default keeps backward compatibility for clients that never send an
    explicit user_id (anonymous single-user deployments).
    """
    uid = (body_user_id or "").strip()
    if not uid:
        uid = (x_user_id or "").strip()
    if not uid and request is not None:
        uid = (request.headers.get("x-user-id") or "").strip()
    if not uid:
        uid = DEFAULT_USER_ID
    return uid


def build_policy_context(user_id: str, session_data: Dict[str, Any]) -> PolicyContext:
    """Build policy context from all intelligence layers (per-user)."""
    bundle = get_user_bundle(user_id)

    conf_scores = bundle.confidence_tracker.get_all_scores()
    behavior_summary = bundle.behavioral_inference.get_profile_summary()
    identity_summary = bundle.identity_model.get_profile_summary()
    coaching_summary = bundle.coaching_planner.get_plan_summary()
    active_tasks = session_data.get("active_tasks", [])

    return PolicyContext(
        user_id=user_id,
        conversation_state=session_data.get("conversation_state", "onboarding"),
        conversation_count=session_data.get("conversation_count", 0),
        goal_clarity=conf_scores.get("goal_clarity", 0.0),
        constraint_clarity=conf_scores.get("constraint_clarity", 0.0),
        habit_clarity=conf_scores.get("habit_clarity", 0.0),
        identity_clarity=conf_scores.get("identity_clarity", 0.0),
        motivation_clarity=conf_scores.get("motivation_clarity", 0.0),
        routine_clarity=conf_scores.get("routine_clarity", 0.0),
        readiness_for_action=conf_scores.get("readiness_for_action", 0.0),
        trust_rapport=conf_scores.get("trust_rapport", 0.0),
        conversation_depth=conf_scores.get("conversation_depth", 0.0),
        behavioral_patterns=list(behavior_summary.get("risk_factors", [])) + list(behavior_summary.get("protective_factors", [])),
        behavioral_confidences={
            "procrastination": behavior_summary.get("procrastination_score", 0),
            "avoidance": behavior_summary.get("avoidance_score", 0),
            "perfectionism": behavior_summary.get("perfectionism_score", 0),
            "burnout_risk": behavior_summary.get("burnout_risk", 0),
            "follow_through_score": behavior_summary.get("follow_through_score", 0),
            "consistency_score": behavior_summary.get("consistency_score", 0),
        },
        active_tasks=len(active_tasks),
        completed_today=session_data.get("completed_today", 0),
        missed_today=session_data.get("missed_today", 0),
        blocked_tasks=0,
        unresolved_task_count=len([t for t in active_tasks if t.get("status") != "completed"]),
        streak_days=session_data.get("streak_days", 0),
        recent_completion_rate=session_data.get("recent_completion_rate", 0.0),
        consistency_score=behavior_summary.get("consistency_score", 0.0),
        has_relevant_memory=False,
        memory_summary="",
        rolling_memory_available=True,
        session_start_time=session_data.get("session_start_time"),
        last_action=session_data.get("last_action"),
        last_action_time=session_data.get("last_action_time"),
        has_identity_profile=identity_summary.get("version", 0) > 0,
        identity_version=identity_summary.get("version", 0),
        coaching_strategy=coaching_summary.get("primary_strategy"),
        pacing=coaching_summary.get("pacing"),
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    chat_req: ChatRequest,
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
):
    """Main chat endpoint with full intelligence pipeline (user-scoped)."""
    user_id = _resolve_user_id(chat_req.user_id, x_user_id, request)
    bundle = get_user_bundle(user_id)

    session_data = await _get_session_data(user_id, chat_req.session_id)

    identity_summary = bundle.identity_model.get_profile_summary()
    behavior_summary = bundle.behavioral_inference.get_profile_summary()
    coaching_summary = bundle.coaching_planner.get_plan_summary()

    # 1. Retrieve relevant memory (user-scoped)
    memory_query = _build_memory_query(
        user_id, chat_req.message, identity_summary, behavior_summary, coaching_summary, session_data
    )
    memory_result = bundle.adaptive_memory.retrieve(memory_query)
    memory_context = bundle.adaptive_memory.get_context_for_prompt(memory_query)

    # 2. Update confidence from conversation (user-scoped)
    confidence_evidence = bundle.confidence_tracker.infer_from_conversation(chat_req.message, {"session_data": session_data})
    bundle.confidence_tracker.add_evidence_batch(confidence_evidence)

    # 3. Build policy context
    policy_context = build_policy_context(user_id, session_data)
    policy_context.has_relevant_memory = len(memory_result.entries) > 0
    policy_context.memory_summary = memory_context

    # 4. Get policy decision (deterministic)
    policy_decision = policy_engine.decide(policy_context)

    # 5. Generate LLM response with full context
    llm_response = await _generate_llm_response(
        user_id=user_id,
        user_message=chat_req.message,
        policy_decision=policy_decision,
        memory_context=memory_context,
        identity_context=bundle.identity_model.get_context_for_prompt(),
        behavioral_context=bundle.behavioral_inference.get_context_for_prompt(),
        coaching_context=bundle.coaching_planner.get_context_for_prompt(),
        policy_context=policy_context,
    )

    # 6. Update models with interaction (user-scoped)
    await _update_models_from_interaction(
        user_id=user_id,
        user_message=chat_req.message,
        assistant_response=llm_response,
        policy_decision=policy_decision,
        session_data=session_data,
    )

    # 7. Generate tasks if policy says so (user-scoped)
    tasks = []
    if policy_decision.action == PolicyAction.GENERATE_TASK:
        task_request = _build_task_request(
            user_id, identity_summary, behavior_summary, coaching_summary, bundle, session_data
        )
        task_result = bundle.task_quality_engine.generate_tasks(task_request)
        tasks = [_serialize_task(t) for t in task_result.tasks]
        session_data["active_tasks"].extend(tasks)
        await _save_session_data(user_id, chat_req.session_id, session_data)

    # Daily review at the start of a new day (user-scoped)
    if session_data.get("conversation_count", 0) == 0 and len(session_data.get("active_tasks", [])) > 0:
        from core.daily_review import DailyReviewInput, ReviewFocus

        review_input = DailyReviewInput(
            user_id=user_id,
            review_date=session_data.get("current_date"),
            focus=ReviewFocus.DAILY_START,
            previous_tasks=session_data.get("yesterday_tasks", []),
            active_tasks=session_data.get("active_tasks", []),
            identity_profile=identity_summary,
            behavioral_profile=behavior_summary,
            confidence_scores=bundle.confidence_tracker.get_all_scores(),
            streak_days=session_data.get("streak_days", 0),
        )
        review_output = bundle.daily_review.conduct_review(review_input)
        if review_output.new_tasks:
            tasks.extend(review_output.new_tasks)

    session_data["conversation_count"] = session_data.get("conversation_count", 0) + 1
    session_data["last_action"] = policy_decision.action.value
    session_data["last_action_time"] = datetime.utcnow().isoformat()
    await _save_session_data(user_id, chat_req.session_id, session_data)

    return ChatResponse(
        response=llm_response,
        action=policy_decision.action.value,
        confidence=policy_decision.confidence,
        reasoning=policy_decision.reasoning,
        tasks=tasks,
        coaching_context=coaching_summary,
        memory_context=memory_context,
        tasks_generated=bool(tasks),
    )


# ---------------------------------------------------------------------------
# Helpers — memory query / task request / serialization
# ---------------------------------------------------------------------------

def _build_memory_query(user_id, message, identity_summary, behavior_summary, coaching_summary, session_data):
    from core.adaptive_memory import MemoryQuery

    return MemoryQuery(
        user_id=user_id,
        current_context=message,
        goal=identity_summary.get("goals", [""])[0] if identity_summary.get("goals") else None,
        struggle=None,
        active_task=session_data.get("current_task"),
        behavioral_patterns=list(behavior_summary.get("risk_factors", [])),
        coaching_strategy=coaching_summary.get("primary_strategy"),
        max_entries=5,
    )


def _build_task_request(user_id, identity_summary, behavior_summary, coaching_summary, bundle, session_data):
    from core.task_quality_engine import TaskGenerationRequest

    return TaskGenerationRequest(
        user_id=user_id,
        goal=identity_summary.get("goals", [""])[0] if identity_summary.get("goals") else "",
        struggle=session_data.get("current_struggle"),
        identity_profile=identity_summary,
        behavioral_profile=behavior_summary,
        confidence_scores=bundle.confidence_tracker.get_all_scores(),
        active_tasks=session_data.get("active_tasks", []),
        completed_today=session_data.get("completed_today", 0),
        missed_today=session_data.get("missed_today", 0),
        coaching_strategy=coaching_summary.get("primary_strategy", "balanced"),
        max_tasks_to_generate=coaching_summary.get("max_tasks_per_session", 1),
    )


def _serialize_task(t):
    return {
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "reason": t.reason,
        "expected_outcome": t.expected_outcome,
        "success_criteria": t.success_criteria,
        "estimated_duration_minutes": t.estimated_duration_minutes,
        "micro_steps": t.micro_steps,
        "sub_tasks": t.micro_steps,  # alias for frontend compat
        "execution_tips": getattr(t, "execution_tips", []) or [],
        "difficulty": t.difficulty.value,
        "goal_area": t.goal_area,
        "discipline": getattr(t, "discipline", "mental"),
        "priority": getattr(t, "priority", "medium"),
        "review_condition": t.review_condition,
        "adaptation_strategy": t.adaptation_strategy,
    }


async def _generate_llm_response(
    user_id: str,
    user_message: str,
    policy_decision,
    memory_context: str,
    identity_context: str,
    behavioral_context: str,
    coaching_context: str,
    policy_context: PolicyContext,
) -> str:
    """Generate LLM response using all context."""
    system_prompt = f"""You are ChitraGupta, an AI coach that helps users achieve their goals through structured conversation and actionable tasks.

COACHING STRATEGY: {coaching_context}

{identity_context}

{behavioral_context}

{memory_context}

CURRENT POLICY DECISION: {policy_decision.action.value} (confidence: {policy_decision.confidence:.0%})
REASONING: {policy_decision.reasoning}

CONVERSATION STATE:
- Count: {policy_context.conversation_count}
- Goal clarity: {policy_context.goal_clarity:.0%}
- Readiness: {policy_context.readiness_for_action:.0%}
- Trust: {policy_context.trust_rapport:.0%}

INSTRUCTIONS:
- Action: {policy_decision.action.value}
- Follow the coaching strategy and pacing
- Be {coaching_context.split('PACING: ')[-1].split('\\n')[0] if 'PACING:' in coaching_context else 'moderate'} paced
- {'Ask questions to reduce uncertainty' if policy_decision.action.value == 'ask_question' else ''}
- {'Reflect back what you hear' if policy_decision.action.value == 'reflect' else ''}
- {'Generate a specific, tiny task' if policy_decision.action.value == 'generate_task' else ''}
- Keep responses conversational, not robotic
- One main point per response
"""
    try:
        import core.engine_shifter as engine_shifter

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        response = engine_shifter.invoke_with_fallback(engine_shifter.ProviderRole.CHAT, messages, temperature=0.7)
        return response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        return _fallback_response(policy_decision.action)


def _fallback_response(action: PolicyAction) -> str:
    fallbacks = {
        PolicyAction.ASK_QUESTION: "That's interesting. Can you tell me more about what's important to you right now?",
        PolicyAction.REFLECT: "What I'm hearing is that you're looking to make some changes. Is that right?",
        PolicyAction.EXPLORE_GOAL: "What would you like to achieve? What's the goal you're working toward?",
        PolicyAction.GENERATE_TASK: "Here's a small step you could take today: [task would be generated here]",
        PolicyAction.WAIT: "I'm listening. Please continue.",
    }
    return fallbacks.get(action, "I'm here to help. What's on your mind?")


async def _update_models_from_interaction(
    user_id: str,
    user_message: str,
    assistant_response: str,
    policy_decision,
    session_data: Dict[str, Any],
):
    """Update all intelligence models from the interaction (user-scoped)."""
    bundle = get_user_bundle(user_id)

    bundle.adaptive_memory.record_conversation(
        content=f"User: {user_message}\nAssistant: {assistant_response}",
        summary=f"Exchange about {user_message[:50]}",
        session_id=session_data.get("session_id", "unknown"),
        coaching_effectiveness=0.5,
        intervention_type=policy_decision.action.value,
    )

    identity_evidence = bundle.identity_model.infer_evidence_from_conversation(user_message, session_data)
    for ev in identity_evidence:
        bundle.identity_model.add_evidence(ev)

    bundle.coaching_planner.plan.sessions_in_current_strategy += 1


async def _get_session_data(user_id: str, session_id: Optional[str]) -> Dict[str, Any]:
    """Get session data from Supabase (user-scoped)."""
    try:
        from core.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if supabase:
            response = supabase.table("sessions").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
            if response.data:
                return response.data[0]
    except Exception as e:
        logger.warning(f"Failed to load session: {e}")

    return {
        "user_id": user_id,
        "session_id": session_id,
        "conversation_count": 0,
        "conversation_state": "onboarding",
        "active_tasks": [],
        "completed_today": 0,
        "missed_today": 0,
        "streak_days": 0,
        "current_date": datetime.utcnow().date().isoformat(),
        "yesterday_tasks": [],
    }


async def _save_session_data(user_id: str, session_id: Optional[str], data: Dict[str, Any]):
    """Save session data to Supabase (user-scoped)."""
    try:
        from core.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if supabase:
            data["user_id"] = user_id
            data["updated_at"] = datetime.utcnow().isoformat()
            supabase.table("sessions").upsert(data, on_conflict="user_id").execute()
    except Exception as e:
        logger.warning(f"Failed to save session: {e}")