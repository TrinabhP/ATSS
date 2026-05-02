# Requirements — LabOS Research Analysis Engine

## Overview

LabOS is a multi-agent scientific research analysis system. A user submits a research abstract or question, and a pipeline of 4 specialized AI agents — Literature Finder, Results Extractor, Analysis Agent, and a 3-cycle Debate Loop (Critic ↔ Results ↔ Analysis) — collaboratively produce a structured final recommendation.

**Tech Stack:** Python, Claude API (claude-sonnet-4-20250514), LangGraph, Streamlit, web_search tool

---

## User Stories & Acceptance Criteria

### US-001 — Abstract Input

**As a** researcher,  
**I want to** paste a research abstract or question into the app,  
**So that** the agent pipeline can analyze it automatically.

**Acceptance Criteria:**
- WHEN the user opens the app, THEN a text area input is displayed with a placeholder explaining accepted input formats
- WHEN the user submits an empty input, THEN the launch button is disabled and no pipeline is triggered
- WHEN the user submits an abstract of at least 20 characters, THEN the launch button becomes active
- WHEN the user clicks launch, THEN the pipeline begins and the input is locked to prevent mid-run edits
- IF the abstract exceeds 4000 characters, THEN the system truncates to 4000 characters and displays a warning

---

### US-002 — Literature Finder (Agent 1)

**As a** researcher,  
**I want** the system to find relevant published papers based on my abstract,  
**So that** the analysis is grounded in real scientific literature.

**Acceptance Criteria:**
- WHEN Agent 1 receives the abstract, THEN it extracts 3–5 precise search terms before searching
- WHEN Agent 1 searches, THEN it uses the Claude web_search tool with those extracted terms
- WHEN Agent 1 completes, THEN it returns between 5 and 10 papers, each with: title, URL, abstract summary, and relevance score (0.0–1.0)
- IF fewer than 5 papers are found, THEN the system logs a warning but continues the pipeline with available papers
- IF the web search fails, THEN the system retries once before surfacing an error to the UI
- WHEN Agent 1 output is produced, THEN it is stored in `state["papers"]` as a list of Paper dicts matching the schema in state.py

---

### US-003 — Results Extractor (Agent 2)

**As a** researcher,  
**I want** the system to extract key empirical findings from each paper,  
**So that** the analysis is based on specific data points, not vague summaries.

**Acceptance Criteria:**
- WHEN Agent 2 receives the paper list, THEN it processes each paper's URL using web_fetch
- WHEN extracting from a paper, THEN the agent captures: key findings (with specific values/p-values where available), methods, sample size, datasets, and limitations
- WHEN a paper URL is inaccessible, THEN Agent 2 skips that paper gracefully and notes it in output
- WHEN Agent 2 completes, THEN it returns results stored in `state["extracted_results"]` as a list of ExtractedResult dicts
- WHEN extracting findings, THEN verbatim numerical results (e.g., "p<0.001", "n=156", "65% response rate") are preserved exactly
- IF all paper URLs are inaccessible, THEN the pipeline surfaces an error and halts

---

### US-004 — Initial Analysis Agent (Agent 3)

**As a** researcher,  
**I want** an initial synthesis of the extracted findings before debate begins,  
**So that** there is a concrete position for the debate agents to challenge.

**Acceptance Criteria:**
- WHEN Agent 3 receives extracted results, THEN it produces a synthesis of 2–3 paragraphs covering what the collective evidence suggests
- WHEN Agent 3 completes, THEN it also returns a list of 2–5 identified gaps or inconsistencies across the papers
- WHEN Agent 3 output is produced, THEN it is stored in `state["initial_synthesis"]` (string) and `state["identified_gaps"]` (list of strings)
- WHEN synthesizing, THEN the agent explicitly notes contradictions between papers rather than averaging them away
- WHEN Agent 3 completes, THEN `state["debate_rounds"]` is initialized as an empty list and `state["current_round"]` is set to 0

---

### US-005 — Debate Loop (Critic ↔ Results ↔ Analysis)

**As a** researcher,  
**I want** the agents to challenge and refine each other's conclusions over 3 rounds,  
**So that** the final output is more rigorous than a single-pass analysis.

**Acceptance Criteria:**
- WHEN the debate loop begins, THEN it runs for exactly 3 cycles (configurable via MAX_DEBATE_ROUNDS constant)
- WHEN each cycle begins, THEN the Critic agent receives the current analysis and produces specific challenges (sample size issues, confounding variables, overgeneralization, statistical concerns)
- WHEN the Critic completes, THEN the Results Re-evaluator receives the critic's feedback and re-examines the raw extracted results to either confirm, refute, or partially validate the critique
- WHEN the Results Re-evaluator completes, THEN the Analysis Refiner updates the synthesis, explicitly stating what changed and why
- WHEN each round completes, THEN a DebateRound dict is appended to `state["debate_rounds"]` containing: round_number, critic_feedback, results_refinement, analysis_update
- WHEN the Critic's feedback references a specific paper, THEN it must cite the paper by title
- WHEN the debate loop ends after round 3, THEN the graph transitions to the Final Recommendation node

---

### US-006 — Final Recommendation

**As a** researcher,  
**I want** a structured final recommendation after all debate rounds,  
**So that** I can act on the research findings with clear guidance.

**Acceptance Criteria:**
- WHEN the Final Recommendation agent runs, THEN it produces: a recommendation (2–3 paragraphs), a confidence level (High / Moderate / Low), a list of 2–4 action items, and a list of 1–3 caveats
- WHEN confidence is "High", THEN at least 3 papers with consistent findings support the conclusion
- WHEN confidence is "Moderate", THEN findings are consistent but sample sizes are small or studies are limited
- WHEN confidence is "Low", THEN findings are contradictory or evidence base is weak
- WHEN the final output is produced, THEN all fields are stored in state: `final_recommendation`, `confidence_level`, `action_items`, `caveats`

---

### US-007 — Streamlit Dashboard

**As a** researcher,  
**I want** to see each agent's output and the debate unfold in a live dashboard,  
**So that** I can understand how the final recommendation was reached.

**Acceptance Criteria:**
- WHEN the pipeline runs, THEN the UI displays a pipeline status bar showing which agent is currently active
- WHEN Agent 1 completes, THEN the dashboard displays the list of found papers with titles and links in a collapsible section
- WHEN Agent 2 completes, THEN extracted results are available in a collapsible section
- WHEN Agent 3 completes, THEN the initial synthesis is displayed
- WHEN each debate round completes, THEN it is shown in a collapsible section with color-coded sections: red (Critic), blue (Results), green (Analysis)
- WHEN the final recommendation is ready, THEN it is displayed prominently with confidence level, action items, and caveats
- WHEN the pipeline encounters an error, THEN a descriptive error message is shown and the pipeline halts gracefully
- WHEN the pipeline completes, THEN a "Run New Analysis" button appears to reset state

---

### US-008 — Error Handling & Resilience

**As a** developer,  
**I want** the system to handle API failures and JSON parse errors gracefully,  
**So that** the app doesn't crash during a live demo.

**Acceptance Criteria:**
- WHEN any Claude API call fails, THEN the system catches the exception, stores an error in `state["error"]`, and surfaces it in the UI
- WHEN any agent returns malformed JSON, THEN the system falls back to storing the raw text response rather than crashing
- WHEN a web_search or web_fetch call times out, THEN the agent retries once before continuing without that result
- WHEN the pipeline errors, THEN all partial results collected so far remain visible in the UI

---

### US-009 — State Management

**As a** developer,  
**I want** all agent state to flow through a single typed schema,  
**So that** each agent's output is predictable and integration is clean.

**Acceptance Criteria:**
- WHEN any agent reads or writes state, THEN it uses only fields defined in `ResearchState` in state.py
- WHEN a new field is needed, THEN it must be added to `ResearchState` first before any agent uses it
- WHEN the graph is initialized, THEN all optional fields default to empty lists, empty strings, or None
- WHEN `current_stage` is updated, THEN it matches one of the defined stage IDs used by the UI status bar
