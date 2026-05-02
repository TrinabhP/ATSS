# Requirements Document

## Introduction

This feature integrates Supabase as the persistent data layer and authentication provider for LabOS. The Python backend (LangGraph pipeline) will write all research session data — including every agent output, critic review, and final recommendation — to Supabase after each pipeline run. The React/Vite frontend (`labos-mockup/`) will read that data from Supabase directly, replacing all hardcoded mock data. Supabase Auth will gate the entire frontend, replacing the current no-op sign-in form. All database access will be secured with Row-Level Security (RLS) policies so users can only read and write their own data. Supabase middleware will be added to the React app to manage session state and protect routes.

The Supabase schema does not yet exist and must be designed and created as part of this feature. The user will supply their own Supabase project URL and anon key via environment variables; this spec does not provision a Supabase project.

---

## Glossary

- **Supabase_Client**: The `@supabase/supabase-js` JavaScript client used by the React frontend to communicate with Supabase.
- **Supabase_Python_Client**: The `supabase-py` Python client used by the backend pipeline to write data to Supabase.
- **Research_Session**: A single end-to-end pipeline run, identified by a UUID, tied to the user who submitted the abstract.
- **Agent_Output**: A persisted record of one agent's final approved output (literature, hypothesis, or procedure) within a Research_Session.
- **Critic_Review**: A persisted record of one Orchestrator review event (pass or fail) for a given agent within a Research_Session.
- **Final_Synthesis**: The persisted final recommendation, confidence level, action items, and caveats produced at the end of a Research_Session.
- **Auth_Session**: A Supabase Auth session token pair (access token + refresh token) held by the React frontend.
- **RLS**: Row-Level Security — Postgres policies enforced by Supabase that restrict which rows a given authenticated user may read or write.
- **Protected_Route**: A React route that redirects unauthenticated users to the sign-in page.
- **Auth_Guard**: A React component that checks for a valid Auth_Session before rendering its children.
- **Middleware**: A React context provider (`SupabaseProvider`) that initialises the Supabase_Client, listens for auth state changes, and exposes the current session and user to all child components.
- **Service_Role_Key**: A Supabase secret key that bypasses RLS; used only in the Python backend, never exposed to the browser.
- **Anon_Key**: The Supabase public key used by the React frontend; safe to expose in the browser because RLS enforces access control.

---

## Requirements

### Requirement 1: Supabase Database Schema

**User Story:** As a developer, I want a well-structured Supabase schema, so that all LabOS data is stored in a normalised, queryable form with proper access controls.

#### Acceptance Criteria

1. THE Schema SHALL contain a `research_sessions` table with columns: `id` (UUID primary key, default `gen_random_uuid()`), `user_id` (UUID, foreign key to `auth.users.id`), `abstract` (text, not null), `status` (text, not null, one of `'running'`, `'complete'`, `'error'`), `created_at` (timestamptz, default `now()`), `updated_at` (timestamptz, default `now()`).
2. THE Schema SHALL contain an `agent_outputs` table with columns: `id` (UUID primary key), `session_id` (UUID, foreign key to `research_sessions.id` with `ON DELETE CASCADE`), `agent_name` (text, not null, one of `'literature'`, `'hypothesis'`, `'procedure'`), `revision_count` (integer, not null), `output_json` (jsonb, not null), `created_at` (timestamptz, default `now()`).
3. THE Schema SHALL contain a `critic_reviews` table with columns: `id` (UUID primary key), `session_id` (UUID, foreign key to `research_sessions.id` with `ON DELETE CASCADE`), `agent_name` (text, not null), `revision_number` (integer, not null), `passed` (boolean, not null), `feedback` (text), `reviewed_at` (timestamptz, not null).
4. THE Schema SHALL contain a `final_syntheses` table with columns: `id` (UUID primary key), `session_id` (UUID, unique, foreign key to `research_sessions.id` with `ON DELETE CASCADE`), `final_recommendation` (text), `confidence_level` (text, one of `'High'`, `'Moderate'`, `'Low'`), `action_items` (jsonb), `caveats` (jsonb), `created_at` (timestamptz, default `now()`).
5. THE Schema SHALL define RLS policies on all four tables such that authenticated users may only SELECT, INSERT, and UPDATE rows where `user_id = auth.uid()` (for `research_sessions`) or where the parent `session_id` belongs to a `research_sessions` row owned by `auth.uid()` (for the three child tables).
6. THE Schema SHALL enable RLS on all four tables (`ALTER TABLE … ENABLE ROW LEVEL SECURITY`).
7. WHEN a `research_sessions` row is updated, THE Schema SHALL automatically set `updated_at` to `now()` via a Postgres trigger.

---

### Requirement 2: Python Backend — Supabase Write Integration

**User Story:** As a researcher, I want every pipeline run to be automatically saved to the database, so that I can review past results without re-running the pipeline.

#### Acceptance Criteria

1. THE Supabase_Python_Client SHALL be initialised once using the `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` environment variables read via `os.environ.get(...)`.
2. WHEN `run_research()` is called in `graph.py`, THE Backend SHALL create a `research_sessions` row with `status = 'running'` before the pipeline begins and return the session UUID to the caller.
3. WHEN an agent node completes successfully in `graph.py`, THE Backend SHALL upsert a row into `agent_outputs` containing the agent name, revision count, and the full agent output serialised as JSON.
4. WHEN a critic review node completes in `graph.py`, THE Backend SHALL insert a row into `critic_reviews` containing the agent name, revision number, pass/fail result, feedback text, and ISO timestamp.
5. WHEN `synthesize_node` completes in `graph.py`, THE Backend SHALL insert a row into `final_syntheses` and update the `research_sessions` row to `status = 'complete'`.
6. IF any pipeline stage raises an unhandled exception, THEN THE Backend SHALL update the `research_sessions` row to `status = 'error'` and store the error message in the `research_sessions.abstract` field is NOT acceptable — THE Backend SHALL add an `error` column (text, nullable) to `research_sessions` for this purpose.
7. THE Backend SHALL never expose the `SUPABASE_SERVICE_ROLE_KEY` in any log output, error message, or API response.
8. IF the Supabase write call fails, THEN THE Backend SHALL log the error and continue pipeline execution — a Supabase write failure SHALL NOT abort the research pipeline.
9. THE Supabase_Python_Client integration SHALL be isolated in a new module `research_lab/supabase_client.py` — no Supabase imports SHALL appear directly in `graph.py`, `app.py`, or any agent file.

---

### Requirement 3: Supabase Auth — Frontend Authentication

**User Story:** As a researcher, I want to sign in with my institutional email and password via Supabase Auth, so that my research sessions are private and tied to my account.

#### Acceptance Criteria

1. THE Supabase_Client SHALL be initialised once in a dedicated module (`labos-mockup/src/lib/supabase.js`) using `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` environment variables.
2. THE Middleware SHALL be implemented as a React context provider (`SupabaseProvider` in `labos-mockup/src/context/SupabaseContext.jsx`) that calls `supabase.auth.onAuthStateChange(...)` on mount and exposes `{ session, user, loading }` to all consumers.
3. WHEN the application loads, THE Middleware SHALL call `supabase.auth.getSession()` to restore any existing Auth_Session from local storage before rendering protected content.
4. THE SignIn page SHALL call `supabase.auth.signInWithPassword({ email, password })` on form submission and navigate to `/projects` on success.
5. WHEN `signInWithPassword` returns an error, THE SignIn page SHALL display the error message to the user without navigating away.
6. THE SignIn page SHALL include a password field in addition to the existing email field, replacing the current no-op form submission.
7. WHERE the SSO button is present, THE SignIn page SHALL call `supabase.auth.signInWithOAuth(...)` — the specific OAuth provider SHALL be left configurable via a constant so the user can set it themselves.
8. THE Auth_Guard SHALL be implemented as a `ProtectedRoute` component (`labos-mockup/src/components/Auth/ProtectedRoute.jsx`) that reads `{ session, loading }` from `SupabaseContext` and redirects to `/` if no session exists.
9. WHILE `loading` is true, THE Auth_Guard SHALL render a loading indicator rather than redirecting or rendering protected content.
10. THE Layout route in `App.jsx` SHALL be wrapped with `ProtectedRoute` so that `/projects`, `/projects/new`, and `/projects/:id` all require authentication.
11. WHEN the user clicks the logout button in the Sidebar, THE Sidebar SHALL call `supabase.auth.signOut()` and navigate to `/`.
12. THE Supabase_Client module SHALL NOT import or reference `SUPABASE_SERVICE_ROLE_KEY` — only the anon key is permitted in frontend code.

---

### Requirement 4: Frontend — Real-Time Data Fetching from Supabase

**User Story:** As a researcher, I want the frontend to display my actual research sessions and agent outputs from the database, so that I can review past work without re-running the pipeline.

#### Acceptance Criteria

1. THE ProjectList page SHALL fetch all `research_sessions` rows where `user_id = auth.uid()` from Supabase on mount, ordered by `created_at` descending, replacing the current hardcoded project array.
2. WHEN the ProjectList fetch is in progress, THE ProjectList page SHALL render a loading skeleton in place of the project cards.
3. IF the ProjectList fetch returns an error, THEN THE ProjectList page SHALL display an inline error message and a retry button.
4. THE ProjectDashboard page SHALL fetch the `research_sessions` row, all `agent_outputs` rows, all `critic_reviews` rows, and the `final_syntheses` row for the given session `id` from Supabase on mount, replacing all mock data.
5. WHEN the ProjectDashboard fetch is in progress, THE ProjectDashboard page SHALL render loading skeletons for each agent card.
6. IF the ProjectDashboard fetch returns a session with `status = 'running'`, THEN THE ProjectDashboard page SHALL poll Supabase every 5 seconds until the status changes to `'complete'` or `'error'`.
7. THE Sidebar SHALL fetch the 5 most recent `research_sessions` rows for the authenticated user from Supabase on mount, replacing the current hardcoded `recentProjects` array.
8. THE NewProject page SHALL insert a new `research_sessions` row into Supabase with `status = 'running'` on form submission and navigate to `/projects/:id` using the returned UUID.
9. ALL Supabase data-fetching calls in the frontend SHALL be made through a dedicated service layer (`labos-mockup/src/lib/api.js`) — no raw `supabase.from(...)` calls SHALL appear directly inside React component files.
10. THE Api service layer SHALL use the authenticated Supabase_Client so that all queries automatically include the user's JWT and are subject to RLS enforcement.

---

### Requirement 5: Security — Secrets Management and Access Control

**User Story:** As a security-conscious developer, I want all credentials and access patterns to follow least-privilege principles, so that user data cannot be accessed or leaked by unauthorised parties.

#### Acceptance Criteria

1. THE Backend SHALL read `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` exclusively from environment variables — these values SHALL NOT appear in any committed source file.
2. THE Frontend SHALL read `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` exclusively from environment variables — these values SHALL NOT appear in any committed source file.
3. THE `.env.example` file SHALL be updated to document all four new environment variable names with placeholder values and comments explaining their purpose and where to obtain them.
4. THE `SUPABASE_SERVICE_ROLE_KEY` SHALL only be used in `research_lab/supabase_client.py` and SHALL NOT be referenced in any frontend file, `app.py`, or any agent file.
5. THE RLS policies defined in Requirement 1 SHALL ensure that a frontend user authenticated as user A cannot read, update, or delete rows belonging to user B, even if user A constructs a direct Supabase API request.
6. IF a frontend data-fetch call returns a Supabase `401` or `403` error, THEN THE Frontend SHALL call `supabase.auth.signOut()` and redirect the user to the sign-in page.
7. THE Frontend SHALL store Auth_Session tokens only in the mechanism provided by `@supabase/supabase-js` (localStorage by default) — no custom token storage SHALL be implemented.
8. THE `labos-mockup/.env.example` file SHALL be committed to the repository; the actual `labos-mockup/.env` or `.env.local` file SHALL be listed in `.gitignore`.

---

### Requirement 6: Supabase Middleware — Session Lifecycle Management

**User Story:** As a researcher, I want my session to be automatically refreshed and my sign-out to be clean, so that I never encounter stale token errors during a long pipeline run.

#### Acceptance Criteria

1. THE Middleware SHALL call `supabase.auth.startAutoRefresh()` when a session is established and `supabase.auth.stopAutoRefresh()` when the session ends, ensuring tokens are refreshed before expiry.
2. WHEN the `onAuthStateChange` callback fires with event `'SIGNED_OUT'`, THE Middleware SHALL clear the local `session` and `user` state and the `ProtectedRoute` SHALL redirect to `/`.
3. WHEN the `onAuthStateChange` callback fires with event `'TOKEN_REFRESHED'`, THE Middleware SHALL update the stored session in context without triggering a full page reload.
4. THE Middleware SHALL unsubscribe from `onAuthStateChange` in the React `useEffect` cleanup function to prevent memory leaks.
5. WHILE a pipeline run is in progress (session `status = 'running'`), THE Frontend SHALL NOT sign the user out automatically — the polling loop SHALL continue until the session resolves.
