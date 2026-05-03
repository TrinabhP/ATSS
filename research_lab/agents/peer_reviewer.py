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

from groq import Groq
from state import (
    LiteratureOutput,
    HypothesisOutput,
    ProcedureOutput,
    PeerReviewOutput,
    ReproducibilityIssue,
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
    import re
    stripped = text.strip()
    # Strip <think>...</think> blocks from reasoning models
    stripped = re.sub(r'<think>.*?</think>', '', stripped, flags=re.DOTALL).strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        inner = lines[1:-1] if lines[-1].strip().startswith("```") else lines[1:]
        stripped = "\n".join(inner)
    # Try to find a JSON object anywhere in the response
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        stripped = stripped[start:end+1]
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
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": _PEER_REVIEW_SYSTEM},
                {"role": "user", "content": user_content},
            ],
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
