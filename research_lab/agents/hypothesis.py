"""
agents/hypothesis.py — Agent 2: Hypothesis Design
"""

import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from groq import Groq
from state import LiteratureOutput, HypothesisOutput

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


_HYPOTHESIS_SYSTEM = """You are a senior research scientist specializing in hypothesis formation.
Given a research abstract and literature synthesis, generate a well-formed scientific hypothesis.

Return valid JSON only (no markdown, no extra text):
{
  "hypothesis": "Specific, testable primary hypothesis with measurable outcome",
  "null_hypothesis": "The formal statistical null (no effect / no difference)",
  "rationale": "Why this hypothesis, citing specific findings from the literature provided",
  "design_approach": "Proposed study design (e.g., randomized controlled trial, prospective cohort, case-control)",
  "expected_outcomes": ["Concrete measurable outcome 1", "Concrete measurable outcome 2"]
}

Requirements:
- hypothesis must name the intervention/exposure, the population, the comparator, and the outcome
- null_hypothesis must be the formal H0 (no difference / no association)
- rationale must cite at least one specific finding from the provided literature
- design_approach must be appropriate for the hypothesis type
- expected_outcomes: 2-4 concrete, measurable outcomes with anticipated direction of effect"""

_HYPOTHESIS_REVISION_SYSTEM = """You are a senior research scientist revising a research hypothesis based on reviewer feedback.
Apply every feedback point precisely.

Return valid JSON only (no markdown, no extra text):
{
  "hypothesis": "Revised primary hypothesis",
  "null_hypothesis": "Revised null hypothesis",
  "rationale": "Revised rationale citing specific literature findings",
  "design_approach": "Revised study design approach",
  "expected_outcomes": ["Revised expected outcome 1", "Revised expected outcome 2"]
}"""

_SELF_REVIEW_SYSTEM = """You are reviewing a research hypothesis against standard scientific criteria.

Evaluate on:
1. Specificity — is it precise enough to be tested? Does it name population, intervention, comparator, outcome?
2. Testability — can it be empirically tested with realistic methods?
3. Falsifiability — could evidence potentially refute it?
4. Literature grounding — does the rationale cite specific findings from the provided literature?

Respond with EXACTLY one of:
- "ISSUES_NONE" if the hypothesis meets all criteria
- "ISSUES_FOUND: [describe each issue clearly on one line each]" if significant issues exist

No other text."""

_HYPOTHESIS_FIX_SYSTEM = """You are a senior research scientist correcting a hypothesis based on self-review issues.

Issues to address: {issues}

Return valid JSON only (no markdown, no extra text):
{{
  "hypothesis": "Corrected primary hypothesis",
  "null_hypothesis": "Corrected null hypothesis",
  "rationale": "Corrected rationale",
  "design_approach": "Corrected study design approach",
  "expected_outcomes": ["Corrected expected outcome 1", "Corrected expected outcome 2"]
}}"""


def _build_lit_context(literature: LiteratureOutput) -> str:
    synthesis = literature.get("synthesis") or "No synthesis available."
    context = f"Literature Synthesis:\n{synthesis}\n"
    analyses = literature.get("analyses") or []
    if analyses:
        context += "\nKey Findings from Analyzed Papers:\n"
        for a in analyses[:6]:
            title = a.get("paper_title", "Unknown paper")
            findings = a.get("key_findings") or []
            finding_str = "; ".join(findings[:2]) if findings else "No findings listed"
            context += f"- {title}: {finding_str}\n"
    return context


def run_hypothesis_agent(
    literature: LiteratureOutput,
    abstract: str,
    critic_feedback: str = "",
    revision_count: int = 0,
) -> HypothesisOutput:
    client = _get_client()
    lit_context = _build_lit_context(literature)

    if critic_feedback:
        system = _HYPOTHESIS_REVISION_SYSTEM
        user_content = (
            f"Research abstract:\n{abstract}\n\n"
            f"{lit_context}\n"
            f"Critic feedback requiring revision:\n{critic_feedback}\n\n"
            "Revise the hypothesis to address all feedback points."
        )
    else:
        system = _HYPOTHESIS_SYSTEM
        user_content = (
            f"Research abstract:\n{abstract}\n\n"
            f"{lit_context}\n"
            "Generate a well-formed research hypothesis."
        )

    raw_data: dict = {}
    try:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
        )
        text = _extract_text(response)
        parsed = _safe_json(text, {})
        raw_data = parsed if isinstance(parsed, dict) else {}
    except Exception as e:
        return HypothesisOutput(
            hypothesis=f"[Hypothesis generation error: {e}]",
            null_hypothesis="",
            rationale="",
            design_approach="",
            expected_outcomes=[],
            revision_count=revision_count,
        )

    hypothesis_text = raw_data.get("hypothesis", "")
    if hypothesis_text:
        try:
            self_review_input = (
                f"Research abstract:\n{abstract}\n\n"
                f"{lit_context}\n"
                f"Hypothesis under review:\n"
                f"Primary: {hypothesis_text}\n"
                f"Null: {raw_data.get('null_hypothesis', '')}\n"
                f"Rationale: {raw_data.get('rationale', '')}\n"
                f"Design: {raw_data.get('design_approach', '')}"
            )
            review_resp = client.chat.completions.create(
                model=MODEL,
                max_tokens=512,
                messages=[
                    {"role": "system", "content": _SELF_REVIEW_SYSTEM},
                    {"role": "user", "content": self_review_input},
                ],
            )
            review_text = _extract_text(review_resp).strip()

            if review_text.startswith("ISSUES_FOUND:"):
                issues = review_text[len("ISSUES_FOUND:"):].strip()
                fix_system = _HYPOTHESIS_FIX_SYSTEM.format(issues=issues)
                fix_resp = client.chat.completions.create(
                    model=MODEL,
                    max_tokens=2048,
                    messages=[
                        {"role": "system", "content": fix_system},
                        {"role": "user", "content": (
                            f"Research abstract:\n{abstract}\n\n"
                            f"{lit_context}\n"
                            f"Original hypothesis (needs fixing):\n{json.dumps(raw_data, indent=2)}"
                        )},
                    ],
                )
                fix_text = _extract_text(fix_resp)
                fixed = _safe_json(fix_text, {})
                if isinstance(fixed, dict) and fixed.get("hypothesis"):
                    raw_data = fixed
        except Exception:
            pass

    return HypothesisOutput(
        hypothesis=str(raw_data.get("hypothesis", "")),
        null_hypothesis=str(raw_data.get("null_hypothesis", "")),
        rationale=str(raw_data.get("rationale", "")),
        design_approach=str(raw_data.get("design_approach", "")),
        expected_outcomes=[str(o) for o in (raw_data.get("expected_outcomes") or [])],
        revision_count=revision_count,
    )
