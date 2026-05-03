# Bugfix Requirements Document

## Introduction

The FastAPI server (`research_lab/server.py`) fails when handling POST `/api/analyze` requests, while the standalone pipeline runner (`run_pipeline.py`) works correctly. The server routes requests through `graph.py` → `agents/literature.py` → `agents/hypothesis.py` → `agents/orchestrator.py`, all of which contain four distinct defects that prevent the pipeline from completing successfully. The standalone runner bypasses these agents entirely, calling `literature.py` and `rag.py` directly with the correct Groq model, which is why it succeeds.

The four defects are:
1. All three agent files (`agents/literature.py`, `agents/hypothesis.py`, `agents/orchestrator.py`) use the invalid Groq model name `"openai/gpt-oss-20b"` instead of the working model `"llama-3.3-70b-versatile"`.
2. `agents/literature.py` passes `Paper` TypedDicts (with `title`, `url`, `abstract`, `relevance_score` fields) to `extract_results_threaded()`, which expects raw PubMed paper dicts (with `pmid`, `authors`, `journal`, `year` fields), causing extraction failures.
3. `graph.py`'s `run_research()` initialises `ResearchState` without the `"peer_review"` key, which is a required field in the `ResearchState` TypedDict.
4. `server.py` inserts `research_lab/` into `sys.path`, but `graph.py` and its agent imports rely on that path being set before any sub-imports resolve, creating a fragile import ordering dependency that can fail depending on execution context.

---

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the server calls `agents/literature.py`, `agents/hypothesis.py`, or `agents/orchestrator.py` to process a request THEN the system raises a Groq API error because the model name `"openai/gpt-oss-20b"` is not a valid Groq model identifier.

1.2 WHEN `agents/literature.py` calls `extract_results_threaded(papers, progress)` after mapping raw PubMed results to `Paper` TypedDicts THEN the system passes dicts missing `pmid`, `authors`, `journal`, and `year` fields, causing the extraction function to produce empty or fallback results for every paper.

1.3 WHEN `graph.py`'s `run_research()` constructs the initial `ResearchState` dict THEN the system omits the `"peer_review"` key, producing a TypedDict that is structurally incomplete and may raise a `KeyError` when the `peer_review_node` attempts to write to `state["peer_review"]`.

1.4 WHEN `server.py` is launched from the repository root (e.g. `python3 research_lab/server.py`) and `graph.py` imports `from state import ...` and `from agents.literature import ...` THEN the system may fail to resolve those imports if the `sys.path` insertion in `server.py` has not propagated to all nested import contexts before the modules are loaded.

### Expected Behavior (Correct)

2.1 WHEN the server calls any agent that uses the Groq client THEN the system SHALL use the valid model name `"llama-3.3-70b-versatile"` (matching the working `run_pipeline.py`) so that all Groq API calls succeed.

2.2 WHEN `agents/literature.py` calls `extract_results_threaded()` THEN the system SHALL pass the original raw PubMed paper dicts (containing `pmid`, `authors`, `journal`, `year`, and `abstract`) rather than the mapped `Paper` TypedDicts, so that extraction produces complete structured results for every paper.

2.3 WHEN `graph.py`'s `run_research()` constructs the initial `ResearchState` THEN the system SHALL include `"peer_review": None` in the initial dict so that the state is fully initialised and the `peer_review_node` can write its output without a `KeyError`.

2.4 WHEN `server.py` sets up the Python path THEN the system SHALL ensure that `research_lab/` is on `sys.path` before any module from that package is imported, so that all relative-style imports in `graph.py` and its agents resolve correctly regardless of the working directory from which the server is started.

### Unchanged Behavior (Regression Prevention)

3.1 WHEN `run_pipeline.py` is executed as a standalone script THEN the system SHALL CONTINUE TO call `find_literature()` and `extract_and_build_rag()` directly and complete the Phase 1 pipeline successfully without any changes to its behaviour.

3.2 WHEN `agents/literature.py` maps raw PubMed papers to `Paper` TypedDicts for the `LiteratureOutput.papers` list THEN the system SHALL CONTINUE TO produce `Paper` objects with `title`, `url`, `abstract`, and `relevance_score` fields as required by the `state.py` contract.

3.3 WHEN the Groq client is used in `literature.py` for search-term extraction THEN the system SHALL CONTINUE TO use `"llama-3.3-70b-versatile"` as it already does, with no change to that file.

3.4 WHEN `rag.py`'s `extract_results_threaded()` receives raw PubMed paper dicts THEN the system SHALL CONTINUE TO extract `key_findings`, `methods`, `sample_size`, `limitations`, and `relevance` fields using `"llama-3.3-70b-versatile"` via Groq, with no change to that function's logic.

3.5 WHEN the LangGraph pipeline completes all stages (literature → hypothesis → procedure → peer review → synthesis) THEN the system SHALL CONTINUE TO return a fully populated `ResearchState` dict from `run_research()` that the server serialises and returns as JSON.

---

## Bug Condition Pseudocode

**Bug Condition Function** — identifies requests that trigger the server failure:

```pascal
FUNCTION isBugCondition(X)
  INPUT: X of type AnalyzeRequest (POST /api/analyze with a valid abstract)
  OUTPUT: boolean

  // Any request routed through the server triggers at least one of the four defects
  RETURN X is processed via server.py → graph.py → agents/
END FUNCTION
```

**Property: Fix Checking**

```pascal
FOR ALL X WHERE isBugCondition(X) DO
  result ← run_research'(X.abstract)   // F' = fixed pipeline
  ASSERT result is a complete ResearchState with no exception raised
  ASSERT result["peer_review"] is not None or gracefully handled
  ASSERT all Groq API calls used model "llama-3.3-70b-versatile"
  ASSERT extract_results_threaded received raw PubMed dicts with pmid/authors/journal/year
END FOR
```

**Property: Preservation Checking**

```pascal
FOR ALL X WHERE NOT isBugCondition(X) DO
  // i.e. requests handled by run_pipeline.py directly
  ASSERT F(X) = F'(X)   // standalone pipeline output is unchanged
END FOR
```
