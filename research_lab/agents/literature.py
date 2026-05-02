"""
agents/literature.py — Agent 1: wires PubMed search + Gemini extraction into
the LiteratureOutput contract expected by graph.py.

Delegates to:
  research_lab/literature.py  — PubMed search via NCBI Entrez + Gemini term extraction
  research_lab/rag.py         — parallel Gemini extraction of findings per paper
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic
from state import LiteratureOutput, Paper, PaperAnalysis
from literature import find_literature
from rag import extract_results_threaded, ProgressTracker


def _build_synthesis(abstract: str, extracted: list, search_terms: list) -> str:
    client = anthropic.Anthropic()
    all_findings = [f for e in extracted for f in e.get("key_findings", [])]
    prompt = (
        f"Research question: {abstract}\n\n"
        f"Search terms: {', '.join(search_terms)}\n\n"
        f"Key findings across {len(extracted)} papers:\n"
        + "\n".join(f"- {f}" for f in all_findings[:20])
        + "\n\nWrite a concise 2-3 sentence synthesis of what this literature "
        "collectively shows about the research question."
    )
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text
    except Exception:
        return (
            f"Found {len(extracted)} papers on {', '.join(search_terms)} "
            f"with {len(all_findings)} key findings."
        )


def find_papers(abstract: str) -> list:
    """Sub-Agent 1A: search PubMed, return List[Paper]."""
    lit_result = find_literature(abstract, max_papers=10)
    raw = lit_result["papers"]
    return [
        Paper(
            title=p["title"],
            url=f"https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/",
            abstract=p.get("abstract", "")[:600],
            relevance_score=round(max(0.5, 1.0 - i * 0.05), 2),
        )
        for i, p in enumerate(raw)
    ]


def analyze_papers(papers: list, abstract: str) -> tuple:
    """Sub-Agent 1B: extract findings per paper, return (List[PaperAnalysis], synthesis)."""
    progress = ProgressTracker()
    extracted = extract_results_threaded(papers, progress)
    analyses = [
        PaperAnalysis(
            paper_title=e["title"],
            key_findings=e.get("key_findings", []),
            methodology=e.get("methods", ""),
            sample_size=e.get("sample_size", "N/A"),
            limitations=e.get("limitations", ""),
            relevance_to_question=e.get("relevance", ""),
        )
        for e in extracted
    ]
    synthesis = _build_synthesis(abstract, extracted, [])
    return analyses, synthesis


def run_literature_agent(abstract: str, critic_feedback: str = "") -> LiteratureOutput:
    """Main entry point called by graph.py."""
    search_context = abstract
    if critic_feedback:
        search_context = f"{abstract}\n\nPrior review feedback to address: {critic_feedback}"

    # Step 1: PubMed search + term extraction
    lit_result = find_literature(search_context, max_papers=10)
    raw_papers = lit_result["papers"]
    search_terms = lit_result["search_terms"]

    if not raw_papers:
        raise ValueError("PubMed search returned no papers — check GOOGLE_API_KEY and ENTREZ_EMAIL")

    # Step 2: Map to Paper TypedDicts
    papers = [
        Paper(
            title=p["title"],
            url=f"https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/",
            abstract=p.get("abstract", "")[:600],
            relevance_score=round(max(0.5, 1.0 - i * 0.05), 2),
        )
        for i, p in enumerate(raw_papers)
    ]

    # Step 3: Parallel Gemini extraction
    progress = ProgressTracker()
    extracted = extract_results_threaded(raw_papers, progress)

    analyses = [
        PaperAnalysis(
            paper_title=e["title"],
            key_findings=e.get("key_findings", []),
            methodology=e.get("methods", ""),
            sample_size=e.get("sample_size", "N/A"),
            limitations=e.get("limitations", ""),
            relevance_to_question=e.get("relevance", ""),
        )
        for e in extracted
    ]

    # Step 4: Claude synthesis across all findings
    synthesis = _build_synthesis(abstract, extracted, search_terms)

    return LiteratureOutput(
        papers=papers,
        analyses=analyses,
        search_terms=search_terms,
        synthesis=synthesis,
        revision_count=0,
    )
