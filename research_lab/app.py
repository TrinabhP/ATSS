"""
app.py — Streamlit dashboard for LabOS Research Analysis Engine.
Imports run_research from graph.py. All styles are inline.
"""

import streamlit as st

from state import ResearchState, empty_state

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_ABSTRACT_LENGTH = 4000
MIN_ABSTRACT_LENGTH = 20

STAGE_IDS = [
    "literature_finder",
    "results_extractor",
    "initial_analysis",
    "debate_round_1",
    "debate_round_2",
    "debate_round_3",
    "final_recommendation",
]

STAGE_LABELS = [
    "📚 Literature",
    "🔬 Extraction",
    "🧠 Analysis",
    "⚔️ Debate 1",
    "⚔️ Debate 2",
    "⚔️ Debate 3",
    "🏆 Final",
]

# ---------------------------------------------------------------------------
# Page config & global CSS
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="LabOS — Research Analysis Engine",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

    :root {
        --bg:        #0a0e1a;
        --card-bg:   #111827;
        --accent:    #3b82f6;
        --success:   #10b981;
        --danger:    #ef4444;
        --warning:   #f59e0b;
        --muted:     #6b7280;
        --text:      #e0e6f0;
    }

    html, body, [class*="css"] {
        background-color: var(--bg) !important;
        color: var(--text) !important;
        font-family: 'IBM Plex Sans', sans-serif;
    }

    h1, h2, h3, h4, .mono {
        font-family: 'IBM Plex Mono', monospace !important;
    }

    /* Cards */
    .lab-card {
        background: var(--card-bg);
        border-radius: 10px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 1rem;
        border: 1px solid #1f2937;
    }

    /* Pipeline stage cards */
    .stage-card {
        background: var(--card-bg);
        border-radius: 8px;
        padding: 0.6rem 0.4rem;
        text-align: center;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.72rem;
        border: 1px solid #1f2937;
        color: var(--muted);
        transition: all 0.3s;
    }
    .stage-card.active {
        border-color: var(--accent);
        color: var(--accent);
        box-shadow: 0 0 12px rgba(59,130,246,0.35);
    }
    .stage-card.done {
        border-color: var(--success);
        color: var(--success);
    }

    /* Confidence badges */
    .badge-high     { background:#064e3b; color:#10b981; padding:3px 10px; border-radius:20px; font-family:'IBM Plex Mono',monospace; font-size:0.85rem; }
    .badge-moderate { background:#451a03; color:#f59e0b; padding:3px 10px; border-radius:20px; font-family:'IBM Plex Mono',monospace; font-size:0.85rem; }
    .badge-low      { background:#450a0a; color:#ef4444; padding:3px 10px; border-radius:20px; font-family:'IBM Plex Mono',monospace; font-size:0.85rem; }

    /* Debate color bands */
    .critic-band   { border-left: 4px solid #ef4444; padding-left: 0.8rem; margin-bottom: 0.8rem; }
    .results-band  { border-left: 4px solid #3b82f6; padding-left: 0.8rem; margin-bottom: 0.8rem; }
    .analysis-band { border-left: 4px solid #10b981; padding-left: 0.8rem; margin-bottom: 0.8rem; }

    /* Final recommendation card */
    .final-card {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        border: 1px solid var(--accent);
        border-radius: 12px;
        padding: 1.6rem;
        margin-top: 1rem;
    }

    /* Streamlit overrides */
    .stTextArea textarea {
        background: var(--card-bg) !important;
        color: var(--text) !important;
        border: 1px solid #374151 !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
    }
    .stButton > button {
        background: var(--accent) !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-weight: 600 !important;
        padding: 0.5rem 1.5rem !important;
    }
    .stButton > button:disabled {
        background: #374151 !important;
        color: var(--muted) !important;
        cursor: not-allowed !important;
    }
    div[data-testid="stExpander"] {
        background: var(--card-bg) !important;
        border: 1px solid #1f2937 !important;
        border-radius: 8px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------

def _init_session():
    if "result" not in st.session_state:
        st.session_state.result = None
    if "running" not in st.session_state:
        st.session_state.running = False
    if "error_msg" not in st.session_state:
        st.session_state.error_msg = None
    if "abstract" not in st.session_state:
        st.session_state.abstract = ""


_init_session()


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div style="padding: 1.5rem 0 0.5rem 0;">
        <h1 style="font-family:'IBM Plex Mono',monospace; font-size:2rem; margin:0; color:#e0e6f0;">
            🧬 LabOS
        </h1>
        <p style="color:#6b7280; font-family:'IBM Plex Mono',monospace; font-size:0.9rem; margin:0.3rem 0 0 0;">
            Multi-Agent Research Analysis Engine · Powered by Claude
        </p>
    </div>
    <hr style="border-color:#1f2937; margin: 1rem 0;">
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Input section
# ---------------------------------------------------------------------------

abstract_input = st.text_area(
    "Research Abstract or Question",
    placeholder=(
        "Paste a research abstract or question here.\n\n"
        "Example: 'Does HOX gene expression predict treatment response to menin inhibitors "
        "in NPM1-mutant acute myeloid leukemia patients?'"
    ),
    height=140,
    max_chars=MAX_ABSTRACT_LENGTH,
    disabled=st.session_state.running,
    key="abstract_input",
)

char_count = len(abstract_input) if abstract_input else 0
col_char, col_btn = st.columns([3, 1])

with col_char:
    if char_count > 0:
        color = "#6b7280" if char_count < MAX_ABSTRACT_LENGTH else "#ef4444"
        st.markdown(
            f'<p style="color:{color}; font-size:0.78rem; font-family:\'IBM Plex Mono\',monospace;">'
            f"{char_count}/{MAX_ABSTRACT_LENGTH} characters</p>",
            unsafe_allow_html=True,
        )
    if char_count >= MAX_ABSTRACT_LENGTH:
        st.warning(f"Abstract truncated to {MAX_ABSTRACT_LENGTH} characters.")

with col_btn:
    launch_disabled = (
        char_count < MIN_ABSTRACT_LENGTH or st.session_state.running
    )
    launch_clicked = st.button(
        "🚀 Launch Analysis" if not st.session_state.running else "⏳ Running...",
        disabled=launch_disabled,
        use_container_width=True,
    )

# ---------------------------------------------------------------------------
# Placeholders for live updates
# ---------------------------------------------------------------------------

pipeline_status_placeholder = st.empty()
st.markdown("<br>", unsafe_allow_html=True)
results_placeholder = st.empty()


# ---------------------------------------------------------------------------
# Pipeline status bar
# ---------------------------------------------------------------------------

def render_pipeline_status(current_stage: str, result: ResearchState | None):
    """Render the 7-stage pipeline status bar."""
    completed_stages = set()
    if result:
        # All stages are done if we have a final result
        completed_stages = set(STAGE_IDS)
    elif current_stage:
        # Mark stages before current as done
        if current_stage in STAGE_IDS:
            idx = STAGE_IDS.index(current_stage)
            completed_stages = set(STAGE_IDS[:idx])

    st.markdown(
        '<p style="font-family:\'IBM Plex Mono\',monospace; font-size:0.8rem; color:#6b7280; margin-bottom:0.4rem;">PIPELINE STATUS</p>',
        unsafe_allow_html=True,
    )
    cols = st.columns(7)
    for i, (stage_id, label) in enumerate(zip(STAGE_IDS, STAGE_LABELS)):
        with cols[i]:
            if result:
                css_class = "stage-card done"
            elif stage_id == current_stage:
                css_class = "stage-card active"
            elif stage_id in completed_stages:
                css_class = "stage-card done"
            else:
                css_class = "stage-card"
            st.markdown(
                f'<div class="{css_class}">{label}</div>',
                unsafe_allow_html=True,
            )


# Render initial pipeline status (updated live during streaming)
with pipeline_status_placeholder.container():
    render_pipeline_status("", st.session_state.result if not st.session_state.running else None)


# ---------------------------------------------------------------------------
# Results rendering
# ---------------------------------------------------------------------------

def render_papers(papers: list, search_terms: list = None):
    with st.expander(f"📚 Papers Found ({len(papers)})", expanded=False):
        if search_terms:
            terms_str = "  ".join(f"`{t}`" for t in search_terms)
            st.markdown(f"**Search terms:** {terms_str}")
            st.markdown("---")
        for i, paper in enumerate(papers, 1):
            score = paper.get("relevance_score")
            score_str = f" · relevance {score:.2f}" if score is not None else ""
            st.markdown(
                f"**{i}. [{paper['title']}]({paper['url']})**{score_str}",
                unsafe_allow_html=False,
            )
            if paper.get("abstract"):
                st.markdown(
                    f'<p style="color:#9ca3af; font-size:0.85rem;">{paper["abstract"][:300]}{"..." if len(paper["abstract"]) > 300 else ""}</p>',
                    unsafe_allow_html=True,
                )
            st.markdown("---")


def render_extracted_results(results: list):
    with st.expander(f"🔬 Extracted Results ({len(results)} papers)", expanded=False):
        for result in results:
            st.markdown(f"**{result['paper_title']}**")
            col_meta, col_findings = st.columns([1, 2])
            with col_meta:
                if result.get("sample_size"):
                    st.markdown(f"**Sample size:** `{result['sample_size']}`")
                if result.get("methods"):
                    st.markdown(
                        f'<p style="font-size:0.83rem; color:#9ca3af;">{result["methods"][:200]}</p>',
                        unsafe_allow_html=True,
                    )
                if result.get("datasets"):
                    st.markdown(
                        f'<p style="font-size:0.83rem; color:#9ca3af;"><em>Data: {result["datasets"][:120]}</em></p>',
                        unsafe_allow_html=True,
                    )
            with col_findings:
                if result.get("key_findings"):
                    st.markdown("**Key findings:**")
                    for finding in result["key_findings"][:6]:
                        st.markdown(f"- {finding}")
            if result.get("limitations"):
                st.markdown(
                    f'<p style="color:#6b7280; font-size:0.8rem; margin-top:0.2rem;"><em>⚠ Limitations: {result["limitations"][:240]}</em></p>',
                    unsafe_allow_html=True,
                )
            st.markdown("---")


def render_initial_analysis(synthesis: str, gaps: list):
    with st.expander("🧠 Initial Analysis", expanded=False):
        st.markdown(synthesis)
        if gaps:
            st.markdown("**Identified Gaps & Inconsistencies:**")
            for gap in gaps:
                st.markdown(f"- {gap}")


def render_debate_round(round_data: dict):
    rn = round_data["round_number"]
    with st.expander(f"⚔️ Debate Round {rn}", expanded=False):
        st.markdown(
            '<div class="critic-band"><strong style="color:#ef4444;">🔴 Critic</strong></div>',
            unsafe_allow_html=True,
        )
        st.markdown(round_data["critic_feedback"])

        st.markdown(
            '<div class="results-band"><strong style="color:#3b82f6;">🔵 Results Re-evaluator</strong></div>',
            unsafe_allow_html=True,
        )
        st.markdown(round_data["results_refinement"])

        st.markdown(
            '<div class="analysis-band"><strong style="color:#10b981;">🟢 Analysis Refiner</strong></div>',
            unsafe_allow_html=True,
        )
        st.markdown(round_data["analysis_update"])


def render_final_recommendation(state: ResearchState):
    confidence = state.get("confidence_level", "Low")
    badge_class = {
        "High": "badge-high",
        "Moderate": "badge-moderate",
        "Low": "badge-low",
    }.get(confidence, "badge-low")

    st.markdown(
        f"""
        <div class="final-card">
            <div style="display:flex; align-items:center; gap:1rem; margin-bottom:1rem;">
                <h2 style="font-family:'IBM Plex Mono',monospace; margin:0; color:#e0e6f0;">🏆 Final Recommendation</h2>
                <span class="{badge_class}">{confidence} Confidence</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(state.get("final_recommendation", ""))

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("**✅ Action Items**")
        for item in state.get("action_items", []):
            st.markdown(f"- {item}")
    with col_right:
        st.markdown("**⚠️ Caveats**")
        for caveat in state.get("caveats", []):
            st.markdown(f"- {caveat}")


def render_results(state: ResearchState):
    """Render all result sections from the pipeline state."""
    if state.get("papers"):
        render_papers(state["papers"], state.get("search_terms", []))

    if state.get("extracted_results"):
        render_extracted_results(state["extracted_results"])

    if state.get("initial_synthesis"):
        render_initial_analysis(
            state["initial_synthesis"], state.get("identified_gaps", [])
        )

    for round_data in state.get("debate_rounds", []):
        render_debate_round(round_data)

    if state.get("final_recommendation"):
        render_final_recommendation(state)


# ---------------------------------------------------------------------------
# Pipeline execution
# ---------------------------------------------------------------------------

if launch_clicked and not st.session_state.running:
    st.session_state.running = True
    st.session_state.abstract = abstract_input  # save before rerun locks the input
    st.session_state.result = None
    st.session_state.error_msg = None
    st.rerun()

if st.session_state.running and st.session_state.result is None:
    from graph import stream_research

    last_state = None
    try:
        for state_snapshot in stream_research(st.session_state.abstract):
            last_state = state_snapshot
            stage = state_snapshot.get("current_stage", "")

            with pipeline_status_placeholder.container():
                render_pipeline_status(stage, None)

            with results_placeholder.container():
                render_results(state_snapshot)

        st.session_state.result = last_state
        if last_state and last_state.get("error"):
            st.session_state.error_msg = last_state["error"]

    except Exception as e:
        st.session_state.error_msg = str(e)

    st.session_state.running = False
    st.rerun()


# ---------------------------------------------------------------------------
# Display results or errors
# ---------------------------------------------------------------------------

if st.session_state.error_msg:
    st.error(f"Pipeline error: {st.session_state.error_msg}")

if st.session_state.result:
    with pipeline_status_placeholder.container():
        render_pipeline_status("", st.session_state.result)

    with results_placeholder.container():
        render_results(st.session_state.result)

    # Partial results warning
    result = st.session_state.result
    if result.get("error") and (result.get("papers") or result.get("initial_synthesis")):
        st.warning(
            "The pipeline encountered an error but partial results are shown above."
        )

    # Reset button
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Run New Analysis", use_container_width=False):
        st.session_state.result = None
        st.session_state.running = False
        st.session_state.error_msg = None
        st.rerun()
