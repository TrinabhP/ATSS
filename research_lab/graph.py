"""
graph.py — LangGraph graph definition for LabOS Research Analysis Engine.
Imports from agents.py and state.py only. No Streamlit imports.
"""

from langgraph.graph import StateGraph, END

from state import ResearchState, DebateRound, empty_state
from agents import (
    literature_finder,
    results_extractor,
    initial_analysis_agent,
    critic_agent,
    results_reevaluator,
    analysis_refiner,
    final_recommendation_agent,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_DEBATE_ROUNDS = 3


# ---------------------------------------------------------------------------
# Debate round node — orchestrates Critic → Re-evaluator → Refiner
# ---------------------------------------------------------------------------


def debate_round_node(state: ResearchState) -> ResearchState:
    """Run one full debate cycle: Critic → Results Re-evaluator → Analysis Refiner."""
    round_number = state["current_round"] + 1
    state["current_stage"] = f"debate_round_{round_number}"

    # Run the three debate agents in sequence
    feedback = critic_agent(state)
    reeval = results_reevaluator(state, feedback)
    refined = analysis_refiner(state, feedback, reeval)

    # Append the completed round to state
    debate_round = DebateRound(
        round_number=round_number,
        critic_feedback=feedback,
        results_refinement=reeval,
        analysis_update=refined,
    )
    state["debate_rounds"] = state["debate_rounds"] + [debate_round]
    state["current_round"] = round_number

    return state


# ---------------------------------------------------------------------------
# Conditional edge — continue debate or finalize
# ---------------------------------------------------------------------------


def should_continue_debate(state: ResearchState) -> str:
    """Return 'debate' to loop, 'finalize' to proceed to final recommendation."""
    if state["current_round"] < MAX_DEBATE_ROUNDS:
        return "debate"
    return "finalize"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_graph() -> "CompiledGraph":  # type: ignore[name-defined]
    """Build and compile the LangGraph research pipeline."""
    graph = StateGraph(ResearchState)

    # Add all nodes
    graph.add_node("literature_finder", literature_finder)
    graph.add_node("results_extractor", results_extractor)
    graph.add_node("initial_analysis", initial_analysis_agent)
    graph.add_node("debate_round", debate_round_node)
    graph.add_node("final_recommendation", final_recommendation_agent)

    # Set entry point
    graph.set_entry_point("literature_finder")

    # Linear edges
    graph.add_edge("literature_finder", "results_extractor")
    graph.add_edge("results_extractor", "initial_analysis")
    graph.add_edge("initial_analysis", "debate_round")

    # Conditional edge from debate_round
    graph.add_conditional_edges(
        "debate_round",
        should_continue_debate,
        {
            "debate": "debate_round",
            "finalize": "final_recommendation",
        },
    )

    # Final edge to END
    graph.add_edge("final_recommendation", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_research(abstract: str) -> ResearchState:
    """Run the full research pipeline and return the final state."""
    compiled = build_graph()

    initial = empty_state()
    initial["abstract"] = abstract[:4000]  # Respect MAX_ABSTRACT_LENGTH

    final_state: ResearchState = compiled.invoke(initial)
    return final_state


def stream_research(abstract: str):
    """Yield accumulated state snapshots after each pipeline node completes."""
    compiled = build_graph()

    initial = empty_state()
    initial["abstract"] = abstract[:4000]

    accumulated: dict = dict(initial)
    for chunk in compiled.stream(initial):
        for node_output in chunk.values():
            if isinstance(node_output, dict):
                accumulated.update(node_output)
        yield dict(accumulated)


# ---------------------------------------------------------------------------
# Standalone integration test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    DEMO_ABSTRACT = (
        "We're investigating menin inhibitors for NPM1-mutant AML. "
        "Key question: Does HOX gene expression predict treatment response to "
        "menin inhibitors in NPM1-mutant acute myeloid leukemia patients?"
    )

    print("Starting LabOS Research Analysis Engine...")
    print(f"Abstract: {DEMO_ABSTRACT[:80]}...\n")

    result = run_research(DEMO_ABSTRACT)

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Papers found:        {len(result['papers'])}")
    print(f"Extracted results:   {len(result['extracted_results'])}")
    print(f"Debate rounds:       {len(result['debate_rounds'])}")
    print(f"Confidence level:    {result['confidence_level']}")
    print(f"Action items:        {len(result['action_items'])}")
    print(f"Caveats:             {len(result['caveats'])}")

    if result.get("error"):
        print(f"\n[ERROR] {result['error']}")

    print("\n--- FINAL RECOMMENDATION ---")
    print(result["final_recommendation"])

    print("\n--- ACTION ITEMS ---")
    for i, item in enumerate(result["action_items"], 1):
        print(f"  {i}. {item}")

    print("\n--- CAVEATS ---")
    for i, caveat in enumerate(result["caveats"], 1):
        print(f"  {i}. {caveat}")

    # Assertions
    assert len(result["debate_rounds"]) == MAX_DEBATE_ROUNDS, (
        f"Expected {MAX_DEBATE_ROUNDS} debate rounds, got {len(result['debate_rounds'])}"
    )
    assert result["confidence_level"] in ("High", "Moderate", "Low"), (
        f"Invalid confidence level: {result['confidence_level']}"
    )
    print("\nAll integration assertions passed!")
