"""
graph.py — LangGraph wiring for LabOS Research Analysis Engine.
Imports from agents/ and state.py only. No Streamlit imports.
"""

from datetime import datetime
from typing import List

from langgraph.graph import StateGraph, END

from state import ResearchState, LiteratureOutput, CriticReview
from agents.literature import run_literature_agent
from agents.hypothesis import run_hypothesis_agent
from agents.procedure import run_procedure_agent
from agents.orchestrator import (
    review_literature,
    review_hypothesis,
    review_procedure,
    synthesize_final,
)
from agents.peer_reviewer import run_peer_review_agent

# ── Constants ──────────────────────────────────────────────────────────────────

MAX_REVISIONS = 2


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
    return state


def peer_review_node(state: ResearchState) -> ResearchState:
    state["current_stage"] = "peer_review"
    try:
        result = run_peer_review_agent(
            state["literature"],
            state["hypothesis"],
            state["procedure"],
            state["abstract"],
        )
        state["peer_review"] = result
        state["orchestrator_messages"].append(
            f"[{_now()}] Peer review complete — verdict: {result['overall_verdict']} "
            f"(reproducibility score: {result['reproducibility_score']}/10)"
        )
    except Exception as e:
        state["error"] = f"Peer review error: {e}"
        state["orchestrator_messages"].append(f"[{_now()}] Peer review failed: {e}")
    state["current_stage"] = "complete"
    return state


# ── Conditional edges ──────────────────────────────────────────────────────────

def should_retry_literature(state: ResearchState) -> str:
    latest = _get_latest_review(state["reviews"], "literature")
    lit_revisions = state["literature"]["revision_count"] if state["literature"] else 0
    if latest and not latest["passed"] and lit_revisions < MAX_REVISIONS:
        return "retry_literature"
    return "run_hypothesis"


def should_retry_hypothesis(state: ResearchState) -> str:
    latest = _get_latest_review(state["reviews"], "hypothesis")
    hyp_revisions = state["hypothesis"]["revision_count"] if state["hypothesis"] else 0
    if latest and not latest["passed"] and hyp_revisions < MAX_REVISIONS:
        return "retry_hypothesis"
    return "run_procedure"


def should_retry_procedure(state: ResearchState) -> str:
    latest = _get_latest_review(state["reviews"], "procedure")
    proc_revisions = state["procedure"]["revision_count"] if state["procedure"] else 0
    if latest and not latest["passed"] and proc_revisions < MAX_REVISIONS:
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
    graph.add_node("peer_review_node", peer_review_node)

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

    graph.add_edge("synthesize_node", "peer_review_node")
    graph.add_edge("peer_review_node", END)

    return graph.compile()


# ── Public entry point ─────────────────────────────────────────────────────────

def run_research(abstract: str) -> ResearchState:
    """Run the full research pipeline and return the final state."""
    compiled = _build_graph()

    initial: ResearchState = {
        "abstract": abstract[:4000],
        "current_stage": "",
        "orchestrator_messages": [],
        "literature": None,
        "hypothesis": None,
        "procedure": None,
        "peer_review": None,
        "reviews": [],
        "final_recommendation": None,
        "confidence_level": None,
        "action_items": [],
        "caveats": [],
        "error": None,
    }

    final_state: ResearchState = compiled.invoke(initial)
    return final_state


# ── Standalone integration test ────────────────────────────────────────────────

if __name__ == "__main__":
    DEMO_ABSTRACT = (
        "We're investigating menin inhibitors for NPM1-mutant AML. "
        "Key question: Does HOX gene expression predict treatment response to "
        "menin inhibitors in NPM1-mutant acute myeloid leukemia patients?"
    )

    print("Starting LabOS Research Analysis Engine (new architecture)...")
    print(f"Abstract: {DEMO_ABSTRACT[:80]}...\n")

    result = run_research(DEMO_ABSTRACT)

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Current stage:     {result['current_stage']}")
    print(f"Reviews completed: {len(result['reviews'])}")
    print(f"Confidence level:  {result['confidence_level']}")
    print(f"Action items:      {len(result['action_items'])}")
    print(f"Caveats:           {len(result['caveats'])}")

    if result.get("error"):
        print(f"\n[ERROR] {result['error']}")

    print("\n--- ORCHESTRATOR LOG ---")
    for msg in result["orchestrator_messages"]:
        print(f"  {msg}")

    print("\n--- FINAL RECOMMENDATION ---")
    print(result.get("final_recommendation", "(none)"))
