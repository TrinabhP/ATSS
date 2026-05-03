# Tasks — Supabase Integration for LabOS

## Task 1: Supabase Database Schema Setup
- [x] 1.1 Create the `projects` table in Supabase with columns: `id` (UUID PK), `user_id` (UUID FK to auth.users), `name` (text), `abstract` (text), `status` (text, default 'running'), `created_at` (timestamptz), `updated_at` (timestamptz)
- [x] 1.2 Enable RLS on `projects` table and create policies for SELECT, INSERT, UPDATE, DELETE restricted to `auth.uid() = user_id`
- [x] 1.3 Create the `analysis_results` table in Supabase with columns: `id` (UUID PK), `project_id` (UUID FK to projects.id, UNIQUE), `user_id` (UUID FK to auth.users), `literature` (jsonb), `hypothesis` (jsonb), `procedure` (jsonb), `final_recommendation` (text), `confidence_level` (text), `action_items` (jsonb, default '[]'), `caveats` (jsonb, default '[]'), `created_at` (timestamptz)
- [x] 1.4 Enable RLS on `analysis_results` table with SELECT policy restricted to `auth.uid() = user_id` (no INSERT/UPDATE policies — backend uses service role key)

## Task 2: Environment Variable Configuration
- [x] 2.1 Update `ATSS/.env.example` to document all required Supabase environment variables (`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`) with placeholder values
- [x] 2.2 Verify `ATSS/.gitignore` includes `.env` to prevent committing secrets
- [x] 2.3 Update `ATSS/labos-mockup/.gitignore` to include `.env` if not already present

## Task 3: Frontend Supabase Client Initialization
- [x] 3.1 Install `@supabase/supabase-js` in `ATSS/labos-mockup/` via npm
- [x] 3.2 Create `ATSS/labos-mockup/src/lib/supabase.js` — singleton client initialized from `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`, throwing descriptive errors if either is missing

## Task 4: Auth Context and Session Management
- [x] 4.1 Create `ATSS/labos-mockup/src/context/AuthContext.jsx` — React context provider exposing `{ user, session, loading }`, subscribing to `onAuthStateChange`, and restoring existing sessions on mount
- [x] 4.2 Update `ATSS/labos-mockup/src/main.jsx` to wrap the app with `AuthProvider`

## Task 5: Protected Routes
- [x] 5.1 Create `ATSS/labos-mockup/src/components/ProtectedRoute.jsx` — route wrapper that redirects unauthenticated users to sign-in, shows loading indicator during session check
- [x] 5.2 Update `ATSS/labos-mockup/src/App.jsx` to wrap protected routes (`/projects`, `/projects/new`, `/projects/:id`) with `ProtectedRoute` and redirect authenticated users away from sign-in page to `/projects`

## Task 6: Sign-In Page with Supabase Auth
- [x] 6.1 Update `ATSS/labos-mockup/src/pages/SignIn.jsx` to add password field, implement `supabase.auth.signInWithPassword()`, display auth errors, and add sign-up toggle with `supabase.auth.signUp()`
- [x] 6.2 Add sign-out functionality — add a sign-out button to the Layout component that calls `supabase.auth.signOut()` and redirects to sign-in

## Task 7: Project Creation and Persistence (Frontend)
- [x] 7.1 Update `ATSS/labos-mockup/src/pages/NewProject.jsx` to insert a new row into the `projects` table via Supabase on form submit (with `user_id`, default name, abstract, status 'running'), navigate to `/projects/{id}` on success, display error on failure

## Task 8: Project Listing from Supabase (Frontend)
- [x] 8.1 Update `ATSS/labos-mockup/src/pages/ProjectList.jsx` to query the `projects` table for the authenticated user's projects ordered by `created_at` descending, display loading state, render project cards with name/status/date, and show empty state when no projects exist
- [x] 8.2 Add status badge rendering to project cards reflecting `'running'`, `'completed'`, or `'error'` status values

## Task 9: Project Rename (Frontend)
- [x] 9.1 Add inline rename functionality to `ProjectList.jsx` or `ProjectDashboard.jsx` — editable field pre-filled with current name, Supabase update on confirm, reject whitespace-only names, revert on failure

## Task 10: Backend Supabase Client
- [x] 10.1 Install `supabase` Python package — add `supabase>=2.0.0` to `ATSS/requirements.txt`
- [x] 10.2 Create `ATSS/research_lab/supabase_client.py` — lazy singleton client using `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`, with `get_client()` raising `EnvironmentError` on missing vars
- [x] 10.3 Implement `save_analysis_results(project_id, user_id, results)` in `supabase_client.py` — upserts to `analysis_results` table, logs and swallows errors (never raises)
- [x] 10.4 Implement `update_project_status(project_id, status)` in `supabase_client.py` — updates `projects` table status column, logs and swallows errors (never raises)

## Task 11: Backend Authentication Middleware
- [x] 11.1 Create `ATSS/research_lab/auth.py` — FastAPI dependency `get_current_user(request)` that extracts JWT from `Authorization: Bearer` header, verifies it using Supabase JWT secret or JWKS, and returns `user_id` from the `sub` claim. Returns 401 on missing/invalid token.
- [x] 11.2 Update `ATSS/research_lab/server.py` — add `project_id: str` and `user_id: str` fields to `AnalyzeRequest`, apply `Depends(get_current_user)` to `/api/analyze` and `/api/analyze/stream` endpoints, keep `/health` and `/api/chat/*` unauthenticated

## Task 12: Analysis Results Persistence from Backend
- [x] 12.1 Update `ATSS/research_lab/server.py` (or `graph.py` integration) — after pipeline completes, call `save_analysis_results()` with the pipeline output and `update_project_status(project_id, 'completed')`. On pipeline failure, call `update_project_status(project_id, 'error')`.

## Task 13: Loading Persisted Analysis Results (Frontend)
- [x] 13.1 Update `ATSS/labos-mockup/src/pages/ProjectDashboard.jsx` — on mount, query `analysis_results` for the project. If results exist, render them directly without triggering the pipeline. If no results, show the pipeline form and run analysis as before.
- [x] 13.2 Update `ProjectDashboard.jsx` to include JWT in `Authorization: Bearer` header and pass `project_id` and `user_id` in the request body when calling `/api/analyze/stream`

## Task 14: Frontend Authenticated API Requests
- [x] 14.1 Create a helper utility (e.g., `src/lib/api.js`) or update fetch calls in `ProjectDashboard.jsx` to automatically include the Supabase session access token in the `Authorization: Bearer` header for analyze endpoints
- [x] 14.2 Add 401 response handling — redirect to sign-in page when analyze endpoints return 401

## Task 15: Verify Chat Data Exclusion (skipped — verification only, no code changes needed)
- [ ]* 15.1 Verify that `ATSS/research_lab/chat/` modules have no Supabase imports and continue using in-memory storage only
- [ ]* 15.2 Verify that frontend chat components (`ChatPanel.jsx`) make no Supabase DB calls

## Task 16: Backend Unit Tests (skipped — not required for functioning)
- [ ]* 16.1 Write pytest tests for `supabase_client.py` — test `get_client()` raises `EnvironmentError` on missing env vars, test singleton behavior, test `save_analysis_results()` calls correct table with correct payload, test `update_project_status()` calls correct table
- [ ]* 16.2 Write pytest tests for `auth.py` — test JWT extraction, test 401 on missing/invalid token, test user_id extraction from valid token
- [ ]* 16.3 Write property-based tests (hypothesis) for Property 3 (analysis results upsert data integrity) and Property 4 (Supabase write error resilience) and Property 5 (JWT user_id extraction)

## Task 17: Frontend Unit Tests (skipped — not required for functioning)
- [ ]* 17.1 Set up Vitest + React Testing Library in `ATSS/labos-mockup/` if not already configured
- [ ]* 17.2 Write tests for `AuthContext`, `ProtectedRoute`, `SignIn`, `ProjectList`, `NewProject`, and `ProjectDashboard` components covering key acceptance criteria
- [ ]* 17.3 Write property-based tests (fast-check) for Property 1 (project list rendering completeness) and Property 2 (whitespace-only rename rejection)
