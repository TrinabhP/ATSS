"""
AGENT 1: PubMed Literature Finder (GROQ-POWERED)
Uses Groq API (14,400 free requests/day!) instead of Gemini
"""

import os
import json
import time
from typing import Dict, List, Callable, Optional
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

try:
    from Bio import Entrez
    ENTREZ_AVAILABLE = True
except ImportError:
    ENTREZ_AVAILABLE = False
    print("⚠️  Install biopython: pip install biopython")


class ProgressTracker:
    """Tracks and logs progress for real-time dashboard updates"""
    
    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback or print
        self.start_time = datetime.now()
    
    def log(self, message: str, status: str = "info"):
        """Log a message with timestamp and status icon"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        timestamp = f"[{int(elapsed//60):02d}:{int(elapsed%60):02d}]"
        
        icons = {
            "info": "ℹ️", "success": "✓", "error": "✗", 
            "search": "🔍", "download": "📥", "process": "🧠", 
            "complete": "✅"
        }
        icon = icons.get(status, "•")
        
        self.callback(f"{timestamp} {icon} {message}")


def extract_search_terms(abstract: str, progress: ProgressTracker) -> List[str]:
    """Extract PubMed-optimized search terms using Groq"""
    
    progress.log("Extracting PubMed search terms (Groq)...", "process")
    
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment")
    
    client = Groq(api_key=api_key)
    
    prompt = f"""You are a biomedical research librarian. Extract 3-5 precise PubMed search terms from this abstract.

Focus on:
- Specific genes/proteins (e.g., "HOXA9", "NPM1", "menin")
- Disease subtypes (e.g., "NPM1-mutant AML", "acute myeloid leukemia")
- Drug/treatment names (e.g., "menin inhibitor", "CAR-T therapy")
- Key biological processes (e.g., "HOX gene expression", "stem cell differentiation")

Abstract:
{abstract}

Return ONLY a JSON array, no markdown, no explanation:
["term1", "term2", "term3"]
"""
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # Chat model — better for structured JSON output
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )
        
        text = response.choices[0].message.content.strip()
        progress.log(f"Raw Groq response: {text[:200]}", "info")
        
        # Strip markdown fences
        if "```" in text:
            # Extract content between first ``` pair
            parts = text.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("["):
                    text = part
                    break
        
        # Find the JSON array anywhere in the response
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            text = text[start:end+1]
        
        search_terms = json.loads(text)
        
        # Validate it's a non-empty list of strings
        if not isinstance(search_terms, list) or len(search_terms) == 0:
            raise ValueError(f"Parsed empty or invalid list: {search_terms}")
        
        search_terms = [str(t).strip() for t in search_terms if str(t).strip()]
        
    except Exception as e:
        progress.log(f"Groq term extraction failed ({e}), using fallback terms", "error")
        # Fallback: extract key noun phrases from the abstract directly
        search_terms = _fallback_search_terms(abstract)
    
    progress.log(f"Extracted {len(search_terms)} search terms: {', '.join(search_terms)}", "success")
    return search_terms


def _fallback_search_terms(abstract: str) -> List[str]:
    """
    Simple keyword fallback when LLM extraction fails.
    Looks for known biomedical patterns and common words.
    """
    import re
    terms = []
    
    # Look for gene names (all-caps 2-8 chars, or mixed like NPM1, HOXA9)
    genes = re.findall(r'\b[A-Z][A-Z0-9]{1,7}\b', abstract)
    terms.extend(genes[:2])
    
    # Look for disease mentions
    diseases = re.findall(
        r'\b(?:leukemia|lymphoma|cancer|carcinoma|AML|CML|ALL|myeloma|tumor)\b',
        abstract, re.IGNORECASE
    )
    terms.extend(diseases[:1])
    
    # Look for drug/therapy mentions
    therapies = re.findall(
        r'\b(?:inhibitor|therapy|treatment|CAR-T|immunotherapy|chemotherapy)\b',
        abstract, re.IGNORECASE
    )
    terms.extend(therapies[:1])
    
    # Deduplicate and ensure we have at least something
    seen = set()
    unique = []
    for t in terms:
        if t.lower() not in seen:
            seen.add(t.lower())
            unique.append(t)
    
    if not unique:
        # Last resort: first 3 significant words
        words = [w for w in abstract.split() if len(w) > 5]
        unique = words[:3]
    
    return unique[:5]


def search_pubmed(search_terms: List[str], max_results: int, progress: ProgressTracker) -> List[str]:
    """Search PubMed database using NCBI Entrez API"""
    
    if not ENTREZ_AVAILABLE:
        raise ImportError("Biopython required. Install: pip install biopython")
    
    Entrez.email = os.environ.get("ENTREZ_EMAIL", "your.email@example.com")
    
    all_pmids = set()
    
    for i, term in enumerate(search_terms, 1):
        progress.log(f"Searching PubMed for: '{term}' ({i}/{len(search_terms)})", "search")
        
        try:
            handle = Entrez.esearch(
                db="pubmed",
                term=term,
                retmax=max_results,
                sort="relevance",
                retmode="xml"
            )
            record = Entrez.read(handle)
            handle.close()
            
            pmids = record["IdList"]
            all_pmids.update(pmids)
            
            progress.log(f"  Found {len(pmids)} papers for '{term}'", "success")
            time.sleep(0.4)  # Respect NCBI rate limit (3 requests/sec)
            
        except Exception as e:
            progress.log(f"  Error searching '{term}': {str(e)}", "error")
            continue
    
    pmid_list = list(all_pmids)
    progress.log(f"Total unique papers found: {len(pmid_list)}", "success")
    
    return pmid_list


def fetch_paper_metadata(pmids: List[str], progress: ProgressTracker) -> List[Dict]:
    """Fetch detailed metadata for papers from PubMed"""
    
    if not ENTREZ_AVAILABLE:
        raise ImportError("Biopython required")
    
    progress.log(f"Fetching metadata for {len(pmids)} papers...", "download")
    
    Entrez.email = os.environ.get("ENTREZ_EMAIL", "your.email@example.com")
    
    papers = []
    
    try:
        handle = Entrez.efetch(
            db="pubmed",
            id=pmids,
            rettype="medline",
            retmode="xml"
        )
        records = Entrez.read(handle)
        handle.close()
        
        for record in records['PubmedArticle']:
            try:
                article = record['MedlineCitation']['Article']
                
                pmid = str(record['MedlineCitation']['PMID'])
                title = article['ArticleTitle']
                
                # Abstract
                abstract_parts = article.get('Abstract', {}).get('AbstractText', [])
                if isinstance(abstract_parts, list):
                    abstract = ' '.join([str(part) for part in abstract_parts])
                else:
                    abstract = str(abstract_parts)
                
                # Authors
                authors = []
                if 'AuthorList' in article:
                    for author in article['AuthorList'][:3]:
                        if 'LastName' in author and 'Initials' in author:
                            authors.append(f"{author['LastName']} {author['Initials']}")
                
                # Journal and year
                journal = article['Journal']['Title']
                pub_date = article['Journal']['JournalIssue'].get('PubDate', {})
                year = pub_date.get('Year', 'N/A')
                
                # Check for PMC full-text
                pmc_id = None
                if 'PubmedData' in record:
                    for id_obj in record['PubmedData'].get('ArticleIdList', []):
                        if id_obj.attributes.get('IdType') == 'pmc':
                            pmc_id = str(id_obj)
                
                paper = {
                    'pmid': pmid,
                    'title': title,
                    'abstract': abstract,
                    'authors': authors,
                    'journal': journal,
                    'year': year,
                    'pmc_id': pmc_id,
                    'has_fulltext': pmc_id is not None
                }
                
                papers.append(paper)
                
            except Exception as e:
                progress.log(f"  Error parsing paper: {str(e)}", "error")
                continue
        
        fulltext_count = sum(1 for p in papers if p['has_fulltext'])
        progress.log(f"Retrieved {len(papers)} papers successfully", "success")
        progress.log(f"  {fulltext_count} have full-text in PMC, {len(papers) - fulltext_count} abstract-only", "info")
        
    except Exception as e:
        progress.log(f"Error fetching metadata: {str(e)}", "error")
    
    return papers


def find_literature(abstract: str, max_papers: int = 8, 
                   progress_callback: Optional[Callable] = None) -> Dict:
    """
    MAIN FUNCTION: Find biomedical literature from PubMed (GROQ-POWERED)
    """
    progress = ProgressTracker(progress_callback)
    
    progress.log("=" * 60, "info")
    progress.log("🔬 AGENT 1: PUBMED FINDER (Groq)", "info")
    progress.log("=" * 60, "info")
    
    # Step 1: Extract search terms
    search_terms = extract_search_terms(abstract, progress)
    
    # Step 2: Search PubMed
    pmids = search_pubmed(search_terms, max_results=max_papers, progress=progress)
    
    # Step 3: Fetch metadata
    papers = fetch_paper_metadata(pmids, progress=progress)
    
    # Calculate statistics
    stats = {
        "total_papers": len(papers),
        "with_fulltext": sum(1 for p in papers if p['has_fulltext']),
        "abstract_only": sum(1 for p in papers if not p['has_fulltext'])
    }
    
    progress.log("=" * 60, "info")
    progress.log(f"✅ AGENT 1 COMPLETE: Found {stats['total_papers']} papers", "complete")
    progress.log(f"   {stats['with_fulltext']} with full-text, {stats['abstract_only']} abstract-only", "info")
    progress.log("=" * 60, "info")
    
    return {
        "papers": papers,
        "search_terms": search_terms,
        "stats": stats
    }


def run_literature_agent(abstract: str, critic_feedback: str = ""):
    """
    Entry point called by graph.py.
    Runs find_literature + extract_results_threaded and returns a LiteratureOutput.
    Kept here so graph.py imports from a single canonical file.
    """
    from state import LiteratureOutput, Paper, PaperAnalysis
    from rag import extract_results_threaded, ProgressTracker as RagProgressTracker

    _SYNTHESIS_MODEL = "openai/gpt-oss-20b"

    search_context = abstract
    if critic_feedback:
        search_context = f"{abstract}\n\nPrior review feedback to address: {critic_feedback}"

    # Step 1: PubMed search + term extraction
    lit_result = find_literature(search_context, max_papers=3)
    raw_papers = lit_result["papers"]
    search_terms = lit_result["search_terms"]

    if not raw_papers:
        raise ValueError("PubMed search returned no papers — check GROQ_API_KEY and ENTREZ_EMAIL")

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

    # Step 3: Parallel extraction — must use raw_papers (has pmid/authors/journal/year)
    progress = RagProgressTracker()
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

    # Step 4: Synthesis
    all_findings = [f for e in extracted for f in e.get("key_findings", [])]
    synthesis_prompt = (
        f"Research question: {abstract}\n\n"
        f"Search terms: {', '.join(search_terms)}\n\n"
        f"Key findings across {len(extracted)} papers:\n"
        + "\n".join(f"- {f}" for f in all_findings[:20])
        + "\n\nWrite a concise 2-3 sentence synthesis of what this literature "
        "collectively shows about the research question."
    )
    try:
        groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        resp = groq_client.chat.completions.create(
            model=_SYNTHESIS_MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": synthesis_prompt}],
        )
        synthesis = resp.choices[0].message.content or ""
    except Exception:
        synthesis = (
            f"Found {len(extracted)} papers on {', '.join(search_terms)} "
            f"with {len(all_findings)} key findings."
        )

    return LiteratureOutput(
        papers=papers,
        analyses=analyses,
        search_terms=search_terms,
        synthesis=synthesis,
        revision_count=0,
    )


if __name__ == "__main__":
    test_abstract = """
    We investigate menin inhibitors for NPM1-mutant AML treatment. 
    Does HOX gene expression predict response to menin inhibitors?
    """
    
    try:
        result = find_literature(test_abstract, max_papers=5)
        
        print(f"\n📄 Sample papers:")
        for i, paper in enumerate(result['papers'][:2], 1):
            print(f"\n{i}. {paper['title']}")
            print(f"   PMID: {paper['pmid']}, Full-text: {paper['has_fulltext']}")
        
        with open("agent1_output.json", "w") as f:
            json.dump(result, indent=2, fp=f)
        print(f"\n✅ Saved to agent1_output.json")
        
    except Exception as e:
        print(f"❌ Error: {e}")








# """
# AGENT 1: PubMed Literature Finder
# Searches PubMed for biomedical research papers using intelligent term extraction
# Outputs structured paper data for Agent 2 (Ragie RAG)
# """

# import os
# import json
# from typing import Dict, List, Callable, Optional
# from datetime import datetime
# import google.generativeai as genai
# from dotenv import load_dotenv

# load_dotenv()

# try:
#     from Bio import Entrez
#     ENTREZ_AVAILABLE = True
# except ImportError:
#     ENTREZ_AVAILABLE = False
#     print("⚠️  Install biopython: pip install biopython")


# class ProgressTracker:
#     """Tracks and logs progress for real-time dashboard updates"""
    
#     def __init__(self, callback: Optional[Callable] = None):
#         self.callback = callback or print
#         self.start_time = datetime.now()
    
#     def log(self, message: str, status: str = "info"):
#         """Log a message with timestamp and status icon"""
#         elapsed = (datetime.now() - self.start_time).total_seconds()
#         timestamp = f"[{int(elapsed//60):02d}:{int(elapsed%60):02d}]"
        
#         icons = {
#             "info": "ℹ️", "success": "✓", "error": "✗", 
#             "search": "🔍", "download": "📥", "process": "🧠", 
#             "complete": "✅"
#         }
#         icon = icons.get(status, "•")
        
#         self.callback(f"{timestamp} {icon} {message}")


# def extract_search_terms(abstract: str, progress: ProgressTracker) -> List[str]:
#     """
#     Extract PubMed-optimized search terms from research abstract
    
#     Uses Gemini to identify key biological/medical terms that will
#     yield the best PubMed search results
    
#     Args:
#         abstract: Research abstract text
#         progress: Progress tracker for logging
        
#     Returns:
#         List[str]: 3-5 optimized search terms
#     """
#     progress.log("Extracting PubMed search terms from abstract...", "process")
    
#     api_key = os.environ.get("GROQ_API_KEY")
#     if not api_key:
#         raise ValueError("GROQ_API_KEY not found in .env file")
    
#     genai.configure(api_key=api_key)
#     model = genai.GenerativeModel('gemini-2.0-flash')
    
#     prompt = f"""You are a biomedical research librarian. Extract 3-5 precise search terms for PubMed.

# Focus on:
# - Specific genes/proteins 
# - Disease subtypes (e.g., "NPM1-mutant AML", "acute myeloid leukemia")
# - Drug/treatment names (e.g., "menin inhibitor", "CAR-T therapy")
# - Key biological processes (e.g., "HOX gene expression", "stem cell differentiation")

# Abstract:
# {abstract}

# Return ONLY a JSON array, no markdown, no explanation:
# ["term1", "term2", "term3"]
# """
    
#     response = model.generate_content(prompt)
#     text = response.text.strip()
    
#     # Clean markdown if present
#     if text.startswith("```"):
#         text = text.split("```")[1]
#         if text.startswith("json"):
#             text = text[4:]
#         text = text.strip()
    
#     search_terms = json.loads(text)
#     progress.log(f"Extracted {len(search_terms)} search terms: {', '.join(search_terms)}", "success")
    
#     return search_terms


# def search_pubmed(search_terms: List[str], max_results: int, progress: ProgressTracker) -> List[str]:
#     """
#     Search PubMed database using NCBI Entrez API
    
#     Args:
#         search_terms: List of search terms from extract_search_terms()
#         max_results: Maximum papers to retrieve per search term
#         progress: Progress tracker
        
#     Returns:
#         List[str]: Unique PubMed IDs (PMIDs)
#     """
#     if not ENTREZ_AVAILABLE:
#         raise ImportError("Biopython required. Install: pip install biopython")
    
#     # Set email for NCBI (required by their policy)
#     Entrez.email = os.environ.get("ENTREZ_EMAIL", "your.email@example.com")
    
#     all_pmids = set()
    
#     for i, term in enumerate(search_terms, 1):
#         progress.log(f"Searching PubMed for: '{term}' ({i}/{len(search_terms)})", "search")
        
#         try:
#             # Execute PubMed search
#             handle = Entrez.esearch(
#                 db="pubmed",
#                 term=term,
#                 retmax=max_results,
#                 sort="relevance",
#                 retmode="xml"
#             )
#             record = Entrez.read(handle)
#             handle.close()
            
#             pmids = record["IdList"]
#             all_pmids.update(pmids)
            
#             progress.log(f"  Found {len(pmids)} papers for '{term}'", "success")
            
#         except Exception as e:
#             progress.log(f"  Error searching '{term}': {str(e)}", "error")
#             continue
    
#     pmid_list = list(all_pmids)
#     progress.log(f"Total unique papers found: {len(pmid_list)}", "success")
    
#     return pmid_list


# def fetch_paper_metadata(pmids: List[str], progress: ProgressTracker) -> List[Dict]:
#     """
#     Fetch detailed metadata for papers from PubMed
    
#     Retrieves: title, abstract, authors, journal, year, PMC ID (for full-text)
    
#     Args:
#         pmids: List of PubMed IDs from search_pubmed()
#         progress: Progress tracker
        
#     Returns:
#         List[Dict]: Paper metadata dictionaries
#     """
#     if not ENTREZ_AVAILABLE:
#         raise ImportError("Biopython required")
    
#     progress.log(f"Fetching metadata for {len(pmids)} papers...", "download")
    
#     Entrez.email = os.environ.get("ENTREZ_EMAIL", "your.email@example.com")
    
#     papers = []
    
#     try:
#         # Fetch all metadata in one batch request (efficient!)
#         handle = Entrez.efetch(
#             db="pubmed",
#             id=pmids,
#             rettype="medline",
#             retmode="xml"
#         )
#         records = Entrez.read(handle)
#         handle.close()
        
#         for record in records['PubmedArticle']:
#             try:
#                 article = record['MedlineCitation']['Article']
                
#                 # Extract basic info
#                 pmid = str(record['MedlineCitation']['PMID'])
#                 title = article['ArticleTitle']
                
#                 # Abstract (can be multi-part)
#                 abstract_parts = article.get('Abstract', {}).get('AbstractText', [])
#                 if isinstance(abstract_parts, list):
#                     abstract = ' '.join([str(part) for part in abstract_parts])
#                 else:
#                     abstract = str(abstract_parts)
                
#                 # Authors (first 3 for brevity)
#                 authors = []
#                 if 'AuthorList' in article:
#                     for author in article['AuthorList'][:3]:
#                         if 'LastName' in author and 'Initials' in author:
#                             authors.append(f"{author['LastName']} {author['Initials']}")
                
#                 # Journal and publication year
#                 journal = article['Journal']['Title']
#                 pub_date = article['Journal']['JournalIssue'].get('PubDate', {})
#                 year = pub_date.get('Year', 'N/A')
                
#                 # Check if full-text is available in PubMed Central (PMC)
#                 pmc_id = None
#                 if 'PubmedData' in record:
#                     for id_obj in record['PubmedData'].get('ArticleIdList', []):
#                         if id_obj.attributes.get('IdType') == 'pmc':
#                             pmc_id = str(id_obj)
                
#                 paper = {
#                     'pmid': pmid,
#                     'title': title,
#                     'abstract': abstract,
#                     'authors': authors,
#                     'journal': journal,
#                     'year': year,
#                     'pmc_id': pmc_id,
#                     'has_fulltext': pmc_id is not None
#                 }
                
#                 papers.append(paper)
                
#             except Exception as e:
#                 progress.log(f"  Error parsing paper: {str(e)}", "error")
#                 continue
        
#         fulltext_count = sum(1 for p in papers if p['has_fulltext'])
#         progress.log(f"Retrieved {len(papers)} papers successfully", "success")
#         progress.log(f"  {fulltext_count} have full-text in PMC, {len(papers) - fulltext_count} abstract-only", "info")
        
#     except Exception as e:
#         progress.log(f"Error fetching metadata: {str(e)}", "error")
    
#     return papers


# def find_literature(abstract: str, max_papers: int = 20, 
#                    progress_callback: Optional[Callable] = None) -> Dict:
#     """
#     MAIN FUNCTION: Find biomedical literature from PubMed
    
#     Complete pipeline:
#     1. Extract search terms from abstract (LLM)
#     2. Search PubMed database (Entrez API)
#     3. Fetch detailed metadata (titles, abstracts, authors, PMC IDs)
    
#     Args:
#         abstract: Research abstract describing your project
#         max_papers: Maximum number of papers to retrieve (default: 20)
#         progress_callback: Optional function to receive progress updates
        
#     Returns:
#         Dict: {
#             "papers": [
#                 {
#                     "pmid": "12345678",
#                     "title": "Paper title",
#                     "abstract": "Full abstract text",
#                     "authors": ["Smith J", "Doe A"],
#                     "journal": "Nature Medicine",
#                     "year": "2023",
#                     "pmc_id": "PMC9876543" or None,
#                     "has_fulltext": True/False
#                 },
#                 ...
#             ],
#             "search_terms": ["menin inhibitor", "NPM1-mutant AML", ...],
#             "stats": {
#                 "total_papers": 15,
#                 "with_fulltext": 8,
#                 "abstract_only": 7
#             }
#         }
#     """
#     progress = ProgressTracker(progress_callback)
    
#     progress.log("=" * 60, "info")
#     progress.log("🔬 AGENT 1: PUBMED LITERATURE FINDER", "info")
#     progress.log("=" * 60, "info")
    
#     # Step 1: Extract search terms
#     search_terms = extract_search_terms(abstract, progress)
    
#     # Step 2: Search PubMed
#     pmids = search_pubmed(search_terms, max_results=max_papers, progress=progress)
    
#     # Step 3: Fetch detailed metadata
#     papers = fetch_paper_metadata(pmids, progress=progress)
    
#     # Calculate statistics
#     stats = {
#         "total_papers": len(papers),
#         "with_fulltext": sum(1 for p in papers if p['has_fulltext']),
#         "abstract_only": sum(1 for p in papers if not p['has_fulltext'])
#     }
    
#     progress.log("=" * 60, "info")
#     progress.log(f"✅ AGENT 1 COMPLETE: Found {stats['total_papers']} papers", "complete")
#     progress.log(f"   {stats['with_fulltext']} with full-text, {stats['abstract_only']} abstract-only", "info")
#     progress.log("=" * 60, "info")
    
#     return {
#         "papers": papers,
#         "search_terms": search_terms,
#         "stats": stats
#     }


# if __name__ == "__main__":
#     # Quick test
#     test_abstract = """
#     We investigate menin inhibitors for NPM1-mutant AML treatment. 
#     Does HOX gene expression predict response to menin inhibitors?
#     """
    
#     try:
#         result = find_literature(test_abstract, max_papers=5)
        
#         print(f"\n📄 Sample papers:")
#         for i, paper in enumerate(result['papers'][:2], 1):
#             print(f"\n{i}. {paper['title']}")
#             print(f"   PMID: {paper['pmid']}, Full-text: {paper['has_fulltext']}")
        
#         with open("agent1_output.json", "w") as f:
#             json.dump(result, indent=2, fp=f)
#         print(f"\n✅ Saved to agent1_output.json")
        
#     except Exception as e:
#         print(f"❌ Error: {e}")