# Project Structure

## Repository Layout

```
/
├── research_lab/          # Production Python backend
│   ├── app.py             # Streamlit dashboard (UI only, imports run_research from graph.py)
│   ├── graph.py           # LangGraph wiring — nodes, edges, conditional retry logic, run_research()
│   ├── state.py           # Shared TypedDict schema — ResearchState and all output types
│   ├── agents.py          # Legacy flat agent file (older architecture, kept for reference)
│   ├── critic_agent.py    # Legacy critic (older architecture)
│   ├── requirements.txt   # Pinned Python dependencies
│   └── agents/            # Current hierarchical agent implementations
│       ├── __init__.py
│       ├── literature.py  # Agent 1 — Sub-Agent 1A (paper discovery) + Sub-Agent 1B (analysis/synthesis)
│       ├── hypothesis.py  # Agent 2 — Hypothesis design with internal self-review loop
│       ├── procedure.py   # Agent 3 — Study procedure design
│       └── orchestrator.py # Critic review functions + final synthesis
│
├── labos-mockup/          # React/Vite UI prototype (independent of Python backend)
│   ├── src/
│   │   ├── App.jsx
│   │   ├── pages/         # Route-level page components
│   │   ├── components/    # Shared UI components
│   │   │   └── Layout/
│   │   └── context/       # React context providers (e.g., ThemeContext)
│   ├── public/
│   └── package.json
│
├── .kiro/
│   ├── specs/             # Feature specs (requirements, design, tasks)
│   │   └── labos-research-engine/
│   ├── steering/          # AI steering rules (this directory)
│   └── hooks/             # Kiro automation hooks
│
├── main.py                # Standalone prototype (older flat LangGraph + Tavily, not production)
├── design.md              # Top-level design notes
├── requirements.md        # Top-level requirements notes
└── .env.example           # Environment variable template
```

---

## File Ownership Rules

These boundaries must not be crossed without explicit instruction:

| File | Responsibility | What does NOT belong here |
|---|---|---|
| `state.py` | TypedDict definitions only — shared contract | No agent logic, no LangGraph imports |
| `agents/literature.py` | Agent 1 Claude API calls | No LangGraph imports, no Streamlit |
| `agents/hypothesis.py` | Agent 2 Claude API calls | No LangGraph imports, no Streamlit |
| `agents/procedure.py` | Agent 3 Claude API calls | No LangGraph imports, no Streamlit |
| `agents/orchestrator.py` | Critic review functions + synthesize_final | No LangGraph imports, no Streamlit |
| `graph.py` | LangGraph node/edge wiring, `run_research()` | No direct Claude API calls, no Streamlit |
| `app.py` | Streamlit rendering only | No Claude API calls, no LangGraph logic |

---

## Coding Conventions

- All functions must have type hints
- Agent function signatures: `fn(state: ResearchState) -> ResearchState` (graph nodes) or typed input/output structs (agent modules)
- All Claude API calls wrapped in `try/except` with fallback behavior — never let an exception propagate out of an agent
- JSON parse errors caught via `_safe_json()` helper — never crash on malformed LLM output
- `state["current_stage"]` updated at the start of every graph node
- Constants (`MODEL`, `MAX_REVISIONS`, etc.) defined at the top of their respective files
- All styles inline in `app.py` — no separate CSS files
- Everything synchronous — no `async/await`
- Standalone tests guarded by `if __name__ == "__main__":` at the bottom of agent files
