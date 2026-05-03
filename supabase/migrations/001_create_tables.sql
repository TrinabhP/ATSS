-- Migration: Create projects and analysis_results tables for LabOS Supabase integration
-- Applied via Supabase MCP to the hosted database

-- ============================================================
-- Task 1.1: Create the projects table
-- ============================================================
CREATE TABLE projects (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES auth.users(id),
    name        TEXT NOT NULL,
    abstract    TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'running',
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- Task 1.2: Enable RLS on projects table with user-scoped policies
-- ============================================================
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can select own projects"
    ON projects FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own projects"
    ON projects FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own projects"
    ON projects FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own projects"
    ON projects FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================================
-- Task 1.3: Create the analysis_results table
-- ============================================================
CREATE TABLE analysis_results (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id            UUID NOT NULL UNIQUE REFERENCES projects(id),
    user_id               UUID NOT NULL REFERENCES auth.users(id),
    literature            JSONB,
    hypothesis            JSONB,
    procedure             JSONB,
    final_recommendation  TEXT,
    confidence_level      TEXT,
    action_items          JSONB DEFAULT '[]',
    caveats               JSONB DEFAULT '[]',
    created_at            TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- Task 1.4: Enable RLS on analysis_results with SELECT-only policy
-- (Backend uses service role key for INSERT/UPDATE, bypassing RLS)
-- ============================================================
ALTER TABLE analysis_results ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can select own results"
    ON analysis_results FOR SELECT
    USING (auth.uid() = user_id);
