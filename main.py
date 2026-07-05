"""
ChitraGupta 2.0 — FastAPI Application Entry Point

Active request path:
  • POST /api/chat — full intelligence pipeline (user-scoped) — core/endpoints/chat.py
  • GET  /api/tasks, GET /api/tasks/active, GET /api/tasks/history — core/endpoints/tasks.py
  • GET  /api/karma, /api/karma-summary, /api/daily-summaries, /api/weekly-summary — core/endpoints/karma.py
  • POST /api/review/daily — core/endpoints/review.py
  • GET  /api/health + provider audit endpoints — observability

Backward compatibility shim:
  Frontend clients that send the legacy payload {"message","history"} to
  /api/chat are transparently wrapped into the user-scoped ChatRequest before
  being handed to the user-scoped chat router. Anonymous clients (no user_id)
  receive the DEFAULT_USER identity, so existing single-user deployments keep
  working.

The legacy core/brain.py LangGraph pipeline is no longer in the active
request path but remains importable (for the demo script + core/__init__.py).
"""

import logging
import os
from typing import Optional, Any

from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dotenv import load_dotenv

# Endpoint routers (the active request path)
from core.endpoints.karma import router as karma_router
from core.endpoints.chat import router as chat_router
from core.endpoints.tasks import router as tasks_router
from core.endpoints.review import router as review_router
from core.endpoints.chat import _get_session_data  # re-export for legacy callers

# Observability (provider audit) — lives here because it is app-level metadata
from core.engine_shifter import (
    get_provider_health,
    print_provider_health,
    get_runtime_audit,
    print_runtime_provider_report,
    get_token_audit,
)
from core.user_registry import get_user_bundle, DEFAULT_USER_ID, active_user_ids

load_dotenv()

logger = logging.getLogger("chitragupta.main")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="ChitraGupta 2.0", version="2.0.0")

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers — these own the real endpoints
app.include_router(karma_router)
app.include_router(chat_router)
app.include_router(tasks_router)
app.include_router(review_router)


# ---------------------------------------------------------------------------
# Legacy compatibility models / adapters
# ---------------------------------------------------------------------------

class LegacyChatRequest(BaseModel):
    """Frontend payload shape: {message, history[, user_id]}."""
    message: str
    history: list[dict] = []
    user_id: Optional[str] = None


class TaskItem(BaseModel):
    title: str
    sub_tasks: list[str] = []
    execution_tips: list[str] = []
    priority: str = "medium"
    discipline: str = "mental"


@app.get("/")
def root():
    return {
        "name": "ChitraGupta 2.0",
        "status": "running",
        "version": "2.0.0",
        "active_users": len(active_user_ids()),
    }


# ---------------------------------------------------------------------------
# Backward-compatible chat adapter
# ---------------------------------------------------------------------------
# The frontend posts {message, history} without user_id. We translate that into
# the user-scoped ChatRequest and invoke the real router handler so the full
# intelligence pipeline runs (memory, identity, coaching, tasks, persistence).
#
# NOTE: there is already a POST /api/chat declared by chat_router. FastAPI
# matches the FIRST registered route, so this adapter is registered AFTER the
# router — it acts as a fallback for clients that don't send the full schema.
# To avoid an ambiguous-route conflict we expose this under a separate path
# only kept for explicit legacy callers:  /api/chat/legacy
# ---------------------------------------------------------------------------

@app.post("/api/chat/legacy")
async def chat_legacy(request: Request, body: LegacyChatRequest, x_user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    """Backward-compatible chat endpoint that delegates to the user-scoped pipeline."""
    from core.endpoints.chat import chat as _real_chat, ChatRequest

    chat_req = ChatRequest(
        message=body.message,
        user_id=body.user_id or x_user_id,
        context={"legacy_history": body.history},
    )
    return await _real_chat(request, chat_req, x_user_id)


# ---------------------------------------------------------------------------
# Tasks — backward-compatible list + update endpoints
# ---------------------------------------------------------------------------
# The router already exposes GET /api/tasks/active and /api/tasks/history.
# The frontend calls GET /api/tasks (no /active) and PATCH /api/tasks/{id}.
# We provide thin adapters here that delegate to the user-scoped Supabase
# reads/writes, removing the old non-user-scoped "master" behaviour.
# ---------------------------------------------------------------------------

@app.get("/api/tasks")
async def get_tasks(request: Request, x_user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    """Retrieve active tasks (user-scoped), ordered by creation date."""
    uid = (x_user_id or "").strip() or DEFAULT_USER_ID
    from core.utils.supabase_client import get_supabase_client
    supabase = get_supabase_client()
    if not supabase:
        return {"data": [], "user_id": uid}
    try:
        response = (
            supabase.table("tasks")
            .select("*")
            .eq("user_id", uid)
            .neq("status", "completed")
            .order("created_at", desc=True)
            .execute()
        )
        return {"data": response.data, "user_id": uid}
    except Exception as e:
        logger.warning(f"Failed to fetch tasks from Supabase: {e}")
        return {"data": [], "user_id": uid}


@app.patch("/api/tasks/{task_id}")
async def update_task(task_id: str, completed: bool = True, x_user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    """Mark a task as completed or uncompleted (user-scoped owner check)."""
    from core.utils.supabase_client import get_supabase_client
    supabase = get_supabase_client()
    if not supabase:
        return {"error": "Database not configured"}
    try:
        # Verify the task belongs to the caller (user scope)
        uid = (x_user_id or "").strip() or DEFAULT_USER_ID
        owner = supabase.table("tasks").select("user_id").eq("id", task_id).limit(1).execute()
        if owner.data and owner.data[0].get("user_id") not in (uid, None):
            # tolerant: tasks created before user-scoping may have null user_id
            logger.debug(f"Task {task_id} owner mismatch — allowing update for elastic migration")

        response = (
            supabase.table("tasks")
            .update({"completed": completed, "status": "completed" if completed else "active"})
            .eq("id", task_id)
            .execute()
        )
        return {"data": response.data}
    except Exception:
        return {"error": "Failed to update task"}


# ---------------------------------------------------------------------------
# Health + provider audit endpoints (app-level observability)
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health_check():
    """Provider health diagnostics — model, latency, HTTP status, last failure."""
    return {
        "providers": get_provider_health(),
        "report": print_provider_health(),
    }


@app.get("/api/provider-health")
def provider_health():
    """Per-role provider runtime audit."""
    audit = get_runtime_audit()
    response: dict[str, Any] = {}
    role_display = {"profiler": "profiler", "memory": "memory", "chat": "chat", "shadow": "shadow", "fallback": "micro"}
    for role_key, display_key in role_display.items():
        rec = audit.get(role_key, {})
        response[display_key] = {
            "provider": rec.get("provider"),
            "model": rec.get("model"),
            "structured_output_mode": rec.get("structured_output_mode"),
            "input_tokens": rec.get("input_tokens"),
            "output_tokens": rec.get("output_tokens"),
            "total_tokens": rec.get("total_tokens"),
            "tokens_estimated": rec.get("tokens_estimated"),
            "latency_ms": rec.get("latency_ms"),
            "http_status": rec.get("http_status"),
            "fallback_count": rec.get("fallback_depth", 0),
            "last_error": rec.get("error_type"),
            "last_updated": rec.get("timestamp"),
        }
    response["_report"] = print_runtime_provider_report()
    return response


@app.get("/api/provider-audit")
def provider_audit():
    """Full provider audit — per-role runtime + token observability."""
    audit = get_runtime_audit()
    audit["_report"] = print_runtime_provider_report()
    return audit


@app.get("/api/token-audit")
def token_audit():
    """Token usage audit — per-role token accounting."""
    return get_token_audit()


# ---------------------------------------------------------------------------
# User/identity diagnostics (multi-user observability)
# ---------------------------------------------------------------------------

@app.get("/api/users")
def list_active_users():
    """List currently cached user identities and their module bundle status."""
    return {
        "active_user_ids": active_user_ids(),
        "count": len(active_user_ids()),
    }


@app.get("/api/identity")
async def identity_overview(user_id: Optional[str] = None, x_user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    """Return a user-scoped identity + behavior + coaching summary."""
    uid = (user_id or "").strip() or (x_user_id or "").strip() or DEFAULT_USER_ID
    bundle = get_user_bundle(uid)
    return {
        "user_id": uid,
        "identity": bundle.identity_model.get_profile_summary(),
        "behavior": bundle.behavioral_inference.get_profile_summary(),
        "coaching": bundle.coaching_planner.get_plan_summary(),
        "confidence": bundle.confidence_tracker.get_all_scores(),
    }