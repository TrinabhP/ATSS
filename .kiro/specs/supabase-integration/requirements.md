# Requirements Document — Supabase Integration for LabOS

## Introduction

LabOS is a multi-agent scientific research analysis platform with a React 19 frontend and a Python/FastAPI backend. Currently all state is in-memory — there is no database, no authentication, and no route protection. This feature integrates Supabase across the entire product to provide user authentication, project persistence, analysis results storage, Row Level Security, and proper middleware on both frontend and backend. Chat sessions remain ephemeral and are explicitly excluded from persistence.

## Glossary

- **LabOS_Frontend**: The React 19 + Vite single-page application located at `ATSS/labos-mockup/`, responsible for all user-facing UI including sign-in, project management, and analysis dashboards.
- **LabOS_Backend**: The Python FastAPI server located at `ATSS/research_lab/`, responsible for running the multi-agent research pipeline and serving API endpoints.
- **Supabase_Auth**: The Supabase Authentication service used to manage user registration, login, session tokens, and token refresh.
- **Supabase_DB**: The Supabase PostgreSQL database used to persist projects, analysis results, and user associations.
- **Supabase_Client_Frontend**: The `@supabase/supabase-js` JavaScript client initialized in the React frontend for authentication and database operations.
- **Supabase_Client_Backend**: The `supabase-py` Python client initialized in the FastAPI backend for server-side database writes using the service role key.
- **Auth_Context**: A React context provider that exposes the current authenticated user, session, and loading state to all components in the LabOS_Frontend.
- **Protected_Route**: A React route wrapper component that redirects unauthenticated users to the sign-in page.
- **RLS**: Row Level Security — PostgreSQL policies on Supabase_DB tables that restrict data access to rows owned by the authenticated user.
- **Project**: A research workspace created by a user, containing an abstract/thesis, a display name, and associated analysis results.
- **Analysis_Results**: The full output of the multi-agent research pipeline for a project, including literature, hypothesis, procedure, final recommendation, confidence level, action items, and caveats.
- **Chat_Session**: An ephemeral in-memory conversation session for PDF research chat — explicitly excluded from Supabase persistence.
- **JWT**: JSON Web Token issued by Supabase_Auth, passed in the Authorization header for authenticated API requests.
- **Service_Role_Key**: A privileged Supabase API key used only on the LabOS_Backend to bypass RLS for server-side writes.

---

## Requirements

### Requirement 1: Supabase Client Initialization (Frontend)

**User Story:** As a developer, I want the Supabase JavaScript client properly initialized in the frontend, so that all authentication and database calls use a single shared client instance.

#### Acceptance Criteria

1. THE Supabase_Client_Frontend SHALL be initialized as a singleton module using the `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` environment variables.
2. WHEN `VITE_SUPABASE_URL` or `VITE_SUPABASE_ANON_KEY` is missing, THE Supabase_Client_Frontend SHALL throw a descriptive error at module load time identifying the missing variable.
3. THE Supabase_Client_Frontend SHALL be importable from a single `src/lib/supabase.js` module by any component in the LabOS_Frontend.

---

### Requirement 2: Supabase Client Initialization (Backend)

**User Story:** As a developer, I want the Supabase Python client properly initialized on the backend, so that the FastAPI server can write analysis results to the database.

#### Acceptance Criteria

1. THE Supabase_Client_Backend SHALL be initialized as a lazy singleton using the `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` environment variables.
2. IF `SUPABASE_URL` or `SUPABASE_SERVICE_ROLE_KEY` is missing at initialization time, THEN THE Supabase_Client_Backend SHALL raise an `EnvironmentError` with a message identifying the missing variable.
3. THE Supabase_Client_Backend SHALL use the Service_Role_Key to bypass RLS for server-side writes.
4. THE Supabase_Client_Backend SHALL be importable from a single `research_lab/supabase_client.py` module.

---

### Requirement 3: User Authentication via Supabase Auth

**User Story:** As a researcher, I want to sign in with my email and password through Supabase Auth, so that my identity is verified and my projects are associated with my account.

#### Acceptance Criteria

1. WHEN a user submits the sign-in form with valid credentials, THE LabOS_Frontend SHALL authenticate the user against Supabase_Auth using email/password sign-in.
2. WHEN Supabase_Auth returns a valid session, THE LabOS_Frontend SHALL store the session (including JWT and refresh token) via the Supabase client's built-in session management and redirect the user to the projects page.
3. WHEN Supabase_Auth returns an authentication error, THE LabOS_Frontend SHALL display the error message on the sign-in page without navigating away.
4. THE LabOS_Frontend SHALL provide a sign-up flow that creates a new user account via Supabase_Auth using email and password.
5. WHEN a user clicks the sign-out button, THE LabOS_Frontend SHALL call `supabase.auth.signOut()`, clear the local session, and redirect to the sign-in page.

---

### Requirement 4: Auth Context and Session Management

**User Story:** As a developer, I want a centralized auth context that tracks the current user and session state, so that all components can access authentication status without prop drilling.

#### Acceptance Criteria

1. THE Auth_Context SHALL expose the current user object, session object, and a loading boolean to all child components.
2. WHEN the LabOS_Frontend loads, THE Auth_Context SHALL check for an existing Supabase session and restore it automatically.
3. WHEN the Supabase session token expires, THE Auth_Context SHALL use the refresh token to obtain a new session without requiring the user to re-authenticate.
4. THE Auth_Context SHALL subscribe to Supabase_Auth state changes (via `onAuthStateChange`) and update the exposed user and session values in response.

---

### Requirement 5: Protected Routes

**User Story:** As a researcher, I want all application routes except sign-in to require authentication, so that no one can access projects or analysis data without valid credentials.

#### Acceptance Criteria

1. WHEN an unauthenticated user navigates to any route other than the sign-in page, THE Protected_Route SHALL redirect the user to the sign-in page.
2. WHILE the Auth_Context is in a loading state (checking for an existing session), THE Protected_Route SHALL display a loading indicator instead of redirecting.
3. WHEN an authenticated user navigates to the sign-in page, THE LabOS_Frontend SHALL redirect the user to the projects page.

---

### Requirement 6: Supabase Database Schema — Projects Table

**User Story:** As a developer, I want a `projects` table in Supabase that stores each user's research projects, so that project data persists across sessions.

#### Acceptance Criteria

1. THE Supabase_DB SHALL contain a `projects` table with columns: `id` (UUID, primary key, default `gen_random_uuid()`), `user_id` (UUID, foreign key to `auth.users.id`, not null), `name` (text, not null), `abstract` (text, not null), `status` (text, not null, default `'running'`), `created_at` (timestamptz, default `now()`), and `updated_at` (timestamptz, default `now()`).
2. THE `projects` table SHALL have an RLS policy that allows authenticated users to SELECT, INSERT, UPDATE, and DELETE only rows where `user_id` matches `auth.uid()`.
3. THE `projects` table SHALL have RLS enabled with no public access — only authenticated users matching the `user_id` column can access their own rows.

---

### Requirement 7: Supabase Database Schema — Analysis Results Table

**User Story:** As a developer, I want an `analysis_results` table in Supabase that stores the full pipeline output for each project, so that users can revisit completed analyses.

#### Acceptance Criteria

1. THE Supabase_DB SHALL contain an `analysis_results` table with columns: `id` (UUID, primary key, default `gen_random_uuid()`), `project_id` (UUID, foreign key to `projects.id`, not null, unique), `user_id` (UUID, foreign key to `auth.users.id`, not null), `literature` (jsonb), `hypothesis` (jsonb), `procedure` (jsonb), `final_recommendation` (text), `confidence_level` (text), `action_items` (jsonb, default `'[]'`), `caveats` (jsonb, default `'[]'`), and `created_at` (timestamptz, default `now()`).
2. THE `analysis_results` table SHALL have an RLS policy that allows authenticated users to SELECT only rows where `user_id` matches `auth.uid()`.
3. THE `analysis_results` table SHALL have an RLS policy that allows INSERT and UPDATE only from the LabOS_Backend using the Service_Role_Key (bypassing RLS).
4. THE `analysis_results` table SHALL enforce a one-to-one relationship with the `projects` table via the unique constraint on `project_id`.

---

### Requirement 8: Project Creation and Persistence

**User Story:** As a researcher, I want new projects to be saved to Supabase immediately when I create them, so that my work is persisted from the start.

#### Acceptance Criteria

1. WHEN a user submits the new project form with an abstract, THE LabOS_Frontend SHALL insert a new row into the `projects` table with the authenticated user's `user_id`, a default name (e.g., "Untitled Project"), the abstract text, and status `'running'`.
2. WHEN the Supabase insert succeeds, THE LabOS_Frontend SHALL navigate to the project dashboard using the returned project `id`.
3. IF the Supabase insert fails, THEN THE LabOS_Frontend SHALL display an error message and remain on the new project page.

---

### Requirement 9: Project Listing from Supabase

**User Story:** As a researcher, I want the projects page to load my projects from Supabase, so that I can see all my past and current research workspaces.

#### Acceptance Criteria

1. WHEN the projects page loads, THE LabOS_Frontend SHALL query the `projects` table for all rows belonging to the authenticated user, ordered by `created_at` descending.
2. WHEN projects are returned, THE LabOS_Frontend SHALL display each project's name, status, and creation date in the project grid.
3. WHEN no projects exist for the user, THE LabOS_Frontend SHALL display the empty state with a "Create New Project" card.
4. WHILE the projects query is in progress, THE LabOS_Frontend SHALL display a loading indicator.

---

### Requirement 10: Project Rename

**User Story:** As a researcher, I want to rename my projects, so that I can give them meaningful names instead of the default.

#### Acceptance Criteria

1. WHEN a user triggers the rename action on a project, THE LabOS_Frontend SHALL display an inline editable field pre-filled with the current project name.
2. WHEN the user confirms the new name, THE LabOS_Frontend SHALL update the `name` column in the `projects` table for that project's row.
3. WHEN the Supabase update succeeds, THE LabOS_Frontend SHALL reflect the new name in the UI immediately.
4. IF the new name is empty or whitespace-only, THEN THE LabOS_Frontend SHALL reject the rename and retain the previous name.
5. IF the Supabase update fails, THEN THE LabOS_Frontend SHALL display an error message and revert the displayed name to the previous value.

---

### Requirement 11: Analysis Results Persistence from Backend

**User Story:** As a researcher, I want the backend to save my analysis results to Supabase after the pipeline completes, so that I can come back and reference them later.

#### Acceptance Criteria

1. WHEN the research pipeline completes successfully, THE LabOS_Backend SHALL insert or upsert a row in the `analysis_results` table with the project's `project_id`, `user_id`, and the full pipeline output (literature, hypothesis, procedure, final_recommendation, confidence_level, action_items, caveats).
2. WHEN the analysis results are persisted, THE LabOS_Backend SHALL update the corresponding `projects` row status to `'completed'`.
3. IF the Supabase write fails, THEN THE LabOS_Backend SHALL log the error and continue returning the pipeline results to the frontend without raising an exception.
4. THE LabOS_Backend SHALL accept a `project_id` and a `user_id` in the analyze API request payload so that results can be associated with the correct project and user.

---

### Requirement 12: Loading Persisted Analysis Results

**User Story:** As a researcher, I want to see my previously completed analysis results when I open a project, so that I do not need to re-run the pipeline.

#### Acceptance Criteria

1. WHEN a user navigates to a project dashboard, THE LabOS_Frontend SHALL query the `analysis_results` table for the row matching the project's `id`.
2. WHEN analysis results exist for the project, THE LabOS_Frontend SHALL render the full results (literature, hypothesis, procedure, final recommendation, confidence level, action items, caveats) without triggering the pipeline.
3. WHEN no analysis results exist for the project, THE LabOS_Frontend SHALL display the pipeline input form and allow the user to run the analysis.

---

### Requirement 13: Chat Data Exclusion from Persistence

**User Story:** As a developer, I want to ensure chat sessions are never persisted to Supabase, so that the chat feature remains ephemeral as designed.

#### Acceptance Criteria

1. THE LabOS_Backend chat module (`research_lab/chat/`) SHALL continue to use in-memory storage only for all chat session data.
2. THE LabOS_Backend SHALL NOT write any chat session data, conversation history, or PDF text to Supabase_DB.
3. THE LabOS_Frontend SHALL NOT make any Supabase_DB calls related to chat session data.

---

### Requirement 14: Backend Authentication Middleware

**User Story:** As a developer, I want the FastAPI backend to verify Supabase JWTs on protected endpoints, so that only authenticated users can trigger analysis pipelines and access results.

#### Acceptance Criteria

1. WHEN a request is made to any `/api/analyze` endpoint, THE LabOS_Backend SHALL extract the JWT from the `Authorization: Bearer <token>` header.
2. WHEN the JWT is valid, THE LabOS_Backend SHALL extract the `user_id` from the token claims and make it available to the route handler.
3. IF the JWT is missing or invalid, THEN THE LabOS_Backend SHALL return a 401 Unauthorized response with a descriptive error message.
4. THE LabOS_Backend SHALL NOT require authentication for the `/health` endpoint.
5. THE LabOS_Backend SHALL NOT require authentication for the `/api/chat/*` endpoints (chat remains stateless and ephemeral).

---

### Requirement 15: Frontend Authenticated API Requests

**User Story:** As a developer, I want the frontend to automatically include the Supabase JWT in all API requests to the backend, so that the backend can verify the user's identity.

#### Acceptance Criteria

1. WHEN the LabOS_Frontend makes any request to the `/api/analyze` or `/api/analyze/stream` endpoints, THE LabOS_Frontend SHALL include the current Supabase session's access token in the `Authorization: Bearer <token>` header.
2. WHEN the LabOS_Frontend makes a request to the `/api/analyze` endpoints and receives a 401 response, THE LabOS_Frontend SHALL redirect the user to the sign-in page.
3. THE LabOS_Frontend SHALL pass the `project_id` and `user_id` in the request body when calling the analyze endpoints so the backend can associate results with the correct project.

---

### Requirement 16: Row Level Security Enforcement

**User Story:** As a developer, I want Row Level Security enabled on all Supabase tables, so that users cannot access or modify other users' data even if they bypass the frontend.

#### Acceptance Criteria

1. THE Supabase_DB SHALL have RLS enabled on the `projects` table with policies restricting all operations (SELECT, INSERT, UPDATE, DELETE) to rows where `user_id = auth.uid()`.
2. THE Supabase_DB SHALL have RLS enabled on the `analysis_results` table with a SELECT policy restricting reads to rows where `user_id = auth.uid()`.
3. THE Supabase_DB SHALL allow the Service_Role_Key to bypass RLS on the `analysis_results` table for backend writes.
4. THE Supabase_DB SHALL NOT have any policies that grant public or anonymous access to the `projects` or `analysis_results` tables.

---

### Requirement 17: Environment Variable Configuration

**User Story:** As a developer, I want all Supabase credentials managed through environment variables, so that secrets are not hardcoded in the codebase.

#### Acceptance Criteria

1. THE LabOS_Frontend SHALL read `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` from Vite environment variables (`.env` file or process environment).
2. THE LabOS_Backend SHALL read `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` from environment variables (`.env` file or process environment).
3. THE `.env.example` file SHALL document all required Supabase environment variables with placeholder values.
4. THE `.gitignore` file SHALL include `.env` to prevent committing secrets to version control.

---

### Requirement 18: Project Status Tracking

**User Story:** As a researcher, I want to see whether each project's analysis is running, completed, or errored, so that I know which projects have results ready.

#### Acceptance Criteria

1. THE `projects` table `status` column SHALL support the values `'running'`, `'completed'`, and `'error'`.
2. WHEN the analysis pipeline completes successfully, THE LabOS_Backend SHALL update the project's status to `'completed'`.
3. IF the analysis pipeline fails, THEN THE LabOS_Backend SHALL update the project's status to `'error'`.
4. WHEN the projects list is displayed, THE LabOS_Frontend SHALL show a status badge for each project reflecting the current status value.
