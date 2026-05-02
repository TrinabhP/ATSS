"""
agents/peer_reviewer.py — Agent 4: Peer Review

Performs an independent reproducibility-focused review of the full research plan
(literature + hypothesis + procedure) and returns a structured PeerReviewOutput.
No LangGraph imports. No Streamlit.
"""

import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic
from state import (
    LiteratureOutput,
    HypothesisOutput,
    ProcedureOutput,
    PeerReviewOutput,
    ReproducibilityIssue,
)

MODEL = "claude-sonnet-4-20250514"

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return _client


def _extract_text(response: anthropic.types.Message) -> str:
    for block in response.content:
        if block.type == "text":
            return block.text
    return ""


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


_PEER_REVIEW_SYSTEM = """You are an independent peer reviewer evaluating a complete research plan for scientific rigor and reproducibility.

Assess the literature review, hypothesis, and study procedure as a unified package.

Return valid JSON only (no markdown, no extra text):
{
  "overall_verdict": "Accept",
  "reproducibility_score": 8,
  "summary": "2-3 paragraph narrative review covering the overall quality, key strengths, and main concerns.",
  "strengths": [
    "Specific strength 1",
    "Specific strength 2"
  ],
  "issues": [
    {
      "section": "Procedure",
      "severity": "Major",
      "description": "What the issue is",
      "suggestion": "Concrete fix"
    }
  ],
  "missing_details": [
    "Information absent that would be needed to replicate this study"
  ],
  "suggested_changes": [
    "Prioritized change 1",
    "Prioritized change 2"
  ],
  "replication_checklist": [
    "Patient population clearly defined: Yes/No",
    "Primary endpoint pre-specified: Yes/No"
  ]
}

Rules:
- overall_verdict must be exactly one of: "Accept", "Minor Revision", "Major Revision", "Reject"
- reproducibility_score: integer 1-10 (10 = fully reproducible from the description alone)
- issues[].severity must be exactly "Critical", "Major", or "Minor"
- strengths: 2-5 items
- issues: list every reproducibility or methodological problem found (can be empty list if none)
- missing_details: information a replicating lab would need but cannot find in the plan
- suggested_changes: ordered by priority, most important first
- replication_checklist: 5-8 yes/no items a replicating team would check"""


def run_peer_review_agent(
    literature: LiteratureOutput,
    hypothesis: HypothesisOutput,
    procedure: ProcedureOutput,
    abstract: str,
) -> PeerReviewOutput:
    """
    Perform an independent peer review of the full research plan.

    Args:
        literature: Approved output from Agent 1
        hypothesis: Approved output from Agent 2
        procedure:  Approved output from Agent 3
        abstract:   Original research abstract

    Returns:
        PeerReviewOutput with verdict, score, issues, and replication checklist
    """
    client = _get_client()

    lit = literature or {}
    hyp = hypothesis or {}
    proc = procedure or {}

    papers = lit.get("papers") or []
    analyses = lit.get("analyses") or []
    findings_snippet = "\n".join(
        f"  - {a.get('paper_title', '')}: {'; '.join((a.get('key_findings') or [])[:2])}"
        for a in analyses[:6]
    )

    user_content = (
        f"=== RESEARCH ABSTRACT ===\n{abstract}\n\n"
        f"=== LITERATURE REVIEW ===\n"
        f"Papers found: {len(papers)}\n"
        f"Search terms: {', '.join(lit.get('search_terms') or [])}\n"
        f"Key findings:\n{findings_snippet}\n"
        f"Synthesis:\n{lit.get('synthesis', 'N/A')}\n\n"
        f"=== HYPOTHESIS ===\n"
        f"Primary: {hyp.get('hypothesis', 'N/A')}\n"
        f"Null: {hyp.get('null_hypothesis', 'N/A')}\n"
        f"Rationale: {hyp.get('rationale', 'N/A')}\n"
        f"Design approach: {hyp.get('design_approach', 'N/A')}\n"
        f"Expected outcomes: {hyp.get('expected_outcomes', [])}\n\n"
        f"=== STUDY PROCEDURE ===\n"
        f"Population size: {proc.get('population_size', 'N/A')}\n"
        f"Population criteria: {proc.get('population_criteria', 'N/A')}\n"
        f"Research design: {proc.get('research_design', 'N/A')}\n"
        f"Data collection: {proc.get('data_collection', 'N/A')}\n"
        f"Statistical approach: {proc.get('statistical_approach', 'N/A')}\n"
        f"Timeline: {proc.get('timeline_estimate', 'N/A')}\n"
    )

    raw: dict = {}
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=_PEER_REVIEW_SYSTEM,
            messages=[{"role": "user", "content": user_content}],
        )
        text = _extract_text(response)
        parsed = _safe_json(text, {})
        raw = parsed if isinstance(parsed, dict) else {}
    except Exception as e:
        return PeerReviewOutput(
            overall_verdict="Major Revision",
            reproducibility_score=1,
            summary=f"[Peer review error: {e}]",
            strengths=[],
            issues=[],
            missing_details=["Peer review failed — manual review required"],
            suggested_changes=[],
            replication_checklist=[],
        )

    verdict = str(raw.get("overall_verdict", "Major Revision"))
    if verdict not in ("Accept", "Minor Revision", "Major Revision", "Reject"):
        verdict = "Major Revision"

    score = raw.get("reproducibility_score", 5)
    try:
        score = max(1, min(10, int(score)))
    except (TypeError, ValueError):
        score = 5

    raw_issues = raw.get("issues") or []
    issues: list[ReproducibilityIssue] = []
    for item in raw_issues:
        if not isinstance(item, dict):
            continue
        severity = str(item.get("severity", "Minor"))
        if severity not in ("Critical", "Major", "Minor"):
            severity = "Minor"
        issues.append(
            ReproducibilityIssue(
                section=str(item.get("section", "")),
                severity=severity,
                description=str(item.get("description", "")),
                suggestion=str(item.get("suggestion", "")),
            )
        )

    return PeerReviewOutput(
        overall_verdict=verdict,
        reproducibility_score=score,
        summary=str(raw.get("summary", "")),
        strengths=[str(s) for s in (raw.get("strengths") or [])],
        issues=issues,
        missing_details=[str(m) for m in (raw.get("missing_details") or [])],
        suggested_changes=[str(c) for c in (raw.get("suggested_changes") or [])],
        replication_checklist=[str(i) for i in (raw.get("replication_checklist") or [])],
    )


# ── Standalone test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from state import LiteratureOutput, HypothesisOutput, ProcedureOutput

    mock_lit = LiteratureOutput(
        papers=[{"title": "HOX gene expression in AML", "url": "", "abstract": "...", "relevance_score": 0.9}],
        analyses=[{"paper_title": "HOX gene expression in AML", "key_findings": ["HOX overexpression correlates with menin inhibitor response"], "methodology": "retrospective cohort", "sample_size": "120", "limitations": "single center", "relevance_to_question": "directly relevant"}],
        search_terms=["menin inhibitors", "NPM1-mutant AML", "HOX gene expression"],
        synthesis="HOX gene overexpression is a consistent finding in NPM1-mutant AML and preliminary data suggest it may predict menin inhibitor response.",
        revision_count=0,
    )
    mock_hyp = HypothesisOutput(
        hypothesis="In NPM1-mutant AML patients, high HOX gene expression (HOXA9/HOXB4 > median) predicts superior response to menin inhibitors vs. low expressors.",
        null_hypothesis="HOX gene expression level does not predict menin inhibitor response in NPM1-mutant AML.",
        rationale="Based on HOX overexpression data from the literature.",
        design_approach="Prospective cohort study",
        expected_outcomes=["Higher CR rate in HOX-high group", "Longer PFS in HOX-high group"],
        revision_count=0,
    )
    mock_proc = ProcedureOutput(
        population_size="N=120 (60 per arm), 80% power, alpha=0.05, effect size 0.5",
        population_criteria="Adults ≥18, NPM1-mutant AML confirmed by PCR, ECOG 0-2",
        research_design="Prospective cohort, stratified by HOX expression quartile",
        data_collection="RNA-seq at baseline, response assessed at day 28 and 56",
        statistical_approach="Cox proportional hazards for PFS; logistic regression for CR rate",
        timeline_estimate="Months 1-6: enrollment; Months 7-18: follow-up; Months 19-24: analysis",
        revision_count=0,
    )

    print("Running peer review agent test...")
    result = run_peer_review_agent(mock_lit, mock_hyp, mock_proc, "HOX gene expression and menin inhibitor response in NPM1-mutant AML")
    print(f"Verdict: {result['overall_verdict']}")
    print(f"Reproducibility score: {result['reproducibility_score']}/10")
    print(f"Summary: {result['summary'][:200]}...")
    print(f"Issues: {len(result['issues'])}")
    print(f"Strengths: {result['strengths']}")
