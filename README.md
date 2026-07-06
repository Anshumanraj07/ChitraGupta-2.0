# ChitraGupta 2.0 👁️
**Agentic AI Coaching Platform | Mind & Action Observer**

ChitraGupta 2.0 is an autonomous AI coaching system that bridges the gap between unstructured conversation and structured goal execution. It combines deterministic policy-based decision-making with LLM-powered conversational intelligence to provide personalized, adaptive coaching through multi-layer intelligence subsystems.

## 🚀 Key Features

- **Deterministic Policy Engine** — Rule-based action selection (ask_question, reflect, explore_goal, generate_task, wait) ensures predictable, auditable coaching decisions
- **8 Intelligence LLM Router with Fallback** — Multi-provider LLM routing (Groq → Google → Mistral → OpenAI) with role-based chains and automatic failover
- **Identity Model** — Persistent user identity built incrementally from conversation evidence with confidence thresholds (Supabase `user_identities`)
- **Behavioral Inference** — 34 deterministic patterns detected from task history (procrastination, avoidance, perfectionism, burnout, momentum, follow-through, etc.)
- **Confidence Tracker** — 9 confidence dimensions tracked from conversation (goal_clarity, trust_rapport, readiness_for_action, etc.)
- **Coaching Planner** — Adaptive strategy selection (understand, explore, guide, challenge, support, accountability, reflective) with pacing control
- **Task Quality Engine** — Reasoning-driven task generation with required fields: reason, expected_outcome, success_criteria, micro_steps, review_condition, adaptation_strategy
- **Adaptive Memory** — Context-aware retrieval with 7-factor weighted scoring (semantic, goal relevance, struggle match, behavioral, coaching, recency, effectiveness)
- **Daily Review** — Structured reflection with focus types (daily_start, daily_end, weekly, monthly) generating task decisions and coaching adjustments
- **Karma Analytics** — Completion rates, streaks, discipline trajectory, goal area breakdown
- **Real-time Dashboard** — Next.js 16 + Tailwind 4 + Recharts with Chat, Karma, and Tasks views
- **Multi-user Architecture** — User-scoped intelligence via registry; `user_id` resolved from body → header → default

## 🛠 Tech Stack

- **Backend:** FastAPI (Python 3.12+)
- **AI Engine:** Multi-provider LLM router (Groq, Google Gemini, Mistral, OpenAI/OpenRouter, Cloudflare)
- **Database:** Supabase (PostgreSQL + pgvector) with graceful in-memory fallback
- **Frontend:** Next.js 16 (App Router) + React 19 + Tailwind CSS 4 + TypeScript + Recharts
- **Observability:** Structured logging, provider health tracking, token audit, runtime provider report

## 🏗 System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CHITRAGUPTA 2.0 ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐  │
│  │   FRONTEND   │    │    BACKEND   │    │ INTELLIGENCE │    │  DATA    │  │
│  │  (Next.js)   │◄───│  (FastAPI)   │◄───│   LAYERS     │◄───│(Supabase)│  │
│  └──────────────┘    └──────────────┘    └──────────────┘    └──────────┘  │
│         │                   │                   │                   ▲        │
│         │                   │                   │                   │        │
│         ▼                   ▼                   ▼                   │        │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                        ENGINE SHIFTER (LLM Router)                      │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐     │  │
│  │  │  Groq   │  │ Gemini  │  │ Mistral │  │ OpenAI  │  │ Cloudflare│   │  │
│  │  │(Primary)│  │(Fallback)│ │(Fallback)│ │(Fallback)│ │  (Fallback)│  │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘     │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Chat Request Pipeline

```
User Message
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 1. MEMORY RETRIEVAL (AdaptiveMemory)                                │
│    Query: current_context + goals + struggles + behavioral_patterns │
│    Output: Relevant past conversations, task outcomes, insights     │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. CONFIDENCE UPDATE (ConfidenceTracker)                            │
│    Infer evidence from user message                                 │
│    Update 9 confidence dimensions                                   │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. POLICY CONTEXT BUILDING                                          │
│    Aggregate: Identity + Behavior + Coaching + Confidence + Memory │
│    Output: PolicyContext (30+ fields)                               │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. POLICY DECISION (PolicyEngine - DETERMINISTIC)                   │
│    Rules evaluated in priority order                                │
│    Output: PolicyAction + confidence + reasoning                    │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 5. LLM RESPONSE GENERATION (EngineShifter)                          │
│    System Prompt: Policy decision + Identity + Behavior + Coaching  │
│    + Memory context                                                 │
│    Multi-provider fallback with role-based routing                  │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 6. MODEL UPDATES (Post-Interaction)                                 │
│    • Record conversation in AdaptiveMemory                          │
│    • Extract identity evidence → IdentityModel                      │
│    • Update coaching planner session count                          │
│    • Save session state (Supabase)                                  │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 7. TASK GENERATION (if policy = GENERATE_TASK)                      │
│    TaskQualityEngine with full context                              │
│    Output: QualityTask[] with reasoning, micro-steps, success criteria
└─────────────────────────────────────────────────────────────────────┘
```

## 📚 Core Intelligence Layers

| Layer | File | Purpose |
|-------|------|---------|
| Policy Engine | `core/policy_engine.py` | Deterministic action selection (5 actions, 10 rules, 30+ context dims) |
| Confidence Tracker | `core/confidence_tracker.py` | 9 confidence dimensions from conversation evidence |
| Identity Model | `core/identity_model.py` | Persistent user identity with evidence-based updates |
| Behavioral Inference | `core/behavioral_inference.py` | 34 patterns from task history + composite scores |
| Coaching Planner | `core/coaching_planner.py` | 7 adaptive strategies with pacing & difficulty control |
| Task Quality Engine | `core/task_quality_engine.py` | Reasoning-driven tasks (not templates) with quality scoring |
| Adaptive Memory | `core/adaptive_memory.py` | 7-factor weighted context-aware retrieval |
| Daily Review | `core/daily_review.py` | Structured reflection with task decisions & coaching adjustments |

## 🔌 API Endpoints

### Chat — Core Conversation
```bash
POST /api/chat
{
  "message": "I want to learn Python",
  "user_id": "user_123",       # optional (body or X-User-Id header)
  "session_id": "optional"
}

Response:
{
  "response": "That's a great goal...",
  "action": "ask_question",
  "confidence": 0.85,
  "reasoning": "Rule 'build_rapport' matched...",
  "tasks": [...],
  "coaching_context": {...},
  "memory_context": "..."
}
```

### Tasks
```bash
GET    /api/tasks?user_id=user_123          # Active tasks
GET    /api/tasks/history?user_id=user_123  # Completed/archived
POST   /api/tasks                           # Create task
PATCH  /api/tasks/{id}                      # Update (complete/uncomplete)
DELETE /api/tasks/{id}                      # Archive
```

### Karma / Analytics
```bash
GET /api/karma-summary?user_id=user_123     # Streaks, completion rate, trajectory
GET /api/daily-summaries?user_id=user_123   # Daily breakdown
GET /api/weekly-summary?user_id=user_123    # Weekly rollup
```

### Daily Review
```bash
POST /api/review/daily
{
  "user_id": "user_123",
  "review_date": "2026-07-05",
  "focus": "daily_start"  # or daily_end, weekly, monthly
}
```

### Identity & Users
```bash
GET /api/identity?user_id=user_123          # Identity profile
GET /api/users                               # List active users
```

### Health & Observability
```bash
GET /                                       # {"status": "running"}
GET /api/health                             # Detailed health
GET /api/provider-health                    # LLM provider health
GET /api/provider-audit                     # Runtime provider report
GET /api/token-audit                        # Token usage per role
```

## 💻 Running Locally

### Backend
```bash
cd ChitraGupta-2.0
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Add your keys
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# Opens http://localhost:3000
```

### Environment Variables

**Backend (`.env`):**
```bash
# Supabase (optional - runs in-memory if omitted)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# LLM Providers (at least one required)
GROQ_API_KEY=gsk_...
GOOGLE_API_KEY=AIza...
MISTRAL_API_KEY=...
OPENAI_API_KEY=sk-...
OPENROUTER_API_KEY=...
CLOUDFLARE_API_TOKEN=...
CLOUDFLARE_ACCOUNT_ID=...
CLOUDFLARE_GATEWAY_ID=...

# Optional
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=...
```

**Frontend (`.env.local`):**
```bash
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
```

## 📊 Data Persistence (Supabase Schema)

Core tables: `user_identities`, `behavioral_profiles`, `coaching_plans`, `sessions`, `tasks`, `daily_summaries`, `memory_entries`, `daily_reviews`, `streaks`

Full schema: `supabase_schema.sql`

**Graceful Degradation:** If Supabase credentials are missing, all intelligence layers fall back to in-memory operation. Data is lost on restart but the system remains fully functional for development/testing.

## 🎨 Frontend Dashboard

**Three Views (Sidebar Navigation):**

1. **Chat** — Real-time conversation with AI coach
   - Message history with bias flags, extracted tasks
   - TTS (Text-to-Speech) toggle
   - Auto-scroll, loading states

2. **Karma** — Analytics dashboard (Recharts)
   - Discipline trajectory (mental/physical line chart)
   - Tasks completed (bar chart)
   - Auto-sync from `/api/karma-summary` and `/api/tasks`

3. **Tasks** — Active task management
   - Checkbox completion with PATCH to backend
   - Priority color coding (red/zinc borders)
   - Sub-tasks and execution tips display

## 🧪 Testing

```bash
# Backend API tests
python tests/api_test.py
python tests/remaining_api_test.py

# Demo conversation flow
python demo_conversation_flow.py
```

All 16 endpoints tested: chat, tasks (4), karma (3), review, identity, users, health (4)

## 📁 Project Structure

```
ChitraGupta-2.0/
├── main.py                    # FastAPI app entry
├── requirements.txt           # Python deps
├── supabase_schema.sql        # Database schema
├── core/
│   ├── __init__.py
│   ├── user_registry.py       # Multi-user bundle registry
│   ├── engine_shifter.py      # LLM router (1,104 lines)
│   ├── policy_engine.py       # Deterministic rules
│   ├── confidence_tracker.py  # 9-dim confidence
│   ├── identity_model.py      # Evidence-based identity
│   ├── behavioral_inference.py# 34 pattern detection
│   ├── coaching_planner.py    # 7 strategies
│   ├── task_quality_engine.py # Reasoning-driven tasks
│   ├── adaptive_memory.py     # Context-aware retrieval
│   ├── daily_review.py        # Structured reflection
│   ├── conversation_manager.py
│   ├── session_manager.py
│   ├── memory_manager.py
│   ├── goal_discovery.py
│   ├── endpoints/
│   │   ├── chat.py
│   │   ├── tasks.py
│   │   ├── karma.py
│   │   └── review.py
│   ├── schemas/
│   │   ├── identity.py
│   │   ├── task.py
│   │   ├── behavior.py
│   │   ├── daily_review.py
│   │   ├── memory.py
│   │   ├── confidence.py
│   │   ├── coaching.py
│   │   └── policy.py
│   └── utils/
│       ├── supabase_client.py
│       └── json_parser.py
├── frontend/
│   ├── src/app/page.tsx       # Dashboard (chat/karma/tasks)
│   ├── src/app/layout.tsx
│   ├── src/app/globals.css
│   └── package.json
└── tests/
    ├── api_test.py
    ├── remaining_api_test.py
    └── api_results.json
```

## 📈 Observability

- **Structured logging** per module: `chitragupta.chat_endpoint`, `chitragupta.engine_shifter`, etc.
- **Provider health** tracked with model, latency, HTTP status, last failure
- **Runtime audit** per LLM call: provider, model, tokens (in/out/total), latency, fallback depth, structured output mode
- **Token audit** per role: chat, memory, profiler, shadow, fallback

---

*Version 2.0.0 | Built with deterministic policy + multi-provider LLM intelligence*
