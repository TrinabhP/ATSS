"""
agents/procedure.py — Agent 3: Procedure Design
"""

import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic
from state import LiteratureOutput, HypothesisOutput, ProcedureOutput

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


_PROCEDURE_SYSTEM = """You are a research methodologist and biostatistician. Design the full study procedure for testing the given research hypothesis.

Return valid JSON only (no markdown, no extra text):
{
  "population_size": "Estimated sample size with power calculation (e.g., 'Given expected effect size of 0.5 and 80% power at alpha=0.05, minimum n=128 per arm, total N=256 accounting for 10% dropout')",
  "population_criteria": "Specific inclusion and exclusion criteria as a bulleted list",
  "research_design": "Detailed study design methodology including blinding, randomization, controls",
  "data_collection": "How data will be collected: instruments, timepoints, primary/secondary endpoints",
  "statistical_approach": "Statistical tests, software, how the primary endpoint will be analyzed, multiple comparisons strategy",
  "timeline_estimate": "Realistic milestone-based timeline (e.g., 'Months 1-3: enrollment, Months 4-18: follow-up, Months 19-24: analysis and publication')"
}

Requirements:
- population_size MUST include a power calculation rationale with effect size, power (80% or 90%), and alpha level
- population_criteria must be specific (age range, diagnosis criteria, biomarker thresholds) not generic
- research_design must match the hypothesis type (interventional vs. observational)
- statistical_approach must name the specific test(s) and address the primary endpoint
- All six fields must be substantive — no placeholder text"""

_PROCEDURE_REVISION_SYSTEM = """You are a research methodologist revising a study procedure based on reviewer feedback.
Apply every feedback point precisely.

Return valid JSON only (no markdown, no extra text):
{
  "population_size": "Revised sample size with power calculation",
  "population_criteria": "Revised inclusion and exclusion criteria",
  "research_design": "Revised detailed design methodology",
  "data_collection": "Revised data collection plan",
  "statistical_approach": "Revised statistical analysis approach",
  "timeline_estimate": "Revised realistic timeline"
}"""


def _build_context(
    literature: LiteratureOutput,
    hypothesis: HypothesisOutput,
    abstract: str,
) -> str:
    context = f"Research abstract:\n{abstract}\n\n"
    context += f"Research Hypothesis:\n{hypothesis.get('hypothesis', '')}\n"
    context += f"Null Hypothesis:\n{hypothesis.get('null_hypothesis', '')}\n"
    context += f"Design Approach (from Agent 2):\n{hypothesis.get('design_approach', '')}\n\n"

    synthesis = literature.get("synthesis") or "No literature synthesis available."
    context += f"Literature Synthesis:\n{synthesis}\n"
    return context


def run_procedure_agent(
    literature: LiteratureOutput,
    hypothesis: HypothesisOutput,
    abstract: str,
    critic_feedback: str = "",
    revision_count: int = 0,
) -> ProcedureOutput:
    """
    Design the full study procedure for the given hypothesis.

    Args:
        literature: Output from Agent 1 (or mock during testing)
        hypothesis: Output from Agent 2
        abstract: Original research abstract
        critic_feedback: Non-empty string triggers revision mode
        revision_count: Passed in by the dispatch node; stored in returned output
    """
    client = _get_client()
    context = _build_context(literature, hypothesis, abstract)

    if critic_feedback:
        system = _PROCEDURE_REVISION_SYSTEM
        user_content = (
            f"{context}\n"
            f"Critic feedback requiring revision:\n{critic_feedback}\n\n"
            "Revise the study procedure to address all feedback points."
        )
    else:
        system = _PROCEDURE_SYSTEM
        user_content = (
            f"{context}\n"
            "Design the complete study procedure for testing this hypothesis."
        )

    raw_data: dict = {}
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=3000,
            system=system,
            messages=[{"role": "user", "content": user_content}],
        )
        text = _extract_text(response)
        parsed = _safe_json(text, {})
        raw_data = parsed if isinstance(parsed, dict) else {}
    except Exception as e:
        return ProcedureOutput(
            population_size=f"[Procedure generation error: {e}]",
            population_criteria="",
            research_design="",
            data_collection="",
            statistical_approach="",
            timeline_estimate="",
            revision_count=revision_count,
        )

    return ProcedureOutput(
        population_size=str(raw_data.get("population_size", "")),
        population_criteria=str(raw_data.get("population_criteria", "")),
        research_design=str(raw_data.get("research_design", "")),
        data_collection=str(raw_data.get("data_collection", "")),
        statistical_approach=str(raw_data.get("statistical_approach", "")),
        timeline_estimate=str(raw_data.get("timeline_estimate", "")),
        revision_count=revision_count,
    )
