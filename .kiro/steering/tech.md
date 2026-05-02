# Tech Stack

## Python Backend (`research_lab/`)

- **Language**: Python 3.11+
- **AI**: Anthropic Claude API — model `claude-sonnet-4-20250514` (do not change this)
- **Orchestration**: LangGraph (`StateGraph`) — synchronous only, no async/await
- **Frontend**: Streamlit
- **State**: `TypedDict` (`ResearchState` in `state.py`)
- **HTTP client**: `anthropic` SDK with `web_search_20250305` tool for Agents 1 & 2

### Pinned Dependencies (`research_lab/requirements.txt`)
```
anthropic==0.49.0
langgraph==0.3.34
streamlit==1.45.0
typing_extensions>=4.0.0
```
Do not add new dependencies without explicit instruction.

### Environment Variables
| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Used by all agents via `os.environ.get("ANTHROPIC_API_KEY")` |

---

## React Mockup (`labos-mockup/`)

- **Framework**: React 19 + Vite 8
- **Routing**: React Router DOM v7
- **Animation**: Framer Motion
- **Icons**: Lucide React
- **Linting**: ESLint 10

---

## Common Commands

### Python backend
```bash
# Run the Streamlit dashboard
streamlit run research_lab/app.py

# Run the full pipeline integration test
python research_lab/graph.py

# Run individual agent tests
python research_lab/agents/hypothesis.py
python research_lab/agents/procedure.py
python research_lab/agents/orchestrator.py
```

### React mockup
```bash
cd labos-mockup
npm install
npm run dev       # development server
npm run build     # production build
npm run lint      # ESLint
```

---

## Key Constants

| Constant | Value | File |
|---|---|---|
| `MODEL` | `"claude-sonnet-4-20250514"` | each agent file |
| `MAX_REVISIONS` | `2` | `graph.py` |
| `MAX_ABSTRACT_LENGTH` | `4000` | `app.py` |
| `MIN_ABSTRACT_LENGTH` | `20` | `app.py` |
| `MAX_PAPERS` | `10` | `agents/literature.py` |
| `MIN_PAPERS` | `5` | `agents/literature.py` |
