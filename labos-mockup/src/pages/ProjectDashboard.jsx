import { useState, useEffect, useRef } from 'react';
import { useLocation, useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, FlaskConical, Network, X, ExternalLink, CheckCircle2, CircleDashed, AlertCircle } from 'lucide-react';

const API_BASE = '';

export default function ProjectDashboard() {
  const { id } = useParams();
  const location = useLocation();
  const abstract = location.state?.abstract || '';

  const [pipelineState, setPipelineState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activePanel, setActivePanel] = useState(null);
  const hasRun = useRef(false);

  useEffect(() => {
    if (!abstract) {
      setError('No abstract provided. Please start a new project.');
      setLoading(false);
      return;
    }

    // Guard against React StrictMode double-invocation
    if (hasRun.current) return;
    hasRun.current = true;

    const run = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/analyze/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ abstract }),
        });
        if (!res.ok) {
          const detail = await res.json().catch(() => ({}));
          throw new Error(detail?.detail || `Server error ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          // Keep the last incomplete line in the buffer
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                setPipelineState(prev => ({ ...prev, ...data }));

                if (data.stage === 'done' || data.stage === 'error') {
                  setLoading(false);
                }
                if (data.error && data.stage === 'error') {
                  setError(data.error);
                  setLoading(false);
                }
              } catch {
                // Skip malformed JSON lines
              }
            }
          }
        }

        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };

    run();
  }, [abstract]);

  const agentStatus = (key) => {
    if (error) return 'error';
    if (!pipelineState) return loading ? (key === 'literature' ? 'running' : 'waiting') : 'waiting';

    // If this agent's data exists, it's done
    if (pipelineState[key]) return 'done';

    // Determine what's currently running based on the stage
    const stage = pipelineState.stage || pipelineState.current_stage || '';
    if (key === 'literature' && (stage.startsWith('literature') || !stage)) return loading ? 'running' : 'waiting';
    if (key === 'hypothesis' && stage.startsWith('hypothesis')) return 'running';
    if (key === 'procedure' && (stage.startsWith('procedure') || stage === 'synthesis' || stage === 'done')) return stage === 'procedure' ? 'running' : 'waiting';

    return loading ? 'waiting' : 'waiting';
  };

  const renderStatus = (status) => {
    if (status === 'done') return <CheckCircle2 size={20} color="var(--success)" />;
    if (status === 'running') return (
      <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 2, ease: 'linear' }}>
        <CircleDashed size={20} color="var(--accent-primary)" />
      </motion.div>
    );
    if (status === 'error') return <AlertCircle size={20} color="var(--danger, #ef4444)" />;
    return <CircleDashed size={20} color="var(--text-secondary)" />;
  };

  const lit = pipelineState?.literature;
  const hyp = pipelineState?.hypothesis;
  const proc = pipelineState?.procedure;
  const peer = pipelineState?.peer_review;

  return (
    <div className="project-dashboard relative">
      <div className="page-header">
        <h1 className="page-title">Project #{id} Dashboard</h1>
        <p className="text-muted">Research overview and agent status.</p>
      </div>

      <div className="card p-6 mb-6">
        <h3 className="font-mono mb-2 text-sm text-muted uppercase">Input Abstract</h3>
        <p className="text-sm">{abstract || 'No abstract provided.'}</p>
      </div>

      {loading && (
        <div className="card p-6 mb-6 text-center">
          <p className="text-muted text-sm">Running multi-agent pipeline… this takes 1–3 minutes.</p>
        </div>
      )}

      {error && (
        <div className="card p-6 mb-6" style={{ borderColor: '#ef4444' }}>
          <p className="text-sm" style={{ color: '#ef4444' }}><strong>Error:</strong> {error}</p>
        </div>
      )}

      <h3 className="font-mono mb-4 mt-6 text-sm text-muted uppercase">Agent Modules</h3>
      <div className="overview-cards">

        {/* Agent 1: Literature */}
        <div className="agent-card flex flex-col" onClick={() => lit && setActivePanel('lit')}>
          <div className="flex justify-between items-start mb-4">
            <div className="flex items-center gap-2 font-mono font-semibold">
              <Search size={18} color="var(--accent-primary)" />
              Agent 1: Lit Review
            </div>
            {renderStatus(agentStatus('literature'))}
          </div>
          <p className="text-sm text-muted flex-grow">Searches academic databases to extract relevant context and prior methodologies.</p>
          {lit && (
            <div className="mt-4 pt-4 border-t border-subtle text-sm font-semibold" style={{ color: 'var(--success)' }}>
              {lit.papers?.length ?? 0} Papers Extracted
            </div>
          )}
        </div>

        {/* Agent 2: Hypothesis */}
        <div className="agent-card flex flex-col" onClick={() => hyp && setActivePanel('hypothesis')}>
          <div className="flex justify-between items-start mb-4">
            <div className="flex items-center gap-2 font-mono font-semibold">
              <FlaskConical size={18} color="var(--accent-primary)" />
              Agent 2: Hypothesis
            </div>
            {renderStatus(agentStatus('hypothesis'))}
          </div>
          <p className="text-sm text-muted flex-grow">Synthesizes literature to propose testable primary and null hypotheses.</p>
          {hyp && (
            <div className="mt-4 pt-4 border-t border-subtle text-sm font-semibold" style={{ color: 'var(--success)' }}>
              Hypothesis Generated
            </div>
          )}
        </div>

        {/* Agent 3: Procedure */}
        <div className="agent-card flex flex-col" onClick={() => proc && setActivePanel('design')}>
          <div className="flex justify-between items-start mb-4">
            <div className="flex items-center gap-2 font-mono font-semibold">
              <Network size={18} color="var(--accent-primary)" />
              Agent 3: Protocol Design
            </div>
            {renderStatus(agentStatus('procedure'))}
          </div>
          <p className="text-sm text-muted flex-grow">Drafts a step-by-step scientific process cycle to test the hypothesis.</p>
          {proc && (
            <div className="mt-4 pt-4 border-t border-subtle text-sm font-semibold" style={{ color: 'var(--success)' }}>
              Protocol Ready
            </div>
          )}
        </div>

      </div>

      {/* Final recommendation */}
      {pipelineState?.final_recommendation && (
        <div className="card p-6 mt-6">
          <div className="flex items-center gap-3 mb-2">
            <h3 className="font-mono text-sm text-muted uppercase mb-0">Final Recommendation</h3>
            {pipelineState.confidence_level && (
              <span className="badge" style={{
                backgroundColor: pipelineState.confidence_level === 'High' ? 'rgba(16, 185, 129, 0.15)' : pipelineState.confidence_level === 'Moderate' ? 'rgba(245, 158, 11, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                color: pipelineState.confidence_level === 'High' ? '#10b981' : pipelineState.confidence_level === 'Moderate' ? '#f59e0b' : '#ef4444',
                border: `1px solid ${pipelineState.confidence_level === 'High' ? 'rgba(16, 185, 129, 0.3)' : pipelineState.confidence_level === 'Moderate' ? 'rgba(245, 158, 11, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`
              }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'currentColor' }}></span>
                {pipelineState.confidence_level} Confidence
              </span>
            )}
          </div>
          <p className="text-sm whitespace-pre-wrap">{pipelineState.final_recommendation}</p>
          {pipelineState.action_items?.length > 0 && (
            <div className="mt-4">
              <p className="text-xs text-muted font-mono uppercase mb-1">Action Items</p>
              <ul className="text-sm list-disc pl-4">
                {pipelineState.action_items.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Peer review summary */}
      {peer && (
        <div className="card p-6 mt-6">
          <div className="flex items-center gap-3 mb-2">
            <h3 className="font-mono text-sm text-muted uppercase mb-0">Peer Review</h3>
            <span className="badge" style={{ 
              backgroundColor: 'rgba(96, 165, 250, 0.15)', 
              color: '#60a5fa',
              border: '1px solid rgba(96, 165, 250, 0.3)'
            }}>
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'currentColor' }}></span>
              {peer.overall_verdict} · Reproducibility {peer.reproducibility_score}/10
            </span>
          </div>
          <p className="text-sm">{peer.summary}</p>
        </div>
      )}

      {/* Slide-out panels */}
      <AnimatePresence>
        {activePanel && (
          <>
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="slide-panel-backdrop"
              onClick={() => setActivePanel(null)}
            />
            <motion.div
              initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="slide-panel"
            >
              <div className="slide-panel-header">
                <h2 className="font-mono text-lg">
                  {activePanel === 'lit' && 'Agent 1: Literature Context'}
                  {activePanel === 'hypothesis' && 'Agent 2: Hypothesis Design'}
                  {activePanel === 'design' && 'Agent 3: Research Protocol'}
                </h2>
                <button className="btn-icon" onClick={() => setActivePanel(null)}><X size={20} /></button>
              </div>
              <div className="slide-panel-content">

                {activePanel === 'lit' && lit && (
                  <div>
                    {lit.synthesis && (
                      <div className="mb-6">
                        <p className="text-xs text-muted font-mono uppercase mb-2">Synthesis</p>
                        <p className="text-sm">{lit.synthesis}</p>
                      </div>
                    )}
                    {lit.papers?.length > 0 && lit.papers.map((paper, i) => (
                      <div key={i} className="paper-card">
                        <div className="flex justify-between items-center mb-2">
                          <span className="font-semibold">{paper.title}</span>
                          {paper.relevance_score != null && (
                            <span className="badge badge-success">Score: {paper.relevance_score.toFixed(2)}</span>
                          )}
                        </div>
                        <p className="text-sm text-muted mb-2">{paper.abstract?.slice(0, 300)}</p>
                        <a href={paper.url} target="_blank" rel="noreferrer" className="text-sm flex items-center gap-1" style={{ color: 'var(--accent-primary)' }}>
                          <ExternalLink size={14} /> View Source
                        </a>
                      </div>
                    ))}
                    {(!lit.papers || lit.papers.length === 0) && (
                      <p className="text-muted text-sm">Literature agent not yet integrated — no papers available.</p>
                    )}
                  </div>
                )}

                {activePanel === 'hypothesis' && hyp && (
                  <div>
                    <div className="hypothesis-card">
                      <h4 className="font-mono text-sm mb-2 uppercase" style={{ color: 'var(--accent-primary)' }}>Primary Hypothesis</h4>
                      <p className="text-sm">{hyp.hypothesis}</p>
                    </div>
                    <div className="hypothesis-card">
                      <h4 className="font-mono text-sm mb-2 uppercase" style={{ color: 'var(--text-secondary)' }}>Null Hypothesis (H₀)</h4>
                      <p className="text-sm">{hyp.null_hypothesis}</p>
                    </div>
                    {hyp.rationale && (
                      <div className="hypothesis-card">
                        <h4 className="font-mono text-sm mb-2 uppercase" style={{ color: 'var(--text-secondary)' }}>Rationale</h4>
                        <p className="text-sm">{hyp.rationale}</p>
                      </div>
                    )}
                    {hyp.expected_outcomes?.length > 0 && (
                      <div className="hypothesis-card">
                        <h4 className="font-mono text-sm mb-2 uppercase" style={{ color: 'var(--text-secondary)' }}>Expected Outcomes</h4>
                        <ul className="text-sm list-disc pl-4">
                          {hyp.expected_outcomes.map((o, i) => <li key={i}>{o}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {activePanel === 'design' && proc && (
                  <div className="research-design-board">
                    <div className="design-step">
                      <h4 className="font-mono text-sm uppercase">Research Design</h4>
                      <p className="text-sm mt-2">{proc.research_design}</p>
                    </div>
                    <div className="design-step">
                      <h4 className="font-mono text-sm uppercase">Population</h4>
                      <p className="text-sm mt-2"><strong>Size:</strong> {proc.population_size}</p>
                      <p className="text-sm mt-1"><strong>Criteria:</strong> {proc.population_criteria}</p>
                    </div>
                    <div className="design-step">
                      <h4 className="font-mono text-sm uppercase">Data Collection</h4>
                      <p className="text-sm mt-2">{proc.data_collection}</p>
                    </div>
                    <div className="design-step">
                      <h4 className="font-mono text-sm uppercase">Statistical Approach</h4>
                      <p className="text-sm mt-2">{proc.statistical_approach}</p>
                    </div>
                    <div className="design-step">
                      <h4 className="font-mono text-sm uppercase">Timeline</h4>
                      <p className="text-sm mt-2">{proc.timeline_estimate}</p>
                    </div>
                  </div>
                )}

              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
