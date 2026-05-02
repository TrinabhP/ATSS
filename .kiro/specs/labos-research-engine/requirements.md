# Requirements Document

## Introduction

LabOS is a hierarchical multi-agent research analysis system. A researcher submits a scientific abstract (20–4,000 characters), and a sequential pipeline of three specialized AI agents — Literature Review (Agent 1), Hypothesis Design (Agent 2), and Procedure Design (Agent 3) — each produce structured outputs that are reviewed by an Orchestrator/Critic before the next agent runs. The Orchestrator synthesizes a final recommendation once all agents have passed review or exhausted their revision budget (MAX_REVISIONS = 2). The entire pipeline is surfaced through a Streamlit dashboard.

**Tech Stack:** Python, Claude API (`claude-sonnet-4-20250514`), LangGraph, Streamlit  
**Key constants:** `MAX_REVISIONS = 2`, `MIN_ABSTRACT_LENGTH = 20`, `MAX_ABSTRACT_LENGTH = 4000`, `MIN_PAPERS = 5`, `MAX_PAPERS = 10`

---

## Glossary

- **LabOS**: The full hierarchical multi-agent research analysis system described in this document.
- **Orchestrator**: The top-level controller that dispatches tasks to agents, reviews their outputs, sends revision requests, and synthesizes the final recommendation.
- **Critic**: The review function of the Orchestrator; evaluates each agent's output and returns a `CriticReview`.
- **Agent_1**: The Literature Review agent, composed of Sub-Agent_1A and Sub-Agent_1B.
- **Sub-Agent_1A**: The paper-finding sub-agent within Agent_1; uses `web_search` to locate relevant papers.
- **Sub-Agent_1B**: The paper-analysis sub-agent within Agent_1; analyzes each paper and produces a synthesis.
- **Agent_2**: The Hypothesis Design agent; generates a research hypothesis with an internal self-review loop.
- **Agent_3**: The Procedure Design agent; designs the full study procedure.
- **Graph**: The LangGraph state machine that wires all nodes and conditional retry edges.
- **ResearchState**: The single `TypedDict` that carries all pipeline state between nodes.
- **LiteratureOutput**: The `TypedDict` contract for Agent_1's output (`papers`, `analyses`, `search_terms`, `synthesis`, `revision_count`).
- **HypothesisOutput**: The `TypedDict` contract for Agent_2's output (`hypothesis`, `null_hypothesis`, `rationale`, `design_approach`, `expected_outcomes`, `revision_count`).
- **ProcedureOutput**: The `TypedDict` contract for Agent_3's output (`population_size`, `population_criteria`, `research_design`, `data_collection`, `statistical_approach`, `timeline_estimate`, `revision_count`).
- **CriticReview**: The `TypedDict` produced by the Critic for each agent review (`agent_name`, `revision_number`, `passed`, `feedback`, `timestamp`).
- **Paper**: A `TypedDict` with fields `title`, `url`, `abstract`, `relevance_score`.
- **PaperAnalysis**: A `TypedDict` with fields `paper_title`, `key_findings`, `methodology`, `sample_size`, `limitations`, `relevance_to_question`.
- **Dashboard**: The Streamlit web application that renders pipeline status and results.
- **MAX_REVISIONS**: The maximum number of revision cycles allowed per agent (value: 2).
- **Confidence_Level**: A string value that must be exactly `"High"`, `"Moderate"`, or `"Low"`.

---

## Requirements

### Requirement 1: Abstract Input

**User Story:** As a researcher, I want to paste a research abstract or question into the app, so that the agent pipeline can analyze it automatically.

#### Acceptance Criteria

1. WHEN the user opens the Dashboard, THE Dashboard SHALL display a text area input with a placeholder explaining accepted input formats.
2. WHILE the abstract input contains fewer than 20 characters, THE Dashboard SHALL keep the launch button disabled.
3. WHEN the abstract input reaches at least 20 characters, THE Dashboard SHALL enable the launch button.
4. WHEN the user clicks the launch button, THE Dashboard SHALL lock the abstract input field to prevent edits during the pipeline run.
5. IF the submitted abstract exceeds 4,000 characters, THEN THE Graph SHALL truncate it to 4,000 characters before passing it to any agent, and THE Dashboard SHALL display a truncation warning.
6. WHEN the pipeline is running, THE Dashboard SHALL display a character count indicator showing current length against the 4,000-character limit.

---

### Requirement 2: Sub-Agent 1A — Paper Discovery

**User Story:** As a researcher, I want the system to find relevant published papers based on my abstract, so that the analysis is grounded in real scientific literature.

#### Acceptance Criteria

1. WHEN Sub-Agent_1A receives the abstract, THE Sub-Agent_1A SHALL extract between 3 and 5 precise search terms from the abstract before issuing any search.
2. WHEN Sub-Agent_1A issues searches, THE Sub-Agent_1A SHALL use the `web_search` tool with the extracted search terms.
3. WHEN Sub-Agent_1A completes its search, THE Sub-Agent_1A SHALL return between 5 and 10 `Paper` dicts, each containing a non-empty `title`, a non-empty `url`, a non-empty `abstract`, and a `relevance_score` between 0.0 and 1.0 inclusive.
4. IF Sub-Agent_1A finds fewer than 5 papers after exhausting its search attempts, THEN THE Agent_1 SHALL log a warning in `state["orchestrator_messages"]` and continue the pipeline with the available papers rather than halting.
5. IF the `web_search` tool call fails, THEN THE Sub-Agent_1A SHALL retry the search once before surfacing an error.
6. THE Sub-Agent_1A SHALL store the extracted search terms in `state["literature"]["search_terms"]` as a non-empty list of strings.

---

### Requirement 3: Sub-Agent 1B — Paper Analysis and Synthesis

**User Story:** As a researcher, I want the system to analyze each found paper and synthesize the findings, so that the hypothesis and procedure agents have a grounded evidence base.

#### Acceptance Criteria

1. WHEN Sub-Agent_1B receives the list of papers from Sub-Agent_1A, THE Sub-Agent_1B SHALL produce one `PaperAnalysis` dict per paper, containing non-empty `paper_title`, at least one entry in `key_findings`, non-empty `methodology`, and non-empty `relevance_to_question`.
2. WHEN Sub-Agent_1B extracts numerical findings (p-values, effect sizes, sample sizes, percentages), THE Sub-Agent_1B SHALL preserve the verbatim numerical values rather than paraphrasing them.
3. WHEN Sub-Agent_1B completes analysis of all papers, THE Sub-Agent_1B SHALL produce a `synthesis` string of at least two paragraphs that directly addresses the research question from the abstract.
4. WHEN the synthesis contains contradictions between papers, THE Sub-Agent_1B SHALL explicitly name the contradiction rather than averaging the findings.
5. WHEN Agent_1 completes, THE Agent_1 SHALL store the result in `state["literature"]` as a `LiteratureOutput` dict with all five required fields populated: `papers`, `analyses`, `search_terms`, `synthesis`, and `revision_count`.

---

### Requirement 4: Agent 1 — Critic-Driven Revision

**User Story:** As a researcher, I want the literature review to be revised when the Critic identifies deficiencies, so that the downstream agents receive a high-quality evidence base.

#### Acceptance Criteria

1. WHEN the Critic review of Agent_1 output has `passed = False` and `revision_count < MAX_REVISIONS`, THE Graph SHALL dispatch Agent_1 again with the Critic's `feedback` string as `critic_feedback`.
2. WHEN Agent_1 is dispatched for revision, THE Agent_1 SHALL increment `revision_count` by 1 in the returned `LiteratureOutput`.
3. WHEN Agent_1 has been revised `MAX_REVISIONS` times, THE Graph SHALL proceed to Agent_2 regardless of the Critic's verdict on the final revision.
4. THE Agent_1 `revision_count` SHALL never exceed `MAX_REVISIONS` across any pipeline run.

---

### Requirement 5: Agent 2 — Hypothesis Design with Self-Review

**User Story:** As a researcher, I want a well-formed, self-reviewed research hypothesis generated from the literature, so that the hypothesis is scientifically rigorous before the Critic evaluates it.

#### Acceptance Criteria

1. WHEN Agent_2 receives the `LiteratureOutput` and abstract, THE Agent_2 SHALL generate a `HypothesisOutput` containing: a non-empty `hypothesis` naming the population, intervention/exposure, comparator, and outcome; a non-empty `null_hypothesis` stating the formal H₀; a non-empty `rationale` citing at least one specific finding from the provided literature; a non-empty `design_approach`; and at least two entries in `expected_outcomes`.
2. WHEN Agent_2 generates an initial hypothesis, THE Agent_2 SHALL perform an internal self-review evaluating specificity, testability, falsifiability, and literature grounding before returning the output to the Orchestrator.
3. IF the self-review identifies issues, THEN THE Agent_2 SHALL generate a corrected hypothesis addressing those issues before returning to the Orchestrator.
4. WHEN the Critic review of Agent_2 output has `passed = False` and `revision_count < MAX_REVISIONS`, THE Graph SHALL dispatch Agent_2 again with the Critic's `feedback` string as `critic_feedback`.
5. WHEN Agent_2 is dispatched for revision, THE Agent_2 SHALL increment `revision_count` by 1 in the returned `HypothesisOutput`.
6. THE Agent_2 `revision_count` SHALL never exceed `MAX_REVISIONS` across any pipeline run.

---

### Requirement 6: Agent 3 — Procedure Design

**User Story:** As a researcher, I want a complete study procedure designed for the approved hypothesis, so that I have an actionable research plan.

#### Acceptance Criteria

1. WHEN Agent_3 receives the `LiteratureOutput`, `HypothesisOutput`, and abstract, THE Agent_3 SHALL generate a `ProcedureOutput` containing all six required fields: `population_size`, `population_criteria`, `research_design`, `data_collection`, `statistical_approach`, and `timeline_estimate`.
2. WHEN Agent_3 generates `population_size`, THE Agent_3 SHALL include a power calculation rationale specifying the assumed effect size, power level (80% or 90%), and alpha level.
3. WHEN Agent_3 generates `population_criteria`, THE Agent_3 SHALL specify concrete inclusion and exclusion criteria (e.g., age ranges, diagnosis codes, biomarker thresholds) rather than generic descriptions.
4. WHEN Agent_3 generates `statistical_approach`, THE Agent_3 SHALL name the specific statistical test(s) and directly address the primary endpoint from the hypothesis.
5. WHEN the Critic review of Agent_3 output has `passed = False` and `revision_count < MAX_REVISIONS`, THE Graph SHALL dispatch Agent_3 again with the Critic's `feedback` string as `critic_feedback`.
6. WHEN Agent_3 is dispatched for revision, THE Agent_3 SHALL increment `revision_count` by 1 in the returned `ProcedureOutput`.
7. THE Agent_3 `revision_count` SHALL never exceed `MAX_REVISIONS` across any pipeline run.

---

### Requirement 7: Orchestrator — Dispatch and Review

**User Story:** As a researcher, I want the Orchestrator to review each agent's output and request revisions when needed, so that only high-quality outputs proceed to the next stage.

#### Acceptance Criteria

1. WHEN the Graph starts, THE Orchestrator SHALL dispatch Agent_1 first, then Agent_2 after Agent_1's review cycle completes, then Agent_3 after Agent_2's review cycle completes.
2. WHEN any agent completes, THE Orchestrator SHALL produce a `CriticReview` with `agent_name`, `revision_number`, `passed`, `feedback`, and `timestamp` fields populated.
3. WHEN the Critic review `passed = True`, THE Orchestrator SHALL set `feedback` to an empty string in the `CriticReview`.
4. WHEN the Critic review `passed = False`, THE Orchestrator SHALL set `feedback` to a specific, actionable critique in the `CriticReview`.
5. WHEN a `CriticReview` is produced, THE Graph SHALL append it to `state["reviews"]`.
6. THE Orchestrator SHALL log each dispatch and review decision as a timestamped entry in `state["orchestrator_messages"]`.

---

### Requirement 8: Orchestrator — Final Synthesis

**User Story:** As a researcher, I want a final synthesized recommendation after all agents have completed, so that I receive a single actionable conclusion from the full pipeline.

#### Acceptance Criteria

1. WHEN all three agents have either passed their Critic review or exhausted `MAX_REVISIONS`, THE Orchestrator SHALL run the final synthesis.
2. WHEN the Orchestrator synthesizes, THE Orchestrator SHALL produce a `final_recommendation` string of at least two paragraphs integrating the literature evidence, hypothesis, and procedure.
3. WHEN the Orchestrator synthesizes, THE Orchestrator SHALL produce a `confidence_level` that is exactly one of `"High"`, `"Moderate"`, or `"Low"`.
4. WHEN `confidence_level` is `"High"`, THE Orchestrator SHALL require that at least 5 papers with consistent findings support the conclusion.
5. WHEN `confidence_level` is `"Moderate"`, THE Orchestrator SHALL indicate that findings are consistent but evidence has limitations (small samples, limited study types, or gaps).
6. WHEN `confidence_level` is `"Low"`, THE Orchestrator SHALL indicate that findings are contradictory or the evidence base is weak.
7. WHEN the Orchestrator synthesizes, THE Orchestrator SHALL produce `action_items` as a list of 3–5 specific next steps and `caveats` as a list of 2–4 important limitations.
8. WHEN synthesis completes, THE Graph SHALL store `final_recommendation`, `confidence_level`, `action_items`, and `caveats` in `ResearchState`.

---

### Requirement 9: LangGraph Graph — Pipeline Structure

**User Story:** As a developer, I want the pipeline wired as a LangGraph state machine with conditional retry loops, so that the revision logic is explicit and auditable.

#### Acceptance Criteria

1. THE Graph SHALL define nodes in this order: `dispatch_literature` → `review_literature_node` → `dispatch_hypothesis` → `review_hypothesis_node` → `dispatch_procedure` → `review_procedure_node` → `synthesize_node`.
2. WHEN `review_literature_node` completes, THE Graph SHALL route to `dispatch_literature` if the latest literature review failed and `revision_count < MAX_REVISIONS`, otherwise route to `dispatch_hypothesis`.
3. WHEN `review_hypothesis_node` completes, THE Graph SHALL route to `dispatch_hypothesis` if the latest hypothesis review failed and `revision_count < MAX_REVISIONS`, otherwise route to `dispatch_procedure`.
4. WHEN `review_procedure_node` completes, THE Graph SHALL route to `dispatch_procedure` if the latest procedure review failed and `revision_count < MAX_REVISIONS`, otherwise route to `synthesize_node`.
5. WHEN `synthesize_node` completes, THE Graph SHALL transition to `END`.
6. THE Graph SHALL use `ResearchState` as its sole state type.

---

### Requirement 10: State Management

**User Story:** As a developer, I want all agent state to flow through a single typed schema, so that each agent's output is predictable and integration is clean.

#### Acceptance Criteria

1. THE ResearchState SHALL be the only state type passed between Graph nodes, containing exactly the fields defined in `state.py`: `abstract`, `current_stage`, `orchestrator_messages`, `literature`, `hypothesis`, `procedure`, `reviews`, `final_recommendation`, `confidence_level`, `action_items`, `caveats`, `error`.
2. WHEN any agent reads or writes state, THE agent SHALL access only fields defined in `ResearchState` in `state.py`.
3. WHEN the Graph is initialized, THE Graph SHALL set all optional fields to their zero values: `literature`, `hypothesis`, `procedure`, `final_recommendation`, `confidence_level`, `error` to `None`; `orchestrator_messages`, `reviews`, `action_items`, `caveats` to empty lists.
4. WHEN `current_stage` is updated, THE Graph SHALL set it to one of the defined stage IDs: `"literature_running"`, `"literature_review"`, `"hypothesis_running"`, `"hypothesis_review"`, `"procedure_running"`, `"procedure_review"`, `"synthesizing"`, or `"complete"`.

---

### Requirement 11: Streamlit Dashboard

**User Story:** As a researcher, I want to see each agent's output and the Critic reviews in a live dashboard, so that I can understand how the final recommendation was reached.

#### Acceptance Criteria

1. WHEN the Dashboard renders, THE Dashboard SHALL display a pipeline status bar with exactly 7 stage cards corresponding to the 7 pipeline stages.
2. WHEN a pipeline stage is active, THE Dashboard SHALL highlight that stage card with the accent color (`#3b82f6`).
3. WHEN a pipeline stage is complete, THE Dashboard SHALL mark that stage card with the success color (`#10b981`).
4. WHEN Agent_1 completes, THE Dashboard SHALL display the found papers with titles and links in a collapsible section.
5. WHEN Agent_1 completes, THE Dashboard SHALL display the paper analyses and literature synthesis in collapsible sections.
6. WHEN Agent_2 completes, THE Dashboard SHALL display the hypothesis, null hypothesis, rationale, design approach, and expected outcomes in a collapsible section.
7. WHEN Agent_3 completes, THE Dashboard SHALL display all six procedure fields in a collapsible section.
8. WHEN a Critic review is produced, THE Dashboard SHALL display it with a green left border if `passed = True` and a red left border if `passed = False`.
9. WHEN the final recommendation is ready, THE Dashboard SHALL display it in a prominently styled card with the confidence level badge, action items, and caveats.
10. WHEN an agent has been revised at least once, THE Dashboard SHALL display a revision badge indicating the revision count.
11. WHEN the pipeline completes, THE Dashboard SHALL display a "Run New Analysis" button to reset state.

---

### Requirement 12: Error Handling and Resilience

**User Story:** As a developer, I want the system to handle API failures and malformed outputs gracefully, so that the app does not crash during a live run.

#### Acceptance Criteria

1. WHEN any Claude API call raises an exception, THE agent SHALL catch the exception, store a descriptive error string in `state["error"]`, and return a partial output rather than propagating the exception.
2. WHEN any agent receives a response that cannot be parsed as valid JSON, THE agent SHALL fall back to storing the raw text response in the relevant output field rather than raising an exception.
3. WHEN a `web_search` call times out or fails, THE Sub-Agent_1A SHALL retry the call once before continuing without that result.
4. WHEN the pipeline encounters an error, THE Dashboard SHALL display a descriptive error message and all partial results collected up to that point SHALL remain visible.
5. IF Agent_1 raises `NotImplementedError` (stub state), THEN THE Graph SHALL substitute a placeholder `LiteratureOutput` with `revision_count = MAX_REVISIONS` to prevent the retry loop from cycling, and THE Dashboard SHALL display a pending notice rather than an error.

---

## Correctness Properties

The following properties are suitable for property-based testing using a framework such as Hypothesis or fast-check. Each property should hold for any valid input within the specified domain.

### Property 1: LiteratureOutput Contract Invariant

FOR ALL abstract strings of length between 20 and 4,000 characters, WHEN `run_literature_agent` completes without raising an exception, THE returned `LiteratureOutput` SHALL contain `papers` as a list, `analyses` as a list, `search_terms` as a non-empty list, `synthesis` as a string, and `revision_count` as a non-negative integer.

*Pattern: Structural invariant — output always satisfies the TypedDict contract.*

### Property 2: Paper Count Bounds

FOR ALL abstract strings of length between 20 and 4,000 characters, WHEN `run_literature_agent` completes successfully (no API error), THE `papers` list in the returned `LiteratureOutput` SHALL contain between 1 and 10 entries (lower bound relaxed to 1 to account for the graceful-degradation path; upper bound is strict at 10).

*Pattern: Invariant — collection size is bounded.*

### Property 3: Revision Count Never Exceeds MAX_REVISIONS

FOR ALL sequences of Critic reviews where every review has `passed = False`, WHEN the Graph processes any agent through its full retry loop, THE `revision_count` in the final agent output SHALL be less than or equal to `MAX_REVISIONS` (2).

*Pattern: Invariant — numeric bound preserved under adversarial input.*

### Property 4: Orchestrator Dispatch Order

FOR ALL valid abstract inputs, WHEN `run_research` completes, THE `orchestrator_messages` list in the returned `ResearchState` SHALL contain an Agent_1 completion entry before any Agent_2 completion entry, and an Agent_2 completion entry before any Agent_3 completion entry, and an Agent_3 completion entry before any synthesis completion entry.

*Pattern: Ordering invariant — sequential dispatch is preserved.*

### Property 5: Synthesis Precondition

FOR ALL valid abstract inputs, WHEN `synthesize_node` is reached, THE `ResearchState` SHALL have a non-None `literature` field, a non-None `hypothesis` field, and a non-None `procedure` field.

*Pattern: Precondition invariant — synthesis only runs after all agents have produced output.*

### Property 6: Confidence Level Value Set

FOR ALL valid abstract inputs, WHEN `run_research` completes and `final_recommendation` is non-None, THE `confidence_level` in the returned `ResearchState` SHALL be exactly one of `"High"`, `"Moderate"`, or `"Low"`.

*Pattern: Value-set invariant — enumerated field is always valid.*

### Property 7: ResearchState Schema Closure

FOR ALL valid abstract inputs, WHEN `run_research` completes, THE keys of the returned `ResearchState` dict SHALL be exactly the set `{"abstract", "current_stage", "orchestrator_messages", "literature", "hypothesis", "procedure", "reviews", "final_recommendation", "confidence_level", "action_items", "caveats", "error"}` — no additional keys, no missing keys.

*Pattern: Structural invariant — state schema is closed under all pipeline paths.*

### Property 8: CriticReview Feedback Consistency

FOR ALL `CriticReview` dicts in `state["reviews"]`, IF `passed = True` THEN `feedback` SHALL be an empty string; IF `passed = False` THEN `feedback` SHALL be a non-empty string.

*Pattern: Conditional invariant — feedback presence is consistent with pass/fail status.*

### Property 9: Analyses Count Matches Papers Count

FOR ALL `LiteratureOutput` dicts where `papers` is non-empty, THE length of `analyses` SHALL be greater than 0 and less than or equal to the length of `papers`.

*Pattern: Metamorphic invariant — analysis count is bounded by paper count.*

### Property 10: Revision Count Monotonicity

FOR ALL agents across a single pipeline run, WHEN the Graph dispatches an agent for the Nth time, THE `revision_count` in the returned output SHALL equal N − 1 (0-indexed: first dispatch returns 0, first revision returns 1, second revision returns 2).

*Pattern: Monotonic increment invariant.*
