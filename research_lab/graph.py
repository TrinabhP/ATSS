"""
graph.py — LangGraph wiring for LabOS Research Analysis Engine.
Imports from agents/ and state.py only. No Streamlit imports.
"""

from datetime import datetime
from typing import List

from langgraph.graph import StateGraph, END

from state import ResearchState, LiteratureOutput, CriticReview
from literature import run_literature_agent
from agents.hypothesis import run_hypothesis_agent
from agents.procedure import run_procedure_agent
from agents.orchestrator import (
    review_literature,
    review_hypothesis,
    review_procedure,
    synthesize_final,
)

# ── Constants ──────────────────────────────────────────────────────────────────

MAX_REVISIONS = 1

# Per-agent revision caps (override MAX_REVISIONS for specific agents)
LITERATURE_MAX_REVISIONS = 0   # Agent 1: no retries — 3 papers + Ragie is sufficient
HYPOTHESIS_MAX_REVISIONS = 0   # Agent 2: no retries — self-review handles quality internally
PROCEDURE_MAX_REVISIONS = 0    # Agent 3: no retries — single pass


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_latest_feedback(reviews: List[CriticReview], agent_name: str) -> str:
    """Returns the most recent failed review feedback for an agent, or empty string."""
    agent_reviews = [r for r in reviews if r["agent_name"] == agent_name and not r["passed"]]
    return agent_reviews[-1]["feedback"] if agent_reviews else ""


def _get_latest_review(reviews: List[CriticReview], agent_name: str):
    """Returns the most recent review for an agent (passed or failed), or None."""
    agent_reviews = [r for r in reviews if r["agent_name"] == agent_name]
    return agent_reviews[-1] if agent_reviews else None


def _now() -> str:
    return datetime.now().isoformat()


# ── Nodes ──────────────────────────────────────────────────────────────────────

def dispatch_literature(state: ResearchState) -> ResearchState:
    print(f"\n🔬 [GRAPH] Starting literature agent...")
    state["current_stage"] = "literature_running"
    feedback = get_latest_feedback(state["reviews"], "literature")

    prev_count = state["literature"]["revision_count"] if state["literature"] else -1
    new_count = prev_count + 1

    try:
        result = run_literature_agent(state["abstract"], feedback)
        result["revision_count"] = new_count
        state["literature"] = result
        state["orchestrator_messages"].append(
            f"[{_now()}] Literature agent completed (revision {new_count})"
        )
    except NotImplementedError:
        # Agent 1 stub — allow rest of graph to be tested
        state["current_stage"] = "literature_pending"
        state["error"] = "Agent 1 not yet integrated"
        state["literature"] = LiteratureOutput(
            papers=[],
            analyses=[],
            search_terms=[],
            synthesis="",
            revision_count=MAX_REVISIONS,  # Prevents retry loop
        )
        state["orchestrator_messages"].append(
            f"[{_now()}] Literature agent not yet integrated (stub placeholder)"
        )
    except Exception as e:
        state["error"] = f"Literature agent error: {e}"
        state["literature"] = LiteratureOutput(
            papers=[], analyses=[], search_terms=[], synthesis="", revision_count=MAX_REVISIONS
        )
        state["orchestrator_messages"].append(f"[{_now()}] Literature agent failed: {e}")

    return state


def review_literature_node(state: ResearchState) -> ResearchState:
    print(f"📋 [GRAPH] Reviewing literature output...")
    state["current_stage"] = "literature_review"
    review = review_literature(state["literature"], state["abstract"])
    review["timestamp"] = _now()
    state["reviews"] = state["reviews"] + [review]

    if review["passed"]:
        state["orchestrator_messages"].append(
            f"[{_now()}] Literature passed review"
        )
    else:
        snippet = review["feedback"][:120]
        state["orchestrator_messages"].append(
            f"[{_now()}] Literature failed review: {snippet}..."
        )
    return state


def dispatch_hypothesis(state: ResearchState) -> ResearchState:
    print(f"\n🧪 [GRAPH] Starting hypothesis agent...")
    state["current_stage"] = "hypothesis_running"
    feedback = get_latest_feedback(state["reviews"], "hypothesis")

    prev_count = state["hypothesis"]["revision_count"] if state["hypothesis"] else -1
    new_count = prev_count + 1

    try:
        result = run_hypothesis_agent(
            state["literature"],
            state["abstract"],
            critic_feedback=feedback,
            revision_count=new_count,
        )
        state["hypothesis"] = result
        state["orchestrator_messages"].append(
            f"[{_now()}] Hypothesis agent completed (revision {new_count})"
        )
    except Exception as e:
        state["error"] = f"Hypothesis agent error: {e}"
        state["orchestrator_messages"].append(f"[{_now()}] Hypothesis agent failed: {e}")

    return state


def review_hypothesis_node(state: ResearchState) -> ResearchState:
    print(f"📋 [GRAPH] Reviewing hypothesis output...")
    state["current_stage"] = "hypothesis_review"

    if not state.get("hypothesis"):
        # Can't review what doesn't exist — fail gracefully
        review = CriticReview(
            agent_name="hypothesis",
            revision_number=0,
            passed=False,
            feedback="Hypothesis agent produced no output.",
            timestamp=_now(),
        )
        state["reviews"] = state["reviews"] + [review]
        state["orchestrator_messages"].append(
            f"[{_now()}] Hypothesis review skipped — no output to review"
        )
        return state

    review = review_hypothesis(state["hypothesis"], state["literature"], state["abstract"])
    review["timestamp"] = _now()
    state["reviews"] = state["reviews"] + [review]

    if review["passed"]:
        state["orchestrator_messages"].append(f"[{_now()}] Hypothesis passed review")
    else:
        snippet = review["feedback"][:120]
        state["orchestrator_messages"].append(
            f"[{_now()}] Hypothesis failed review: {snippet}..."
        )
    return state


def dispatch_procedure(state: ResearchState) -> ResearchState:
    print(f"\n📝 [GRAPH] Starting procedure agent...")
    state["current_stage"] = "procedure_running"
    feedback = get_latest_feedback(state["reviews"], "procedure")

    prev_count = state["procedure"]["revision_count"] if state["procedure"] else -1
    new_count = prev_count + 1

    try:
        result = run_procedure_agent(
            state["literature"],
            state["hypothesis"],
            state["abstract"],
            critic_feedback=feedback,
            revision_count=new_count,
        )
        state["procedure"] = result
        state["orchestrator_messages"].append(
            f"[{_now()}] Procedure agent completed (revision {new_count})"
        )
    except Exception as e:
        state["error"] = f"Procedure agent error: {e}"
        state["orchestrator_messages"].append(f"[{_now()}] Procedure agent failed: {e}")

    return state


def review_procedure_node(state: ResearchState) -> ResearchState:
    print(f"📋 [GRAPH] Reviewing procedure output...")
    state["current_stage"] = "procedure_review"

    if not state.get("procedure"):
        review = CriticReview(
            agent_name="procedure",
            revision_number=0,
            passed=False,
            feedback="Procedure agent produced no output.",
            timestamp=_now(),
        )
        state["reviews"] = state["reviews"] + [review]
        state["orchestrator_messages"].append(
            f"[{_now()}] Procedure review skipped — no output to review"
        )
        return state

    review = review_procedure(state["procedure"], state["hypothesis"], state["abstract"])
    review["timestamp"] = _now()
    state["reviews"] = state["reviews"] + [review]

    if review["passed"]:
        state["orchestrator_messages"].append(f"[{_now()}] Procedure passed review")
    else:
        snippet = review["feedback"][:120]
        state["orchestrator_messages"].append(
            f"[{_now()}] Procedure failed review: {snippet}..."
        )
    return state


def synthesize_node(state: ResearchState) -> ResearchState:
    print(f"\n🔮 [GRAPH] Running final synthesis...")
    state["current_stage"] = "synthesizing"
    try:
        rec, conf, actions, caveats = synthesize_final(state)
        state["final_recommendation"] = rec
        state["confidence_level"] = conf
        state["action_items"] = actions
        state["caveats"] = caveats
        state["orchestrator_messages"].append(
            f"[{_now()}] Final synthesis complete — confidence: {conf}"
        )
    except Exception as e:
        state["error"] = f"Synthesis error: {e}"
        state["orchestrator_messages"].append(f"[{_now()}] Synthesis failed: {e}")
    state["current_stage"] = "complete"
    return state


# ── Conditional edges ──────────────────────────────────────────────────────────

def should_retry_literature(state: ResearchState) -> str:
    latest = _get_latest_review(state["reviews"], "literature")
    lit_revisions = state["literature"]["revision_count"] if state["literature"] else 0
    if latest and not latest["passed"] and lit_revisions < LITERATURE_MAX_REVISIONS:
        return "retry_literature"
    return "run_hypothesis"


def should_retry_hypothesis(state: ResearchState) -> str:
    latest = _get_latest_review(state["reviews"], "hypothesis")
    hyp_revisions = state["hypothesis"]["revision_count"] if state["hypothesis"] else 0
    if latest and not latest["passed"] and hyp_revisions < HYPOTHESIS_MAX_REVISIONS:
        return "retry_hypothesis"
    return "run_procedure"


def should_retry_procedure(state: ResearchState) -> str:
    latest = _get_latest_review(state["reviews"], "procedure")
    proc_revisions = state["procedure"]["revision_count"] if state["procedure"] else 0
    if latest and not latest["passed"] and proc_revisions < PROCEDURE_MAX_REVISIONS:
        return "retry_procedure"
    return "synthesize"


# ── Graph builder ──────────────────────────────────────────────────────────────

def _build_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("dispatch_literature", dispatch_literature)
    graph.add_node("review_literature_node", review_literature_node)
    graph.add_node("dispatch_hypothesis", dispatch_hypothesis)
    graph.add_node("review_hypothesis_node", review_hypothesis_node)
    graph.add_node("dispatch_procedure", dispatch_procedure)
    graph.add_node("review_procedure_node", review_procedure_node)
    graph.add_node("synthesize_node", synthesize_node)

    graph.set_entry_point("dispatch_literature")

    graph.add_edge("dispatch_literature", "review_literature_node")
    graph.add_conditional_edges(
        "review_literature_node",
        should_retry_literature,
        {
            "retry_literature": "dispatch_literature",
            "run_hypothesis": "dispatch_hypothesis",
        },
    )

    graph.add_edge("dispatch_hypothesis", "review_hypothesis_node")
    graph.add_conditional_edges(
        "review_hypothesis_node",
        should_retry_hypothesis,
        {
            "retry_hypothesis": "dispatch_hypothesis",
            "run_procedure": "dispatch_procedure",
        },
    )

    graph.add_edge("dispatch_procedure", "review_procedure_node")
    graph.add_conditional_edges(
        "review_procedure_node",
        should_retry_procedure,
        {
            "retry_procedure": "dispatch_procedure",
            "synthesize": "synthesize_node",
        },
    )

    graph.add_edge("synthesize_node", END)

    return graph.compile()


# ── Public entry point ─────────────────────────────────────────────────────────

def run_research(abstract: str) -> ResearchState:
    """Run the full research pipeline and return the final state."""
    # Use the streaming version and just return the last state
    state = None
    for _stage, state in run_research_streaming(abstract):
        pass
    return state


def run_research_streaming(abstract: str):
    """
    Generator that runs the pipeline step-by-step, yielding (stage_name, state)
    after each major step completes. Used by the SSE endpoint.
    """
    state: ResearchState = {
        "abstract": abstract[:4000],
        "current_stage": "",
        "orchestrator_messages": [],
        "literature": None,
        "hypothesis": None,
        "procedure": None,
        "reviews": [],
        "final_recommendation": None,
        "confidence_level": None,
        "action_items": [],
        "caveats": [],
        "error": None,
    }

    # Step 1: Literature
    state = dispatch_literature(state)
    state = review_literature_node(state)
    yield ("literature", state)

    # Retry literature if needed
    if should_retry_literature(state) == "retry_literature":
        state = dispatch_literature(state)
        state = review_literature_node(state)
        yield ("literature_retry", state)

    # Step 2: Hypothesis
    state = dispatch_hypothesis(state)
    state = review_hypothesis_node(state)
    yield ("hypothesis", state)

    # Retry hypothesis if needed
    if should_retry_hypothesis(state) == "retry_hypothesis":
        state = dispatch_hypothesis(state)
        state = review_hypothesis_node(state)
        yield ("hypothesis_retry", state)

    # Step 3: Procedure
    state = dispatch_procedure(state)
    state = review_procedure_node(state)
    yield ("procedure", state)

    # Retry procedure if needed
    if should_retry_procedure(state) == "retry_procedure":
        state = dispatch_procedure(state)
        state = review_procedure_node(state)
        yield ("procedure_retry", state)

    # Step 4: Synthesis
    state = synthesize_node(state)
    yield ("done", state)


# ── CLI entry point ────────────────────────────────────────────────────────────

def _print_section(title: str) -> None:
    width = 64
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")


def _print_field(label: str, value: str, indent: int = 2) -> None:
    pad = " " * indent
    prefix = f"{pad}{label}: "
    # Wrap long values
    if len(value) > 80:
        print(f"{prefix}")
        for line in value.splitlines():
            print(f"{pad}  {line}")
    else:
        print(f"{prefix}{value}")


def print_results(result: ResearchState) -> None:
    """Pretty-print the full pipeline result to stdout."""

    _print_section("PIPELINE COMPLETE")
    print(f"  Stage:      {result['current_stage']}")
    print(f"  Reviews:    {len(result['reviews'])}")
    print(f"  Confidence: {result.get('confidence_level', 'N/A')}")
    if result.get("error"):
        print(f"\n  ⚠  ERROR: {result['error']}")

    # Orchestrator log
    _print_section("ORCHESTRATOR LOG")
    for msg in result["orchestrator_messages"]:
        print(f"  {msg}")

    # Review history
    _print_section("REVIEW HISTORY")
    for r in result["reviews"]:
        status = "✓ PASS" if r["passed"] else "✗ FAIL"
        print(f"  [{r['agent_name']:12s}] rev {r['revision_number']}  {status}")
        if not r["passed"] and r["feedback"]:
            for line in r["feedback"][:300].splitlines():
                print(f"               {line}")

    # Literature
    lit = result.get("literature")
    if lit:
        _print_section("LITERATURE REVIEW")
        print(f"  Papers found:  {len(lit.get('papers', []))}")
        print(f"  Search terms:  {', '.join(lit.get('search_terms', []))}")
        print(f"  Synthesis:\n")
        for line in (lit.get("synthesis") or "").splitlines():
            print(f"    {line}")

    # Hypothesis
    hyp = result.get("hypothesis")
    if hyp:
        _print_section("HYPOTHESIS")
        _print_field("H1", hyp.get("hypothesis", ""))
        _print_field("H0", hyp.get("null_hypothesis", ""))
        _print_field("Design", hyp.get("design_approach", ""))
        print(f"  Expected outcomes:")
        for o in hyp.get("expected_outcomes", []):
            print(f"    - {o}")

    # Procedure
    proc = result.get("procedure")
    if proc:
        _print_section("STUDY PROCEDURE")
        _print_field("Population N", proc.get("population_size", ""))
        _print_field("Criteria", proc.get("population_criteria", ""))
        _print_field("Design", proc.get("research_design", ""))
        _print_field("Statistics", proc.get("statistical_approach", ""))
        _print_field("Timeline", proc.get("timeline_estimate", ""))

    # Final recommendation
    _print_section("FINAL RECOMMENDATION")
    print(f"  Confidence: {result.get('confidence_level', 'N/A')}\n")
    for line in (result.get("final_recommendation") or "(none)").splitlines():
        print(f"  {line}")

    if result.get("action_items"):
        print(f"\n  Action items:")
        for item in result["action_items"]:
            print(f"    • {item}")

    if result.get("caveats"):
        print(f"\n  Caveats:")
        for c in result["caveats"]:
            print(f"    • {c}")

    print(f"\n{'=' * 64}\n")


if __name__ == "__main__":
    import sys as _sys

    DEMO_ABSTRACT = (
        "We're investigating menin inhibitors for NPM1-mutant AML. "
        "Key question: Does HOX gene expression predict treatment response to "
        "menin inhibitors in NPM1-mutant acute myeloid leukemia patients?"
    )

    abstract = " ".join(_sys.argv[1:]) if len(_sys.argv) > 1 else DEMO_ABSTRACT

    print("LabOS Research Analysis Engine")
    print(f"Abstract: {abstract[:100]}{'...' if len(abstract) > 100 else ''}\n")
    print("Running pipeline — this may take 1-3 minutes...\n")

    result = run_research(abstract)
    print_results(result)
