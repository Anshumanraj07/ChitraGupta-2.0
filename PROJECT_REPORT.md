# ChitraGupta 2.0 — Project Report

## Executive Summary

ChitraGupta 2.0 is an **agentic AI coaching platform** that helps users achieve their goals through structured conversation, intelligent task generation, and behavioral pattern detection. It combines deterministic policy-based decision-making with LLM-powered conversational intelligence to provide personalized, adaptive coaching.

**Key Differentiators:**
- **Deterministic Policy Engine** — Rule-based action selection (not LLM-driven) ensures predictable, auditable coaching decisions
- **Multi-Layer Intelligence** — 7 specialized subsystems (Identity, Behavior, Confidence, Coaching, Memory, Task Quality, Daily Review) that feed into policy decisions
- **Evidence-Based Identity Tracking** — Incremental profile building from conversation evidence with confidence thresholds
- **Behavioral Pattern Detection** — 34 detectable patterns from task history and conversation with intervention suggestions
- **Adaptive Memory Retrieval** — Context-aware memory queries with multi-dimensional scoring
- **Multi-Provider LLM Fallback** — Automatic failover across Groq, Gemini, Mistral, OpenAI with role-based routing
- **Real-Time Frontend** — Next.js 16 + Tailwind 4 + Recharts dashboard with TTS support

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CHITRAGUPTA 2.0 ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐  │
│  │   FRONTEND   │    │    BACKEND   │    │ INTELLIGENCE │    │  DATA    │  │
│  │  (Next.js)   │◄───│  (FastAPI)   │◄───│   LAYERS     │◄───│ (Supabase)│  │
│  └──────────────┘    └──────────────┘    └──────────────┘    └──────────┘  │
│         │                   │                   │                   ▲        │
│         │                   │                   │                   │        │
│         ▼                   ▼                   ▼                   │        │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                        ENGINE SHIFTER (LLM Router)                      │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐     │  │
│  │  │  Groq   │  │ Gemini  │  │ Mistral │  │ OpenAI  │  │  Local  │     │  │
│  │  │(Primary)│  │(Fallback)│ │(Fallback)│ │(Fallback)│ │ (Ollama)│     │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘     │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow: Chat Request Pipeline

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
│    Update 9 confidence dimensions (goal_clarity, trust_rapport, etc)│
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
│    Output: PolicyAction (ask_question, reflect, explore_goal,       │
│              generate_task, wait) + confidence + reasoning          │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 5. LLM RESPONSE GENERATION (EngineShifter)                          │
│    System Prompt: Policy decision + Identity + Behavior + Coaching │
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
│    • Save session state                                             │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 7. TASK GENERATION (if policy = GENERATE_TASK)                      │
│    TaskQualityEngine with full context                              │
│    Output: QualityTask[] with reasoning, micro-steps, success criteria
└─────────────────────────────────────────────────────────────────────┘
```

---

## Core Intelligence Layers

### 1. Policy Engine (`core/policy_engine.py`)
**Purpose:** Deterministic action selection based on rules.

**Key Features:**
- Rule-based evaluation with priority ordering
- 30+ context dimensions as input
- 5 action types: `ask_question`, `reflect`, `explore_goal`, `generate_task`, `wait`
- Confidence scoring per decision
- Extensible rule system with conditions and actions

**Rules (Priority Order):**
| Priority | Rule | Condition | Action |
|----------|------|-----------|--------|
| 100 | crisis_intervention | burnout_risk > 0.8 | wait |
| 90 | safety_check | trust_rapport < 0.2 & depth > 3 | ask_question |
| 80 | build_rapport | trust_rapport < 0.4 & count < 5 | ask_question |
| 70 | goal_clarity_needed | goal_clarity < 0.5 | explore_goal |
| 60 | reflect_on_progress | completed_today > 0 & depth > 2 | reflect |
| 50 | generate_task_ready | readiness > 0.6 & active_tasks < 2 | generate_task |
| 40 | maintain_momentum | momentum pattern & active_tasks < 3 | generate_task |
| 30 | reduce_overwhelm | active_tasks > 3 | reflect |
| 20 | address_avoidance | avoidance_score > 0.6 | ask_question |
| 10 | default_explore | — | explore_goal |

### 2. Confidence Tracker (`core/confidence_tracker.py`)
**Purpose:** Track 9 confidence dimensions from conversation evidence.

**Dimensions:**
| Dimension | Description | Evidence Sources |
|-----------|-------------|------------------|
| goal_clarity | How clear are user's goals | Goal statements, specificity |
| constraint_clarity | Understanding of constraints | Time, energy, resource mentions |
| habit_clarity | Clarity on habit formation | Routine mentions, consistency |
| identity_clarity | Self-knowledge level | Values, strengths, beliefs |
| motivation_clarity | Understanding of drivers | Intrinsic/extrinsic language |
| routine_clarity | Daily structure clarity | Schedule, energy patterns |
| readiness_for_action | Prepared to act | Commitment language, planning |
| trust_rapport | Relationship quality | Openness, engagement depth |
| conversation_depth | Substantive exchange level | Topic depth, reflection quality |

**Update Mechanism:** Keyword/pattern-based inference from user messages with weighted evidence accumulation.

### 3. Identity Model (`core/identity_model.py`)
**Purpose:** Persistent user identity with incremental, evidence-based updates.

**Profile Structure:**
```python
IdentityProfile:
  - values: List[str]           # "health", "growth", "family"
  - beliefs: List[str]          # "I can change", "discipline = freedom"
  - goals: List[str]            # Long-term aspirations
  - fears: List[str]            # What holds them back
  - strengths/weaknesses: List[str]
  - motivation_style: Enum      # intrinsic, extrinsic, social, achievement, mastery,,
 
                                 # mastery, autonomy, purpose
  - discipline_pattern: Enum    # consistent, sporadic, burst, procrastinator,
                                 # perfectionist, all_or_nothing, gradual
  - energy_pattern: Enum        # morning, afternoon, evening, night, variable
  - learning_style: Enum        # visual, auditory, kinesthetic, reading,
                                 # experiential, reflective
  - communication_preference: Enum
  - coaching_preference: Enum   # coach, mentor, partner, accountability,
                                 # reflective, directive
  - self_image_trajectory: List # Point-in-time self-assessments
  - confidence_scores: Dict     # Per-category confidence (0-1)
  - evidence_count: Dict        # Evidence pieces per category
```

**Update Logic:**
- Evidence accumulates per category (threshold: 3 pieces)
- Weighted confidence averaging
- Minimum confidence threshold: 0.6
- Version-controlled with audit trail
- Stored in Supabase `user_identities` table

### 4. Behavioral Inference (`core/behavioral_inference.py`)
**Purpose:** Detect 34 behavioral patterns from task history + conversation.

**Detected Patterns (with composite scores):**
| Pattern | Composite Score | Key Indicators |
|---------|----------------|----------------|
| Procrastination | procrastination_score | Delayed starts, rescheduling, guilt |
| Avoidance | avoidance_score | Abandoned tasks, fear language |
| Perfectionism | perfectionism_score | "Not perfect" completions, over-planning |
| Burnout | burnout_risk | Drop in completion, exhaustion language |
| Overthinking | — | Long deliberation, excessive questions |
| Validation Seeking | — | External confirmation needs |
| Inconsistency | — | High variance, frequent streak breaks |
| Momentum | — | Completion begets completion |
| Resistance | — | Rejects structure, prefers own way |
| Follow-Through | follow_through_score | High completion rate, commitment language |
| Task Friction Sensitivity | — | Avoids hard tasks, needs exact steps |

**Outputs:**
- Active patterns with confidence
- Risk factors & protective factors
- Coaching recommendations (pacing, approach, difficulty, feedback style)

### 5. Coaching Planner (`core/coaching_planner.py`)
**Purpose:** Adaptive coaching strategy selection and pacing.

**Strategies:**
| Strategy | When Used | Pacing | Max Tasks/Session |
|----------|-----------|--------|-------------------|
| understand | Onboarding, low trust | moderate | 1 |
| explore | Goal unclear | moderate | 1 |
| guide | Clear goals, moderate readiness | moderate | 1-2 |
| challenge | High readiness, momentum | fast | 2 |
| support | Burnout risk, low energy | slow | 1 |
| accountability | Consistency issues | moderate | 1-2 |
| reflective | Deep patterns, identity work | slow | 1 |

**Adaptation Triggers:**
- Session count in current strategy (max 5-10)
- Behavioral pattern shifts
- Confidence dimension changes
- User feedback (explicit/implicit)

### 6. Task Quality Engine (`core/task_quality_engine.py`)
**Purpose:** Generate high-quality, reasoning-driven tasks (not templates).

**QualityTask Fields (Required Reasoning):**
```python
QualityTask:
  - title, description
  - task_type: micro/habit/project/review/experiment/recovery
  - priority: critical/high/medium/low/optional
  - difficulty: trivial/easy/moderate/challenging/difficult
  - reason: "Why this task, why now, what it addresses"  # REQUIRED
  - expected_outcome: "What changes if completed"        # REQUIRED
  - success_criteria: List[str]                          # Measurable signals
  - micro_steps: List[str]                               # Atomic steps
  - review_condition: "end_of_day"/"after_completion"/"if_blocked"
  - adaptation_strategy: "reduce_scope"/"extend_time"/
                          "change_approach"/"archive"
  - goal_area, discipline, coaching_strategy
  - alignment_score: 0-1 (aligns with goals/identity)
  - user_commitment_level: 0-1
```

**Generation Pipeline:**
1. Context assembly (identity, behavior, confidence, active tasks)
2. Candidate generation via LLM with structured output
3. Quality filtering (alignment, feasibility, variety)
4. Ranking by composite score
5. Top-N selection with rejection reasoning

### 7. Adaptive Memory (`core/adaptive_memory.py`)
**Purpose:** Context-aware memory retrieval with multi-dimensional scoring.

**MemoryEntry:**
```python
MemoryEntry:
  - content: str
  - summary: str
  - session_id: str
  - timestamp: datetime
  - coaching_effectiveness: float
  - intervention_type: str
  - goal_area: str
  - behavioral_tags: List[str]
  - embedding: Optional[List[float]]  # For semantic search
```

**Retrieval Scoring (Weighted):**
| Factor | Weight | Description |
|--------|--------|-------------|
| Semantic Similarity | 0.35 | Embedding cosine similarity |
| Goal Relevance | 0.20 | Matches current goal area |
| Struggle Match | 0.15 | Addresses current struggle |
| Behavioral Relevance | 0.10 | Matches active patterns |
| Coaching Strategy Match | 0.10 | Same intervention type |
| Recency | 0.05 | More recent = higher |
| Effectiveness | 0.05 | High coaching effectiveness |

### 8. Daily Review (`core/daily_review.py`)
**Purpose:** Structured end-of-day / start-of-day reflection.

**Review Focus Types:**
- `daily_start` — Morning planning, task selection
- `daily_end` — Evening reflection, completion review
- `weekly` — Weekly pattern analysis
- `monthly` — Monthly trajectory review

**Outputs:**
- Completion rate analysis
- Pattern detection
- Task decisions (continue/modify/retry/archive/split/merge)
- New task generation
- Coaching strategy adjustments
- Encouragement / warning signals

---

## Engine Shifter — Multi-Provider LLM Router

**File:** `core/engine_shifter.py` (1,104 lines)

**Architecture:**
```
Role-Based Provider Chains:
├── CHAT (conversation)
│   ├── Groq: llama-3.1-8b-instant (primary)
│   ├── Google: gemini-1.5-flash
│   ├── Mistral: mistral-small-latest
│   └── OpenAI: gpt-4o-mini
├── STRUCTURED (JSON/output parsing)
│   ├── Groq: llama-3.1-8b-instant
│   ├── Google: gemini-1.5-flash
│   └── OpenAI: gpt-4o-mini
├── FAST (classification/extraction)
│   ├── Groq: llama-3.1-8b-instant
│   └── Google: gemini-1.5-flash
└── EMBEDDING
    ├── Google: text-embedding-004
    └── OpenAI: text-embedding-3-small
```

**Key Features:**
- Automatic failover with exponential backoff (tenacity)
- Per-role provider chains with health tracking
- Structured output parsing with Pydantic schemas
- Token usage logging per call
- Sync `invoke_with_fallback()` + `invoke_structured()` APIs
- Health monitoring with circuit breaker pattern

**Configuration:** Environment variables for API keys
```bash
GROQ_API_KEY=...
GOOGLE_API_KEY=...
MISTRAL_API_KEY=...
OPENAI_API_KEY=...
```

---

## API Endpoints

### Chat (`/api/chat`) — Core Conversation
```python
POST /api/chat
{
  "message": "I want to learn Python",
  "user_id": "default_user",
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

### Tasks (`/api/tasks`)
```python
GET    /api/tasks              # List active tasks
POST   /api/tasks              # Create task
PATCH  /api/tasks/{id}         # Update task (complete/uncomplete)
DELETE /api/tasks/{id}         # Archive task
```

### Karma/Summary (`/api/karma-summary`, `/api/daily-summaries`, `/api/weekly-summary`)
```python
GET /api/karma-summary?user_id=default_user
Response:
{
  "total_karma": 1250,
  "average_daily_karma": 42.3,
  "current_streak_days": 7,
  "longest_streak_days": 21,
  "completion_rate": 78.5,
  "total_tasks_completed": 156,
  "recent_trend": "up",
  "goal_areas": {"learning": 45, "fitness": 32},
  "days_tracked": 30
}
```

### Daily Review (`/api/review/daily`, `/api/review/history`)
```python
POST /api/review/daily
{
  "user_id": "default_user",
  "review_date": "2026-07-05",
  "focus": "daily_start"
}
```

### Health (`/`)
```python
GET /
Response: {"name": "ChitraGupta 2.0", "status": "running", "version": "2.0.0"}
```

---

## Frontend Architecture

**Stack:** Next.js 16 (App Router) + React 19 + Tailwind CSS 4 + TypeScript + Recharts

### Structure
```
frontend/
├── src/
│   └── app/
│       ├── page.tsx          # Main dashboard (chat + karma + tasks views)
│       ├── layout.tsx        # Root layout with Geist fonts
│       └── globals.css       # Tailwind 4 + CSS variables
├── package.json
├── tsconfig.json
├── next.config.ts
├── eslint.config.mjs
└── postcss.config.mjs
```

### Main Dashboard (`page.tsx`) — Single Page Application

**Three Views (Sidebar Navigation):**
1. **Chat** — Real-time conversation with AI coach
   - Message history with bias flags, extracted tasks
   - TTS (Text-to-Speech) toggle
   - Auto-scroll, loading states
2. **Karma** — Analytics dashboard with Recharts
   - Discipline trajectory (mental/physical line chart)
   - Tasks completed (bar chart)
   - Auto-sync from `/api/karma-summary` and `/api/tasks`
3. **Tasks** — Active task management
   - Checkbox completion with PATCH to backend
   - Priority color coding (red/zinc borders)
   - Sub-tasks and execution tips display

**API Integration:**
```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

// Chat with history
fetch(`${API_BASE}/api/chat`, {
  method: "POST",
  body: JSON.stringify({ message, history: messages.slice(-20) })
})

// Karma sync
Promise.all([
  fetch(`${API_BASE}/api/karma-summary`),
  fetch(`${API_BASE}/api/tasks`)
])
```

**Styling:** Minimalist dark theme (zinc/black palette), Geist fonts, inline SVG icons (no dependencies), custom scrollbar hiding.

---

## Data Models (Supabase Schema)

### Core Tables

```sql
-- User identity profiles
CREATE TABLE user_identities (
  user_id TEXT PRIMARY KEY,
  version INT DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  values TEXT[],
  beliefs TEXT[],
  goals TEXT[],
  fears TEXT[],
  strengths TEXT[],
  weaknesses TEXT[],
  motivation_style TEXT,
  discipline_pattern TEXT,
  energy_pattern TEXT,
  learning_style TEXT,
  communication_preference TEXT,
  coaching_preference TEXT,
  self_image_trajectory JSONB,
  confidence_scores JSONB,
  evidence_count JSONB,
  last_session_date DATE,
  sessions_since_update INT DEFAULT 0
);

-- Behavioral profiles
CREATE TABLE behavioral_profiles (
  user_id TEXT PRIMARY KEY,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  patterns JSONB,
  procrastination_score FLOAT,
  avoidance_score FLOAT,
  perfectionism_score FLOAT,
  burnout_risk FLOAT,
  consistency_score FLOAT,
  follow_through_score FLOAT,
  motivation_quality FLOAT,
  emotional_stability FLOAT,
  primary_pattern TEXT,
  secondary_patterns TEXT[],
  risk_factors TEXT[],
  protective_factors TEXT[],
  recommended_pacing TEXT,
  recommended_approach TEXT,
  task_difficulty_preference TEXT,
  feedback_style TEXT,
  pattern_history JSONB
);

-- Coaching plans
CREATE TABLE coaching_plans (
  user_id TEXT PRIMARY KEY,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  primary_strategy TEXT,
  secondary_strategies TEXT[],
  pacing TEXT,
  focus_areas TEXT[],
  sessions_in_current_strategy INT DEFAULT 0,
  max_tasks_per_session INT DEFAULT 1,
  min_reflection_ratio FLOAT DEFAULT 0.3,
  challenge_level FLOAT DEFAULT 0.5,
  adaptation_count INT DEFAULT 0,
  strategy_history JSONB
);

-- Sessions
CREATE TABLE sessions (
  user_id TEXT PRIMARY KEY,
  session_id TEXT,
  conversation_count INT DEFAULT 0,
  conversation_state TEXT DEFAULT 'onboarding',
  active_tasks JSONB DEFAULT '[]',
  completed_today INT DEFAULT 0,
  missed_today INT DEFAULT 0,
  streak_days INT DEFAULT 0,
  current_date DATE DEFAULT CURRENT_DATE,
  yesterday_tasks JSONB DEFAULT '[]',
  current_task JSONB,
  current_struggle TEXT,
  session_start_time TIMESTAMPTZ,
  last_action TEXT,
  last_action_time TIMESTAMPTZ,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tasks
CREATE TABLE tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT,
  title TEXT,
  description TEXT,
  task_type TEXT,
  priority TEXT,
  difficulty TEXT,
  reason TEXT,
  expected_outcome TEXT,
  success_criteria JSONB,
  estimated_duration_minutes INT,
  micro_steps JSONB,
  dependencies JSONB,
  review_condition TEXT,
  adaptation_strategy TEXT,
  max_retries INT DEFAULT 2,
  retry_count INT DEFAULT 0,
  goal_area TEXT,
  discipline TEXT,
  coaching_strategy TEXT,
  status TEXT DEFAULT 'pending',
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  blocked_reason TEXT,
  actual_duration_minutes INT,
  user_commitment_level FLOAT,
  generated_confidence FLOAT,
  alignment_score FLOAT,
  completion_notes TEXT,
  difficulty_rating INT,
  value_rating INT,
  date DATE DEFAULT CURRENT_DATE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Daily summaries (for karma)
CREATE TABLE daily_summaries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT,
  date DATE,
  karma INT DEFAULT 0,
  tasks_completed INT DEFAULT 0,
  tasks_missed INT DEFAULT 0,
  discipline_score FLOAT DEFAULT 0,
  mental_score FLOAT DEFAULT 0,
  physical_score FLOAT DEFAULT 0,
  goals_addressed TEXT[],
  trajectory JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Memory entries
CREATE TABLE memory_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT,
  content TEXT,
  summary TEXT,
  session_id TEXT,
  timestamp TIMESTAMPTZ DEFAULT NOW(),
  coaching_effectiveness FLOAT,
  intervention_type TEXT,
  goal_area TEXT,
  behavioral_tags TEXT[],
  embedding VECTOR(768)  -- pgvector for semantic search
);

-- Daily reviews
CREATE TABLE daily_reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT,
  review_date DATE,
  focus TEXT,
  completion_rate FLOAT,
  overall_assessment TEXT,
  key_insights JSONB,
  patterns_noticed JSONB,
  task_decisions JSONB,
  new_tasks JSONB,
  coaching_strategy_adjustment TEXT,
  pacing_recommendation TEXT,
  focus_areas JSONB,
  avoid_areas JSONB,
  identity_updates JSONB,
  behavioral_updates JSONB,
  confidence_adjustments JSONB,
  encouragement TEXT,
  warning_signals JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Streaks
CREATE TABLE streaks (
  user_id TEXT PRIMARY KEY,
  current_streak INT DEFAULT 0,
  longest_streak INT DEFAULT 0,
  last_completion_date DATE,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Configuration & Deployment

### Environment Variables

**Backend (`.env`):**
```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# LLM Providers (at least one required)
GROQ_API_KEY=gsk_...
GOOGLE_API_KEY=AIza...
MISTRAL_API_KEY=...
OPENAI_API_KEY=sk-...

# Optional
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=...
```

**Frontend (`.env.local`):**
```bash
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
```

### Running Locally

**Backend:**
```bash
cd /path/to/ChitraGupta-2.0
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Add your keys
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
# Opens http://localhost:3000
```

### Docker Deployment

**Backend Dockerfile:**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Frontend Dockerfile:**
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - supabase  # If local
  
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_BASE=http://backend:8000
    depends_on:
      - backend
### Production Considerations

| Aspect | Recommendation |
|--------|----------------|
| Supabase | Enable RLS policies, connection pooling |
| LLM Keys | Use secret manager (AWS Secrets, GCP Secret Manager) |
| Scaling | Horizontal pod autoscaling for FastAPI workers |
| Monitoring | LangSmith for LLM traces, Prometheus/Grafana for metrics |
| Logging | Structured JSON logs to ELK/Loki |
| Rate Limiting | Per-user limits on chat endpoint |
| Auth | Add JWT authentication (currently user_id in body) |

---

## Observability & Monitoring

### Logging
- Structured logging with `logging` module
- Loggers per module: `chitragupta.chat_endpoint`, `chitragupta.engine_shifter`, etc.
- Levels: DEBUG, INFO, WARNING, ERROR
- LLM calls logged with provider, model, tokens, latency, fallback status

### Metrics to Track
| Metric | Source | Purpose |
|--------|--------|---------|
| Chat latency (p50/p95/p99) | Engine shifter | Performance |
| Fallback rate | Engine shifter | Provider reliability |
| Policy action distribution | Policy engine | Coaching behavior |
| Task completion rate | Tasks API | User engagement |
| Confidence dimension trends | Confidence tracker | User progress |
| Behavioral pattern prevalence | Behavioral inference | Population insights |
| Memory retrieval relevance | Adaptive memory | Context quality |
| Daily review completion | Review endpoint | Retention |

### Health Checks
```bash
# Backend
GET /  # Returns {"status": "running"}

# LLM Providers
# Engine shifter logs each call with provider/model/latency
```

---

## Testing

### Current Test Structure
```
tests/
├── api_results.json      # Sample API responses
├── api_test.ps1          # PowerShell API tests
└── api_test.py           # Python API tests
```

### Recommended Test Coverage

**Unit Tests (pytest):**
- Policy engine rule evaluation
- Confidence tracker evidence inference
- Identity model evidence processing
- Behavioral pattern detection rules
- Task quality engine generation logic
- Memory retrieval scoring
- Daily review calculations

**Integration Tests:**
- Full chat pipeline (mock LLM)
- Task generation → completion → review cycle
- Multi-user session isolation
- Supabase CRUD operations

**E2E Tests (Playwright):**
- Chat conversation flow
- Task creation/completion
- View switching (chat/karma/tasks)
- TTS toggle

**Load Tests:**
- Concurrent chat requests
- LLM provider failover under load
- Memory retrieval with large datasets

---

## Known Issues & Technical Debt

### Current Limitations
1. **No Authentication** — `user_id` passed in request body/header (dev only)
2. **Supabase Optional** — Runs in-memory if credentials missing (data lost on restart)
3. **No Rate Limiting** — Chat endpoint vulnerable to abuse
4. **No Streaming** — Full LLM response before returning to user
5. **Embeddings Not Implemented** — Memory uses text matching only
6. **Frontend-Backend Type Mismatch** — Frontend expects `discipline_score`, backend returns different fields

### Code Quality Issues
- `engine_shifter.py` is 1,104 lines (monitor - split if needed)
- Some `Any` types in schemas
- Inconsistent error handling patterns
- No request validation middleware
- Missing OpenAPI documentation enhancements

### Architecture Improvements Needed
- Extract engine shifter into separate package
- Add event bus for model updates (decouple chat from identity/behavior)
- Implement background workers for daily reviews, summarization
- Add WebSocket support for real-time updates
- Implement proper user authentication (Supabase Auth)

---

## Future Roadmap

### Phase 1: Stabilization (Current)
- [x] Fix chat endpoint LLM integration
- [x] Implement identity evidence extraction
- [x] Connect all API endpoints
- [x] Multi-user support via user registry
- [x] Remove legacy brain.py from active path
- [ ] Add authentication (Supabase Auth + JWT)
- [ ] Add rate limiting
- [ ] Fix frontend-backend type contracts

### Phase 2: Intelligence Enhancement
- [ ] Semantic memory with pgvector embeddings
- [ ] Streaming LLM responses (Server-Sent Events)
- [ ] Multi-turn conversation context optimization
- [ ] Advanced behavioral pattern ML models
- [ ] Cross-user pattern learning (privacy-preserving)

### Phase 3: Platform Features
- [ ] Mobile app (React Native)
- [ ] Team/organization views
- [ ] Coach dashboard for human coaches
- [ ] Integration marketplace (Notion, Obsidian, Google Calendar)
- [ ] Voice interface (STT/TTS)

### Phase 4: Intelligence Autonomy
- [ ] Autonomous task scheduling
- [ ] Proactive interventions (push notifications)
- [ ] Goal achievement prediction
- [ ] Personalized curriculum generation
- [ ] Multi-modal input (images, voice, documents)

---

## Appendix: File Inventory

### Backend Core (`core/`)
```
core/
├── __init__.py
├── brain.py                    # Main orchestrator (legacy)
├── conversation_manager.py     # Session management
├── engine_shifter.py           # LLM router (1,104 lines)
├── goal_discovery.py           # Goal extraction
├── memory_manager.py           # Memory operations
├── session_manager.py          # Session persistence
├── task_generator.py           # Task creation (legacy)
├── endpoints/
│   ├── __init__.py
│   ├── chat.py                 # Main chat endpoint
│   ├── tasks.py                # Task CRUD
│   ├── karma.py                # Analytics
│   └── review.py               # Daily review
├── schemas/
│   ├── __init__.py
│   ├── identity.py             # Identity models
│   ├── task.py                 # Task models
│   ├── behavior.py             # Behavioral models
│   ├── daily_review.py         # Review models
│   ├── memory.py               # Memory models
│   ├── confidence.py           # Confidence models
│   ├── coaching.py             # Coaching models
│   └── policy.py               # Policy models
├── confidence_tracker.py       # 9-dimension confidence
├── identity_model.py           # Identity persistence
├── behavioral_inference.py     # 34 pattern detection
├── coaching_planner.py         # Strategy selection
├── task_quality_engine.py      # Reasoning-driven tasks
├── adaptive_memory.py          # Context-aware retrieval
├── daily_review.py             # Structured reflection
├── policy_engine.py            # Deterministic rules
└── utils/
    ├── __init__.py
    ├── supabase_client.py      # Database client
    └── json_parser.py          # LLM output parsing
```

### Frontend (`frontend/src/app/`)
```
frontend/src/app/
├── page.tsx        # Main dashboard (chat/karma/tasks)
├── layout.tsx      # Root layout
└── globals.css     # Tailwind 4 styles
```

### Configuration
```
├── main.py                 # FastAPI app entry
├── requirements.txt        # Python dependencies
├── package.json            # Root (minimal)
├── frontend/package.json   # Frontend dependencies
├── supabase_schema.sql     # Database schema
├── README.md               # Project overview
├── EXECUTIVE_SUMMARY.md    # High-level summary
├── core_principles.md      # Design principles
├── IMPLEMENTATION_PLAN.md  # Development plan
└── PROJECT_REPORT.md       # This file
```

---

## Conclusion

ChitraGupta 2.0 represents a **sophisticated agentic coaching system** that moves beyond simple chatbots by combining:

1. **Deterministic Policy Control** — Predictable, auditable coaching decisions
2. **Multi-Layer Intelligence** — 8 specialized subsystems with distinct responsibilities
3. **Evidence-Based Personalization** — Identity and behavior built from real interactions
4. **Quality-First Task Generation** — Reasoning-driven tasks with measurable outcomes
5. **Resilient LLM Infrastructure** — Multi-provider fallback with role-based routing
6. **Real-Time Dashboard** — Live analytics and task management

The system is **production-ready for beta testing** with the core chat pipeline functional, all API endpoints responding, and the frontend integrated. Primary next steps are authentication, rate limiting, and embedding-based semantic memory.

---

*Report generated: 2026-07-05*  
*Version: 2.0.0*  
*Commit: e709f03*