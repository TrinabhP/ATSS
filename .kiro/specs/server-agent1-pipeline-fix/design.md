# Server / Agent-1 Pipeline Fix — Bugfix Design

## Overview

The FastAPI server (`research_lab/server.py`) fails on every POST `/api/analyze` request while
the standalone runner (`run_pipeline.py`) succeeds. Four independent defects in the server-side
agent files cause the failure. The fix is surgical: change three model-name string literals,
reorder two variable references in one function, add one key to one dict, and verify the
`sys.path` / `.env` setup in `server.py`. No logic is restructured; no interfaces change.

---

## Glossary

- **Bug_Condition (C)**: Any request routed through `server.py → graph.py → agents/` — all four
  defects are triggered on this path.
- **Property (P)**: The fixed pipeline SHALL complete without raising an exception and SHALL
  return a fully-populated `ResearchState` dict.
- **Preservation**: The standalone `run_pipeline.py` path (which calls `literature.py` and
  `rag.py` directly) must be completely unaffected.
- **`_SYNTHESIS_MODEL` / `MODEL`**: Module-level constants in the three agent files that name
  the Groq model to use for all LLM calls.
- **`extract_results_threaded(papers, progress)`**: Function in `rag.py` that expects raw
  PubMed dicts with `pmid`, `authors`, `journal`, `year`, and `abstract` keys.
- **`Paper` TypedDict**: The `state.py` contract type with `title`, `url`, `abstract`, and
  `relevance_score` keys — **not** accepted by `extract_results_threaded()`.
- **`ResearchState`**: The top-level LangGraph state TypedDict defined in `state.py`; requires
  a `peer_review` key.
- **`run_research()`**: The public entry point in `graph.py` that builds and invokes the
  LangGraph pipeline.

---

## Bug Details

### Bug Condition

The bug manifests whenever a request is processed through the server path. All four defects
are present simultaneously; any one of them is sufficient to cause a failure.

**Formal Specification:**

```
FUNCTION isBugCondition(X)
  INPUT: X of type AnalyzeRequest (POST /api/analyze with a valid abstract string)
  OUTPUT: boolean

  RETURN X is routed via server.py → graph.py → agents/
         // Equivalently: NOT (X is run directly via run_pipeline.py)
END FUNCTION
```

### Examples

- **Fix 1 — model name**: Sending any abstract via the server causes a Groq `BadRequestError`
  because `"openai/gpt-oss-20b"` is not a valid Groq model ID. Expected: model
  `"llama-3.3-70b-versatile"` is used, matching `run_pipeline.py` and `rag.py`.

- **Fix 2 — wrong dict type**: After `run_literature_agent()` maps raw papers to `Paper`
  TypedDicts, it passes those to `extract_results_threaded()`. That function accesses
  `paper['pmid']`, `paper['authors']`, `paper['journal']`, `paper['year']` — keys absent from
  `Paper` — so every paper falls through to the fallback branch and returns empty findings.
  Expected: `raw_papers` (the original list from `find_literature()`) is passed instead.

- **Fix 3 — missing `peer_review` key**: `run_research()` builds `initial` without
  `"peer_review"`. When `peer_review_node` writes `state["peer_review"] = result`, LangGraph
  may raise a `KeyError` or produce a structurally invalid state. Expected: `"peer_review": None`
  is present in `initial` from the start.

- **Fix 4 — `sys.path` / `.env` robustness**: `server.py` already inserts
  `os.path.dirname(os.path.abspath(__file__))` (i.e. `research_lab/`) into `sys.path` and
  manually parses `.env` from the repo root. This is correct for `python3 research_lab/server.py`
  run from the repo root. Verification confirms no change is needed; the existing code is sound.

---

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**

- `run_pipeline.py` calls `find_literature()` and `extract_and_build_rag()` directly and must
  continue to work exactly as before.
- `rag.py`'s `extract_results_threaded()` already uses `"llama-3.3-70b-versatile"` and must
  not be modified.
- `literature.py`'s `extract_search_terms()` already uses `"llama-3.3-70b-versatile"` and must
  not be modified.
- `agents/literature.py`'s mapping of raw PubMed papers to `Paper` TypedDicts for the
  `LiteratureOutput.papers` field must continue to produce objects with `title`, `url`,
  `abstract`, and `relevance_score`.
- The full LangGraph pipeline (literature → hypothesis → procedure → peer review → synthesis)
  must continue to return a complete `ResearchState` dict that the server serialises as JSON.

**Scope:**

All code paths that do NOT go through `server.py → graph.py → agents/` are completely
unaffected. This includes:

- Direct execution of `run_pipeline.py`
- Direct calls to `find_literature()` or `extract_and_build_rag()`
- Any test that exercises `rag.py` or `literature.py` in isolation

---

## Hypothesized Root Cause

1. **Copy-paste of a non-Groq model name (Fix 1)**: The three agent files were written or
   scaffolded with `"openai/gpt-oss-20b"` — a model identifier from a different provider's
   API — rather than the Groq model name used in the working `rag.py` and `literature.py`.

2. **Premature type conversion before extraction (Fix 2)**: `run_literature_agent()` was
   refactored to use `raw_papers` for the `extract_results_threaded()` call, but an earlier
   version of the function converted to `Paper` TypedDicts first and passed those. The
   conversion step was moved up without updating the argument passed to the extractor.

3. **Incomplete initial state dict (Fix 3)**: `run_research()` was written before
   `peer_review` was added to `ResearchState`, or the key was simply omitted. The `state.py`
   `__main__` block at the bottom of the file also omits `peer_review`, confirming this was
   a consistent oversight.

4. **`sys.path` / `.env` setup (Fix 4)**: The existing `server.py` code is already correct.
   It inserts `research_lab/` (the directory containing `server.py`) into `sys.path[0]` before
   any local imports, and it manually reads `.env` from the repo root using
   `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`. No change is required.

---

## Correctness Properties

Property 1: Bug Condition — Server Pipeline Completes Without Error

_For any_ `AnalyzeRequest` where `isBugCondition` holds (i.e. the request is routed through
`server.py → graph.py → agents/`), the fixed `run_research()` function SHALL return a
`ResearchState` dict without raising an exception, with all Groq calls using model
`"llama-3.3-70b-versatile"`, `extract_results_threaded()` receiving raw PubMed dicts, and
`state["peer_review"]` present from initialisation.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

Property 2: Preservation — Standalone Pipeline Unchanged

_For any_ input where `isBugCondition` does NOT hold (i.e. the request is processed by
`run_pipeline.py` directly), the fixed codebase SHALL produce exactly the same output as the
original codebase, preserving all behaviour of `find_literature()`, `extract_and_build_rag()`,
and `rag.py`'s `extract_results_threaded()`.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

---

## Fix Implementation

### Fix 1 — Wrong Groq model name

**Files:** `agents/literature.py`, `agents/hypothesis.py`, `agents/orchestrator.py`

#### `agents/literature.py`

```python
# BEFORE (line 14)
_SYNTHESIS_MODEL = "openai/gpt-oss-20b"

# AFTER
_SYNTHESIS_MODEL = "llama-3.3-70b-versatile"
```

#### `agents/hypothesis.py`

```python
# BEFORE (line 11)
MODEL = "openai/gpt-oss-20b"

# AFTER
MODEL = "llama-3.3-70b-versatile"
```

#### `agents/orchestrator.py`

```python
# BEFORE (line 19)
MODEL = "openai/gpt-oss-20b"

# AFTER
MODEL = "llama-3.3-70b-versatile"
```

---

### Fix 2 — Wrong dict type passed to `extract_results_threaded()`

**File:** `agents/literature.py`, function `run_literature_agent()`

The current code maps `raw_papers` → `Paper` TypedDicts first, then passes `papers` (the
mapped list) to `extract_results_threaded()`. The fix passes `raw_papers` (the original list
from `find_literature()`) to the extractor, and keeps the `Paper` mapping only for the
`LiteratureOutput.papers` field.

```python
# BEFORE — Step 3 in run_literature_agent()
    # Step 3: Parallel Gemini extraction
    progress = ProgressTracker()
    extracted = extract_results_threaded(papers, progress)   # ← passes Paper TypedDicts

# AFTER — Step 3 in run_literature_agent()
    # Step 3: Parallel extraction — must use raw_papers (has pmid/authors/journal/year)
    progress = ProgressTracker()
    extracted = extract_results_threaded(raw_papers, progress)  # ← passes raw PubMed dicts
```

No other lines in `run_literature_agent()` change. The `papers` variable (mapped `Paper`
TypedDicts) is still used unchanged for `LiteratureOutput(papers=papers, ...)`.

---

### Fix 3 — Missing `peer_review` key in initial `ResearchState`

**File:** `graph.py`, function `run_research()`

```python
# BEFORE — initial dict in run_research()
    initial: ResearchState = {
        "abstract": abstract[:4000],
        "current_stage": "",
        "orchestrator_messages": [],
        "literature": None,
        "hypothesis": None,
        "procedure": None,
        # "peer_review" key is absent
        "reviews": [],
        "final_recommendation": None,
        "confidence_level": None,
        "action_items": [],
        "caveats": [],
        "error": None,
    }

# AFTER — initial dict in run_research()
    initial: ResearchState = {
        "abstract": abstract[:4000],
        "current_stage": "",
        "orchestrator_messages": [],
        "literature": None,
        "hypothesis": None,
        "procedure": None,
        "peer_review": None,          # ← added
        "reviews": [],
        "final_recommendation": None,
        "confidence_level": None,
        "action_items": [],
        "caveats": [],
        "error": None,
    }
```

---

### Fix 4 — `sys.path` / `.env` setup in `server.py`

**File:** `research_lab/server.py`

**Verdict: No change required.** The existing code is already correct for
`python3 research_lab/server.py` run from the repo root:

```python
# Already present and correct in server.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# → inserts the absolute path of research_lab/ before any local imports

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env_path = os.path.join(_repo_root, ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            ...
            os.environ.setdefault(_key.strip(), _val.strip())
# → reads ATSS/.env from the repo root regardless of cwd
```

`os.path.abspath(__file__)` resolves to the absolute path of `server.py` at import time, so
the path computation is cwd-independent. The `os.environ.setdefault` call means existing
environment variables (e.g. from a shell export) are never overwritten. No fix needed.

---

## Testing Strategy

### Validation Approach

Two-phase approach: first run exploratory tests against the **unfixed** code to confirm the
root cause, then run fix-checking and preservation tests against the **fixed** code.

---

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate each defect on unfixed code and confirm the
root cause analysis.

**Test Plan**: Write unit tests that call the affected functions directly (bypassing the full
server stack) and assert the correct outcomes. Run on unfixed code to observe failures.

**Test Cases**:

1. **Model name test** (Fix 1): Call `run_hypothesis_agent()` with a minimal `LiteratureOutput`
   and a short abstract. Assert no `BadRequestError` is raised and the returned
   `HypothesisOutput` has a non-empty `hypothesis` field.
   _(Will fail on unfixed code with a Groq API error for unknown model.)_

2. **Dict type test** (Fix 2): Call `extract_results_threaded()` with a list of `Paper`
   TypedDicts (missing `pmid`, `authors`, `journal`, `year`). Assert that the returned dicts
   contain non-empty `key_findings`.
   _(Will fail on unfixed code — every paper falls to the fallback with empty findings.)_

3. **State key test** (Fix 3): Construct the `initial` dict as written in the unfixed
   `run_research()` and assert `"peer_review" in initial`.
   _(Will fail on unfixed code — key is absent.)_

4. **`sys.path` test** (Fix 4): Import `graph` from a subprocess launched as
   `python3 research_lab/server.py --dry-run` from the repo root. Assert no `ImportError`.
   _(Expected to pass on both unfixed and fixed code — no change needed.)_

**Expected Counterexamples**:

- Fix 1: `groq.BadRequestError: model 'openai/gpt-oss-20b' not found`
- Fix 2: All extracted results have `key_findings: []` (fallback path triggered by `KeyError`
  on `paper['pmid']`)
- Fix 3: `AssertionError` — `"peer_review"` not in `initial`

---

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed pipeline produces
the expected behaviour.

**Pseudocode:**

```
FOR ALL X WHERE isBugCondition(X) DO
  result := run_research_fixed(X.abstract)
  ASSERT no exception raised
  ASSERT result["peer_review"] is not None OR gracefully set to None by peer_review_node
  ASSERT all Groq calls used model "llama-3.3-70b-versatile"
  ASSERT extract_results_threaded received dicts with "pmid" key present
END FOR
```

---

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed codebase
produces the same result as the original.

**Pseudocode:**

```
FOR ALL X WHERE NOT isBugCondition(X) DO
  ASSERT run_pipeline_original(X) = run_pipeline_fixed(X)
END FOR
```

**Testing Approach**: Property-based testing is appropriate here because:

- `run_pipeline.py` accepts arbitrary abstract strings; PBT can generate many variants.
- The preservation guarantee must hold across the full input domain, not just a few examples.
- PBT libraries (e.g. Hypothesis) can shrink failing inputs to minimal counterexamples.

**Test Cases**:

1. **`find_literature()` preservation**: Generate random abstract strings; assert
   `find_literature()` returns the same structure before and after the fix (it is not touched).

2. **`extract_results_threaded()` preservation**: Pass raw PubMed dicts (as `run_pipeline.py`
   does); assert the function returns the same fields and non-empty `key_findings` before and
   after the fix (it is not touched).

3. **`Paper` TypedDict preservation**: Assert that `run_literature_agent()` still populates
   `LiteratureOutput.papers` with `Paper` objects containing `title`, `url`, `abstract`, and
   `relevance_score` after Fix 2 is applied.

---

### Unit Tests

- Test that `_SYNTHESIS_MODEL` / `MODEL` equals `"llama-3.3-70b-versatile"` in all three
  agent modules after the fix.
- Test that `run_literature_agent()` passes a list of dicts with `"pmid"` keys to
  `extract_results_threaded()` (mock the function and inspect the call argument).
- Test that `run_research()` returns an `initial` dict containing `"peer_review"`.
- Test that `server.py`'s `sys.path[0]` equals the absolute path of `research_lab/` when
  the module is loaded.

### Property-Based Tests

- Generate random abstract strings and assert `run_literature_agent()` always returns a
  `LiteratureOutput` with `papers` containing only `Paper`-shaped dicts (has `title`, `url`,
  `abstract`, `relevance_score`).
- Generate random lists of raw PubMed dicts and assert `extract_results_threaded()` always
  returns one result per input paper with a `pmid` field matching the input.
- Generate random `ResearchState`-compatible dicts and assert `run_research()` never raises
  a `KeyError` for `"peer_review"`.

### Integration Tests

- Start the FastAPI server and POST a short abstract to `/api/analyze`; assert HTTP 200 and
  a JSON body containing `"peer_review"`, `"literature"`, `"hypothesis"`, `"procedure"`, and
  `"final_recommendation"` keys.
- Run `run_pipeline.py` with a short abstract and assert it exits 0 and writes
  `agent1_output.json` and `agent2_output.json` (regression guard).
- Assert the `/health` endpoint returns `{"status": "ok"}` after the server starts.
