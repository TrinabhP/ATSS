"""
agents.py — All Claude API agent functions for LabOS Research Analysis Engine.
No LangGraph imports here. All external calls wrapped in try/except.
"""

import json
import os
from typing import List

import anthropic

from state import ResearchState, Paper, ExtractedResult, DebateRound, empty_state

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL = "claude-sonnet-4-20250514"
MAX_PAPERS = 10
MIN_PAPERS = 5

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return _client


def _extract_text(response: anthropic.types.Message) -> str:
    """Pull the first text block from a Claude response."""
    for block in response.content:
        if block.type == "text":
            return block.text
    return ""


def _safe_json(text: str, fallback: object) -> object:
    """Parse JSON, returning fallback on any error."""
    # Strip markdown code fences if present
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        # Remove first and last fence lines
        inner = lines[1:-1] if lines[-1].strip().startswith("```") else lines[1:]
        stripped = "\n".join(inner)
    try:
        return json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return fallback


# ---------------------------------------------------------------------------
# Agent 1 — Literature Finder
# ---------------------------------------------------------------------------

LITERATURE_FINDER_PROMPT = """You are a scientific literature researcher. Your task is to find relevant published papers for a given research abstract or question.

STEP 1: Extract 3–5 precise search terms from the abstract. Focus on specific biological targets, diseases, mechanisms, or methodologies.

STEP 2: Use the web_search tool to search for relevant scientific papers. Prioritize papers published from 2018 onwards. Search PubMed, bioRxiv, Nature, Science, Cell, and other reputable sources.

STEP 3: Return between 5 and 10 papers. If you find fewer than 5, include what you found and note the limitation.

Return your response as valid JSON in this exact format (no markdown, no extra text):
{
  "search_terms": ["term1", "term2", "term3"],
  "papers": [
    {
      "title": "Full paper title",
      "url": "https://...",
      "abstract": "Brief abstract summary (2-3 sentences)",
      "relevance_score": 0.95
    }
  ]
}

Requirements:
- relevance_score must be a float between 0.0 and 1.0
- Each paper must have all four fields
- Prioritize papers with direct experimental evidence
- Include papers that may contradict each other — diversity of evidence is valuable
"""


def literature_finder(state: ResearchState) -> ResearchState:
    """Agent 1: Find relevant papers using web_search."""
    state["current_stage"] = "literature_finder"
    client = _get_client()

    abstract = state["abstract"][:4000]  # Respect MAX_ABSTRACT_LENGTH

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=LITERATURE_FINDER_PROMPT,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[
                {
                    "role": "user",
                    "content": f"Find relevant scientific papers for this research abstract:\n\n{abstract}",
                }
            ],
        )

        text = _extract_text(response)
        data = _safe_json(text, {})

        papers_raw = data.get("papers", []) if isinstance(data, dict) else []
        search_terms = data.get("search_terms", []) if isinstance(data, dict) else []

        # Validate and cap papers
        papers: List[Paper] = []
        for p in papers_raw[:MAX_PAPERS]:
            if isinstance(p, dict) and p.get("title") and p.get("url"):
                papers.append(
                    Paper(
                        title=str(p.get("title", "")),
                        url=str(p.get("url", "")),
                        abstract=str(p.get("abstract", "")),
                        relevance_score=float(p["relevance_score"])
                        if p.get("relevance_score") is not None
                        else None,
                    )
                )

        if len(papers) < MIN_PAPERS:
            print(
                f"[WARNING] Literature Finder found only {len(papers)} papers (minimum is {MIN_PAPERS})"
            )

        state["papers"] = papers
        state["search_terms"] = [str(t) for t in search_terms]

    except anthropic.APIError as e:
        # Retry once
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=LITERATURE_FINDER_PROMPT,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[
                    {
                        "role": "user",
                        "content": f"Find relevant scientific papers for this research abstract:\n\n{abstract}",
                    }
                ],
            )
            text = _extract_text(response)
            data = _safe_json(text, {})
            papers_raw = data.get("papers", []) if isinstance(data, dict) else []
            search_terms = data.get("search_terms", []) if isinstance(data, dict) else []
            papers = []
            for p in papers_raw[:MAX_PAPERS]:
                if isinstance(p, dict) and p.get("title") and p.get("url"):
                    papers.append(
                        Paper(
                            title=str(p.get("title", "")),
                            url=str(p.get("url", "")),
                            abstract=str(p.get("abstract", "")),
                            relevance_score=float(p["relevance_score"])
                            if p.get("relevance_score") is not None
                            else None,
                        )
                    )
            state["papers"] = papers
            state["search_terms"] = [str(t) for t in search_terms]
        except Exception as retry_err:
            state["error"] = f"Literature Finder failed after retry: {retry_err}"
            state["papers"] = []
            state["search_terms"] = []
    except Exception as e:
        state["error"] = f"Literature Finder error: {e}"
        state["papers"] = []
        state["search_terms"] = []

    return state


# ---------------------------------------------------------------------------
# Agent 2 — Results Extractor
# ---------------------------------------------------------------------------

RESULTS_EXTRACTOR_PROMPT = """You are a scientific data extractor. Your task is to extract key empirical findings from a list of research papers.

For each paper, use web_search to fetch its content and extract:
- key_findings: List of specific findings. PRESERVE verbatim numerical results exactly as written (e.g., "p<0.001", "n=156", "65% response rate", "HR=0.43 [95% CI 0.31-0.60]")
- methods: Brief description of study design and methodology
- sample_size: Exact sample size if reported (e.g., "n=156", "N=1,200 patients")
- datasets: Datasets or cohorts used (or null if not applicable)
- limitations: Key limitations stated by authors (or null if not found)

If a paper URL is inaccessible, skip it gracefully and note it in the findings as "URL inaccessible".

Return your response as valid JSON in this exact format (no markdown, no extra text):
{
  "extracted_results": [
    {
      "paper_title": "Exact paper title",
      "key_findings": ["Finding 1 with exact numbers", "Finding 2"],
      "methods": "Study design description",
      "sample_size": "n=156",
      "datasets": "Dataset name or null",
      "limitations": "Key limitations or null"
    }
  ]
}

CRITICAL: Preserve all numerical values exactly as they appear in the paper. Do not round, summarize, or paraphrase numerical results.
"""


def results_extractor(state: ResearchState) -> ResearchState:
    """Agent 2: Extract empirical findings from each paper."""
    state["current_stage"] = "results_extractor"
    client = _get_client()

    papers_json = json.dumps(state["papers"], indent=2)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=8192,
            system=RESULTS_EXTRACTOR_PROMPT,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Extract key findings from these papers:\n\n{papers_json}\n\n"
                        f"Original research question: {state['abstract']}"
                    ),
                }
            ],
        )

        text = _extract_text(response)
        data = _safe_json(text, {})

        results_raw = data.get("extracted_results", []) if isinstance(data, dict) else []

        extracted: list[ExtractedResult] = []
        for r in results_raw:
            if isinstance(r, dict) and r.get("paper_title"):
                extracted.append(
                    ExtractedResult(
                        paper_title=str(r.get("paper_title", "")),
                        key_findings=[str(f) for f in r.get("key_findings", [])],
                        methods=str(r.get("methods", "")),
                        sample_size=str(r["sample_size"]) if r.get("sample_size") else None,
                        datasets=str(r["datasets"]) if r.get("datasets") else None,
                        limitations=str(r["limitations"]) if r.get("limitations") else None,
                    )
                )

        if not extracted:
            state["error"] = "Results Extractor: all paper URLs were inaccessible"

        state["extracted_results"] = extracted

    except anthropic.APIError:
        # Retry once
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=8192,
                system=RESULTS_EXTRACTOR_PROMPT,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Extract key findings from these papers:\n\n{papers_json}\n\n"
                            f"Original research question: {state['abstract']}"
                        ),
                    }
                ],
            )
            text = _extract_text(response)
            data = _safe_json(text, {})
            results_raw = data.get("extracted_results", []) if isinstance(data, dict) else []
            extracted = []
            for r in results_raw:
                if isinstance(r, dict) and r.get("paper_title"):
                    extracted.append(
                        ExtractedResult(
                            paper_title=str(r.get("paper_title", "")),
                            key_findings=[str(f) for f in r.get("key_findings", [])],
                            methods=str(r.get("methods", "")),
                            sample_size=str(r["sample_size"]) if r.get("sample_size") else None,
                            datasets=str(r["datasets"]) if r.get("datasets") else None,
                            limitations=str(r["limitations"]) if r.get("limitations") else None,
                        )
                    )
            state["extracted_results"] = extracted
        except Exception as retry_err:
            state["error"] = f"Results Extractor failed after retry: {retry_err}"
            state["extracted_results"] = []
    except Exception as e:
        state["error"] = f"Results Extractor error: {e}"
        state["extracted_results"] = []

    return state


# ---------------------------------------------------------------------------
# Agent 3 — Initial Analysis
# ---------------------------------------------------------------------------

INITIAL_ANALYSIS_PROMPT = """You are a senior research scientist. Your task is to synthesize extracted findings from multiple papers into an initial analysis.

Your synthesis must:
1. Cover what the collective evidence suggests (2–3 paragraphs)
2. EXPLICITLY name contradictions between papers — do not average them away
3. Identify 2–5 gaps or inconsistencies across the papers

Return your response as valid JSON in this exact format (no markdown, no extra text):
{
  "initial_synthesis": "2-3 paragraph synthesis of the collective evidence...",
  "identified_gaps": [
    "Gap or inconsistency 1",
    "Gap or inconsistency 2"
  ]
}

Be specific. Reference paper titles when noting contradictions. The synthesis will be challenged by a critic agent, so be precise about what the evidence does and does not show.
"""


def initial_analysis_agent(state: ResearchState) -> ResearchState:
    """Agent 3: Synthesize extracted results into an initial analysis."""
    state["current_stage"] = "initial_analysis"
    client = _get_client()

    results_json = json.dumps(state["extracted_results"], indent=2)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=INITIAL_ANALYSIS_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Research question: {state['abstract']}\n\n"
                        f"Extracted findings from papers:\n{results_json}"
                    ),
                }
            ],
        )

        text = _extract_text(response)
        data = _safe_json(text, {})

        if isinstance(data, dict):
            state["initial_synthesis"] = str(data.get("initial_synthesis", text))
            state["identified_gaps"] = [
                str(g) for g in data.get("identified_gaps", [])
            ]
        else:
            state["initial_synthesis"] = text
            state["identified_gaps"] = []

    except Exception as e:
        state["error"] = f"Initial Analysis error: {e}"
        state["initial_synthesis"] = ""
        state["identified_gaps"] = []

    # Always initialize debate state
    state["debate_rounds"] = []
    state["current_round"] = 0

    return state


# ---------------------------------------------------------------------------
# Debate Agents — Critic, Results Re-evaluator, Analysis Refiner
# ---------------------------------------------------------------------------

CRITIC_PROMPT = """You are a rigorous scientific critic. Your job is to challenge the current analysis of research findings.

Focus your critique on:
- Sample size issues (underpowered studies, small n)
- Confounding variables not adequately controlled
- Overgeneralization of findings beyond what the data supports
- Statistical concerns (p-hacking, multiple comparisons, effect sizes)
- Publication bias or missing contradictory evidence

REQUIREMENTS:
- Cite specific papers by their exact title when making a criticism
- Write 2–3 paragraphs of substantive critique
- Be specific — vague criticisms are not useful
- Do NOT simply agree with the analysis; find genuine weaknesses

Return plain text only (no JSON, no markdown headers).
"""

RESULTS_REEVALUATOR_PROMPT = """You are a data-focused research analyst. You have received a critic's feedback on a research analysis. Your job is to re-examine the raw extracted results and respond to each criticism.

For each concern raised by the critic, you must explicitly state one of:
- CONFIRMED: The data supports the critic's concern
- REFUTED: The data contradicts the critic's concern (cite specific numbers)
- PARTIALLY VALIDATED: The concern has merit but is overstated (explain why)

Write 2–3 paragraphs. Be specific about which numbers or findings support your assessment.

Return plain text only (no JSON, no markdown headers).
"""

ANALYSIS_REFINER_PROMPT = """You are a senior scientist updating a research synthesis based on debate feedback.

You will receive:
1. The previous analysis
2. The critic's feedback
3. The results re-evaluator's response

Your job is to produce an updated synthesis that:
- Explicitly states what changed from the previous version and WHY
- Incorporates confirmed criticisms
- Maintains positions that were refuted with evidence
- Adjusts nuance where criticisms were partially validated

Write 2–3 paragraphs. Start with "Updated from previous round: [what changed]..."

Return plain text only (no JSON, no markdown headers).
"""

FINAL_RECOMMENDATION_PROMPT = """You are a research director producing a final recommendation based on a multi-round debate analysis.

Confidence level rules:
- "High": At least 3 papers with consistent findings support the conclusion
- "Moderate": Findings are consistent but sample sizes are small or studies are limited in number
- "Low": Findings are contradictory or the evidence base is weak

Return your response as valid JSON in this exact format (no markdown, no extra text):
{
  "final_recommendation": "2-3 paragraph recommendation...",
  "confidence_level": "High",
  "action_items": [
    "Specific action item 1",
    "Specific action item 2"
  ],
  "caveats": [
    "Important caveat 1",
    "Important caveat 2"
  ]
}

Requirements:
- confidence_level must be exactly "High", "Moderate", or "Low" — no other values
- action_items: 2–4 items
- caveats: 1–3 items
- The recommendation must reflect the final debate round's refined analysis
"""


def critic_agent(state: ResearchState) -> str:
    """Critic: Challenge the current analysis."""
    client = _get_client()

    # Use latest analysis from debate rounds, or initial synthesis
    if state["debate_rounds"]:
        current_analysis = state["debate_rounds"][-1]["analysis_update"]
    else:
        current_analysis = state["initial_synthesis"]

    results_json = json.dumps(state["extracted_results"], indent=2)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=CRITIC_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Current analysis to critique:\n{current_analysis}\n\n"
                        f"Raw extracted results for reference:\n{results_json}"
                    ),
                }
            ],
        )
        return _extract_text(response)
    except Exception as e:
        return f"[Critic agent error: {e}]"


def results_reevaluator(state: ResearchState, critic_feedback: str) -> str:
    """Results Re-evaluator: Respond to critic's concerns with data."""
    client = _get_client()

    results_json = json.dumps(state["extracted_results"], indent=2)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=RESULTS_REEVALUATOR_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Critic's feedback:\n{critic_feedback}\n\n"
                        f"Raw extracted results to re-examine:\n{results_json}"
                    ),
                }
            ],
        )
        return _extract_text(response)
    except Exception as e:
        return f"[Results Re-evaluator error: {e}]"


def analysis_refiner(
    state: ResearchState, critic_feedback: str, results_response: str
) -> str:
    """Analysis Refiner: Update synthesis based on debate."""
    client = _get_client()

    if state["debate_rounds"]:
        previous_analysis = state["debate_rounds"][-1]["analysis_update"]
    else:
        previous_analysis = state["initial_synthesis"]

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=ANALYSIS_REFINER_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Previous analysis:\n{previous_analysis}\n\n"
                        f"Critic's feedback:\n{critic_feedback}\n\n"
                        f"Results re-evaluator's response:\n{results_response}"
                    ),
                }
            ],
        )
        return _extract_text(response)
    except Exception as e:
        return f"[Analysis Refiner error: {e}]"


def final_recommendation_agent(state: ResearchState) -> ResearchState:
    """Final Recommendation: Produce structured recommendation after all debate rounds."""
    state["current_stage"] = "final_recommendation"
    client = _get_client()

    # Use the last debate round's refined analysis
    final_analysis = (
        state["debate_rounds"][-1]["analysis_update"]
        if state["debate_rounds"]
        else state["initial_synthesis"]
    )

    debate_summary = json.dumps(
        [
            {
                "round": r["round_number"],
                "critic": r["critic_feedback"][:500],
                "update": r["analysis_update"][:500],
            }
            for r in state["debate_rounds"]
        ],
        indent=2,
    )

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=FINAL_RECOMMENDATION_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Original research question: {state['abstract']}\n\n"
                        f"Final refined analysis:\n{final_analysis}\n\n"
                        f"Debate round summaries:\n{debate_summary}"
                    ),
                }
            ],
        )

        text = _extract_text(response)
        data = _safe_json(text, {})

        if isinstance(data, dict):
            confidence = str(data.get("confidence_level", "Low"))
            if confidence not in ("High", "Moderate", "Low"):
                confidence = "Low"

            state["final_recommendation"] = str(data.get("final_recommendation", text))
            state["confidence_level"] = confidence
            state["action_items"] = [str(a) for a in data.get("action_items", [])]
            state["caveats"] = [str(c) for c in data.get("caveats", [])]
        else:
            state["final_recommendation"] = text
            state["confidence_level"] = "Low"
            state["action_items"] = []
            state["caveats"] = []

    except Exception as e:
        state["error"] = f"Final Recommendation error: {e}"
        state["final_recommendation"] = ""
        state["confidence_level"] = "Low"
        state["action_items"] = []
        state["caveats"] = []

    return state


# ---------------------------------------------------------------------------
# Standalone tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from state import empty_state

    DEMO_ABSTRACT = (
        "We're investigating menin inhibitors for NPM1-mutant AML. "
        "Key question: Does HOX gene expression predict treatment response to "
        "menin inhibitors in NPM1-mutant acute myeloid leukemia patients?"
    )

    print("=== Testing Agent 1: Literature Finder ===")
    s = empty_state()
    s["abstract"] = DEMO_ABSTRACT
    s = literature_finder(s)
    print(f"Papers found: {len(s['papers'])}")
    print(f"Search terms: {s['search_terms']}")
    if s["papers"]:
        print(f"First paper: {s['papers'][0]['title']}")
    assert len(s["papers"]) >= 1, "Expected at least 1 paper"
    print("Agent 1 OK\n")

    print("=== Testing Agent 2: Results Extractor ===")
    s = results_extractor(s)
    print(f"Extracted results: {len(s['extracted_results'])}")
    if s["extracted_results"]:
        print(f"First result title: {s['extracted_results'][0]['paper_title']}")
        print(f"Key findings: {s['extracted_results'][0]['key_findings'][:2]}")
    assert len(s["extracted_results"]) >= 1, "Expected at least 1 extracted result"
    print("Agent 2 OK\n")

    print("=== Testing Agent 3: Initial Analysis ===")
    s = initial_analysis_agent(s)
    print(f"Synthesis length: {len(s['initial_synthesis'])} chars")
    print(f"Identified gaps: {len(s['identified_gaps'])}")
    assert s["initial_synthesis"], "Expected non-empty synthesis"
    print("Agent 3 OK\n")

    print("=== Testing Critic Agent ===")
    feedback = critic_agent(s)
    print(f"Critic feedback length: {len(feedback)} chars")
    assert feedback and not feedback.startswith("[Critic agent error"), "Critic failed"
    print("Critic OK\n")

    print("=== Testing Results Re-evaluator ===")
    reeval = results_reevaluator(s, feedback)
    print(f"Re-evaluator length: {len(reeval)} chars")
    print("Re-evaluator OK\n")

    print("=== Testing Analysis Refiner ===")
    refined = analysis_refiner(s, feedback, reeval)
    print(f"Refined analysis length: {len(refined)} chars")
    print("Analysis Refiner OK\n")

    print("All agent tests passed!")
