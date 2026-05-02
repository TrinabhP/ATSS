# Tasks — LabOS Research Analysis Engine

Implementation tasks sequenced by dependency. Each task has a clear owner, inputs, outputs, and acceptance test.

---

## Phase 1 — Foundation (Hour 1) — ALL TEAM

### Task 1.1 — Project Setup
**Owner:** Everyone (5 mins each)  
**Depends on:** Nothing

- [ ] Create project directory `research_lab/`
- [ ] Install dependencies: `pip install anthropic langgraph streamlit`
- [ ] Set environment variable: `export ANTHROPIC_API_KEY=<key>`
- [ ] Verify Claude API works:
  ```python
  import anthropic
  client = anthropic.Anthropic()
  r = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=10, messages=[{"role":"user","content":"hi"}])
  print(r.content[0].text)  # Should print something
  ```
- [ ] Copy `state.py` into project root — everyone imports this, nobody edits alone

**Done when:** All 4 team members can import `anthropic` and `langgraph` without errors

---

### Task 1.2 — Define Shared State Contract
**Owner:** Person 3 (LangGraph lead)  
**Depends on:** Task 1.1

- [ ] Confirm `state.py` is finalized with all TypedDicts: `Paper`, `ExtractedResult`, `DebateRound`, `ResearchState`
- [ ] Announce final field names to team on Slack/in person
- [ ] Write a quick sanity check:
  ```python
  from state import ResearchState
  s: ResearchState = {"abstract": "test", "papers": [], ...}  # fill all fields
  print("State schema OK")
  ```

**Done when:** All 4 agents can import ResearchState with no type errors

---

## Phase 2 — Agent Implementation (Hours 1–3) — PARALLEL

*All 4 people work simultaneously on their agent section in `agents.py`*

---

### Task 2.1 — Agent 1: Literature Finder
**Owner:** Person 1  
**Depends on:** Task 1.2  
**File:** `agents.py` (top section)

- [ ] Implement `LITERATURE_FINDER_PROMPT` system prompt
  - Must instruct model to extract 3–5 search terms first
  - Must specify exact JSON output format
  - Must instruct model to prioritize papers from 2018+
- [ ] Implement `literature_finder(state: ResearchState) -> ResearchState`
  - Call Claude API with `web_search` tool enabled
  - Extract text blocks from response (filter `block.type == "text"`)
  - Parse JSON response into `state["papers"]` and `state["search_terms"]`
  - Add try/except around JSON parse with fallback to empty lists
  - Set `state["current_stage"] = "literature_finder"` at start of function
- [ ] Write a standalone test:
  ```python
  from agents import literature_finder
  from state import ResearchState
  test_state = {**empty_state, "abstract": "menin inhibitors NPM1-mutant AML HOX gene expression"}
  result = literature_finder(test_state)
  assert len(result["papers"]) >= 3
  assert len(result["search_terms"]) >= 2
  print("Agent 1 OK:", len(result["papers"]), "papers found")
  ```

**Done when:** Standalone test passes and returns ≥3 papers with titles and URLs

---

### Task 2.2 — Agent 2: Results Extractor
**Owner:** Person 2  
**Depends on:** Task 1.2  
**File:** `agents.py` (second section)

- [ ] Implement `RESULTS_EXTRACTOR_PROMPT` system prompt
  - Must instruct model to preserve verbatim numerical findings
  - Must specify exact JSON output format with all ExtractedResult fields
  - Must instruct model to skip inaccessible URLs gracefully
- [ ] Implement `results_extractor(state: ResearchState) -> ResearchState`
  - Serialize `state["papers"]` to JSON string for the prompt
  - Call Claude API with `web_search` tool enabled (for fetching paper content)
  - Extract and parse JSON response into `state["extracted_results"]`
  - Add try/except around JSON parse
  - Set `state["current_stage"] = "results_extractor"` at start
- [ ] Write a standalone test using mock papers:
  ```python
  mock_papers = [{"title": "Test Paper", "url": "https://pubmed.ncbi.nlm.nih.gov/...", "abstract": "...", "relevance_score": 0.9}]
  test_state = {**empty_state, "papers": mock_papers}
  result = results_extractor(test_state)
  assert len(result["extracted_results"]) > 0
  assert "key_findings" in result["extracted_results"][0]
  print("Agent 2 OK")
  ```

**Done when:** Standalone test passes and returns at least 1 ExtractedResult with key_findings

---

### Task 2.3 — Agent 3: Initial Analysis + Final Recommendation
**Owner:** Person 4  
**Depends on:** Task 1.2  
**File:** `agents.py` (third section) + `app.py`

**Part A — Initial Analysis Agent:**
- [ ] Implement `INITIAL_ANALYSIS_PROMPT` system prompt
  - Must instruct model to note contradictions explicitly
  - Must specify JSON output: `{ initial_synthesis, identified_gaps }`
- [ ] Implement `initial_analysis_agent(state: ResearchState) -> ResearchState`
  - Serialize `state["extracted_results"]` for the prompt
  - Parse response into `state["initial_synthesis"]` and `state["identified_gaps"]`
  - Initialize `state["debate_rounds"] = []` and `state["current_round"] = 0`
  - Set `state["current_stage"] = "initial_analysis"`
- [ ] Write standalone test using mock extracted_results

**Part B — Streamlit App skeleton:**
- [ ] Create `app.py` with:
  - Page config (title, icon, layout="wide")
  - Dark theme CSS block (IBM Plex Mono + IBM Plex Sans, color variables)
  - Header section (LabOS title + subtitle)
  - Abstract text_area input
  - Launch button (disabled when empty)
  - Pipeline status bar (7 placeholder cards)
  - Placeholder results sections (Papers, Initial Analysis, Debate Rounds ×3, Final)
- [ ] Verify `streamlit run app.py` renders without errors

**Done when:** Analysis agent test passes AND `streamlit run app.py` shows the UI skeleton

---

### Task 2.4 — Debate Agents + LangGraph Graph
**Owner:** Person 3  
**Depends on:** Task 1.2  
**File:** `agents.py` (debate section) + `graph.py`

**Part A — Three Debate Agents:**
- [ ] Implement `CRITIC_PROMPT`
  - Must instruct model to cite specific paper titles
  - Must target: sample size, confounders, overgeneralization, statistics
  - Plain text output (no JSON)
- [ ] Implement `critic_agent(state: ResearchState) -> str`
  - Get current analysis: `debate_rounds[-1].analysis_update` if rounds exist, else `initial_synthesis`
  - No tools (reasoning only)
  - Return raw text response

- [ ] Implement `RESULTS_REEVALUATOR_PROMPT`
  - Must instruct model to explicitly confirm / refute / partially validate each concern
  - Plain text output
- [ ] Implement `results_reevaluator(state: ResearchState, critic_feedback: str) -> str`

- [ ] Implement `ANALYSIS_REFINER_PROMPT`
  - Must instruct model to state what changed from previous round and why
  - Plain text output
- [ ] Implement `analysis_refiner(state, critic_feedback, results_response) -> str`

- [ ] Implement `FINAL_RECOMMENDATION_PROMPT`
  - JSON output: `{ final_recommendation, confidence_level, action_items, caveats }`
  - confidence_level must be exactly: "High", "Moderate", or "Low"
- [ ] Implement `final_recommendation_agent(state: ResearchState) -> ResearchState`

**Part B — LangGraph Graph:**
- [ ] Implement `debate_round_node(state: ResearchState) -> ResearchState`
  - Calls critic_agent → results_reevaluator → analysis_refiner in sequence
  - Appends DebateRound to `state["debate_rounds"]`
  - Increments `state["current_round"]`
  - Sets `state["current_stage"]` to `f"debate_round_{state['current_round']}"`
- [ ] Implement `should_continue_debate(state) -> str` returning "debate" or "finalize"
- [ ] Implement `build_graph() -> CompiledGraph`
  - Add all 5 nodes
  - Set entry point to `literature_finder`
  - Add linear edges: 1→2→2.5→3→debate
  - Add conditional edges from debate node
  - Add edge from final_recommendation to END
  - Return `graph.compile()`
- [ ] Implement `run_research(abstract: str) -> ResearchState`
  - Build initial state with all fields initialized to empty defaults
  - Invoke compiled graph
  - Return final state
- [ ] Test standalone: `python graph.py` using the menin inhibitor abstract
  - Should complete 3 debate rounds
  - Should print final recommendation with confidence level

**Done when:** `python graph.py` runs end-to-end and prints a final recommendation

---

## Phase 3 — Integration (Hour 4) — Person 3 leads, others assist

### Task 3.1 — Wire Graph to Streamlit
**Owner:** Person 3 + Person 4  
**Depends on:** Tasks 2.1–2.4

- [ ] Import `run_research` from `graph.py` into `app.py`
- [ ] Wire launch button to call `run_research(abstract)`
- [ ] Pass final state to all rendering functions
- [ ] Verify full pipeline runs from UI input to displayed results
- [ ] Test with menin inhibitor demo abstract

**Done when:** Full pipeline runs from Streamlit UI without errors

---

### Task 3.2 — Integration Testing
**Owner:** All team  
**Depends on:** Task 3.1

- [ ] Run full pipeline with demo abstract — verify all 7 stages complete
- [ ] Check `state["papers"]` has 5–10 entries
- [ ] Check `state["extracted_results"]` has at least 3 entries
- [ ] Check `state["debate_rounds"]` has exactly 3 entries
- [ ] Check `state["confidence_level"]` is one of: "High", "Moderate", "Low"
- [ ] Check `state["action_items"]` has 2–4 items
- [ ] Verify UI shows all sections populated
- [ ] Test with a second, different abstract to confirm generalization

**Done when:** Both test abstracts produce complete outputs with all sections populated

---

## Phase 4 — UI Polish (Hours 5–6) — Person 4 leads

### Task 4.1 — Results Rendering
**Owner:** Person 4  
**Depends on:** Task 3.1

- [ ] Implement `render_results(state: ResearchState)` function
  - Papers section: collapsible, shows title + truncated abstract + URL link per paper
  - Initial analysis section: collapsible, shows synthesis + identified gaps as bullet list
  - Debate rounds: 3 collapsible sections, color-coded (red/blue/green per agent)
  - Final recommendation: always expanded, prominent card with confidence badge
  - Action items (left col) + Caveats (right col) below final rec
- [ ] Implement `render_pipeline(current_stage, state)` function
  - 7 cards in a row (use `st.columns(7)`)
  - Active stage: blue border + glow
  - Completed stages: green border
  - Inactive stages: dark border
- [ ] Add "Run New Analysis" button that resets `st.session_state`

**Done when:** All sections render correctly with the demo abstract output

---

### Task 4.2 — Error Handling in UI
**Owner:** Person 4  
**Depends on:** Task 4.1

- [ ] Wrap `run_research()` call in try/except in app.py
- [ ] Show `st.error()` with descriptive message if pipeline raises
- [ ] Check `state.get("error")` and show warning if set but pipeline continued
- [ ] Add loading spinner during pipeline execution
- [ ] Ensure partial results still display even if pipeline errors mid-run

**Done when:** Deliberately passing a garbage abstract produces an error message, not a crash

---

## Phase 5 — Demo Prep (Hours 7–8) — ALL TEAM

### Task 5.1 — Prompt Tuning
**Owner:** All  
**Depends on:** Task 3.2

- [ ] Run 2–3 test abstracts across different domains (not just menin)
- [ ] Identify any agents producing malformed JSON — fix system prompts
- [ ] Verify Critic agent is actually challenging (not just agreeing)
- [ ] Verify Analysis Refiner is updating conclusions, not just restating them
- [ ] Tune prompts if any agent output is too short (<2 paragraphs)

---

### Task 5.2 — Demo Script
**Owner:** Team lead  
**Depends on:** Task 5.1

- [ ] Prepare 2 demo abstracts:
  - Primary: menin inhibitors / NPM1-mutant AML (preloaded in UI for demo)
  - Backup: a different domain (e.g., climate, materials science)
- [ ] Practice 2-minute demo walkthrough:
  1. Paste abstract (10 sec)
  2. Show Agent 1 finding papers (20 sec)
  3. Show Agent 2 extracting results (20 sec)
  4. Show debate round 1 — Critic challenges (30 sec)
  5. Show debate round 2 — position updating (20 sec)
  6. Show final recommendation + confidence (20 sec)
- [ ] Verify demo runs cleanly in under 3 minutes end-to-end

---

### Task 5.3 — Kiro Pitch Integration
**Owner:** Team lead  
**Depends on:** Task 5.2

- [ ] Screenshot or screen-record Kiro generating the spec from the initial prompt
- [ ] Be ready to show judges: requirements.md, design.md, tasks.md as artifacts
- [ ] Prepare one line: *"We used Kiro's spec-driven development to go from idea to production in 8 hours — here's the spec it generated"*

---

## Task Dependency Graph

```
1.1 (Setup)
 └─► 1.2 (State contract)
      ├─► 2.1 (Agent 1)   ──────────────────────────┐
      ├─► 2.2 (Agent 2)   ──────────────────────────┤
      ├─► 2.3 (Agent 3 + UI skeleton)  ─────────────┤
      └─► 2.4 (Debate agents + LangGraph) ───────────┤
                                                      ▼
                                               3.1 (Integration)
                                                      │
                                               3.2 (Integration tests)
                                                      │
                                               4.1 (UI polish)
                                                      │
                                               4.2 (Error handling)
                                                      │
                                         5.1 → 5.2 → 5.3 (Demo prep)
```

---

## Quick Reference — Who Owns What

| Person | Files | Tasks |
|--------|-------|-------|
| Person 1 | `agents.py` (literature_finder section) | 1.1, 1.2, 2.1, 3.2, 5.1 |
| Person 2 | `agents.py` (results_extractor section) | 1.1, 1.2, 2.2, 3.2, 5.1 |
| Person 3 | `agents.py` (debate section), `graph.py` | 1.1, 1.2, 2.4, 3.1, 3.2, 5.1 |
| Person 4 | `agents.py` (initial_analysis section), `app.py` | 1.1, 1.2, 2.3, 3.2, 4.1, 4.2, 5.1 |
