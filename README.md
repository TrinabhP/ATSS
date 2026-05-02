# LabOS — Research Analysis Engine

A multi-agent system for automated biomedical literature review and analysis. Two pipelines are available depending on your setup.

---

## Architecture

### Pipeline A — LangGraph + Claude (primary)

The main pipeline uses LangGraph for orchestration and Claude (via the Anthropic API) for all agent logic.

```
Abstract Input
    ↓
[Agent 1: Literature Finder]   — Claude + web_search → 5–10 papers
    ↓
[Agent 2: Results Extractor]   — Claude + web_fetch → key findings per paper
    ↓
[Agent 3: Initial Analysis]    — Claude → synthesis + identified gaps
    ↓
[Multi-Agent Debate Loop × 3]
    Critic Agent ↔ Results Re-evaluator ↔ Analysis Refiner
    ↓
[Final Recommendation]         — confidence level + action items + caveats
```

Entry points:
- `research_lab/app.py` — Streamlit dashboard (live streaming UI)
- `research_lab/graph.py` — programmatic entry (`run_research`, `stream_research`)

### Pipeline B — PubMed + Ragie RAG (Groq-Powered)

An alternative Phase 1 pipeline that uses PubMed (via Biopython/Entrez) for literature search and Ragie.ai for RAG indexing. Uses Groq (`llama-3.3-70b-versatile`) for term extraction and result extraction — 14,400 free requests/day with no quota issues.

```
Abstract Input
    ↓
[Agent 1: PubMed Finder]       — Groq term extraction + Entrez API → papers + PMIDs
    ↓
[Agent 2: Ragie RAG Builder]   — PMC full-text fetch (1 worker) + Ragie.ai upload (2 workers, threaded)
    + Results Extractor        — Groq parallel extraction → structured findings (2 workers, threaded)
```

Agent 2 runs two stages concurrently:
- **RAG build**: fetches PMC full-text where available (1 parallel worker, NCBI rate limit), falls back to abstract, then uploads all documents to Ragie.ai in parallel (2 workers). Documents are uploaded with string-coerced metadata and a `"data"` payload field; a 415 fallback automatically retries with `"content"` for older Ragie API versions.
- **Extraction**: calls Groq in parallel (2 workers) to produce structured `key_findings`, `methods`, `sample_size`, `limitations`, and `relevance` fields.

Entry point: `run_pipeline.py`

---

## Project Structure

```
.
├── main.py                    # Standalone LangGraph prototype (Tavily search)
├── run_pipeline.py            # Pipeline B runner (PubMed → Ragie)
├── requirements.txt           # Dependencies for Pipeline A
├── requirements_ragie.txt     # Dependencies for Pipeline B
└── research_lab/
    ├── agents.py              # All Claude agent functions (Pipeline A)
    ├── graph.py               # LangGraph graph definition + stream_research
    ├── app.py                 # Streamlit dashboard
    ├── state.py               # Shared TypedDicts (ResearchState, Paper, etc.)
    ├── literature.py          # PubMed literature finder (Pipeline B, Agent 1)
    ├── rag.py                 # Ragie RAG builder + results extractor (Pipeline B, Agent 2)
    └── .env                   # API keys (gitignored)
```

---

## Setup

### Pipeline A (LangGraph + Claude)

```bash
pip install -r requirements.txt
```

Required keys in `research_lab/.env`:
```
ANTHROPIC_API_KEY=...
```

Run the Streamlit dashboard:
```bash
streamlit run research_lab/app.py
```

Run headless:
```python
from research_lab.graph import run_research
result = run_research("Your research abstract here")
```

### Pipeline B (PubMed + Ragie)

```bash
pip install -r requirements_ragie.txt
```

Required keys in `research_lab/.env`:
```
GROQ_API_KEY=...
RAGIE_API_KEY=...
ENTREZ_EMAIL=your.email@example.com
```

Run the pipeline:
```bash
python run_pipeline.py
```

The default demo abstract in `run_pipeline.py` is:
> "I am researching how NPM1 mutations in Acute Myeloid Leukemia (AML) respond to menin inhibitors. I specifically want to know if high expression of the HOXA9 and MEIS1 genes can predict if a patient will have a good treatment response. Additionally, I am looking for data on combining menin inhibitors with CAR-T cell therapy."

`run_pipeline.py` loads environment variables from `research_lab/.env` at startup and exits with a clear error message if the file is missing, if required packages (`groq`, `biopython`, `requests`) are not installed, or if any API keys are absent.

Outputs are saved to:
- `agent1_output.json` — papers found by PubMed search
- `agent2_output.json` — extracted results and stats

After the pipeline completes, the returned `ragie_client` object can be used to query the indexed documents:

```python
from research_lab.rag import extract_and_build_rag

result = extract_and_build_rag(papers)
ragie_client = result["ragie_client"]

hits = ragie_client.query("HOXA9 expression and treatment response", top_k=3)
for hit in hits:
    print(hit["score"], hit["metadata"]["title"])
    print(hit["text"][:200])
```

`query()` returns a list of scored chunks from Ragie.ai, each with `score`, `text`, and `metadata` (pmid, title, authors, journal, year, has_fulltext).

---

## Agents (Pipeline A)

| Agent | File | Description |
|---|---|---|
| Literature Finder | `agents.py` | Finds 5–10 relevant papers via Claude web_search |
| Results Extractor | `agents.py` | Extracts findings, methods, sample sizes from each paper |
| Initial Analysis | `agents.py` | Synthesizes findings; identifies gaps and contradictions |
| Critic | `agents.py` | Challenges the analysis (sample sizes, confounders, stats) |
| Results Re-evaluator | `agents.py` | Responds to critic with CONFIRMED / REFUTED / PARTIALLY VALIDATED |
| Analysis Refiner | `agents.py` | Updates synthesis based on debate; states what changed and why |
| Final Recommendation | `agents.py` | Produces structured recommendation with confidence level |

Confidence levels: `High` (≥3 consistent papers), `Moderate` (consistent but limited), `Low` (contradictory or weak evidence).

---

## State Schema

Defined in `research_lab/state.py`. Key fields:

```python
class ResearchState(TypedDict):
    abstract: str
    papers: List[Paper]                  # title, url, abstract, relevance_score
    extracted_results: List[ExtractedResult]  # findings, methods, sample_size
    initial_synthesis: str
    identified_gaps: List[str]
    debate_rounds: List[DebateRound]     # critic / re-evaluator / refiner per round
    current_round: int
    final_recommendation: str
    confidence_level: str                # "High" | "Moderate" | "Low"
    action_items: List[str]
    caveats: List[str]
    current_stage: str                   # used by Streamlit status bar
    error: Optional[str]
```

---

## Example

```python
from research_lab.graph import run_research

abstract = """
Does HOX gene expression predict treatment response to menin inhibitors
in NPM1-mutant acute myeloid leukemia patients?
"""

result = run_research(abstract)
print(result["confidence_level"])       # "High" | "Moderate" | "Low"
print(result["final_recommendation"])
for item in result["action_items"]:
    print("-", item)
```
