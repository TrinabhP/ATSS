# Design — LabOS Research Analysis Engine

## System Architecture Overview

LabOS is a single-server Python application. The frontend is a Streamlit dashboard. The backend is a LangGraph state machine that orchestrates sequential and cyclical Claude API calls. There is no persistent database — all state lives in a single `ResearchState` TypedDict that is passed between nodes in the graph.

```
┌─────────────────────────────────────────────────────┐
│                  Streamlit Frontend                  │
│  Abstract Input → Pipeline Status Bar → Results UI  │
└────────────────────────┬────────────────────────────┘
                         │ run_research(abstract)
                         ▼
┌─────────────────────────────────────────────────────┐
│                  LangGraph Graph                     │
│                                                      │
│  [literature_finder] → [results_extractor]           │
│       → [initial_analysis] → [debate_round]*3        │
│       → [final_recommendation] → END                 │
└────────────────────────┬────────────────────────────┘
                         │ Claude API calls
                         ▼
┌─────────────────────────────────────────────────────┐
│              Anthropic Claude API                    │
│   Model: claude-sonnet-4-20250514                    │
│   Tools: web_search (Agents 1 & 2 only)              │
└─────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
User Input: abstract (string)
        │
        ▼
┌───────────────────┐
│  literature_finder │  Reads:  state.abstract
│  (Agent 1)         │  Writes: state.papers, state.search_terms
│  Tools: web_search │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ results_extractor  │  Reads:  state.papers
│ (Agent 2)          │  Writes: state.extracted_results
│ Tools: web_search  │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ initial_analysis   │  Reads:  state.extracted_results, state.abstract
│ (Agent 3)          │  Writes: state.initial_synthesis, state.identified_gaps
│                    │          state.debate_rounds=[], state.current_round=0
└────────┬──────────┘
         │
         ▼
┌────────────────────────────────────┐
│         debate_round (×3)          │
│                                    │
│  critic_agent()                    │  Reads:  latest analysis (debate_rounds[-1]
│    → results_reevaluator()         │           or initial_synthesis), extracted_results
│      → analysis_refiner()          │  Writes: appends DebateRound to debate_rounds,
│                                    │          increments current_round
└────────┬───────────────────────────┘
         │  current_round == 3
         ▼
┌───────────────────┐
│ final_recommenda-  │  Reads:  debate_rounds[-1].analysis_update, abstract
│ tion_agent         │  Writes: final_recommendation, confidence_level,
│                    │          action_items, caveats
└────────┬──────────┘
         │
         ▼
      END → Return final ResearchState to Streamlit
```

---

## TypedDict Interfaces (from state.py)

### Paper
```python
class Paper(TypedDict):
    title: str
    url: str
    abstract: str
    relevance_score: Optional[float]  # 0.0 – 1.0
```

### ExtractedResult
```python
class ExtractedResult(TypedDict):
    paper_title: str
    key_findings: List[str]     # Verbatim numerical findings preferred
    methods: str
    sample_size: Optional[str]  # e.g. "n=156"
    datasets: Optional[str]
    limitations: Optional[str]
```

### DebateRound
```python
class DebateRound(TypedDict):
    round_number: int           # 1, 2, or 3
    critic_feedback: str        # Plain text, 2-3 paragraphs
    results_refinement: str     # Plain text, 2-3 paragraphs
    analysis_update: str        # Plain text, 2-3 paragraphs
```

### ResearchState (full graph state)
```python
class ResearchState(TypedDict):
    abstract: str
    search_terms: List[str]
    papers: List[Paper]
    extracted_results: List[ExtractedResult]
    initial_synthesis: str
    identified_gaps: List[str]
    debate_rounds: List[DebateRound]
    current_round: int
    final_recommendation: str
    confidence_level: str       # "High" | "Moderate" | "Low"
    action_items: List[str]
    caveats: List[str]
    current_stage: str          # Stage ID for UI status bar
    error: Optional[str]
```

---

## LangGraph Node Definitions

### Nodes
| Node Name | Function | Agent Role |
|-----------|----------|------------|
| `literature_finder` | `literature_finder(state)` | Agent 1 — Person 1 |
| `results_extractor` | `results_extractor(state)` | Agent 2 — Person 2 |
| `initial_analysis` | `initial_analysis_agent(state)` | Agent 3 — Person 4 |
| `debate_round` | `debate_round_node(state)` | Critic + Results + Analysis — Person 3 |
| `final_recommendation` | `final_recommendation_agent(state)` | Final synthesis — Person 3 |

### Edges
```
literature_finder → results_extractor (unconditional)
results_extractor → initial_analysis  (unconditional)
initial_analysis  → debate_round      (unconditional)
debate_round      → debate_round      (conditional: current_round < MAX_DEBATE_ROUNDS)
debate_round      → final_recommendation (conditional: current_round == MAX_DEBATE_ROUNDS)
final_recommendation → END            (unconditional)
```

### Conditional Edge Logic
```python
def should_continue_debate(state: ResearchState) -> str:
    if state["current_round"] < MAX_DEBATE_ROUNDS:  # MAX_DEBATE_ROUNDS = 3
        return "debate"
    return "finalize"
```

---

## Agent Prompt Design

### Agent 1 — Literature Finder
- **Role:** Scientific literature researcher
- **Tools:** web_search
- **Input:** Raw abstract text
- **Output format:** JSON `{ search_terms: [], papers: [] }`
- **Key constraints:** 5–10 papers, prioritize 2018+, relevance score required

### Agent 2 — Results Extractor
- **Role:** Scientific data extractor
- **Tools:** web_search (for fetching paper content)
- **Input:** List of Paper dicts
- **Output format:** JSON `{ extracted_results: [] }`
- **Key constraints:** Preserve verbatim numerical findings; skip inaccessible URLs gracefully

### Agent 3 — Initial Analysis
- **Role:** Senior research scientist
- **Tools:** None (reasoning only)
- **Input:** extracted_results + abstract
- **Output format:** JSON `{ initial_synthesis: "", identified_gaps: [] }`
- **Key constraints:** Must explicitly name contradictions between papers

### Critic Agent
- **Role:** Rigorous scientific critic
- **Tools:** None
- **Input:** Current analysis + extracted_results
- **Output format:** Plain text (2–3 paragraphs)
- **Key constraints:** Must cite specific papers by name; target sample size, confounders, statistics

### Results Re-evaluator
- **Role:** Data-focused research analyst
- **Tools:** None
- **Input:** Critic feedback + extracted_results
- **Output format:** Plain text (2–3 paragraphs)
- **Key constraints:** Must explicitly confirm, refute, or partially validate each critic concern

### Analysis Refiner
- **Role:** Senior scientist updating synthesis
- **Tools:** None
- **Input:** Previous analysis + critic feedback + results response
- **Output format:** Plain text (2–3 paragraphs)
- **Key constraints:** Must explicitly state what changed from previous round and why

### Final Recommendation Agent
- **Role:** Research director
- **Tools:** None
- **Input:** Final debate analysis + abstract + all debate_rounds
- **Output format:** JSON `{ final_recommendation: "", confidence_level: "", action_items: [], caveats: [] }`
- **Key constraints:** confidence_level must be "High", "Moderate", or "Low" only

---

## Frontend Design (Streamlit)

### Layout
```
Header: LabOS logo + subtitle (IBM Plex Mono, dark theme #0a0e1a)
─────────────────────────────────────
Input Section:  text_area (abstract) + launch button
─────────────────────────────────────
Pipeline Status Bar: 7 stage cards in a row (icons + labels)
  [Agent 1] [Agent 2] [Agent 3] [Debate 1] [Debate 2] [Debate 3] [Final]
─────────────────────────────────────
Results (populated as pipeline runs):
  ▸ Papers Found (collapsible)
  ▸ Initial Analysis (collapsible)
  ▸ Debate Round 1 (collapsible, color-coded)
  ▸ Debate Round 2 (collapsible, color-coded)
  ▸ Debate Round 3 (collapsible, color-coded)
  ▸ FINAL RECOMMENDATION (always expanded, prominent card)
     Left column: Action Items
     Right column: Caveats
```

### Color System
| Element | Color |
|---------|-------|
| Background | `#0a0e1a` |
| Card background | `#111827` |
| Primary accent | `#3b82f6` (blue) |
| Success / Analysis | `#10b981` (green) |
| Critic / Warning | `#ef4444` (red) |
| Results | `#3b82f6` (blue) |
| Moderate confidence | `#f59e0b` (yellow) |
| Muted text | `#6b7280` |
| Body text | `#e0e6f0` |

### Typography
- Headers / labels: `IBM Plex Mono`
- Body: `IBM Plex Sans`

---

## File Structure

```
research_lab/
├── state.py          # ResearchState TypedDict schema (shared contract)
├── agents.py         # All agent functions + system prompts
├── graph.py          # LangGraph graph definition + run_research()
├── app.py            # Streamlit dashboard
├── requirements.txt  # anthropic, langgraph, streamlit
└── .kiro/
    └── specs/
        ├── requirements.md   ← this file's sibling
        ├── design.md         ← this file
        └── tasks.md
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key for all agent calls |

---

## Constants

| Constant | Value | Location | Description |
|----------|-------|----------|-------------|
| `MODEL` | `"claude-sonnet-4-20250514"` | agents.py | Claude model used by all agents |
| `MAX_DEBATE_ROUNDS` | `3` | graph.py | Number of critic cycles |
| `MAX_ABSTRACT_LENGTH` | `4000` | app.py | Character limit on input |
| `MAX_PAPERS` | `10` | agents.py | Upper limit on papers returned |
| `MIN_PAPERS` | `5` | agents.py | Minimum to proceed without warning |
