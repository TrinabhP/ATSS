# LabOS — Research Analysis Engine

A hierarchical multi-agent research analysis system built for KiroHacks Cal Poly (May 2, 2026). A researcher submits a scientific abstract and a sequential pipeline of three specialized AI agents produces a structured final recommendation.

Two pipelines are available depending on your setup.

---

## How It Works

### Pipeline A — LangGraph + Claude (primary)

```
Abstract Input
    ↓
[Agent 1 — Literature Review]
  Sub-Agent 1A: Paper discovery (5–10 papers via web search)
  Sub-Agent 1B: Analysis & synthesis
    ↓
[Agent 2 — Hypothesis Design]
  Generates a testable hypothesis with an internal self-review loop
    ↓
[Agent 3 — Procedure Design]
  Designs population, methods, statistics, and timeline
    ↓
[Orchestrator / Critic]
  Reviews each agent — up to 2 revision cycles per agent
    ↓
[Final Synthesis]
  Confidence level (High / Moderate / Low) + action items + caveats
    ↓
[Peer Review]
  Reproducibility score, strengths, issues, replication checklist
```

### Pipeline B — PubMed + Ragie RAG (alternative)

An alternative pipeline that uses PubMed (via Biopython/Entrez) for literature search and Ragie.ai for RAG indexing. Uses Groq (`llama-3.3-70b-versatile`) for term extraction and results extraction.

```
Abstract Input
    ↓
[Agent 1: PubMed Finder]       — Groq term extraction + Entrez API → papers + PMIDs
    ↓
[Agent 2: Ragie RAG Builder]   — PMC full-text fetch + Ragie.ai upload (threaded, 1 worker)
    + Results Extractor        — Groq extraction → structured findings (1 worker)
```

Entry point: `run_pipeline.py`

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI | Anthropic Claude (`claude-sonnet-4-20250514`) |
| Orchestration | LangGraph `StateGraph` (synchronous) |
| Frontend (production) | Streamlit |
| Frontend (mockup) | React 19 + Vite + React Router DOM v7 |
| Persistence | Supabase (Postgres + Auth + RLS) |
| Language | Python 3.11+ |

---

## Project Structure

```
/
├── research_lab/              # Production Python backend
│   ├── app.py                 # Streamlit dashboard (UI only)
│   ├── server.py              # FastAPI HTTP server — POST /api/analyze
│   ├── graph.py               # LangGraph wiring — nodes, edges, run_research()
│   ├── state.py               # Shared TypedDict schema (ResearchState)
│   ├── supabase_client.py     # Supabase write integration (service role key)
│   ├── literature.py          # PubMed literature finder (Pipeline B, Agent 1)
│   ├── rag.py                 # Ragie RAG builder + results extractor (Pipeline B, Agent 2)
│   ├── requirements.txt       # Pinned Python dependencies
│   └── agents/
│       ├── literature.py      # Agent 1 — paper discovery + synthesis
│       ├── hypothesis.py      # Agent 2 — hypothesis design
│       ├── procedure.py       # Agent 3 — study procedure design
│       ├── orchestrator.py    # Critic review + final synthesis
│       └── peer_reviewer.py   # Agent 4 — independent reproducibility review
│
├── labos-mockup/              # React/Vite UI prototype
│   ├── src/
│   │   ├── App.jsx
│   │   ├── lib/
│   │   │   ├── supabase.js    # Supabase client (anon key)
│   │   │   └── api.js         # All Supabase data-fetching functions
│   │   ├── context/
│   │   │   └── SupabaseContext.jsx  # Auth session provider
│   │   ├── components/
│   │   │   └── Auth/
│   │   │       └── ProtectedRoute.jsx
│   │   └── pages/
│   │       ├── SignIn.jsx
│   │       ├── ProjectList.jsx
│   │       ├── ProjectDashboard.jsx
│   │       ├── NewProject.jsx
│   │       └── AnalysisView.jsx
│   └── package.json
│
├── main.py                    # Standalone LangGraph prototype (Tavily search)
├── run_pipeline.py            # Pipeline B runner (PubMed → Ragie)
├── requirements_ragie.txt     # Dependencies for Pipeline B
├── .env.example               # Environment variable template (root)
└── .kiro/specs/               # Feature specs (requirements, design, tasks)
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- An [Anthropic API key](https://console.anthropic.com/settings/keys)
- A [Supabase project](https://supabase.com) (for persistence and auth)

### 1. Clone and configure environment

```bash
cp .env.example .env
# Fill in ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
```

### 2. Run the Streamlit dashboard (Pipeline A)

```bash
pip install -r research_lab/requirements.txt
streamlit run research_lab/app.py
```

### 3. Run Pipeline B (PubMed + Ragie)

```bash
pip install -r requirements_ragie.txt
# Fill in GROQ_API_KEY, RAGIE_API_KEY, ENTREZ_EMAIL in research_lab/.env
python run_pipeline.py
```

### 4. Run the React mockup

```bash
cd labos-mockup
cp .env.example .env.local
# Fill in VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY
npm install
npm run dev
```

---

## Streamlit Dashboard

The production UI (`research_lab/app.py`) provides:

- **Abstract input** with character validation (20–4,000 chars)
- **6-stage pipeline status bar** — Literature Review → Hypothesis Design → Procedure Design → Synthesis → Peer Review → Complete
- **Tabbed results view** — Literature, Hypothesis, Procedure, Peer Review, Log
- **Confidence badge** — High / Moderate / Low with colour coding
- **Critic review history** — pass/fail per revision with expandable feedback
- **Dark theme** — IBM Plex fonts, `#0a0e1a` background

### Demo Abstract

```
We're investigating menin inhibitors for NPM1-mutant AML.
Key question: Does HOX gene expression predict treatment response to
menin inhibitors in NPM1-mutant acute myeloid leukemia patients?
```

---

## Environment Variables

| Variable | Used by | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | All agents (Pipeline A) | Claude API access |
| `GROQ_API_KEY` | Pipeline B | Groq API access (term extraction + results extraction) |
| `RAGIE_API_KEY` | Pipeline B (`rag.py`) | Ragie.ai RAG indexing |
| `ENTREZ_EMAIL` | Pipeline B (`literature.py`) | PubMed/Entrez identification |
| `SUPABASE_URL` | `supabase_client.py` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | `supabase_client.py` | Bypasses RLS — backend only, never expose in frontend |
| `VITE_SUPABASE_URL` | `labos-mockup/` | Supabase project URL (Vite env) |
| `VITE_SUPABASE_ANON_KEY` | `labos-mockup/` | Public anon key — safe for browser, RLS enforced |

---

## Running the Pipeline (CLI)

`graph.py` doubles as a CLI entry point:

```bash
# Run with the built-in demo abstract
python research_lab/graph.py

# Run with a custom abstract
python research_lab/graph.py "Your research abstract text here"
```

---

## HTTP API Server

`research_lab/server.py` exposes the pipeline as a FastAPI HTTP server:

```bash
pip install fastapi uvicorn
python3 research_lab/server.py
# Server starts on http://localhost:8000 by default
# Set PORT env var to override: PORT=9000 python3 research_lab/server.py
```

### Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Returns `{"status": "ok"}` — liveness check |
| `POST` | `/api/analyze` | Runs the full pipeline; returns `ResearchState` as JSON |

**Request body:**
```json
{ "abstract": "Your research abstract (20–4000 characters)" }
```

CORS is configured for `localhost:5173`, `localhost:5174`, and `localhost:3000`.

---

## Running Tests

```bash
# Python unit tests
python -m pytest research_lab/tests/

# React build check
cd labos-mockup && npm run build

# ESLint
cd labos-mockup && npm run lint
```

---

## Key Constants

| Constant | Value | File |
|---|---|---|
| `MODEL` | `claude-sonnet-4-20250514` | each agent file |
| `MAX_REVISIONS` | `2` | `graph.py` |
| `MAX_ABSTRACT_LENGTH` | `4,000` | `app.py` |
| `MIN_ABSTRACT_LENGTH` | `20` | `app.py` |
| `MAX_PAPERS` | `10` | `agents/literature.py` |
| `MIN_PAPERS` | `5` | `agents/literature.py` |

---

## Architecture Notes

- **All Python code is synchronous** — no `async/await`, no event loops
- **`supabase_client.py` is the only file** that imports `supabase` in the Python codebase
- **Service role key stays in the backend** — never referenced in any frontend file
- **Supabase write failures do not abort the pipeline** — errors are logged and execution continues
- **All frontend Supabase queries go through `api.js`** — no raw `supabase.from()` calls in component files
- **RLS enforces user isolation** — users can only read and write their own research sessions
