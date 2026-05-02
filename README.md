# ATSS

YES! This is WAY better for a hackathon. Much cleaner demo, shows LangGraph strengths. Here's the streamlined version:
Research Analysis Dashboard - 4 Agent System
The Flow:
User Abstract 
    ↓
[Agent 1: Literature Finder] → finds 5-10 relevant papers
    ↓
[Agent 2: Results Extractor] → pulls key findings/data from papers
    ↓
[Agent 3: Analysis Agent] → synthesizes insights
    ↓
[Multi-Agent Debate Loop - 3 cycles]
    Critic Agent ↔ Results Agent ↔ Analysis Agent
    ↓
[Final Decision/Recommendation]

4-Person Split (MUCH simpler):
Person 1: Agent 1 (Literature Finder)
Tools: Claude API + web_search tool
Input: Abstract text
Output: List of 5-10 papers with titles, abstracts, URLs
python# Pseudocode
def literature_finder(abstract):
    search_query = extract_key_terms(abstract)
    papers = web_search(search_query)
    return {"papers": papers, "search_terms": [...]}

Person 2: Agent 2 (Results Extractor)
Tools: Claude API + web_fetch
Input: Paper list from Agent 1
Output: Extracted key results, methods, datasets
pythondef results_extractor(papers):
    results = []
    for paper in papers:
        content = fetch_paper(paper.url)
        extracted = extract_results_section(content)
        results.append(extracted)
    return {"results": results}

Person 3: LangGraph + Multi-Agent Debate
Tools: LangGraph orchestration
Agents: Critic, Results Re-evaluator, Analysis Refiner
Does: 3-cycle debate loop → convergence
python# LangGraph cycle
for i in range(3):
    critic_feedback = critic_agent(current_analysis)
    refined_results = results_agent(critic_feedback)
    updated_analysis = analysis_agent(refined_results)

Person 4: UI + Agent 3 (Initial Analysis)
Part A: Build initial analysis agent
Part B: Streamlit dashboard showing each step
pythondef analysis_agent(results):
    synthesis = synthesize_findings(results)
    gaps = identify_gaps(results)
    return {"synthesis": synthesis, "gaps": gaps}

Example Demo Flow (X-Menin focused):
User Input:

"We're investigating menin inhibitors for NPM1-mutant AML. Key question: Does HOX gene expression predict treatment response?"

Agent 1 Output:

Found 8 papers on menin inhibitors + NPM1-AML
Search terms: "menin inhibitor", "NPM1 mutation", "HOX genes", "AML response"

Agent 2 Output:

Paper 1: HOXA9/MEIS1 overexpression in responders (p<0.001)
Paper 2: 65% response rate in NPM1+ patients
Paper 3: FLT3-ITD may reduce efficacy

Agent 3 (Initial Analysis):

"Strong correlation between HOX signature and response. Suggests predictive biomarker potential."

Debate Cycle 1:

Critic: "But sample sizes are small (n=45 in Paper 1). Need validation."
Results: "Paper 3 had n=156, confirms HOXA9 signal"
Analysis: "Updating: Consistent across studies despite size variance"

Debate Cycle 2:

Critic: "What about FLT3-ITD confounding?"
Results: "Paper 3 shows FLT3-ITD reduces response even with high HOX"
Analysis: "Refinement: HOX predicts response in FLT3-WT, unclear in FLT3-ITD"

Debate Cycle 3:

Critic: "Can we recommend clinical use?"
Analysis: "Conclusion: HOX signature is promising biomarker, needs prospective trial"

Final Output:

"✅ Recommendation: HOX/MEIS signature shows strong predictive potential for menin inhibitor response in NPM1+ AML. Validated across 3 independent studies (n=45, n=156, n=89). Action: Design prospective biomarker trial. Caveat: FLT3-ITD patients need separate analysis."


Tech Stack (Keep it Simple):

Claude API for all agents (no local models!)
LangGraph for orchestration + debate cycles
Streamlit for UI (1 file, fast)
Simple JSON for state passing


6-Hour Timeline:
Hour 1: Setup + interface contracts
Hour 2-3: Build 4 agents in parallel
Hour 4: Person 3 wires LangGraph
Hour 5: Integration + testing
Hour 6: UI polish + demo prep

This is MUCH better. Want me to:

Write the LangGraph skeleton for Person 3?
Generate example abstract + expected outputs?
Create the agent prompt templates?
