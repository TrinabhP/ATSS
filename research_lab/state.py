"""
state.py — Shared state contract for LabOS Research Analysis Engine.
All TypedDicts are defined here. No agent logic. No LangGraph imports.
"""

from typing import List, Optional
from typing_extensions import TypedDict


class Paper(TypedDict):
    title: str
    url: str
    abstract: str
    relevance_score: Optional[float]  # 0.0 – 1.0


class ExtractedResult(TypedDict):
    paper_title: str
    key_findings: List[str]      # Verbatim numerical findings preferred
    methods: str
    sample_size: Optional[str]   # e.g. "n=156"
    datasets: Optional[str]
    limitations: Optional[str]


class DebateRound(TypedDict):
    round_number: int            # 1, 2, or 3
    critic_feedback: str         # Plain text, 2-3 paragraphs
    results_refinement: str      # Plain text, 2-3 paragraphs
    analysis_update: str         # Plain text, 2-3 paragraphs


class ResearchState(TypedDict):
    abstract: str
    search_terms: List[str]
    papers: List[Paper]
    extracted_results: List[ExtractedResult]
    initial_synthesis: str
    identified_gaps: List[str]
    debate_rounds: List[DebateRound]
    current_round: int
    final_recommendation: str
    confidence_level: str        # "High" | "Moderate" | "Low"
    action_items: List[str]
    caveats: List[str]
    current_stage: str           # Stage ID for UI status bar
    error: Optional[str]


def empty_state() -> ResearchState:
    """Return a ResearchState with all fields initialized to safe defaults."""
    return ResearchState(
        abstract="",
        search_terms=[],
        papers=[],
        extracted_results=[],
        initial_synthesis="",
        identified_gaps=[],
        debate_rounds=[],
        current_round=0,
        final_recommendation="",
        confidence_level="",
        action_items=[],
        caveats=[],
        current_stage="",
        error=None,
    )


if __name__ == "__main__":
    s = empty_state()
    s["abstract"] = "test"
    print("State schema OK:", list(s.keys()))
