"""
app.py — Streamlit dashboard for LabOS Research Analysis Engine (hierarchical architecture).
"""

import streamlit as st

from state import ResearchState

# ── Constants ──────────────────────────────────────────────────────────────────

MAX_ABSTRACT_LENGTH = 4000
MIN_ABSTRACT_LENGTH = 20

DEMO_ABSTRACT = (
    "We're investigating menin inhibitors for NPM1-mutant AML. "
    "Key question: Does HOX gene expression predict treatment response to "
    "menin inhibitors in NPM1-mutant acute myeloid leukemia patients?"
)

STAGE_IDS = [
    "literature_running",
    "literature_review",
    "hypothesis_running",
    "hypothesis_review",
    "procedure_running",
    "procedure_review",
    "synthesizing",
    "peer_review",
]

STAGE_LABELS = [
    "📚 Literature*",
    "🔴 Critic: Lit*",
    "💡 Hypothesis",
    "🔴 Critic: Hyp",
    "🧪 Procedure",
    "🔴 Critic: Proc",
    "✅ Final Synth",
    "🔬 Peer Review",
]

# ── Page config & CSS ──────────────────────────────────────────────────────────

st.set_page_config(
    page_title="LabOS — Research Analysis Engine",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
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

    .lab-card {
        background: var(--card-bg);
        border-radius: 10px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 1rem;
        border: 1px solid #1f2937;
    }

    .stage-card {
        background: var(--card-bg);
        border-radius: 8px;
        padding: 0.6rem 0.4rem;
        text-align: center;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.70rem;
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
    .stage-card.pending {
        border-color: var(--warning);
        color: var(--warning);
    }

    .badge-high     { background:#064e3b; color:#10b981; padding:3px 10px; border-radius:20px; font-family:'IBM Plex Mono',monospace; font-size:0.85rem; }
    .badge-moderate { background:#451a03; color:#f59e0b; padding:3px 10px; border-radius:20px; font-family:'IBM Plex Mono',monospace; font-size:0.85rem; }
    .badge-low      { background:#450a0a; color:#ef4444; padding:3px 10px; border-radius:20px; font-family:'IBM Plex Mono',monospace; font-size:0.85rem; }

    .badge-revised  { background:#1e3a5f; color:#60a5fa; padding:2px 8px; border-radius:12px; font-family:'IBM Plex Mono',monospace; font-size:0.75rem; margin-left:8px; }

    .review-pass { border-left: 4px solid #10b981; padding-left: 0.8rem; margin-bottom: 0.8rem; }
    .review-fail { border-left: 4px solid #ef4444; padding-left: 0.8rem; margin-bottom: 0.8rem; }

    .final-card {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        border: 1px solid var(--accent);
        border-radius: 12px;
        padding: 1.6rem;
        margin-top: 1rem;
    }

    .pending-card {
        background: #1a1400;
        border: 1px solid var(--warning);
        border-radius: 10px;
        padding: 1rem 1.4rem;
        margin-bottom: 1rem;
    }

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
    div[data-testid="stExpander"] {
        background: var(--card-bg) !important;
        border: 1px solid #1f2937 !important;
        border-radius: 8px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Header ─────────────────────────────────────────────────────────────────────

st.markdown(
    """
    <div style="padding: 1.5rem 0 0.5rem 0;">
        <h1 style="font-family:'IBM Plex Mono',monospace; font-size:2rem; margin:0; color:#e0e6f0;">
            🧬 LabOS
        </h1>
        <p style="color:#6b7280; font-family:'IBM Plex Mono',monospace; font-size:0.9rem; margin:0.3rem 0 0 0;">
            Hierarchical Multi-Agent Research Engine · Powered by Claude
        </p>
    </div>
    <hr style="border-color:#1f2937; margin: 1rem 0;">
    """,
    unsafe_allow_html=True,
)

# ── Input ──────────────────────────────────────────────────────────────────────

abstract_input = st.text_area(
    "Research Abstract or Question",
    value=DEMO_ABSTRACT,
    placeholder=(
        "Paste a research abstract or question here.\n\n"
        "Example: 'Does HOX gene expression predict treatment response to menin inhibitors "
        "in NPM1-mutant acute myeloid leukemia patients?'"
    ),
    height=140,
    max_chars=MAX_ABSTRACT_LENGTH,
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

with col_btn:
    launch_clicked = st.button(
        "🚀 Launch Analysis",
        disabled=char_count < MIN_ABSTRACT_LENGTH,
        use_container_width=True,
    )

# ── Sidebar: orchestrator log ──────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<p style="font-family:\'IBM Plex Mono\',monospace; font-size:0.85rem; color:#6b7280;">ORCHESTRATOR LOG</p>',
        unsafe_allow_html=True,
    )
    log_placeholder = st.empty()
    st.markdown("---")
    st.markdown(
        '<p style="font-size:0.75rem; color:#6b7280;">* Stages marked with * depend on Agent 1 (in development by separate developer).</p>',
        unsafe_allow_html=True,
    )


# ── Pipeline status bar ────────────────────────────────────────────────────────

def render_pipeline_status(current_stage: str, is_complete: bool, is_pending: bool):
    st.markdown(
        '<p style="font-family:\'IBM Plex Mono\',monospace; font-size:0.8rem; color:#6b7280; margin-bottom:0.4rem;">PIPELINE STATUS</p>',
        unsafe_allow_html=True,
    )
    cols = st.columns(8)
    for i, (stage_id, label) in enumerate(zip(STAGE_IDS, STAGE_LABELS)):
        with cols[i]:
            if is_complete:
                css = "stage-card done"
            elif is_pending and i < 2:
                css = "stage-card pending"
            elif stage_id == current_stage:
                css = "stage-card active"
            else:
                css = "stage-card"
            st.markdown(f'<div class="{css}">{label}</div>', unsafe_allow_html=True)


# ── Results renderers ──────────────────────────────────────────────────────────

def _revision_badge(revision_count: int) -> str:
    if revision_count and revision_count > 0:
        return f'<span class="badge-revised">Revised {revision_count}x</span>'
    return ""


def render_literature_pending():
    st.markdown(
        """
        <div class="pending-card">
            <p style="font-family:'IBM Plex Mono',monospace; color:#f59e0b; margin:0;">
                ⏳ Agent 1 not yet integrated
            </p>
            <p style="font-size:0.82rem; color:#9ca3af; margin:0.4rem 0 0 0;">
                The Literature Review agent is being developed by a separate team member.
                Hypothesis and Procedure agents will run with placeholder inputs until Agent 1 is merged.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_papers(literature):
    papers = literature.get("papers") or []
    search_terms = literature.get("search_terms") or []
    rev = _revision_badge(literature.get("revision_count", 0))

    with st.expander(
        f"📚 Papers Found ({len(papers)})" + (" — Revised" if literature.get("revision_count", 0) > 0 else ""),
        expanded=False,
    ):
        st.markdown(f'<span>{rev}</span>', unsafe_allow_html=True)
        if search_terms:
            terms_str = "  ".join(f"`{t}`" for t in search_terms)
            st.markdown(f"**Search terms:** {terms_str}")
            st.markdown("---")
        if not papers:
            st.markdown("*No papers found — Agent 1 not yet integrated.*")
            return
        for i, paper in enumerate(papers, 1):
            score = paper.get("relevance_score")
            score_str = f" · relevance {score:.2f}" if score is not None else ""
            st.markdown(f"**{i}. [{paper['title']}]({paper['url']})**{score_str}")
            if paper.get("abstract"):
                st.markdown(
                    f'<p style="color:#9ca3af; font-size:0.85rem;">{paper["abstract"][:300]}</p>',
                    unsafe_allow_html=True,
                )
            st.markdown("---")


def render_analyses(literature):
    analyses = literature.get("analyses") or []
    with st.expander(f"🔬 Paper Analyses ({len(analyses)} papers)", expanded=False):
        if not analyses:
            st.markdown("*No analyses — Agent 1 not yet integrated.*")
            return
        for a in analyses:
            st.markdown(f"**{a.get('paper_title', 'Unknown')}**")
            col_meta, col_findings = st.columns([1, 2])
            with col_meta:
                if a.get("sample_size"):
                    st.markdown(f"**Sample size:** `{a['sample_size']}`")
                if a.get("methodology"):
                    st.markdown(
                        f'<p style="font-size:0.83rem; color:#9ca3af;">{a["methodology"][:200]}</p>',
                        unsafe_allow_html=True,
                    )
                if a.get("limitations"):
                    st.markdown(
                        f'<p style="font-size:0.80rem; color:#6b7280;"><em>⚠ {a["limitations"][:200]}</em></p>',
                        unsafe_allow_html=True,
                    )
            with col_findings:
                findings = a.get("key_findings") or []
                if findings:
                    st.markdown("**Key findings:**")
                    for f in findings[:5]:
                        st.markdown(f"- {f}")
                if a.get("relevance_to_question"):
                    st.markdown(
                        f'<p style="font-size:0.80rem; color:#60a5fa;"><em>Relevance: {a["relevance_to_question"][:200]}</em></p>',
                        unsafe_allow_html=True,
                    )
            st.markdown("---")


def render_lit_synthesis(literature):
    synthesis = literature.get("synthesis") or ""
    with st.expander("🧠 Literature Synthesis", expanded=False):
        if not synthesis:
            st.markdown("*No synthesis — Agent 1 not yet integrated.*")
        else:
            st.markdown(synthesis)


def render_critic_review(reviews, agent_name: str, label: str):
    agent_reviews = [r for r in (reviews or []) if r["agent_name"] == agent_name]
    if not agent_reviews:
        return
    with st.expander(f"{label} ({len(agent_reviews)} review(s))", expanded=False):
        for r in agent_reviews:
            css = "review-pass" if r["passed"] else "review-fail"
            icon = "✅ PASSED" if r["passed"] else "❌ FAILED"
            st.markdown(
                f'<div class="{css}"><strong>{icon}</strong> — Submission #{r["revision_number"]}'
                + (f'<br><small style="color:#9ca3af;">{r.get("timestamp","")}</small>' if r.get("timestamp") else "")
                + "</div>",
                unsafe_allow_html=True,
            )
            if not r["passed"] and r.get("feedback"):
                st.markdown(
                    f'<p style="font-size:0.85rem; color:#fca5a5;">{r["feedback"]}</p>',
                    unsafe_allow_html=True,
                )


def render_hypothesis(hypothesis):
    if not hypothesis:
        return
    rev = _revision_badge(hypothesis.get("revision_count", 0))
    with st.expander(
        "💡 Hypothesis" + (" — Revised" if hypothesis.get("revision_count", 0) > 0 else ""),
        expanded=True,
    ):
        st.markdown(f'<span>{rev}</span>', unsafe_allow_html=True)
        st.markdown(f"**Primary Hypothesis:**\n\n{hypothesis.get('hypothesis', '')}")
        st.markdown(f"**Null Hypothesis (H₀):**\n\n{hypothesis.get('null_hypothesis', '')}")
        st.markdown("---")
        st.markdown(f"**Rationale:**\n\n{hypothesis.get('rationale', '')}")
        st.markdown(f"**Design Approach:** {hypothesis.get('design_approach', '')}")
        outcomes = hypothesis.get("expected_outcomes") or []
        if outcomes:
            st.markdown("**Expected Outcomes:**")
            for o in outcomes:
                st.markdown(f"- {o}")


def render_procedure(procedure):
    if not procedure:
        return
    rev = _revision_badge(procedure.get("revision_count", 0))
    with st.expander(
        "🧪 Procedure Design" + (" — Revised" if procedure.get("revision_count", 0) > 0 else ""),
        expanded=False,
    ):
        st.markdown(f'<span>{rev}</span>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Population Size & Power:**")
            st.markdown(procedure.get("population_size", ""))
            st.markdown("**Population Criteria:**")
            st.markdown(procedure.get("population_criteria", ""))
            st.markdown("**Timeline:**")
            st.markdown(procedure.get("timeline_estimate", ""))
        with col2:
            st.markdown("**Research Design:**")
            st.markdown(procedure.get("research_design", ""))
            st.markdown("**Data Collection:**")
            st.markdown(procedure.get("data_collection", ""))
            st.markdown("**Statistical Approach:**")
            st.markdown(procedure.get("statistical_approach", ""))


def render_final_recommendation(state: ResearchState):
    confidence = state.get("confidence_level") or "Low"
    badge_class = {"High": "badge-high", "Moderate": "badge-moderate", "Low": "badge-low"}.get(
        confidence, "badge-low"
    )
    st.markdown(
        f"""
        <div class="final-card">
            <div style="display:flex; align-items:center; gap:1rem; margin-bottom:1rem;">
                <h2 style="font-family:'IBM Plex Mono',monospace; margin:0; color:#e0e6f0;">✅ Final Recommendation</h2>
                <span class="{badge_class}">{confidence} Confidence</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(state.get("final_recommendation") or "")

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("**Action Items**")
        for item in (state.get("action_items") or []):
            st.markdown(f"- {item}")
    with col_right:
        st.markdown("**Caveats**")
        for caveat in (state.get("caveats") or []):
            st.markdown(f"- {caveat}")


def render_peer_review(peer_review):
    if not peer_review:
        return

    verdict = peer_review.get("overall_verdict", "")
    score = peer_review.get("reproducibility_score", 0)

    verdict_colors = {
        "Accept": ("#064e3b", "#10b981"),
        "Minor Revision": ("#1e3a5f", "#60a5fa"),
        "Major Revision": ("#451a03", "#f59e0b"),
        "Reject": ("#450a0a", "#ef4444"),
    }
    bg, fg = verdict_colors.get(verdict, ("#1f2937", "#9ca3af"))

    score_color = "#10b981" if score >= 8 else "#f59e0b" if score >= 5 else "#ef4444"

    st.markdown(
        f"""
        <div style="background:#111827; border:1px solid #1f2937; border-radius:10px; padding:1.2rem 1.4rem; margin-bottom:1rem;">
            <div style="display:flex; align-items:center; gap:1rem; margin-bottom:0.8rem;">
                <h3 style="font-family:'IBM Plex Mono',monospace; margin:0; color:#e0e6f0;">🔬 Peer Review Report</h3>
                <span style="background:{bg}; color:{fg}; padding:3px 12px; border-radius:20px; font-family:'IBM Plex Mono',monospace; font-size:0.85rem;">{verdict}</span>
                <span style="background:#1f2937; color:{score_color}; padding:3px 10px; border-radius:20px; font-family:'IBM Plex Mono',monospace; font-size:0.85rem;">Reproducibility: {score}/10</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(peer_review.get("summary", ""))

    col_left, col_right = st.columns(2)
    with col_left:
        strengths = peer_review.get("strengths") or []
        if strengths:
            with st.expander(f"✅ Strengths ({len(strengths)})", expanded=True):
                for s in strengths:
                    st.markdown(f"- {s}")

    with col_right:
        missing = peer_review.get("missing_details") or []
        if missing:
            with st.expander(f"⚠️ Missing Details ({len(missing)})", expanded=True):
                for m in missing:
                    st.markdown(f"- {m}")

    issues = peer_review.get("issues") or []
    if issues:
        critical = [i for i in issues if i.get("severity") == "Critical"]
        major = [i for i in issues if i.get("severity") == "Major"]
        minor = [i for i in issues if i.get("severity") == "Minor"]

        with st.expander(
            f"🚨 Reproducibility Issues ({len(issues)} total — "
            f"{len(critical)} critical, {len(major)} major, {len(minor)} minor)",
            expanded=True,
        ):
            severity_styles = {
                "Critical": ("#450a0a", "#ef4444", "🔴"),
                "Major": ("#451a03", "#f59e0b", "🟡"),
                "Minor": ("#1e3a5f", "#60a5fa", "🔵"),
            }
            for issue in issues:
                sev = issue.get("severity", "Minor")
                bg_c, fg_c, icon = severity_styles.get(sev, ("#1f2937", "#9ca3af", "⚪"))
                st.markdown(
                    f'<div style="background:{bg_c}; border-radius:6px; padding:0.6rem 0.8rem; margin-bottom:0.6rem;">'
                    f'<span style="color:{fg_c}; font-family:\'IBM Plex Mono\',monospace; font-size:0.8rem;">{icon} {sev.upper()} — {issue.get("section","")}</span><br>'
                    f'<span style="color:#e0e6f0; font-size:0.88rem;">{issue.get("description","")}</span><br>'
                    f'<span style="color:#9ca3af; font-size:0.82rem;"><em>Suggestion: {issue.get("suggestion","")}</em></span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    changes = peer_review.get("suggested_changes") or []
    if changes:
        with st.expander(f"📋 Suggested Changes ({len(changes)}, priority order)", expanded=False):
            for i, change in enumerate(changes, 1):
                st.markdown(f"**{i}.** {change}")

    checklist = peer_review.get("replication_checklist") or []
    if checklist:
        with st.expander("☑️ Replication Checklist", expanded=False):
            for item in checklist:
                color = "#10b981" if item.upper().endswith("YES") else "#ef4444" if item.upper().endswith("NO") else "#9ca3af"
                st.markdown(
                    f'<p style="font-family:\'IBM Plex Mono\',monospace; font-size:0.82rem; color:{color}; margin:4px 0;">{item}</p>',
                    unsafe_allow_html=True,
                )


def render_results(state: ResearchState):
    literature = state.get("literature")
    hypothesis = state.get("hypothesis")
    procedure = state.get("procedure")
    reviews = state.get("reviews") or []

    # Agent 1 pending or implemented
    if literature is not None:
        is_pending = (
            state.get("error") == "Agent 1 not yet integrated"
            or (not literature.get("papers") and not literature.get("synthesis"))
        )
        if is_pending:
            render_literature_pending()
        else:
            render_papers(literature)
            render_analyses(literature)
            render_lit_synthesis(literature)

        render_critic_review(reviews, "literature", "🔴 Critic Review: Literature")

    if hypothesis is not None:
        render_hypothesis(hypothesis)
        render_critic_review(reviews, "hypothesis", "🔴 Critic Review: Hypothesis")

    if procedure is not None:
        render_procedure(procedure)
        render_critic_review(reviews, "procedure", "🔴 Critic Review: Procedure")

    if state.get("final_recommendation"):
        render_final_recommendation(state)

    if state.get("peer_review"):
        st.markdown("---")
        render_peer_review(state["peer_review"])


# ── Pipeline execution ─────────────────────────────────────────────────────────

if launch_clicked and char_count >= MIN_ABSTRACT_LENGTH:
    from graph import run_research

    pipeline_status_area = st.empty()
    results_area = st.empty()

    with st.spinner("Running multi-agent pipeline... (this takes 1-3 minutes)"):
        try:
            final_state = run_research(abstract_input)
        except Exception as exc:
            st.error(f"Pipeline error: {exc}")
            final_state = None

    if final_state:
        is_complete = final_state.get("current_stage") == "complete"
        is_pending = final_state.get("error") == "Agent 1 not yet integrated"

        with pipeline_status_area.container():
            render_pipeline_status(final_state.get("current_stage", ""), is_complete, is_pending)

        if final_state.get("error") and not is_pending:
            st.warning(f"Pipeline note: {final_state['error']}")

        # Orchestrator log in sidebar
        msgs = final_state.get("orchestrator_messages") or []
        with log_placeholder.container():
            if msgs:
                for msg in msgs:
                    st.markdown(
                        f'<p style="font-size:0.75rem; font-family:\'IBM Plex Mono\',monospace; color:#9ca3af; margin:2px 0;">{msg}</p>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    '<p style="font-size:0.75rem; color:#6b7280;">No log entries.</p>',
                    unsafe_allow_html=True,
                )

        with results_area.container():
            render_results(final_state)

else:
    # Idle state — show empty pipeline
    render_pipeline_status("", False, False)
    with log_placeholder.container():
        st.markdown(
            '<p style="font-size:0.75rem; color:#6b7280;">Pipeline not yet started.</p>',
            unsafe_allow_html=True,
        )
