# LabOS — Product Overview

LabOS is a hierarchical multi-agent research analysis system. A researcher submits a scientific abstract (20–4,000 characters), and a sequential pipeline of three specialized AI agents produces a structured final recommendation:

1. **Agent 1 — Literature Review**: Finds 5–10 relevant papers (Sub-Agent 1A) and analyzes/synthesizes them (Sub-Agent 1B)
2. **Agent 2 — Hypothesis Design**: Generates a testable research hypothesis with an internal self-review loop
3. **Agent 3 — Procedure Design**: Designs a full study procedure (population, methods, statistics, timeline)

An **Orchestrator/Critic** reviews each agent's output and can trigger up to `MAX_REVISIONS = 2` revision cycles per agent before proceeding. After all agents pass (or exhaust revisions), the Orchestrator synthesizes a final recommendation with a confidence level (`"High"` / `"Moderate"` / `"Low"`), action items, and caveats.

The pipeline is surfaced through a **Streamlit dashboard** with a dark theme (IBM Plex fonts, `#0a0e1a` background) and a 7-stage pipeline status bar.

There is also a **React/Vite mockup** (`labos-mockup/`) for UI prototyping — it is separate from the production Python backend.

## Demo Abstract (use for all testing)
> "We're investigating menin inhibitors for NPM1-mutant AML. Key question: Does HOX gene expression predict treatment response to menin inhibitors in NPM1-mutant acute myeloid leukemia patients?"
