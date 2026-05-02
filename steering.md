# LabOS — Kiro Steering File
# This file tells all Kiro agents how to behave across this project.

## Project Context
This is a multi-agent research analysis app built in Python.
It uses LangGraph for orchestration, Claude API for all AI calls, and Streamlit for UI.
The hackathon deadline is 8 hours from start. Prioritize working code over perfection.

## Tech Stack
- Language: Python 3.11+
- AI: Anthropic Claude API (model: claude-sonnet-4-20250514)
- Orchestration: LangGraph (StateGraph)
- Frontend: Streamlit
- State: TypedDict (ResearchState in state.py)

## Coding Standards
- All functions must have type hints
- All agent functions signature: `fn(state: ResearchState) -> ResearchState`
- All Claude API calls must have try/except with fallback behavior
- JSON parse errors must be caught — never let a parse error crash the pipeline
- Use `state["current_stage"]` updates at the start of every agent function
- Constants (MODEL, MAX_DEBATE_ROUNDS) go at the top of their respective files

## File Ownership — Do Not Cross These Boundaries
- `state.py`: Shared contract. No agent-specific logic here. TypedDicts only.
- `agents.py`: All Claude API calls live here. No LangGraph imports.
- `graph.py`: LangGraph wiring only. Imports from agents.py and state.py.
- `app.py`: Streamlit only. Imports run_research from graph.py.

## What Kiro Should Prioritize
1. Integration correctness over feature completeness
2. Error resilience (try/except on all external calls)
3. Clean state passing between agents (no direct variable sharing)
4. Demo-ability: the pipeline must run end-to-end on the menin inhibitor abstract

## What Kiro Should Avoid
- Adding new dependencies not in: anthropic, langgraph, streamlit
- Adding database or file persistence (state is in-memory only)
- Changing TypedDict field names in state.py without explicit instruction
- Using any model other than claude-sonnet-4-20250514
- Adding async/await (keep everything synchronous for simplicity)
- Creating separate CSS files (all styles inline in app.py)

## Testing Approach
- Each agent has a standalone test at the bottom of its section (guarded by `if __name__ == "__main__":` or inline)
- `python graph.py` is the integration test — must run end-to-end
- `streamlit run app.py` is the UI test

## Demo Abstract (use for all testing)
"We're investigating menin inhibitors for NPM1-mutant AML. Key question: Does HOX gene expression predict treatment response to menin inhibitors in NPM1-mutant acute myeloid leukemia patients?"
