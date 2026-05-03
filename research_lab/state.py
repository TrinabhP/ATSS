"""
state.py — Shared state contract for LabOS Research Analysis Engine.
All TypedDicts are defined here. No agent logic. No LangGraph imports.

LiteratureOutput is the integration contract between the Orchestrator and Agent 1.
Do not rename its fields — Agent 1 developer builds to this spec.
"""

from typing import List, Optional, Literal
from typing_extensions import TypedDict


# ── Shared primitives ──────────────────────────────────────────────────────────

class Paper(TypedDict):
    title: str
    url: str
    abstract: str
    relevance_score: Optional[float]


class PaperAnalysis(TypedDict):
    paper_title: str
    key_findings: List[str]
    methodology: str
    sample_size: Optional[str]
    limitations: Optional[str]
    relevance_to_question: str


class CriticReview(TypedDict):
    agent_name: str        # "literature" | "hypothesis" | "procedure"
    revision_number: int   # 0 = first submission, 1 = first revision, 2 = second
    passed: bool
    feedback: str          # Empty string if passed, specific critique if failed
    timestamp: str         # ISO string


# ── Per-agent output structs ───────────────────────────────────────────────────

class LiteratureOutput(TypedDict):
    papers: List[Paper]
    analyses: List[PaperAnalysis]
    search_terms: List[str]
    synthesis: str          # Sub-agent 1B's synthesis across all analyzed papers
    revision_count: int     # How many times this agent was revised


class HypothesisOutput(TypedDict):
    hypothesis: str         # The primary research hypothesis
    null_hypothesis: str    # The corresponding null hypothesis
    rationale: str          # Why this hypothesis based on the literature
    design_approach: str    # Proposed study design (RCT, cohort, etc.)
    expected_outcomes: List[str]
    revision_count: int


class ProcedureOutput(TypedDict):
    population_size: str       # Calculated/estimated N with justification
    population_criteria: str   # Inclusion/exclusion criteria
    research_design: str       # Detailed design methodology
    data_collection: str       # How data will be collected
    statistical_approach: str  # How data will be analyzed
    timeline_estimate: str     # Rough timeline for the study
    revision_count: int


# ── Top-level graph state ──────────────────────────────────────────────────────

class ResearchState(TypedDict):
    # Input
    abstract: str

    # Orchestrator tracking
    current_stage: str                    # UI display: which agent/step is active
    orchestrator_messages: List[str]      # Log of orchestrator decisions

    # Sub-agent outputs (None until that agent completes and passes review)
    literature: Optional[LiteratureOutput]
    hypothesis: Optional[HypothesisOutput]
    procedure: Optional[ProcedureOutput]

    # Critic review history (all reviews, all agents)
    reviews: List[CriticReview]

    # Final output
    final_recommendation: Optional[str]
    confidence_level: Optional[Literal["High", "Moderate", "Low"]]
    action_items: List[str]
    caveats: List[str]

    # Error tracking
    error: Optional[str]


if __name__ == "__main__":
    s: ResearchState = {
        "abstract": "test",
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
    print("State schema OK:", list(s.keys()))
