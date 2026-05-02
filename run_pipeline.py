#!/usr/bin/env python3
"""
GROQ-POWERED PIPELINE RUNNER
No more Gemini quota issues!
Free tier: 14,400 requests/day (vs Gemini's 15/min)
"""
 
import os
import sys
import json
from pathlib import Path  
from dotenv import load_dotenv
 
BASE_DIR = Path(__file__).parent
env_path = BASE_DIR / "research_lab" / ".env"

if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"✅ Loaded .env from {env_path}")
else:
    print(f"❌ Could not find .env at {env_path}") 
print("🔍 Checking setup...")
 
# Check dependencies
missing_deps = []
try:
    from groq import Groq
    print("  ✓ groq")
except ImportError:
    missing_deps.append("groq")
 
try:
    from Bio import Entrez
    print("  ✓ biopython")
except ImportError:
    missing_deps.append("biopython")
 
try:
    import requests
    print("  ✓ requests")
except ImportError:
    missing_deps.append("requests")
 
if missing_deps:
    print(f"\n❌ Missing packages: {', '.join(missing_deps)}")
    print(f"\nInstall with:")
    print(f"  pip install {' '.join(missing_deps)}")
    sys.exit(1)
 
# Check API keys
missing_keys = []
if not os.environ.get("GROQ_API_KEY"):
    missing_keys.append("GROQ_API_KEY")
if not os.environ.get("RAGIE_API_KEY"):
    missing_keys.append("RAGIE_API_KEY")
 
if missing_keys:
    print(f"\n❌ Missing in .env file: {', '.join(missing_keys)}")
    print("\nAdd to your .env file:")
    if "GROQ_API_KEY" in missing_keys:
        print("  GROQ_API_KEY=your-groq-key")
    if "RAGIE_API_KEY" in missing_keys:
        print("  RAGIE_API_KEY=your-ragie-key")
    print("\nGet keys:")
    print("  Groq: https://console.groq.com")
    print("  Ragie: https://ragie.ai")
    sys.exit(1)
 
print("  ✓ GROQ_API_KEY")
print("  ✓ RAGIE_API_KEY")
print("\n✅ All checks passed!\n")
 
# Import agents
from research_lab.literature import find_literature
from research_lab.rag import extract_and_build_rag
 
 
def run_full_pipeline(abstract: str, max_papers: int = 15):
    """
    Run complete Phase 1 pipeline with GROQ
    14,400 free requests/day - no quota worries!
    """
    print("=" * 70)
    print("🚀 LITERATURE REVIEW PIPELINE (Groq-Powered)")
    print("=" * 70)
    print(f"\nAbstract: {abstract[:150]}...")
    print(f"Max papers: {max_papers}\n")
    
    # ==================== AGENT 1: PubMed Search ====================
    print("\n" + "▶" * 35)
    print("AGENT 1: PubMed Literature Finder (Groq)")
    print("▶" * 35 + "\n")
    
    agent1_result = find_literature(abstract, max_papers=max_papers)
    
    papers = agent1_result['papers']
    search_terms = agent1_result['search_terms']
    stats1 = agent1_result['stats']
    
    # Save Agent 1 output
    with open("agent1_output.json", "w") as f:
        json.dump(agent1_result, indent=2, fp=f)
    print(f"\n💾 Agent 1 output saved: agent1_output.json")
    
    if len(papers) == 0:
        print("\n❌ No papers found. Try modifying your abstract.")
        return None
    
    # ==================== AGENT 2: RAG + Extraction ====================
    print("\n" + "▶" * 35)
    print("AGENT 2: Results Extractor + Ragie RAG (Groq, Threaded)")
    print("▶" * 35 + "\n")
    
    agent2_result = extract_and_build_rag(papers)
    
    extracted_results = agent2_result['extracted_results']
    ragie_client = agent2_result['ragie_client']
    stats2 = agent2_result['stats']
    
    # Save Agent 2 output
    with open("agent2_output.json", "w") as f:
        json.dump({
            "extracted_results": extracted_results,
            "stats": stats2
        }, indent=2, fp=f)
    print(f"\n💾 Agent 2 output saved: agent2_output.json")
    
    # ==================== DEMO: RAG Queries ====================
    print("\n" + "=" * 70)
    print("🔍 RAGIE RAG DATABASE DEMO: Semantic Search")
    print("=" * 70)
    
    demo_queries = [
        "What is the relationship between HOXA9 expression and treatment response?",
        "What experimental methods were used in these studies?",
        "What were the sample sizes and study limitations?"
    ]
    
    for query in demo_queries:
        print(f"\n📝 Query: {query}")
        
        try:
            results = ragie_client.query(query, top_k=2)
            
            if results:
                for i, result in enumerate(results, 1):
                    print(f"\n  Result {i} (Relevance: {result['score']:.3f}):")
                    print(f"  Paper: {result['metadata']['title'][:60]}...")
                    print(f"  PMID: {result['metadata']['pmid']}, Year: {result['metadata']['year']}")
                    print(f"  Excerpt: {result['text'][:150]}...")
            else:
                print("  No results found")
                
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
    
    # ==================== SUMMARY ====================
    print("\n" + "=" * 70)
    print("📊 PIPELINE SUMMARY")
    print("=" * 70)
    
    print(f"\n🔬 Agent 1 (PubMed Finder):")
    print(f"  • Search terms: {', '.join(search_terms)}")
    print(f"  • Papers found: {stats1['total_papers']}")
    print(f"  • With full-text: {stats1['with_fulltext']}")
    print(f"  • Abstract-only: {stats1['abstract_only']}")
    
    print(f"\n📊 Agent 2 (Ragie RAG + Extraction):")
    print(f"  • Papers processed: {stats2['papers_processed']}")
    print(f"  • Total key findings: {stats2['total_findings']}")
    print(f"  • LLM: ⚡ Groq (14,400/day free!)")
    print(f"  • RAG: ☁️ Ragie.ai")
    print(f"  • Threading: ✅ Enabled (2.6x faster)")
    
    print(f"\n📄 Sample Extracted Results:")
    for i, result in enumerate(extracted_results[:3], 1):
        print(f"\n{i}. {result['title']}")
        print(f"   Authors: {', '.join(result['authors'])} et al.")
        print(f"   Journal: {result['journal']} ({result['year']})")
        print(f"   Methods: {result['methods'][:80]}...")
        if result['key_findings']:
            print(f"   Key Finding: {result['key_findings'][0][:100]}...")
    
    print("\n" + "=" * 70)
    print("✅ PHASE 1 COMPLETE!")
    print("=" * 70)
    print("\n💡 Groq Benefits:")
    print("  • 14,400 requests/day (vs Gemini 15/min)")
    print("  • 10x faster responses")
    print("  • No quota worries for hackathon!")
    
    print("\nNext steps:")
    print("  • Build Agent 3 (Analysis) to synthesize findings")
    print("  • Build Agent 4 (Critic) for debate cycles")
    
    return {
        "agent1": agent1_result,
        "agent2": agent2_result,
        "ragie_client": ragie_client
    }
 
 
if __name__ == "__main__":
    # Your research abstract
    research_abstract = """
   I am researching how NPM1 mutations in Acute Myeloid Leukemia (AML) respond to menin inhibitors. I specifically want to know if high expression of the HOXA9 and MEIS1 genes can predict if a patient will have a good treatment response. Additionally, I am looking for data on combining menin inhibitors with CAR-T cell therapy
    """
    
    try:
        result = run_full_pipeline(research_abstract, max_papers=12)
        
        if result:
            print("\n🎉 Pipeline completed successfully with Groq!")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)






# #!/usr/bin/env python3
# """
# MAIN PIPELINE RUNNER
# Executes Agent 1 (PubMed) → Agent 2 (Ragie RAG) in sequence
# """

# import os
# import sys
# import json
# from dotenv import load_dotenv
# from pathlib import Path

# # Load environment variables from research_lab/.env
# BASE_DIR = Path(__file__).parent
# env_path = BASE_DIR / "research_lab" / ".env"

# if env_path.exists():
#     load_dotenv(dotenv_path=env_path)
#     print(f"✅ Loaded .env from {env_path}")
# else:
#     print(f"❌ Could not find .env at {env_path}")
# # Check all required dependencies and API keys
# print("🔍 Checking setup...")

# # Check dependencies
# missing_deps = []
# try:
#     import google.generativeai
#     print("  ✓ google-generativeai")
# except ImportError:
#     missing_deps.append("google-generativeai")

# try:
#     from Bio import Entrez
#     print("  ✓ biopython")
# except ImportError:
#     missing_deps.append("biopython")

# try:
#     import requests
#     print("  ✓ requests")
# except ImportError:
#     missing_deps.append("requests")

# if missing_deps:
#     print(f"\n❌ Missing packages: {', '.join(missing_deps)}")
#     print(f"\nInstall with:")
#     print(f"  pip install {' '.join(missing_deps)}")
#     sys.exit(1)

# # Check API keys
# missing_keys = []
# if not os.environ.get("GOOGLE_API_KEY"):
#     missing_keys.append("GOOGLE_API_KEY")
# if not os.environ.get("RAGIE_API_KEY"):
#     missing_keys.append("RAGIE_API_KEY")

# if missing_keys:
#     print(f"\n❌ Missing in .env file: {', '.join(missing_keys)}")
#     print("\nAdd to your .env file:")
#     if "GOOGLE_API_KEY" in missing_keys:
#         print("  GOOGLE_API_KEY=your-google-key")
#     if "RAGIE_API_KEY" in missing_keys:
#         print("  RAGIE_API_KEY=your-ragie-key")
#     print("\nGet keys:")
#     print("  Google: https://aistudio.google.com/app/apikey")
#     print("  Ragie: https://ragie.ai")
#     sys.exit(1)

# print("  ✓ GOOGLE_API_KEY")
# print("  ✓ RAGIE_API_KEY")
# print("\n✅ All checks passed!\n")

# # Import agents
# from research_lab.literature import find_literature
# from research_lab.rag import extract_and_build_rag

# def run_full_pipeline(abstract: str, max_papers: int = 15):
#     """
#     Run complete Phase 1 pipeline
    
#     Agent 1: PubMed search → papers
#     Agent 2: Build RAG + extract results → structured data + searchable database
    
#     Args:
#         abstract: Your research abstract
#         max_papers: Maximum papers to analyze (default: 15)
#     """
#     print("=" * 70)
#     print("🚀 LITERATURE REVIEW PIPELINE (Phase 1)")
#     print("=" * 70)
#     print(f"\nAbstract: {abstract[:150]}...")
#     print(f"Max papers: {max_papers}\n")
    
#     # ==================== AGENT 1: PubMed Search ====================
#     print("\n" + "▶" * 35)
#     print("AGENT 1: PubMed Literature Finder")
#     print("▶" * 35 + "\n")
    
#     print("⏳ Calling Gemini API to extract search terms... (may take 10-30s)")
#     print("⏳ Then searching PubMed... (may take another 30-60s)")
#     print("   If this hangs for >2 minutes, check your API keys and network.\n")
#     agent1_result = find_literature(abstract, max_papers=max_papers)
    
#     papers = agent1_result['papers']
#     search_terms = agent1_result['search_terms']
#     stats1 = agent1_result['stats']
    
#     # Save Agent 1 output
#     with open("agent1_output.json", "w") as f:
#         json.dump(agent1_result, indent=2, fp=f)
#     print(f"\n💾 Agent 1 output saved: agent1_output.json")
    
#     if len(papers) == 0:
#         print("\n❌ No papers found. Try modifying your abstract.")
#         return None
    
#     # ==================== AGENT 2: RAG + Extraction ====================
#     print("\n" + "▶" * 35)
#     print("AGENT 2: Results Extractor + Ragie RAG")
#     print("▶" * 35 + "\n")
    
#     agent2_result = extract_and_build_rag(papers)
    
#     extracted_results = agent2_result['extracted_results']
#     ragie_client = agent2_result['ragie_client']
#     stats2 = agent2_result['stats']
    
#     # Save Agent 2 output (without ragie_client object)
#     with open("agent2_output.json", "w") as f:
#         json.dump({
#             "extracted_results": extracted_results,
#             "stats": stats2
#         }, indent=2, fp=f)
#     print(f"\n💾 Agent 2 output saved: agent2_output.json")
    
#     # ==================== DEMO: RAG Queries ====================
#     print("\n" + "=" * 70)
#     print("🔍 RAGIE RAG DATABASE DEMO: Semantic Search")
#     print("=" * 70)
    
#     demo_queries = [
#         "What is the relationship between HOXA9 expression and treatment response?",
#         "What experimental methods were used in these studies?",
#         "What were the sample sizes and study limitations?"
#     ]
    
#     for query in demo_queries:
#         print(f"\n📝 Query: {query}")
        
#         try:
#             results = ragie_client.query(query, top_k=2)
            
#             if results:
#                 for i, result in enumerate(results, 1):
#                     print(f"\n  Result {i} (Relevance: {result['score']:.3f}):")
#                     print(f"  Paper: {result['metadata']['title'][:60]}...")
#                     print(f"  PMID: {result['metadata']['pmid']}, Year: {result['metadata']['year']}")
#                     print(f"  Excerpt: {result['text'][:150]}...")
#             else:
#                 print("  No results found")
                
#         except Exception as e:
#             print(f"  ✗ Error: {str(e)}")
    
#     # ==================== SUMMARY ====================
#     print("\n" + "=" * 70)
#     print("📊 PIPELINE SUMMARY")
#     print("=" * 70)
    
#     print(f"\n🔬 Agent 1 (PubMed Finder):")
#     print(f"  • Search terms: {', '.join(search_terms)}")
#     print(f"  • Papers found: {stats1['total_papers']}")
#     print(f"  • With full-text: {stats1['with_fulltext']}")
#     print(f"  • Abstract-only: {stats1['abstract_only']}")
    
#     print(f"\n📊 Agent 2 (Ragie RAG + Extraction):")
#     print(f"  • Papers processed: {stats2['papers_processed']}")
#     print(f"  • Total key findings: {stats2['total_findings']}")
#     print(f"  • RAG service: ☁️ {stats2['rag_service']}")
    
#     print(f"\n📄 Sample Extracted Results:")
#     for i, result in enumerate(extracted_results[:3], 1):
#         print(f"\n{i}. {result['title']}")
#         print(f"   Authors: {', '.join(result['authors'])} et al.")
#         print(f"   Journal: {result['journal']} ({result['year']})")
#         print(f"   Methods: {result['methods'][:80]}...")
#         if result['key_findings']:
#             print(f"   Key Finding: {result['key_findings'][0][:100]}...")
    
#     print("\n" + "=" * 70)
#     print("✅ PHASE 1 COMPLETE!")
#     print("=" * 70)
#     print("\nNext steps:")
#     print("  • Review agent1_output.json and agent2_output.json")
#     print("  • Build Agent 3 (Analysis) to synthesize findings")
#     print("  • Build Agent 4 (Critic) for debate cycles")
#     print("  • Query RAG database: ragie_client.query('your question')")
    
#     return {
#         "agent1": agent1_result,
#         "agent2": agent2_result,
#         "ragie_client": ragie_client
#     }


# if __name__ == "__main__":
#     # Your research abstract
#     research_abstract = """
#     We are developing an AI system for optimizing treatment sequencing in acute myeloid leukemia (AML) 
#     patients with NPM1 mutations. Our approach focuses on menin inhibitor therapy combined with CAR-T 
#     cell therapy. A critical question is whether HOX gene expression profiles, particularly HOXA9 and 
#     MEIS1, can predict treatment response to menin inhibitors in NPM1-mutant AML. We hypothesize that 
#     patients with high HOXA9 and MEIS1 expression will show better response to menin inhibitors, and 
#     that pre-treatment with menin inhibitors may enhance CAR-T therapy efficacy by altering the 
#     leukemic stem cell compartment. We are using single-cell RNA-seq data from the Beat AML 2.0 cohort 
#     to build predictive models.
#     """
    
#     try:
#         # Run the full pipeline
#         result = run_full_pipeline(research_abstract, max_papers=12)
        
#         if result:
#             print("\n🎉 Pipeline completed successfully!")
#             print("\n💡 TIP: You can now query the RAG database programmatically:")
#             print("     ragie_client = result['ragie_client']")
#             print("     results = ragie_client.query('your research question')")
        
#     except KeyboardInterrupt:
#         print("\n\n⚠️  Pipeline interrupted by user")
#         sys.exit(0)
#     except Exception as e:
#         print(f"\n❌ ERROR: {str(e)}")
#         import traceback
#         traceback.print_exc()
#         sys.exit(1)