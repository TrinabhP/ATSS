import os
from typing import TypedDict, Literal
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langchain_anthropic import ChatAnthropic
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import HumanMessage

load_dotenv()

MAX_DEBATE_CYCLES = 3


# ── Shared State ─────────────────────────────────────────────────────────────
class State(TypedDict):
    query: str
    sources: list[str]      # raw source content from researcher
    draft_answer: str       # current answer from result_bot
    critique: str           # feedback from critic
    iteration: int          # debate cycle count


# ── Models & Tools ────────────────────────────────────────────────────────────
llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0.3)
search = TavilySearchResults(max_results=5)


# ── Agent Nodes ───────────────────────────────────────────────────────────────

def researcher(state: State) -> dict:
    """Searches the web and returns formatted sources."""
    print("\n[RESEARCHER] Searching for sources...")

    results = search.invoke(state["query"])

    sources = []
    for r in results:
        url = r.get("url", "unknown")
        content = r.get("content", "")
        sources.append(f"[{url}]\n{content}")

    print(f"[RESEARCHER] Found {len(sources)} sources.")
    return {"sources": sources}


def result_bot(state: State) -> dict:
    """Synthesizes sources + any critique into a comprehensive answer."""
    iteration = state.get("iteration", 0)
    critique = state.get("critique", "")
    print(f"\n[RESULT BOT] Synthesizing answer (iteration {iteration + 1})...")

    sources_block = "\n\n---\n\n".join(state.get("sources", []))

    critique_section = ""
    if critique:
        critique_section = f"""
## Critique to Address
{critique}

Revise your answer to specifically address each point of critique above.
"""

    prompt = f"""You are a result synthesizer. Form a comprehensive, well-structured answer.

## Research Query
{state["query"]}

## Sources
{sources_block}
{critique_section}
## Instructions
- Cite sources by URL when making specific claims
- Be accurate; avoid unsupported assertions
- If revising, explicitly note how you addressed the critique
- Use clear headings and bullet points where helpful"""

    response = llm.invoke([HumanMessage(content=prompt)])
    print(f"[RESULT BOT] Answer drafted ({len(response.content)} chars).")
    return {
        "draft_answer": response.content,
        "iteration": iteration + 1,
    }


def critic(state: State) -> dict:
    """Critiques the current draft answer and decides if it's ready."""
    print(f"\n[CRITIC] Reviewing iteration {state.get('iteration', 1)}...")

    prompt = f"""You are a rigorous critic. Evaluate this answer carefully.

## Original Query
{state["query"]}

## Current Answer (Iteration {state.get("iteration", 1)})
{state["draft_answer"]}

## Your Task
Identify specific issues in these categories:
1. **Unsupported claims** — assertions not backed by the provided sources
2. **Logical gaps** — missing reasoning or incomplete arguments
3. **Missing perspectives** — important viewpoints not considered
4. **Evidence quality** — claims that need stronger support

If the answer is comprehensive, accurate, and well-supported, start your response with:
  APPROVED: <brief reason>

Otherwise start with:
  NEEDS REVISION: <brief summary>
and then list specific, actionable feedback."""

    response = llm.invoke([HumanMessage(content=prompt)])
    critique_text = response.content
    status = "APPROVED" if critique_text.upper().startswith("APPROVED") else "NEEDS REVISION"
    print(f"[CRITIC] Verdict: {status}")
    return {"critique": critique_text}


# ── Router ────────────────────────────────────────────────────────────────────

def should_continue(state: State) -> Literal["result_bot", "__end__"]:
    """Routes back to result_bot or ends the debate."""
    if state.get("iteration", 0) >= MAX_DEBATE_CYCLES:
        print("\n[ROUTER] Max debate cycles reached. Ending.")
        return END
    if state.get("critique", "").upper().startswith("APPROVED"):
        print("\n[ROUTER] Critic approved the answer. Ending.")
        return END
    print(f"\n[ROUTER] Sending back to result_bot (iteration {state['iteration']}).")
    return "result_bot"


# ── Build Graph ───────────────────────────────────────────────────────────────

builder = StateGraph(State)

builder.add_node("researcher", researcher)
builder.add_node("result_bot", result_bot)
builder.add_node("critic", critic)

builder.add_edge(START, "researcher")
builder.add_edge("researcher", "result_bot")
builder.add_edge("result_bot", "critic")
builder.add_conditional_edges("critic", should_continue)

graph = builder.compile()


# ── Runner ────────────────────────────────────────────────────────────────────

def run(query: str) -> str:
    """Run the multi-agent debate system on a query and return the final answer."""
    print(f"\n{'='*60}")
    print(f"QUERY: {query}")
    print(f"{'='*60}")

    final_state = graph.invoke({
        "query": query,
        "sources": [],
        "draft_answer": "",
        "critique": "",
        "iteration": 0,
    })

    print(f"\n{'='*60}")
    print(f"FINAL ANSWER (after {final_state['iteration']} debate cycle(s))")
    print(f"{'='*60}")
    print(final_state["draft_answer"])
    return final_state["draft_answer"]


if __name__ == "__main__":
    run("What are the latest breakthroughs in menin inhibitors for AML treatment?")
