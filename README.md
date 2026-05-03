# SynThesis — Multi-Agent Research Analysis Engine

A hierarchical multi-agent research analysis system built for **KiroHacks Cal Poly** (May 2, 2026). A researcher submits a scientific abstract and a sequential pipeline of three specialized AI agents produces a structured final research plan — complete with literature review, hypothesis, study protocol, and confidence assessment.

**Track:** Intellectual Pursuit

**Live:** [https://labos-research-engine.onrender.com](https://labos-research-engine.onrender.com)

### Test Login

Use these credentials to try the app:

| Field | Value |
|---|---|
| Email | `test@gmail.com` |
| Password | `test123` |

---

## How It Works

```
Abstract Input (20–4,000 characters)
    ↓
┌─────────────────────────────────────────┐
│  Agent 1 — Literature Review            │
│  PubMed search + Ragie RAG indexing     │
│  → 5–10 papers extracted & synthesized  │
└──────────────────┬──────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│  Agent 2 — Hypothesis Design            │
│  Generates testable H₁ and H₀          │
│  with internal self-review loop         │
└──────────────────┬──────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│  Agent 3 — Procedure Design             │
│  Population, methods, statistics,       │
│  data collection, and timeline          │
└──────────────────┬──────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│  Orchestrator / Critic                  │
│  Reviews each agent's output            │
│  Up to 2 revision cycles per agent      │
└──────────────────┬──────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│  Final Synthesis                        │
│  Executive summary + hypothesis +       │
│  step-by-step plan + literature         │
│  citations + confidence level +         │
│  action items + caveats                 │
└─────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM (Agents) | Groq (`llama-3.3-70b-versatile`) |
| Orchestration | LangGraph `StateGraph` (synchronous) |
| Frontend | React 19 + Vite 8 + React Router DOM v7 |
| Backend | FastAPI + Uvicorn |
| Literature Search | PubMed via Biopython/Entrez |
| RAG | Ragie.ai (cloud-hosted) |
| Persistence | Supabase (Postgres + Auth + RLS) |
| PDF Export | fpdf2 (server-side) + LaTeX export |
| Chat | Groq-powered document Q&A with PDF upload |
| Deployment | Render (single web service) |
| Language | Python 3.11+ / JavaScript (ES2022) |

---

## Project Structure

```
/
├── research_lab/              # Python backend
│   ├── server.py              # FastAPI HTTP server + SPA serving
│   ├── graph.py               # LangGraph wiring — nodes, edges, run_research()
│   ├── state.py               # Shared TypedDict schema (ResearchState)
│   ├── literature.py          # Agent 1 — PubMed paper discovery + Ragie RAG
│   ├── rag.py                 # Ragie RAG builder + results extractor
│   ├── auth.py                # Supabase JWT auth (optional — anonymous access allowed)
│   ├── supabase_client.py     # Supabase write integration (service role key)
│   ├── agents/
│   │   ├── hypothesis.py      # Agent 2 — hypothesis design
│   │   ├── procedure.py       # Agent 3 — study procedure design
│   │   └── orchestrator.py    # Critic review + final synthesis
│   ├── chat/
│   │   ├── router.py          # FastAPI chat endpoints
│   │   ├── chat_service.py    # In-memory session management
│   │   ├── llm_client.py      # Groq API wrapper for chat
│   │   ├── pdf_extractor.py   # PDF text extraction
│   │   ├── pdf_generator.py   # Server-side PDF generation (fpdf2)
│   │   └── models.py          # Pydantic models for chat
│   └── tests/
│
├── labos-mockup/              # React frontend
│   ├── src/
│   │   ├── App.jsx            # Router setup
│   │   ├── App.css            # Component styles
│   │   ├── index.css          # CSS variables, theme, utilities
│   │   ├── pages/
│   │   │   ├── SignIn.jsx           # Auth page
│   │   │   ├── ProjectList.jsx      # Project grid
│   │   │   ├── NewProject.jsx       # Abstract input form
│   │   │   ├── ProjectDashboard.jsx # Main dashboard + SSE pipeline
│   │   │   └── AnalysisView.jsx     # Pipeline status tracker
│   │   ├── components/
│   │   │   ├── ChatPanel.jsx        # Document Q&A panel
│   │   │   └── Layout/             # Sidebar + main content wrapper
│   │   └── context/
│   │       └── ThemeContext.jsx      # Dark/light theme toggle
│   └── package.json
│
├── render-build.sh            # Render deployment build script
├── run_pipeline.py            # Standalone pipeline runner (CLI)
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
└── .kiro/
    ├── hooks/                 # Agent automation hooks
    ├── specs/                 # Feature specs
    └── steering/              # AI steering rules
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 22+
- A [Groq API key](https://console.groq.com) (free tier available)
- A [Ragie API key](https://app.ragie.ai) (for RAG indexing)
- A [Supabase project](https://supabase.com) (for persistence and auth)

### 1. Clone and configure

```bash
git clone https://github.com/SaiMurthy/ATSS.git
cd ATSS
cp .env.example .env
```

Fill in your `.env`:
```
GROQ_API_KEY=your_groq_key
RAGIE_API_KEY=your_ragie_key
ENTREZ_EMAIL=your_email@example.com
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
pip install fastapi uvicorn python-multipart fpdf2 certifi supabase pyjwt requests groq
```

### 3. Run the backend

```bash
python3 research_lab/server.py
# API starts on http://localhost:8000
```

### 4. Run the frontend (development)

```bash
cd labos-mockup
npm install
npm run dev
# Dev server starts on http://localhost:5173, proxies /api to :8000
```

### 5. Production build (single server)

```bash
cd labos-mockup && npm run build && cd ..
python3 research_lab/server.py
# Serves both API and React app on http://localhost:8000
```

---

## Demo Abstract

Use this for testing:

> We're investigating menin inhibitors for NPM1-mutant AML. Key question: Does HOX gene expression predict treatment response to menin inhibitors in NPM1-mutant acute myeloid leukemia patients?

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check — returns `{"status": "ok"}` |
| `POST` | `/api/analyze` | Runs the full pipeline, returns `ResearchState` as JSON |
| `POST` | `/api/analyze/stream` | Streams pipeline progress as SSE events |
| `GET` | `/api/chat/sessions` | List chat sessions |
| `POST` | `/api/chat/{id}/message` | Send a message in a chat session |
| `POST` | `/api/chat/upload` | Upload a PDF for document Q&A |
| `POST` | `/api/chat/export-pdf` | Generate a PDF export of results |
| `GET` | `/{path}` | Serves the React SPA (production builds only) |

**Request body (analyze endpoints):**
```json
{ "abstract": "Your research abstract (20–4000 characters)" }
```

**SSE stream events:** `literature` → `hypothesis` → `procedure` → `done`

---

## Frontend Features

- **Real-time pipeline tracking** — SSE-powered status updates with spinner animations for each agent phase
- **Three agent cards** — Literature Review, Hypothesis Design, Protocol Design with live status indicators
- **Slide-out detail panels** — click any completed agent card to see full results
- **Final Research Plan** — consolidated output with confidence badge, action items, and caveats
- **PDF export** — Standard, APA, and LaTeX formats via server-side generation
- **Document Q&A chat** — upload PDFs or chat with pipeline results using Groq
- **Dark/light theme** — toggle between warm off-white and deep charcoal themes
- **Responsive design** — IBM Plex Mono/Sans typography, clay/terracotta accent palette

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes | Groq API access for all agents and chat |
| `RAGIE_API_KEY` | Yes | Ragie.ai RAG indexing for literature |
| `ENTREZ_EMAIL` | Yes | PubMed/Entrez API identification |
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Backend-only service role key (bypasses RLS) |
| `SUPABASE_JWT_SECRET` | Optional | JWT verification for auth middleware |
| `PORT` | Optional | Server port (default: 8000) |

---

## Deployment

Deployed as a single Render web service that serves both the FastAPI backend and the built React frontend.

```bash
# Build script (render-build.sh):
pip install -r requirements.txt
pip install fastapi uvicorn python-multipart fpdf2 certifi supabase pyjwt requests groq
cd labos-mockup && npm install && npm run build

# Start command:
cd research_lab && uvicorn server:app --host 0.0.0.0 --port $PORT
```

Auto-deploy is enabled — every push to `main` triggers a new build.

---

## Architecture Notes

- **All backend code is synchronous** — no `async/await` in agents or graph logic
- **File ownership boundaries** — each file has a single responsibility (see `.kiro/steering/structure.md`)
- **Auth is optional** — if no `Authorization` header is sent, `auth.py` returns `None` (anonymous access) instead of rejecting the request; a token is only validated when one is actually provided
- **Supabase write failures do not abort the pipeline** — errors are logged, execution continues
- **Supabase is optional for the frontend** — if `VITE_SUPABASE_URL` or `VITE_SUPABASE_ANON_KEY` are missing, the app still renders; auth features are disabled (`supabase` exports as `null`), protected routes skip authentication entirely (all routes are accessible without sign-in), project creation skips the DB insert using a local timestamp ID, and the project dashboard skips fetching persisted results so the pipeline can still run without a database connection
- **Service role key stays in the backend** — never referenced in frontend code
- **SSL on macOS** — `server.py` and `literature.py` set `SSL_CERT_FILE` from `certifi` at startup
- **Single-port deployment** — when `labos-mockup/dist/` exists, `server.py` serves both API and SPA on the same port

---

## Agent Hooks

The project includes automated agent hooks (`.kiro/hooks/`) for development quality:

- **Guard File Ownership** — blocks writes that violate module boundaries
- **No Async in Agents** — catches `async/await` in backend files
- **Validate Model Constant** — flags changes to the pinned model name
- **Verify State Contract** — checks consumers when `state.py` changes
- **Lint Python/Frontend on Save** — instant syntax and lint feedback
- **CSS Consistency Check** — verifies design system compliance
- **Post-Task Build Check** — runs full build after spec tasks complete

---

## License

MIT
