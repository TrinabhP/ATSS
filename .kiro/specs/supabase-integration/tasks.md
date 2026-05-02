# Implementation Plan: Supabase Integration

## Overview

Integrate Supabase as the persistent data layer and authentication provider for LabOS. The work is split into five sequential phases: schema creation, Python backend write integration, frontend library setup, frontend auth, and frontend data fetching. Each phase builds on the previous one. All Python code remains synchronous. The service role key stays in the Python backend only; the anon key stays in the frontend only.

## Tasks

- [x] 1. Create Supabase database schema
  - Use the Supabase MCP server to execute the SQL DDL from the design document
  - Create `research_sessions` table with `id`, `user_id`, `abstract`, `status`, `error`, `created_at`, `updated_at` columns
  - Create `agent_outputs` table with `id`, `session_id`, `agent_name`, `revision_count`, `output_json`, `created_at` columns and `UNIQUE (session_id, agent_name)` constraint
  - Create `critic_reviews` table with `id`, `session_id`, `agent_name`, `revision_number`, `passed`, `feedback`, `reviewed_at` columns
  - Create `final_syntheses` table with `id`, `session_id` (unique FK), `final_recommendation`, `confidence_level`, `action_items`, `caveats`, `created_at` columns
  - Create the `set_updated_at()` trigger function and attach it to `research_sessions`
  - Enable RLS on all four tables
  - Create all RLS policies: owner-only SELECT/INSERT/UPDATE on `research_sessions`; child-table policies that check `session_id IN (SELECT id FROM research_sessions WHERE user_id = auth.uid())`
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

- [ ] 2. Python backend — Supabase client module
  - [x] 2.1 Add `supabase==2.15.0` to `research_lab/requirements.txt`
    - Append the pinned dependency to the existing file
    - _Requirements: 2.1_

  - [x] 2.2 Create `research_lab/supabase_client.py`
    - Implement lazy singleton `get_client()` that reads `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` from `os.environ.get(...)` and raises `EnvironmentError` if either is missing
    - Implement `create_session(abstract: str) -> str` — INSERT into `research_sessions` with `status='running'`, return the UUID string
    - Implement `upsert_agent_output(session_id: str, agent_name: str, revision_count: int, output: dict) -> None` — UPSERT into `agent_outputs` using `on_conflict='session_id,agent_name'`; wrap in `try/except`, log error, never raise
    - Implement `insert_critic_review(session_id: str, review: CriticReview) -> None` — INSERT into `critic_reviews`; wrap in `try/except`, log error, never raise
    - Implement `insert_final_synthesis(session_id: str, final_recommendation: str, confidence_level: str, action_items: list, caveats: list) -> None` — INSERT into `final_syntheses` then UPDATE `research_sessions` SET `status='complete'`; wrap in `try/except`, log error, never raise
    - Implement `mark_session_error(session_id: str, error_message: str) -> None` — UPDATE `research_sessions` SET `status='error'`, `error=error_message`; wrap in `try/except`, log error, never raise
    - Use Python `logging` module throughout; log messages must never include the key value
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9_

  - [ ] 2.3 Write unit tests for `supabase_client.py`
    - Create `research_lab/tests/test_supabase_client.py`
    - `test_create_session_returns_uuid` — mock supabase client, verify UUID string returned
    - `test_upsert_agent_output_swallows_error` — mock client to raise, verify no exception propagates
    - `test_insert_critic_review_swallows_error` — same pattern
    - `test_mark_session_error_swallows_error` — same pattern
    - `test_get_client_raises_on_missing_env` — unset env vars, verify `EnvironmentError`
    - `test_log_output_excludes_key` — verify key value not in any log record
    - _Requirements: 2.7, 2.8, 2.9_

  - [ ] 2.4 Write property test: agent output round-trip (Property 3)
    - **Property 3: Agent output write round-trip**
    - **Validates: Requirements 2.3**
    - Create `research_lab/tests/test_supabase_properties.py` using Hypothesis
    - Generate random `agent_name` from `{'literature', 'hypothesis', 'procedure'}`, random `revision_count` (0–10), and random JSON-serialisable dict
    - Mock the supabase client; call `upsert_agent_output`; verify the data passed to the mock matches the input
    - Tag: `# Feature: supabase-integration, Property 3: agent output round-trip`

  - [ ] 2.5 Write property test: critic review round-trip (Property 4)
    - **Property 4: Critic review write round-trip**
    - **Validates: Requirements 2.4**
    - Add to `research_lab/tests/test_supabase_properties.py`
    - Generate random `CriticReview` dicts with varied `passed`, `feedback`, `agent_name`, `revision_number`
    - Mock the supabase client; call `insert_critic_review`; verify fields passed to mock match input
    - Tag: `# Feature: supabase-integration, Property 4: critic review round-trip`

  - [ ] 2.6 Write property test: write failure does not abort pipeline (Property 5)
    - **Property 5: Supabase write failure does not abort pipeline**
    - **Validates: Requirements 2.8**
    - Add to `research_lab/tests/test_supabase_properties.py`
    - Generate random exception types from `{ConnectionError, TimeoutError, ValueError}`; inject at random pipeline stages via mock
    - Verify `run_research()` returns a `ResearchState` dict and does not raise
    - Tag: `# Feature: supabase-integration, Property 5: write failure does not abort pipeline`

  - [ ] 2.7 Write property test: service role key never in logs (Property 6)
    - **Property 6: Service role key never appears in log output**
    - **Validates: Requirements 2.7, 5.4**
    - Add to `research_lab/tests/test_supabase_properties.py`
    - Generate random abstract strings; run pipeline with mocked Supabase; collect all log records
    - Verify the `SUPABASE_SERVICE_ROLE_KEY` value is absent from every log message
    - Tag: `# Feature: supabase-integration, Property 6: key never in logs`

- [ ] 3. Python backend — wire `supabase_client` into `graph.py` and `state.py`
  - [ ] 3.1 Add `session_id` field to `ResearchState` in `state.py`
    - Add `session_id: Optional[str]` to the `ResearchState` TypedDict (import `Optional` from `typing` if not already present)
    - Update the `if __name__ == "__main__":` block to include `"session_id": None` in the test state dict
    - _Requirements: 2.2_

  - [ ] 3.2 Integrate `supabase_client` calls into `graph.py`
    - Import `supabase_client` at the top of `graph.py` (the only import of supabase in the Python codebase)
    - In `run_research()`: call `supabase_client.create_session(abstract)` before `compiled.invoke(initial)`; store the returned UUID in `initial["session_id"]`; wrap in `try/except` so a failure sets `session_id = None` and logs but does not abort
    - In `dispatch_literature`, `dispatch_hypothesis`, `dispatch_procedure`: after a successful agent result, call `supabase_client.upsert_agent_output(state["session_id"], agent_name, new_count, result)` — guard with `if state.get("session_id")`
    - In `review_literature_node`, `review_hypothesis_node`, `review_procedure_node`: after appending the review to state, call `supabase_client.insert_critic_review(state["session_id"], review)` — guard with `if state.get("session_id")`
    - In `synthesize_node`: after a successful synthesis, call `supabase_client.insert_final_synthesis(state["session_id"], rec, conf, actions, caveats)` — guard with `if state.get("session_id")`
    - In each node's `except` block: call `supabase_client.mark_session_error(state.get("session_id"), str(e))` — guard with `if state.get("session_id")`
    - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6_

- [ ] 4. Checkpoint — verify Python integration
  - Ensure all Python unit tests pass, ask the user if questions arise.

- [ ] 5. Frontend — library setup and environment
  - [ ] 5.1 Install `@supabase/supabase-js@2.49.4` in `labos-mockup/`
    - Add `"@supabase/supabase-js": "2.49.4"` to the `dependencies` section of `labos-mockup/package.json`
    - _Requirements: 3.1_

  - [ ] 5.2 Create `labos-mockup/src/lib/supabase.js`
    - Import `createClient` from `@supabase/supabase-js`
    - Read `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` from `import.meta.env`
    - Export a single named constant `supabase = createClient(supabaseUrl, supabaseAnonKey)`
    - No other logic; no reference to `SERVICE_ROLE_KEY`
    - _Requirements: 3.1, 5.2_

  - [ ] 5.3 Create `labos-mockup/src/lib/api.js`
    - Import `supabase` from `./supabase`
    - Implement `fetchSessions()` — SELECT all `research_sessions` ordered by `created_at` descending; return `{ data, error }`
    - Implement `fetchRecentSessions(n)` — SELECT top `n` `research_sessions` ordered by `created_at` descending; return `{ data, error }`
    - Implement `createSession(abstract)` — INSERT into `research_sessions` with `status='running'`; return `{ data, error }`
    - Implement `fetchSessionById(id)` — SELECT single `research_sessions` row by `id`; return `{ data, error }`
    - Implement `fetchAgentOutputs(sessionId)` — SELECT all `agent_outputs` for `session_id`; return `{ data, error }`
    - Implement `fetchCriticReviews(sessionId)` — SELECT all `critic_reviews` for `session_id`; return `{ data, error }`
    - Implement `fetchFinalSynthesis(sessionId)` — SELECT single `final_syntheses` row for `session_id`; return `{ data, error }`
    - All functions are `async`; no raw `supabase.from(...)` calls may appear in any component file
    - _Requirements: 4.1, 4.4, 4.7, 4.8, 4.9, 4.10_

  - [ ] 5.4 Update `.env.example` files
    - Update root `.env.example`: add `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` with placeholder values and comments explaining their purpose and where to obtain them
    - Create `labos-mockup/.env.example`: add `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` with placeholder values and comments
    - Verify `labos-mockup/.env` and `labos-mockup/.env.local` are listed in `labos-mockup/.gitignore`
    - _Requirements: 5.1, 5.2, 5.3, 5.8_

- [ ] 6. Frontend — Supabase auth context and protected route
  - [ ] 6.1 Create `labos-mockup/src/context/SupabaseContext.jsx`
    - Create `SupabaseContext` with `createContext(null)`
    - Implement `SupabaseProvider` component: on mount call `supabase.auth.getSession()` to set initial `session`, `user`, and `loading=false`; subscribe to `supabase.auth.onAuthStateChange` and handle `SIGNED_IN`/`TOKEN_REFRESHED` (update session + user, call `startAutoRefresh()`) and `SIGNED_OUT` (clear session + user, call `stopAutoRefresh()`); unsubscribe in `useEffect` cleanup
    - Export `useSupabase()` hook that reads from context and throws if used outside the provider
    - Context value shape: `{ session, user, loading }`
    - _Requirements: 3.2, 3.3, 6.1, 6.2, 6.3, 6.4_

  - [ ] 6.2 Create `labos-mockup/src/components/Auth/ProtectedRoute.jsx`
    - Import `useSupabase` from `SupabaseContext`
    - If `loading` is true, render a loading spinner
    - If `session` is null and `loading` is false, render `<Navigate to="/" replace />`
    - Otherwise render `children`
    - _Requirements: 3.8, 3.9_

  - [ ] 6.3 Write property test: ProtectedRoute redirects unauthenticated requests (Property 7)
    - **Property 7: ProtectedRoute redirects all unauthenticated requests**
    - **Validates: Requirements 3.8**
    - Create `labos-mockup/src/tests/properties/protectedRoute.property.test.jsx` using fast-check
    - Generate random route path strings; render `ProtectedRoute` with `session=null` and `loading=false`; verify the rendered output is a redirect to `'/'` for all generated paths
    - Tag: `# Feature: supabase-integration, Property 7: ProtectedRoute redirects unauthenticated`

  - [ ] 6.4 Update `App.jsx` to add `SupabaseProvider` and `ProtectedRoute`
    - Import `SupabaseProvider` from `./context/SupabaseContext`
    - Import `ProtectedRoute` from `./components/Auth/ProtectedRoute`
    - Wrap the entire `<Router>` tree in `<SupabaseProvider>`
    - Wrap the `<Layout />` route element in `<ProtectedRoute>` so all child routes (`/projects`, `/projects/new`, `/projects/:id`) require authentication
    - _Requirements: 3.10_

- [ ] 7. Frontend — update SignIn page
  - Modify `labos-mockup/src/pages/SignIn.jsx`
  - Add a `password` state variable and a password `<input type="password">` field below the email field
  - Replace the `handleSignIn` function body: call `supabase.auth.signInWithPassword({ email, password })`; on success navigate to `/projects`; on error call `setError(error.message)` and display the message inline below the form
  - Add an `OAUTH_PROVIDER` constant (e.g., `'google'`) at the top of the file; wire the SSO button to call `supabase.auth.signInWithOAuth({ provider: OAUTH_PROVIDER })`
  - Import `supabase` from `../lib/supabase` (not from api.js — auth calls go directly to the supabase client)
  - _Requirements: 3.4, 3.5, 3.6, 3.7_

- [ ] 8. Frontend — update Sidebar
  - Modify `labos-mockup/src/components/Layout/Sidebar.jsx`
  - Import `useSupabase` from `../../context/SupabaseContext`
  - Import `fetchRecentSessions` from `../../lib/api`
  - Replace the hardcoded `recentProjects` array with a `useState([])` + `useEffect` that calls `api.fetchRecentSessions(5)` on mount and sets the result into state
  - Wire the `<LogOut>` button's `onClick` to call `supabase.auth.signOut()` then `navigate('/')`
  - _Requirements: 3.11, 4.7_

- [ ] 8.1 Write unit tests for `SupabaseContext` and `ProtectedRoute`
  - Create `labos-mockup/src/tests/SupabaseContext.test.jsx`
  - Verify `getSession()` is called on mount
  - Verify `SIGNED_OUT` event clears `session` and `user`
  - Verify `TOKEN_REFRESHED` event updates session without page reload
  - Verify `onAuthStateChange` subscription is unsubscribed on unmount
  - Create `labos-mockup/src/tests/ProtectedRoute.test.jsx`
  - Render with `session=null` and `loading=false` — verify redirect to `/`
  - Render with a valid session — verify children are rendered
  - Render with `loading=true` — verify loading indicator is shown, not a redirect
  - _Requirements: 3.2, 3.3, 3.8, 3.9_

- [ ] 9. Frontend — update ProjectList page
  - Modify `labos-mockup/src/pages/ProjectList.jsx`
  - Replace the hardcoded `projects` array with `useState(null)` for data, `useState(false)` for loading, and `useState(null)` for error
  - Add a `useEffect` that calls `api.fetchSessions()` on mount; set loading true before the call, false after; on error set the error state
  - While loading, render a skeleton placeholder in place of the project cards (e.g., three grey placeholder divs with the same card dimensions)
  - If error is set, render an inline error message and a "Retry" button that re-triggers the fetch
  - If a fetch returns a 401 or 403 error, call `supabase.auth.signOut()` and navigate to `/`
  - Map over the fetched `research_sessions` rows to render project cards (use `session.id`, `session.abstract` truncated as title, `session.status`, `session.created_at`)
  - _Requirements: 4.1, 4.2, 4.3, 5.6_

- [ ] 10. Frontend — update NewProject page
  - Modify `labos-mockup/src/pages/NewProject.jsx`
  - Replace the `setTimeout` + random ID logic in `handleSubmit` with a call to `api.createSession(abstract)`
  - On success, navigate to `/projects/${data[0].id}` using the UUID returned from Supabase
  - On error, set an error state and display the message inline; do not navigate
  - _Requirements: 4.8_

- [ ] 11. Frontend — update ProjectDashboard page
  - Modify `labos-mockup/src/pages/ProjectDashboard.jsx`
  - Remove all mock data arrays (`mockLitDocs`, `mockHypotheses`) and the `useEffect` timer simulation
  - Add state variables: `session`, `agentOutputs`, `criticReviews`, `finalSynthesis`, `loading`, `error`
  - Add a `useEffect` on mount that calls `api.fetchSessionById(id)`, `api.fetchAgentOutputs(id)`, `api.fetchCriticReviews(id)`, and `api.fetchFinalSynthesis(id)` in parallel using `Promise.all`
  - While loading, render loading skeletons for each agent card
  - If the fetched session has `status === 'running'`, start a polling interval (`setInterval` at 5000ms) that re-fetches `fetchSessionById(id)` until status changes to `'complete'` or `'error'`; clear the interval in the `useEffect` cleanup
  - If the session has `status === 'error'`, render an error state card showing `session.error`
  - Replace mock data references in the render with real data from state (agent outputs keyed by `agent_name`, critic reviews filtered by `agent_name`, final synthesis fields)
  - If any fetch returns a 401 or 403 error, call `supabase.auth.signOut()` and navigate to `/`
  - _Requirements: 4.4, 4.5, 4.6, 5.6_

  - [ ] 11.1 Write property test: polling does not sign out during running session (Property 9)
    - **Property 9: Polling continues while session is running**
    - **Validates: Requirements 4.6, 6.5**
    - Create `labos-mockup/src/tests/properties/polling.property.test.jsx` using fast-check
    - Generate random numbers of polling cycles (1–20); mock `fetchSessionById` to always return `status='running'`; verify `supabase.auth.signOut()` is never called regardless of cycle count
    - Tag: `# Feature: supabase-integration, Property 9: polling does not sign out`

  - [ ] 11.2 Write property test: 401/403 responses trigger sign-out (Property 8)
    - **Property 8: 401/403 responses trigger sign-out**
    - **Validates: Requirements 5.6**
    - Create `labos-mockup/src/tests/properties/api.property.test.js` using fast-check
    - Generate random API function names from the `api.js` exports; mock Supabase to return a 401 or 403 error; verify `supabase.auth.signOut()` is called for all functions
    - Tag: `# Feature: supabase-integration, Property 8: 401/403 triggers sign-out`

- [ ] 12. Final checkpoint — ensure all tests pass
  - Ensure all Python unit and property tests pass (`python -m pytest research_lab/tests/`)
  - Ensure the React app builds without errors (`npm run build` in `labos-mockup/`)
  - Ensure ESLint passes (`npm run lint` in `labos-mockup/`)
  - Ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- The Supabase MCP server is available for Task 1 (schema creation) — use it to execute the SQL DDL directly
- Python must remain fully synchronous — no `async/await` anywhere in `research_lab/`
- `supabase_client.py` is the only file in the Python codebase that imports `supabase`
- No raw `supabase.from(...)` calls in React component files — all data access goes through `api.js`
- Auth calls (`signInWithPassword`, `signOut`, `signInWithOAuth`) go directly to the `supabase` client, not through `api.js`
- Service role key: backend only. Anon key: frontend only.
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties; unit tests validate specific examples and edge cases
