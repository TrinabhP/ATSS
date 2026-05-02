"""
agents/literature.py

⚠️  THIS FILE IS OWNED BY ANOTHER DEVELOPER — DO NOT IMPLEMENT.
    Signatures and docstrings define the integration contract.
    The other developer replaces the NotImplementedError bodies.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state import LiteratureOutput, Paper, PaperAnalysis


def find_papers(abstract: str):
    """
    Sub-Agent 1A: Searches for 5-10 relevant papers given a research abstract.
    Uses Claude API with web_search tool.
    Returns: List[Paper]
    """
    raise NotImplementedError("find_papers() is implemented by the Agent 1 developer")


def analyze_papers(papers, abstract: str):
    """
    Sub-Agent 1B: Fetches and analyzes each paper.
    Extracts key findings, methodology, sample size, limitations, relevance.
    Also produces a synthesis paragraph across all papers.
    Returns: tuple[List[PaperAnalysis], str]  (analyses, synthesis)
    """
    raise NotImplementedError("analyze_papers() is implemented by the Agent 1 developer")


def run_literature_agent(abstract: str, critic_feedback: str = "") -> LiteratureOutput:
    """
    Main entry point — called by the Orchestrator in graph.py.
    Internally calls find_papers() then analyze_papers().
    If critic_feedback is non-empty, revises based on that feedback.
    Tracks revision_count in the returned LiteratureOutput.
    Returns: LiteratureOutput
    """
    raise NotImplementedError("run_literature_agent() is implemented by the Agent 1 developer")
