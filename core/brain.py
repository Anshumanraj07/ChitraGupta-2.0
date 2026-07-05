"""
ChitraGupta 2.0 — Brain Layer (Multi-Provider Distributed Architecture)
LangGraph-based 5-node pipeline:
  Profiler (Mistral) → Memory (Gemini) → Conditional Router →
    [Chat (Groq) → Shadow (Cerebras) → Synthesis]  OR  [Micro (Cloudflare)]

Enhanced: Memory node now queries Supabase `daily_summaries` for rolling
14-day context (populated by the daily_summarizer.py cron job).

ENHANCED: Integrated conversation-to-action layer for goal discovery and task generation.
"""

import json
import logging
import os
import re
from datetime import date, timedelta
from typing import TypedDict

from langgraph.graph import StateGraph, END
from pydantic import BaseModel, ValidationError

from core.engine_shifter import (
    ProviderRole,
    invoke_structured,
    invoke_with_fallback,
    AllProvidersExhaustedError,
)
from core.utils.json_parser import build_json_instruction, build_retry_prompt

# Import conversation-to-action layer components
from core.conversation_manager import conversation_manager, ConversationState
from core.goal_discovery import goal_discovery, DiscoveredElements
from core.task_generator import task_generator, GeneratedTask
from core.memory_manager import memory_manager
from core.session_manager import session_manager

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger("chitragupta.brain")

# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------


class TaskSchema(BaseModel):
    title: str = "Untitled Task"
    sub_tasks: list[str] = []
    execution_tips: list[str] = []
    priority: str = "medium"
    discipline: str = "mental"


class ProfilerOutputSchema(BaseModel):
    """Output from the Profiler node — ego-scoring and intent triage."""
    ego_score: int = 5
    ego_labels: list[str] = []
    profiled_intent: str = "general"
    confidence: float = 0.5


class MemoryOutputSchema(BaseModel):
    """Output from the Memory node — context summarization."""
    memory_context: str = ""
    relevant_past: str = ""
    behavioral_pattern: str = ""


class AIOutputSchema(BaseModel):
    """Output from the ChatAgent node — main conversational response."""
    classification: str = "general"
    response: str = ""
    bias_flag: bool = False
    bias_description: str = ""
    journal_insight: str = ""
    extracted_tasks: list[TaskSchema] = []


class ShadowOutputSchema(BaseModel):
    """Output from the ShadowAgent node — meta-cognitive bias detection."""
    shadow_analysis: str = ""
    shadow_perspective: str = ""
    bias_flag: bool = False
    bias_description: str = ""
    corrective_tasks: list[TaskSchema] = []


class MicroOutputSchema(BaseModel):
    """Output from the Micro node — lightweight casual responses."""
    response: str = "Hey! I'm here. What's on your mind?"
    classification: str = "general"


# ---------------------------------------------------------------------------
# Agent State
# ---------------------------------------------------------------------------


class AgentState(TypedDict, total=False):
    user_input: str
    history: list[dict]
    raw_ai_output: str
    cot_reasoning: str
    # --- Profiler fields ---
    ego_score: int
    ego_labels: list[str]
    profiler_classification: str
    # --- Memory fields ---
    memory_context: str
    relevant_past: str
    behavioral_pattern: str
    rolling_memory: str          # Supabase daily_summaries context (last 14 days)
    # --- Chat/Shadow fields ---
    classification: str
    final_response: str
    journal_insight: str
    bias_flag: bool
    bias_description: str
    extracted_tasks: list[dict]
    shadow_analysis: str
    shadow_perspective: str
    # --- Routing ---
    use_micro: bool
    # --- Conversation-to-Action Layer ---
    conversation_state: str
    discovered_goal: str
    discovered_struggle: str
    discovered_habit: str
    discovered_routine: str
    goal_area: str
    discovery_confidence: float
    generated_task_title: str
    generated_task_sub_tasks: list[str]
    generated_task_execution_tips: list[str]
    generated_task_priority: str
    generated_task_discipline: str
    generated_task_estimated_time: int
    task_generation_confidence: float
    should_generate_task: bool


# ---------------------------------------------------------------------------
# CoT Parsing Helper
# ---------------------------------------------------------------------------


def _strip_cot(text: str) -> tuple[str, str]:
    """
    Strip <thinking>...</thinking> blocks from LLM output.
    Returns (cleaned_text, cot_reasoning).
    """
    cot_match = re.search(r"<thinking>(.*?)</thinking>", text, re.DOTALL)
    cot_reasoning = cot_match.group(1).strip() if cot_match else ""
    cleaned = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL).strip()
    return cleaned, cot_reasoning


def _format_history(history: list[dict], limit: int = 20) -> str:
    """Format conversation history into a readable string for prompt context."""
    if not history:
        return ""
    lines = []
    for msg in history[-limit:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        label = "User" if role == "user" else "AI"
        lines.append(f"{label}: {content}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# System Prompts
# ---------------------------------------------------------------------------

PROFILER_SYSTEM_PROMPT = """You are the Profiler — a fast psychological triage engine. You analyze the user's message and produce a brief psychological snapshot.

Output a single JSON object with this EXACT schema:
{
  "ego_score": <integer 1-10, emotional urgency level>,
  "ego_labels": <array of 1-3 emotional tags like "anxious", "ambitious", "frustrated", "calm", "reflective">,
  "profiled_intent": <"task" | "journal" | "general">,
  "confidence": <float 0.0-1.0>
}

RULES:
1. ego_score 1-3 = casual/low urgency (greetings, small talk, chill vibes)
2. ego_score 4-6 = moderate (normal tasks, reflections, questions)
3. ego_score 7-10 = high urgency (crisis, deep distress, urgent goals)
4. profiled_intent: "task" = user wants to do something, "journal" = user is reflecting/venting, "general" = casual/ambiguous
5. Be FAST and CONCISE. No over-analysis. Trust your first instinct.
6. For greetings ("hey", "what's up"), always set ego_score <= 2 and profiled_intent = "general".
"""

MEMORY_SYSTEM_PROMPT = """You are the Memory node — a context synthesis engine. You have access to the full conversation history, the profiler's psychological snapshot, AND rolling daily summaries from the past 14 days. Your job is to distill all this into a concise contextual summary that the conversational agent can use.

Output a single JSON object with this EXACT schema:
{
  "memory_context": <2-3 sentence summary of the conversation flow and current emotional state>,
  "relevant_past": <any recurring themes, goals, or patterns you detect from history AND daily summaries>,
  "behavioral_pattern": <brief note on behavioral tendencies you observe, or empty string>
}

RULES:
1. Be concise. The memory_context should be 2-3 sentences max.
2. Focus on what's RELEVANT to the current user message — not a full transcript.
3. If the user has mentioned goals before, reference them.
4. If daily summaries show emotional trajectories or discipline trends, weave that in.
5. If no meaningful patterns exist, return empty strings for irrelevant fields.
6. Don't fabricate patterns. Only report what you can actually observe.
7. CROSS-REFERENCE: Use the daily summaries to detect long-term patterns that single-session history can't reveal (e.g., declining discipline, recurring anxiety, consistent task avoidance).
"""

CHAT_AGENT_SYSTEM_PROMPT = """You are ChitraGupta — a mentor-coach focused on ACTION and ROADMAP CREATION. Your response must be practical, direct, and action-oriented.

YOU MUST REASON STEP BY STEP INSIDE <thinking>...</thinking> BEFORE OUTPUTTING JSON. Inside the thinking block:
1. Analyze the user's message for explicit goals, struggles, or action items
2. Identify what the user CONTROLS (Dichotomy of Control)
3. If user mentions a goal/life struggle → BREAK INTO SPECIFIC SUB-TASKS with execution tips
4. If user is vague → PROACTIVELY SUGGEST concrete goal areas (fitness, career, discipline)
5. Decide on tasks ONLY when user explicitly mentions action items

After thinking, output JSON with:
{
   "classification": "task" | "journal" | "general",
   "response": "<direct, action-focused response>",
   "bias_flag": <boolean>,
   "bias_description": "<string or empty>",
   "journal_insight": "<string or empty>",
   "extracted_tasks": [<array of task objects>]
}

CRITICAL: The 'priority' field in each task MUST be string: 'high', 'medium', or 'low' (never numbers).

RULES:
1. BE DIRECT: No philosophical fluff unless user asks for depth. Focus on "what to do next".
2. GOAL DISCOVERY: If no clear goal, suggest 2-3 concrete areas: "Most people work on fitness, career direction, or daily discipline. Which resonates?"
3. TASK BREAKDOWN: For any goal, create 3-5 SPECIFIC sub-tasks with clear execution tips (e.g., not "get fit" but "do 20-min walk at 7am Mon/Wed/Fri").
4. HINDI/HINGLISH: Match user's language naturally (bhai, yaar, tu, etc.) if they use it.
5. CASUAL: For simple greetings, keep it warm and brief: "Hey! What's your focus today?"
6. NO VAGUE ADVICE: Replace "you should..." with "do X at Y time".
7. TASK RULE: Only extract tasks when user explicitly mentions action items/goals/struggles.

CRITICAL TASK OVERRIDE: YOU ARE A MINIMALIST, BRUTAL MENTOR. 
Do NOT give absurd, unrealistic advice like '3-hour workouts' for beginners. Give ONE micro-step. 
Furthermore, if the user has not committed to a hard, actionable plan, YOU MUST output your tasks array exactly as: "tasks": []
NEVER output your own internal instructions (e.g., 'ask open-ended questions', 'use empathetic tone') as user tasks.
"""

SHADOW_AGENT_SYSTEM_PROMPT = """You are the ShadowAgent — a measured, precise meta-cognitive observer. Your role is to examine the conversation for hidden biases, logical fallacies, and unchallenged assumptions. You are the devil's advocate, but a wise one.

YOU MUST REASON STEP BY STEP INSIDE <thinking>...</thinking> BEFORE OUTPUTTING JSON. Inside the thinking block, analyze the conversation context and decide whether a genuine bias exists. Be skeptical of your own tendency to over-flag.

After your thinking block, output a single JSON object with this schema:
{
  "shadow_analysis": "<your analysis of potential biases or blind spots>",
  "shadow_perspective": "<a gentle alternative perspective, or empty string if none needed>",
  "bias_flag": <boolean>,
  "bias_description": "<string or empty>",
  "corrective_tasks": [<array of task objects — ONLY if a genuine bias needs corrective action>]
}

CRITICAL INSTRUCTION: The 'priority' field in corrective_tasks MUST be a string value exactly matching 'high', 'medium', or 'low'. DO NOT output integers or numbers (e.g., never output 1, 2, or 3). It must be a STRING.

JSON FORMAT RULES (STRICT):
1. Output ONLY a raw JSON object. No text before it. No text after it. No markdown fences. No explanation.
2. Every string value MUST be enclosed in double quotes. Every boolean MUST be true or false (no quotes).
3. Every array MUST be valid JSON: ["item1", "item2"]. Every key MUST have a value — no trailing commas.
4. If you have nothing to report, output: {"shadow_analysis":"","shadow_perspective":"","bias_flag":false,"bias_description":"","corrective_tasks":[]}
5. sub_tasks and execution_tips MUST be arrays of plain strings, NEVER arrays of objects.

CRITICAL RULES:
1. Be MEASURED. It is better to miss a subtle bias than to over-flag and exhaust the user.
2. Only flag a bias if the user demonstrates a CLEAR, SIGNIFICANT cognitive distortion in a substantive message.
3. Only generate corrective tasks if a genuine bias was detected AND the user mentioned an action item or life struggle.
4. For simple greetings or short messages, return empty analysis with bias_flag = false.
5. When you DO offer a shadow perspective, make it brief and thought-provoking — not preachy.
"""

MICRO_SYSTEM_PROMPT = """You are ChitraGupta in casual mode. The user sent a simple/low-priority message (like a greeting or small talk). Keep it warm, brief, and natural. Match their energy.

Output a single JSON object with this schema:
{
  "response": "<your brief, warm response>",
  "classification": "general"
}

RULES:
1. Keep it short — 1-2 sentences max.
2. Be warm and inviting. Encourage them to share more if they want.
3. If they spoke in Hinglish, respond in Hinglish.
4. Don't over-analyze. No tasks, no bias detection, no deep philosophy for casual messages.
5. Examples: "Hey! What's on your mind?" / "Bhai, bata kya chal raha hai?" / "I'm here — tell me what you need."
"""


# ---------------------------------------------------------------------------
# Node 1: Profiler (Mistral)
# ---------------------------------------------------------------------------


def profiler_node(state: AgentState) -> AgentState:
    """
    Fast psychological triage — ego-scoring and intent pre-classification.
    Powered by Mistral (with OpenRouter/Groq fallback).
    """
    user_input = state.get("user_input", "")
    history = state.get("history", [])

    # Build a lightweight context (last 5 messages only)
    recent_history = _format_history(history, limit=5)

    profiler_prompt = PROFILER_SYSTEM_PROMPT + build_json_instruction(ProfilerOutputSchema)
    messages = [
        {"role": "system", "content": profiler_prompt},
        {"role": "user", "content": f"Recent conversation:\n{recent_history}\n\nCurrent message: {user_input}"},
    ]

    try:
        result = invoke_structured(ProviderRole.PROFILER, messages, ProfilerOutputSchema)

        state["ego_score"] = result.ego_score
        state["ego_labels"] = result.ego_labels
        state["profiler_classification"] = result.profiled_intent

        logger.debug(
            f"Profiler: ego_score={result.ego_score}, "
            f"labels={result.ego_labels}, "
            f"intent={result.profiled_intent}"
        )

    except AllProvidersExhaustedError as e:
        logger.warning(f"Profiler all providers exhausted, using defaults: {e}")
        state["ego_score"] = 5
        state["ego_labels"] = []
        state["profiler_classification"] = "general"
    except Exception as e:
        logger.warning(f"Profiler error, using defaults: {e}")
        state["ego_score"] = 5
        state["ego_labels"] = []
        state["profiler_classification"] = "general"

    return state


# ---------------------------------------------------------------------------
# Supabase Rolling Memory Helper
# ---------------------------------------------------------------------------


def _fetch_rolling_memory(user_id: str = "master", days: int = 14) -> str:
    """
    Query Supabase `daily_summaries` for the last N days of compressed context.
    Returns a formatted string for injection into the Memory node prompt,
    or empty string if Supabase is unavailable.
    """
    try:
        from supabase import create_client
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
        if not url or not key:
            return ""

        sb = create_client(url, key)
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        response = (
            sb.table("daily_summaries")
            .select("summary_date, summary, dominant_emotion, task_count, discipline_mental, discipline_physical, key_topics")
            .eq("user_id", user_id)
            .gte("summary_date", cutoff)
            .order("summary_date", desc=False)
            .execute()
        )

        if not response.data:
            return ""

        lines = []
        for row in response.data:
            d = row.get("summary_date", "?")
            s = row.get("summary", "")
            e = row.get("dominant_emotion", "neutral")
            dm = row.get("discipline_mental", 50)
            dp = row.get("discipline_physical", 50)
            tc = row.get("task_count", 0)
            topics = row.get("key_topics", [])
            topics_str = ", ".join(topics) if topics else "—"
            lines.append(
                f"[{d}] emotion={e} | mental={dm} | physical={dp} | tasks={tc}\n"
                f"  Summary: {s}\n"
                f"  Topics: {topics_str}"
            )

        return "\n".join(lines)

    except Exception as e:
        logger.debug(f"Rolling memory query failed (non-fatal): {e}")
        return ""


# ---------------------------------------------------------------------------
# Node 2: Memory (Google Gemini) — Enhanced with Rolling Memory
# ---------------------------------------------------------------------------


def memory_node(state: AgentState) -> AgentState:
    """
    Long-term context summarization. Processes full conversation history
    AND rolling 14-day daily summaries from Supabase.
    Powered by Google Gemini (with OpenRouter fallback).
    """
    user_input = state.get("user_input", "")
    history = state.get("history", [])
    ego_score = state.get("ego_score", 5)
    ego_labels = state.get("ego_labels", [])

    full_history = _format_history(history, limit=50)

    # Fetch rolling memory from Supabase daily_summaries
    rolling_memory = _fetch_rolling_memory()
    state["rolling_memory"] = rolling_memory

    # Build the prompt — include rolling memory if available
    rolling_block = ""
    if rolling_memory:
        rolling_block = (
            f"\n\nROLLING DAILY SUMMARIES (last 14 days):\n{rolling_memory}\n"
            f"Use these to detect long-term patterns, emotional trajectories, "
            f"and recurring themes that single-session history cannot reveal."
        )

    memory_prompt = MEMORY_SYSTEM_PROMPT + build_json_instruction(MemoryOutputSchema)
    messages = [
        {"role": "system", "content": memory_prompt},
        {"role": "user", "content": (
            f"PROFILER DATA: ego_score={ego_score}, labels={ego_labels}\n\n"
            f"FULL CONVERSATION HISTORY:\n{full_history}\n"
            f"{rolling_block}\n\n"
            f"CURRENT MESSAGE: {user_input}\n\n"
            f"Synthesize the context."
        )},
    ]

    try:
        result = invoke_structured(ProviderRole.MEMORY, messages, MemoryOutputSchema)

        state["memory_context"] = result.memory_context
        state["relevant_past"] = result.relevant_past
        state["behavioral_pattern"] = result.behavioral_pattern

        logger.debug(f"Memory: context='{result.memory_context[:100]}...'")

    except AllProvidersExhaustedError as e:
        logger.warning(f"Memory all providers exhausted, using empty context: {e}")
        state["memory_context"] = ""
        state["relevant_past"] = ""
        state["behavioral_pattern"] = ""
    except Exception as e:
        logger.warning(f"Memory error, using empty context: {e}")
        state["memory_context"] = ""
        state["relevant_past"] = ""
        state["behavioral_pattern"] = ""

    return state


# ---------------------------------------------------------------------------
# Node 3: Conditional Router
# ---------------------------------------------------------------------------


def conditional_router(state: AgentState) -> str:
    """
    Routes based on profiler data:
    - ego_score <= 2 AND profiler_classification == "general"
      → "micro" (lightweight Cloudflare response)
    - Otherwise → "chat_agent" (full pipeline)
    """
    ego_score = state.get("ego_score", 5)
    profiler_cls = state.get("profiler_classification", "general")

    if ego_score <= 2 and profiler_cls == "general":
        logger.debug("Router: → micro (trivial input)")
        state["use_micro"] = True
        return "micro"
    else:
        logger.debug("Router: → chat_agent (substantial input)")
        state["use_micro"] = False
        return "chat_agent"


# ---------------------------------------------------------------------------
# Node 4a: Micro (Cloudflare)
# ---------------------------------------------------------------------------


def micro_node(state: AgentState) -> AgentState:
    """
    Lightweight casual response for trivial inputs.
    Powered by Cloudflare Workers AI (with OpenRouter fallback).
    """
    user_input = state.get("user_input", "")

    micro_prompt = MICRO_SYSTEM_PROMPT + build_json_instruction(MicroOutputSchema)
    messages = [
        {"role": "system", "content": micro_prompt},
        {"role": "user", "content": user_input},
    ]

    try:
        result = invoke_structured(ProviderRole.FALLBACK, messages, MicroOutputSchema)

        state["final_response"] = result.response
        state["classification"] = result.classification
        state["journal_insight"] = ""
        state["bias_flag"] = False
        state["bias_description"] = ""
        state["extracted_tasks"] = []
        state["shadow_analysis"] = ""
        state["shadow_perspective"] = ""

    except AllProvidersExhaustedError as e:
        logger.error(f"Micro all providers exhausted: {e}")
        state["final_response"] = "I'm having trouble connecting right now. Please try again in a moment."
        state["classification"] = "general"
    except Exception as e:
        logger.error(f"Micro error: {e}")
        state["final_response"] = "I'm having trouble connecting right now. Please try again in a moment."
        state["classification"] = "general"

    return state


# ---------------------------------------------------------------------------
# Node 4b: ChatAgent (Groq)
# ---------------------------------------------------------------------------


def chat_agent_node(state: AgentState) -> AgentState:
    """
    Frontline conversational agent — Stoic philosopher-coach.
    Takes profiler data and memory context for enriched responses.
    Powered by Groq (with OpenRouter/Cloudflare fallback).
    
    ENHANCED: Now integrates with conversation-to-action layer for state tracking
    and goal discovery.
    """
    user_input = state.get("user_input", "")
    history = state.get("history", [])
    ego_score = state.get("ego_score", 5)
    ego_labels = state.get("ego_labels", [])
    memory_context = state.get("memory_context", "")
    relevant_past = state.get("relevant_past", "")
    behavioral_pattern = state.get("behavioral_pattern", "")

    # ENHANCEMENT: Update conversation-to-action layer state BEFORE LLM response
    _update_conversation_state(state, user_input, history)

    # Build the enriched user context (includes rolling memory from Supabase)
    rolling_memory = state.get("rolling_memory", "")
    context_block = ""
    if ego_score or ego_labels or memory_context or rolling_memory or state.get("conversation_state") or state.get("discovered_goal") or state.get("discovered_struggle") or state.get("discovered_habit") or state.get("discovered_routine"):
        context_parts = []
        if ego_score:
            context_parts.append(f"[PROFILER] ego_score={ego_score}, labels={ego_labels}")
        if memory_context:
            context_parts.append(f"[MEMORY] {memory_context}")
        if relevant_past:
            context_parts.append(f"[PAST] {relevant_past}")
        if behavioral_pattern:
            context_parts.append(f"[PATTERN] {behavioral_pattern}")
        if rolling_memory:
            context_parts.append(f"[ROLLING 14-DAY CONTEXT]\n{rolling_memory}")
        # ADD THESE LINES to context_parts
        if state.get("conversation_state"):
            context_parts.append(f"[CONVERSATION STATE] {state.get('conversation_state')}")
        if state.get("discovered_goal"):
            context_parts.append(f"[DISCOVERED GOAL] {state.get('discovered_goal')}")
        if state.get("discovered_struggle"):
            context_parts.append(f"[DISCOVERED STRUGGLE] {state.get('discovered_struggle')}")
        context_block = "\n\nCONTEXT FROM PROFILER & MEMORY:\n" + "\n".join(context_parts)

    chat_prompt = CHAT_AGENT_SYSTEM_PROMPT + build_json_instruction(AIOutputSchema)
    messages_list = [
        {"role": "system", "content": chat_prompt},
    ]

    # Inject conversation history as multi-turn messages
    if history:
        for msg in history[-20:]:
            role = "user" if msg.get("role") == "user" else "assistant"
            content = msg.get("content", "")
            if content:
                messages_list.append({"role": role, "content": content})

    # Add the current user message with context block
    enriched_input = f"{context_block}\n\nUSER MESSAGE: {user_input}" if context_block else user_input
    messages_list.append({"role": "user", "content": enriched_input})

    try:
        result = invoke_structured(ProviderRole.CHAT, messages_list, AIOutputSchema)

        state["classification"] = result.classification
        state["final_response"] = result.response
        state["journal_insight"] = result.journal_insight
        state["bias_flag"] = result.bias_flag
        state["bias_description"] = result.bias_description
        state["extracted_tasks"] = [t.model_dump() for t in result.extracted_tasks]

    except AllProvidersExhaustedError as e:
        logger.error(f"ChatAgent all providers exhausted: {e}")
        state["final_response"] = "I'm having trouble connecting right now. Please try again in a moment."
        state["classification"] = "general"
    except Exception as e:
        logger.error(f"ChatAgent error: {e}")
        state["final_response"] = "I'm having trouble connecting right now. Please try again in a moment."
        state["classification"] = "general"

    return state


def _update_conversation_state(state: AgentState, user_input: str, history: list[dict]):
    """
        Update the conversation-to-action layer state based on user input and conversation history.
    This integrates the goal discovery, session management, and task generation components.
    """
    try:
        # Get or create session manager for this user
        user_id = state.get("user_id", "default_user")
        sess_manager = session_manager
        if hasattr(sess_manager, 'user_id') and sess_manager.user_id != user_id:
            sess_manager = session_manager.__class__(user_id)
        
        # Start/get current session
        conv_manager = sess_manager.start_new_session()
        
        # Prepare context for conversation update
        context = {
            "ego_score": state.get("ego_score", 5),
            "ego_labels": state.get("ego_labels", []),
            "profiler_classification": state.get("profiler_classification", "general"),
            "memory_context": state.get("memory_context", ""),
            "relevant_past": state.get("relevant_past", ""),
            "behavioral_pattern": state.get("behavioral_pattern", ""),
            "history": history
        }
        
        # Update conversation state
        new_state = conv_manager.update_state(user_input, context)
        state["conversation_state"] = new_state.value
        
        # Get current context for discovery
        conv_context = conv_manager.get_context_for_task_generation()
        
        # Use goal discovery to extract elements from conversation
        discovered = goal_discovery.discover(user_input, conv_context)
        state["discovered_goal"] = discovered.goal or ""
        state["discovered_struggle"] = discovered.struggle or ""
        state["discovered_habit"] = discovered.habit or ""
        state["discovered_routine"] = discovered.routine or ""
        state["goal_area"] = discovered.goal_area.value if discovered.goal_area else ""
        state["discovery_confidence"] = discovered.confidence
        
        # Check if we should generate a task
        should_gen = conv_manager.should_create_task()
        state["should_generate_task"] = should_gen
        
        if should_gen:
            # Generate task using discovered elements
            generated_task = task_generator.generate_task(discovered, conv_context)
            if generated_task:
                state["generated_task_title"] = generated_task.title
                state["generated_task_sub_tasks"] = generated_task.sub_tasks
                state["generated_task_execution_tips"] = generated_task.execution_tips
                state["generated_task_priority"] = generated_task.priority.value
                state["generated_task_discipline"] = generated_task.discipline.value
                state["generated_task_estimated_time"] = generated_task.estimated_time_minutes
                state["task_generation_confidence"] = generated_task.confidence
            else:
                # Clear task fields if generation failed
                _clear_task_fields(state)
        else:
            # Clear task fields if not ready to generate
            _clear_task_fields(state)
            
        # Update memory manager with conversation turn (optional - could be done per session end)
        # memory_manager.create_session_history([{"role": "user", "content": user_input}])
        
    except Exception as e:
        logger.warning(f"Error updating conversation state: {e}")
        _clear_conversation_fields(state)
        _clear_task_fields(state)


def _clear_conversation_fields(state: AgentState):
    """Clear conversation-related fields in state."""
    state["conversation_state"] = ""
    state["discovered_goal"] = ""
    state["discovered_struggle"] = ""
    state["discovered_habit"] = ""
    state["discovered_routine"] = ""
    state["goal_area"] = ""
    state["discovery_confidence"] = 0.0


def _clear_task_fields(state: AgentState):
    """Clear task-related fields in state."""
    state["generated_task_title"] = ""
    state["generated_task_sub_tasks"] = []
    state["generated_task_execution_tips"] = []
    state["generated_task_priority"] = ""
    state["generated_task_discipline"] = ""
    state["generated_task_estimated_time"] = 0
    state["task_generation_confidence"] = 0.0
    state["should_generate_task"] = False


# ---------------------------------------------------------------------------
# Node 5: ShadowAgent (Cerebras)
# ---------------------------------------------------------------------------


def _is_empty_shadow(result) -> bool:
    """Check if a Shadow output is effectively empty (all defaults)."""
    return (
        not result.shadow_analysis
        and not result.shadow_perspective
        and not result.bias_flag
        and not result.bias_description
        and not result.corrective_tasks
    )


def shadow_agent_node(state: AgentState) -> AgentState:
    """
    Meta-cognitive observer — bias detection with CoT reasoning.
    Powered by Cerebras (with OpenRouter/Groq fallback).

    JSON enforcement is now handled by _invoke_chain:
      - Native JSON mode (response_format) for supported providers
      - Parse-failure retry with short enforcement prompt
      - Schema default fallback on retry failure (never crashes)
    """
    user_input = state.get("user_input", "")

    context = (
        f"USER INPUT: {user_input}\n\n"
        f"PRIMARY AGENT CLASSIFICATION: {state.get('classification', 'general')}\n"
        f"PRIMARY AGENT RESPONSE: {state.get('final_response', '')}\n"
        f"PRIMARY AGENT BIAS FLAG: {state.get('bias_flag', False)}\n"
        f"PRIMARY AGENT BIAS DESCRIPTION: {state.get('bias_description', '')}\n"
        f"PROFILER EGO SCORE: {state.get('ego_score', 5)}\n"
        f"PROFILER LABELS: {state.get('ego_labels', [])}\n"
        f"MEMORY CONTEXT: {state.get('memory_context', '')}"
    )

    shadow_prompt = SHADOW_AGENT_SYSTEM_PROMPT + build_json_instruction(ShadowOutputSchema)
    messages = [
        {"role": "system", "content": shadow_prompt},
        {"role": "user", "content": context},
    ]

    result = None
    try:
        result = invoke_structured(ProviderRole.SHADOW, messages, ShadowOutputSchema)

        state["shadow_analysis"] = result.shadow_analysis
        state["shadow_perspective"] = result.shadow_perspective

        # If shadow detects bias (and primary didn't), upgrade the flag
        if result.bias_flag and not state.get("bias_flag", False):
            state["bias_flag"] = True
            state["bias_description"] = result.bias_description

        # Accumulate corrective tasks
        existing_tasks = state.get("extracted_tasks", [])
        for task in result.corrective_tasks:
            existing_tasks.append(task.model_dump())
        state["extracted_tasks"] = existing_tasks

    except AllProvidersExhaustedError as e:
        logger.warning(f"ShadowAgent all providers exhausted, using empty defaults: {e}")
        state["shadow_analysis"] = ""
        state["shadow_perspective"] = ""
    except Exception as e:
        logger.warning(f"ShadowAgent error, using empty defaults: {e}")
        state["shadow_analysis"] = ""
        state["shadow_perspective"] = ""

    return state


# ---------------------------------------------------------------------------
# Synthesis Node
# ---------------------------------------------------------------------------


def synthesis_node(state: AgentState) -> AgentState:
    """Combine ChatAgent response with ShadowAgent perspective."""
    response = state.get("final_response", "")
    shadow_perspective = state.get("shadow_perspective", "")

    if state.get("bias_flag") and shadow_perspective:
        response += f"\n\n⚠ Shadow Challenge: {shadow_perspective}"

    state["final_response"] = response
    return state


# ---------------------------------------------------------------------------
# LangGraph Definition — Distributed 5-Node Pipeline
# ---------------------------------------------------------------------------

workflow = StateGraph(AgentState)

# Add all nodes
workflow.add_node("profiler", profiler_node)
workflow.add_node("memory", memory_node)
workflow.add_node("chat_agent", chat_agent_node)
workflow.add_node("shadow_agent", shadow_agent_node)
workflow.add_node("micro", micro_node)
workflow.add_node("synthesis", synthesis_node)

# Pipeline: profiler → memory → conditional router
workflow.set_entry_point("profiler")
workflow.add_edge("profiler", "memory")
workflow.add_conditional_edges(
    "memory",
    conditional_router,
    {
        "chat_agent": "chat_agent",
        "micro": "micro",
    },
)

# Heavy pipeline: chat_agent → shadow_agent → synthesis → END
workflow.add_edge("chat_agent", "shadow_agent")
workflow.add_edge("shadow_agent", "synthesis")
workflow.add_edge("synthesis", END)

# Light pipeline: micro → END
workflow.add_edge("micro", END)

compiled_graph = workflow.compile()


# ---------------------------------------------------------------------------
# Public Entry Point
# ---------------------------------------------------------------------------


def process_user_input(user_input: str, history: list[dict] | None = None) -> dict:
    """
    Run the LangGraph distributed pipeline on the given user input.

    Pipeline:
      Profiler (Mistral) → Memory (Gemini) → Conditional Router →
        [ChatAgent (Groq) → ShadowAgent (Cerebras) → Synthesis]
        OR [Micro (Cloudflare)]

    Accepts conversation history for contextual memory.
    Returns the final AgentState as a dict.
    """
    initial_state: AgentState = {
        "user_input": user_input,
        "history": history or [],
        "raw_ai_output": "",
        "cot_reasoning": "",
        # Profiler
        "ego_score": 5,
        "ego_labels": [],
        "profiler_classification": "general",
        # Memory
        "memory_context": "",
        "relevant_past": "",
        "behavioral_pattern": "",
        "rolling_memory": "",
        # Chat/Shadow
        "classification": "",
        "final_response": "",
        "journal_insight": "",
        "bias_flag": False,
        "bias_description": "",
        "extracted_tasks": [],
        "shadow_analysis": "",
        "shadow_perspective": "",
        # Routing
        "use_micro": False,
        # Conversation-to-Action Layer
        "conversation_state": "",
        "discovered_goal": "",
        "discovered_struggle": "",
        "discovered_habit": "",
        "discovered_routine": "",
        "goal_area": "",
        "discovery_confidence": 0.0,
        "generated_task_title": "",
        "generated_task_sub_tasks": [],
        "generated_task_execution_tips": [],
        "generated_task_priority": "",
        "generated_task_discipline": "",
        "generated_task_estimated_time": 0,
        "task_generation_confidence": 0.0,
        "should_generate_task": False,
    }

    result = compiled_graph.invoke(initial_state)
    return dict(result)