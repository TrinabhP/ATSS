"""
agents/orchestrator.py — Orchestrator / Critic

The Critic always owns review logic regardless of who built the agent being reviewed.
Agent 1's developer has no reason to touch this file.
"""

import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List

from groq import Groq
from state import (
    LiteratureOutput,
    HypothesisOutput,
    ProcedureOutput,
    CriticReview,
    ResearchState,
)

MODEL = "openai/gpt-oss-20b"

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    return _client


def _extract_text(response) -> str:
    return response.choices[0].message.content or ""


def _safe_json(text: str, fallback: object) -> object:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        inner = lines[1:-1] if lines[-1].strip().startswith("```") else lines[1:]
        stripped = "\n".join(inner)
    try:
        return json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return fallback


# ── Literature Review ──────────────────────────────────────────────────────────

_REVIEW_LITERATURE_SYSTEM = """You are a rigorous scientific director reviewing a literature review team's output. You are demanding and do not approve mediocre work.

Approve ONLY if ALL of the following are true:
1. At least 5 papers were found — fewer is an automatic FAIL
2. Every paper has a PaperAnalysis with specific, concrete findings (not vague summaries)
3. The synthesis directly and specifically addresses the research question (generic text = FAIL)
4. No glaring gap in the relevant research domain is present

Return valid JSON only (no markdown, no extra text):
{
  "passed": true,
  "feedback": ""
}

OR if failing:
{
  "passed": false,
  "feedback": "Specific critique addressing each failed condition. Tell the agent exactly what to fix."
}"""


def review_literature(literature: LiteratureOutput, abstract: str) -> CriticReview:
    """Review Agent 1's literature output. Returns CriticReview (timestamp set by caller)."""
    client = _get_client()

    papers = literature.get("papers") or []
    analyses = literature.get("analyses") or []
    synthesis = literature.get("synthesis") or ""

    user_content = (
        f"Research question:\n{abstract}\n\n"
        f"Papers found ({len(papers)}):\n"
        + "\n".join(f"- {p.get('title', 'Untitled')}: {p.get('abstract', '')[:200]}" for p in papers)
        + f"\n\nAnalyses ({len(analyses)}):\n"
        + json.dumps(analyses, indent=2)[:3000]
        + f"\n\nSynthesis:\n{synthesis}"
    )

    raw: dict = {}
    try:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": _REVIEW_LITERATURE_SYSTEM},
                {"role": "user", "content": user_content},
            ],
        )
        text = _extract_text(response)
        parsed = _safe_json(text, {})
        raw = parsed if isinstance(parsed, dict) else {}
    except Exception as e:
        raw = {"passed": False, "feedback": f"[Orchestrator review error: {e}]"}

    passed = bool(raw.get("passed", False))
    feedback = str(raw.get("feedback", "")) if not passed else ""

    return CriticReview(
        agent_name="literature",
        revision_number=literature.get("revision_count", 0),
        passed=passed,
        feedback=feedback,
        timestamp="",  # Set by graph node
    )


# ── Hypothesis Review ──────────────────────────────────────────────────────────

_REVIEW_HYPOTHESIS_SYSTEM = """You are a senior scientific director reviewing a hypothesis design. You apply rigorous standards.

Approve ONLY if ALL of the following are true:
1. The hypothesis is specific and testable — it names population, intervention/exposure, comparator, and outcome
2. The null hypothesis is correctly formed as H0 (no difference / no association)
3. The rationale explicitly cites specific findings from the provided literature (generic claims = FAIL)
4. The design approach is appropriate for the hypothesis type (e.g., RCT for causal claims, cohort for associations)

Return valid JSON only (no markdown, no extra text):
{
  "passed": true,
  "feedback": ""
}

OR if failing:
{
  "passed": false,
  "feedback": "Specific critique for each failed condition. Be precise about what is wrong and what must change."
}"""


def review_hypothesis(
    hypothesis: HypothesisOutput,
    literature: LiteratureOutput,
    abstract: str,
) -> CriticReview:
    """Review Agent 2's hypothesis output. Returns CriticReview (timestamp set by caller)."""
    client = _get_client()

    synthesis = literature.get("synthesis") or "No literature synthesis available."
    analyses = literature.get("analyses") or []
    findings_snippet = "\n".join(
        f"- {a.get('paper_title', '')}: {'; '.join((a.get('key_findings') or [])[:2])}"
        for a in analyses[:5]
    )

    user_content = (
        f"Research question:\n{abstract}\n\n"
        f"Literature context (for checking whether rationale is grounded):\n{synthesis}\n"
        f"Key findings available:\n{findings_snippet}\n\n"
        f"Hypothesis submission:\n"
        f"Primary hypothesis: {hypothesis.get('hypothesis', '')}\n"
        f"Null hypothesis: {hypothesis.get('null_hypothesis', '')}\n"
        f"Rationale: {hypothesis.get('rationale', '')}\n"
        f"Design approach: {hypothesis.get('design_approach', '')}\n"
        f"Expected outcomes: {hypothesis.get('expected_outcomes', [])}"
    )

    raw: dict = {}
    try:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": _REVIEW_HYPOTHESIS_SYSTEM},
                {"role": "user", "content": user_content},
            ],
        )
        text = _extract_text(response)
        parsed = _safe_json(text, {})
        raw = parsed if isinstance(parsed, dict) else {}
    except Exception as e:
        raw = {"passed": False, "feedback": f"[Orchestrator review error: {e}]"}

    passed = bool(raw.get("passed", False))
    feedback = str(raw.get("feedback", "")) if not passed else ""

    return CriticReview(
        agent_name="hypothesis",
        revision_number=hypothesis.get("revision_count", 0),
        passed=passed,
        feedback=feedback,
        timestamp="",
    )


# ── Procedure Review ───────────────────────────────────────────────────────────

_REVIEW_PROCEDURE_SYSTEM = """You are a senior scientific director reviewing a study procedure design. You hold researchers to high methodological standards.

Approve ONLY if ALL of the following are true:
1. Population size includes a power calculation rationale with effect size, power level, and alpha — a bare number without justification is an automatic FAIL
2. Inclusion/exclusion criteria are specific (age ranges, diagnosis codes, biomarker thresholds) — generic criteria = FAIL
3. The data collection methodology is consistent with and appropriate for the stated research design
4. The statistical approach names specific tests and directly addresses the primary hypothesis

Return valid JSON only (no markdown, no extra text):
{
  "passed": true,
  "feedback": ""
}

OR if failing:
{
  "passed": false,
  "feedback": "Specific critique for each failed condition. Name exactly what is missing or wrong."
}"""


def review_procedure(
    procedure: ProcedureOutput,
    hypothesis: HypothesisOutput,
    abstract: str,
) -> CriticReview:
    """Review Agent 3's procedure output. Returns CriticReview (timestamp set by caller)."""
    client = _get_client()

    user_content = (
        f"Research question:\n{abstract}\n\n"
        f"Hypothesis being tested:\n{hypothesis.get('hypothesis', '')}\n"
        f"Null hypothesis: {hypothesis.get('null_hypothesis', '')}\n"
        f"Design approach: {hypothesis.get('design_approach', '')}\n\n"
        f"Procedure submission:\n"
        f"Population size: {procedure.get('population_size', '')}\n"
        f"Population criteria: {procedure.get('population_criteria', '')}\n"
        f"Research design: {procedure.get('research_design', '')}\n"
        f"Data collection: {procedure.get('data_collection', '')}\n"
        f"Statistical approach: {procedure.get('statistical_approach', '')}\n"
        f"Timeline: {procedure.get('timeline_estimate', '')}"
    )

    raw: dict = {}
    try:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": _REVIEW_PROCEDURE_SYSTEM},
                {"role": "user", "content": user_content},
            ],
        )
        text = _extract_text(response)
        parsed = _safe_json(text, {})
        raw = parsed if isinstance(parsed, dict) else {}
    except Exception as e:
        raw = {"passed": False, "feedback": f"[Orchestrator review error: {e}]"}

    passed = bool(raw.get("passed", False))
    feedback = str(raw.get("feedback", "")) if not passed else ""

    return CriticReview(
        agent_name="procedure",
        revision_number=procedure.get("revision_count", 0),
        passed=passed,
        feedback=feedback,
        timestamp="",
    )


# ── Final Synthesis ────────────────────────────────────────────────────────────

_SYNTHESIS_SYSTEM = """You are a research director producing a final synthesis after three specialized agents have completed their work and passed expert review.

Return valid JSON only (no markdown, no extra text):
{
  "final_recommendation": "2-3 paragraph recommendation integrating literature evidence, the research hypothesis, and the proposed study procedure. Be concrete and actionable.",
  "confidence_level": "High",
  "action_items": [
    "Specific action item 1",
    "Specific action item 2"
  ],
  "caveats": [
    "Important caveat 1"
  ]
}

Confidence level rules:
- "High": Strong literature base (5+ papers), specific testable hypothesis, rigorous procedure design
- "Moderate": Adequate literature but gaps exist, OR hypothesis needs refinement, OR procedure has limitations
- "Low": Weak literature, vague hypothesis, or methodological concerns remain

Requirements:
- confidence_level must be exactly "High", "Moderate", or "Low"
- action_items: 3-5 specific next steps for the research team
- caveats: 2-4 important limitations or risks to flag"""


def synthesize_final(state: ResearchState) -> tuple:
    """
    Called only after all 3 agents have passed review.
    Returns: (final_recommendation, confidence_level, action_items, caveats)
    """
    client = _get_client()

    literature = state.get("literature") or {}
    hypothesis = state.get("hypothesis") or {}
    procedure = state.get("procedure") or {}
    abstract = state.get("abstract", "")

    reviews = state.get("reviews") or []
    review_summary = "\n".join(
        f"- {r['agent_name']} review #{r['revision_number']}: {'PASSED' if r['passed'] else 'FAILED'}"
        + (f" — {r['feedback'][:100]}" if not r["passed"] else "")
        for r in reviews
    )

    user_content = (
        f"Research question:\n{abstract}\n\n"
        f"Literature synthesis:\n{literature.get('synthesis', 'N/A')}\n"
        f"Papers reviewed: {len(literature.get('papers') or [])}\n\n"
        f"Approved hypothesis:\n{hypothesis.get('hypothesis', 'N/A')}\n"
        f"Null hypothesis: {hypothesis.get('null_hypothesis', 'N/A')}\n"
        f"Rationale: {hypothesis.get('rationale', 'N/A')}\n"
        f"Design approach: {hypothesis.get('design_approach', 'N/A')}\n\n"
        f"Approved procedure:\n"
        f"Sample size: {procedure.get('population_size', 'N/A')}\n"
        f"Design: {procedure.get('research_design', 'N/A')}\n"
        f"Statistics: {procedure.get('statistical_approach', 'N/A')}\n"
        f"Timeline: {procedure.get('timeline_estimate', 'N/A')}\n\n"
        f"Review history:\n{review_summary}"
    )

    raw: dict = {}
    try:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=3000,
            messages=[
                {"role": "system", "content": _SYNTHESIS_SYSTEM},
                {"role": "user", "content": user_content},
            ],
        )
        text = _extract_text(response)
        parsed = _safe_json(text, {})
        raw = parsed if isinstance(parsed, dict) else {}
    except Exception as e:
        return (
            f"[Synthesis error: {e}]",
            "Low",
            ["Review pipeline error and retry"],
            ["Synthesis failed — results unreliable"],
        )

    confidence = str(raw.get("confidence_level", "Low"))
    if confidence not in ("High", "Moderate", "Low"):
        confidence = "Low"

    return (
        str(raw.get("final_recommendation", "")),
        confidence,
        [str(a) for a in (raw.get("action_items") or [])],
        [str(c) for c in (raw.get("caveats") or [])],
    )
