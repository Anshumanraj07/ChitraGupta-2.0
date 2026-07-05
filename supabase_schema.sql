-- ============================================================
-- ChitraGupta 2.0 — Supabase Table Schemas
-- ============================================================
-- Run these SQL statements in the Supabase SQL Editor to create
-- the required tables. Existing tables (tasks, journals) are
-- included for reference — do NOT re-create if they already exist.
-- ============================================================

-- ============================================================
-- EXISTING TABLES (for reference — do NOT re-run if already created)
-- ============================================================

-- tasks table (already exists)
-- CREATE TABLE tasks (
--   id BIGSERIAL PRIMARY KEY,
--   user_id TEXT DEFAULT 'master',
--   title TEXT NOT NULL,
--   sub_tasks JSONB DEFAULT '[]',
--   execution_tips JSONB DEFAULT '[]',
--   priority TEXT DEFAULT 'medium',
--   discipline TEXT DEFAULT 'mental',
--   completed BOOLEAN DEFAULT FALSE,
--   created_at TIMESTAMPTZ DEFAULT NOW()
-- );

-- journals table (already exists)
-- CREATE TABLE journals (
--   id BIGSERIAL PRIMARY KEY,
--   user_id TEXT DEFAULT 'master',
--   content TEXT NOT NULL,
--   insight TEXT,
--   created_at TIMESTAMPTZ DEFAULT NOW()
-- );

-- ============================================================
-- NEW TABLES — Required for Rolling Summarization
-- ============================================================

-- Raw chat messages (persists every user + assistant message for cron summarization)
CREATE TABLE IF NOT EXISTS chats (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT DEFAULT 'master',
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast cron queries (last 24 hours)
CREATE INDEX IF NOT EXISTS idx_chats_created_at ON chats (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chats_user_id ON chats (user_id);

-- Daily summaries (one row per user per day — populated by daily_summarizer.py cron)
CREATE TABLE IF NOT EXISTS daily_summaries (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT DEFAULT 'master',
    summary_date DATE NOT NULL,
    summary TEXT NOT NULL,
    dominant_emotion TEXT DEFAULT 'neutral',
    task_count INT DEFAULT 0,
    discipline_mental FLOAT DEFAULT 50.0,
    discipline_physical FLOAT DEFAULT 50.0,
    key_topics TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, summary_date)
);

-- Index for rolling memory queries (last 14 days)
CREATE INDEX IF NOT EXISTS idx_daily_summaries_date ON daily_summaries (summary_date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_summaries_user ON daily_summaries (user_id);

-- ============================================================
-- ROW-LEVEL SECURITY (optional but recommended)
-- ============================================================

ALTER TABLE chats ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_summaries ENABLE ROW LEVEL SECURITY;

-- Policy: users can only read their own data
CREATE POLICY chats_user_policy ON chats
    FOR ALL USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY daily_summaries_user_policy ON daily_summaries
    FOR ALL USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

-- Note: If using service_role key from backend (no JWT auth yet),
-- RLS is bypassed. These policies are defense-in-depth for future auth.