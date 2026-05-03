import { useState, useEffect, useRef, useMemo } from 'react';
import { useLocation, useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, FlaskConical, Network, X, ExternalLink, CheckCircle2, CircleDashed, AlertCircle, Download, MessageSquare, ChevronDown } from 'lucide-react';
import ChatPanel from '../components/ChatPanel';

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
  const [chatOpen, setChatOpen] = useState(false);
  const [exportMenuOpen, setExportMenuOpen] = useState(false);
  const exportRef = useRef(null);

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
    if (!loading && !pipelineState) return 'waiting';
    if (!pipelineState) return key === 'literature' ? 'running' : 'waiting';

    // If this agent's data exists, it's done
    if (pipelineState[key]) return 'done';

    // Still loading — infer which agent is currently running based on
    // what has completed so far. The SSE stream only yields *after* each
    // agent finishes, so we derive the active agent from the gap.
    if (!loading) return 'waiting';

    const litDone = !!pipelineState.literature;
    const hypDone = !!pipelineState.hypothesis;
    const procDone = !!pipelineState.procedure;

    if (key === 'literature' && !litDone) return 'running';
    if (key === 'hypothesis' && litDone && !hypDone) return 'running';
    if (key === 'procedure' && hypDone && !procDone) return 'running';

    return 'waiting';
  };

  const renderStatus = (status) => {
    if (status === 'done') return <CheckCircle2 size={20} color="var(--success)" />;
    if (status === 'running') return (
      <div className="agent-spinner">
        <div className="agent-spinner-circle" />
      </div>
    );
    if (status === 'error') return <AlertCircle size={20} color="var(--danger, #ef4444)" />;
    return <CircleDashed size={20} color="var(--text-secondary)" />;
  };

  const lit = pipelineState?.literature;
  const hyp = pipelineState?.hypothesis;
  const proc = pipelineState?.procedure;

  // Parse the consolidated final_recommendation JSON
  const synthesis = useMemo(() => {
    const raw = pipelineState?.final_recommendation;
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw);
      if (parsed.result || parsed.hypothesis || parsed.steps || parsed.literature_citations) {
        return parsed;
      }
    } catch {
      // Fallback: treat as plain text (legacy format)
    }
    return { result: raw, hypothesis: '', steps: '', literature_citations: '' };
  }, [pipelineState?.final_recommendation]);

  const handleExportPdf = () => {
    if (!synthesis) return;
    exportAs('standard');
  };

  // Close export menu on outside click
  useEffect(() => {
    const handleClick = (e) => {
      if (exportRef.current && !exportRef.current.contains(e.target)) setExportMenuOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const exportAs = async (format) => {
    if (!synthesis) return;
    setExportMenuOpen(false);
    const title = `LabOS Research Plan — Project #${id}`;
    const sections = [
      { heading: 'Result', body: synthesis.result || '' },
      { heading: 'Hypothesis', body: synthesis.hypothesis || '' },
      { heading: 'Steps', body: synthesis.steps || '' },
      { heading: 'Literature Review Citations', body: synthesis.literature_citations || '' },
    ].filter(s => s.body);

    if (format === 'latex') {
      exportLatex(title, sections);
      return;
    }

    // Server-side PDF generation for standard and APA
    try {
      const res = await fetch(`${API_BASE}/api/chat/export-pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          confidence_level: pipelineState?.confidence_level || '',
          sections,
          action_items: pipelineState?.action_items || [],
          caveats: pipelineState?.caveats || [],
          format: format,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || 'PDF export failed');
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `research-plan-${id}${format === 'apa' ? '-apa' : ''}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert('PDF export failed: ' + err.message);
    }
  };

  const exportLatex = (title, sections) => {
    let latex = `\\documentclass[12pt]{article}\n\\usepackage[utf8]{inputenc}\n\\usepackage[margin=1in]{geometry}\n\\usepackage{hyperref}\n\\title{${title}}\n\\author{LabOS Multi-Agent Research Engine}\n\\date{${new Date().toLocaleDateString()}}\n\\begin{document}\n\\maketitle\n\n`;
    if (pipelineState?.confidence_level) {
      latex += `\\noindent\\textbf{Confidence Level:} ${pipelineState.confidence_level}\n\n`;
    }
    for (const s of sections) {
      if (s.body) {
        latex += `\\section{${s.heading}}\n${s.body.replace(/&/g, '\\&').replace(/%/g, '\\%').replace(/#/g, '\\#')}\n\n`;
      }
    }
    if (pipelineState?.action_items?.length) {
      latex += `\\section{Action Items}\n\\begin{itemize}\n${pipelineState.action_items.map(a => `  \\item ${a.replace(/&/g, '\\&').replace(/%/g, '\\%')}`).join('\n')}\n\\end{itemize}\n\n`;
    }
    if (pipelineState?.caveats?.length) {
      latex += `\\section{Caveats}\n\\begin{itemize}\n${pipelineState.caveats.map(c => `  \\item ${c.replace(/&/g, '\\&').replace(/%/g, '\\%')}`).join('\n')}\n\\end{itemize}\n\n`;
    }
    latex += `\\end{document}`;
    const blob = new Blob([latex], { type: 'application/x-latex' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `research-plan-${id}.tex`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Detect if final result is loading (all agents done, synthesis in progress)
  const isFinalResultLoading = useMemo(() => {
    if (!loading || !pipelineState) return false;
    const litDone = !!pipelineState.literature;
    const hypDone = !!pipelineState.hypothesis;
    const procDone = !!pipelineState.procedure;
    return litDone && hypDone && procDone && !pipelineState.final_recommendation;
  }, [loading, pipelineState]);

  return (
    <div className="project-dashboard relative">
      <div className="page-header">
        <h1 className="page-title">Project #{id} Dashboard</h1>
        <p className="text-muted">Research overview and agent status.</p>
      </div>

      <div className="card p-6 mb-6">
        <h3 className="font-mono mb-2 text-sm text-muted uppercase">Input Abstract</h3>
        <p className="text-sm" style={{ maxHeight: '150px', overflowY: 'auto', whiteSpace: 'pre-wrap' }}>{abstract || 'No abstract provided.'}</p>
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
      <div className="overview-cards mb-6">

        {/* Agent 1: Literature */}
        <div className="agent-card" onClick={() => lit && setActivePanel('lit')}>
          <div className="flex justify-between items-start mb-4">
            <div className="flex items-center gap-2 font-mono font-semibold">
              <Search size={18} color="var(--accent-primary)" />
              Agent 1: Lit Review
            </div>
            {renderStatus(agentStatus('literature'))}
          </div>
          <p className="text-sm text-muted">Searches academic databases to extract relevant context and prior methodologies.</p>
          {lit && (
            <div className="mt-4 pt-4 border-t border-subtle text-sm font-semibold" style={{ color: 'var(--success)' }}>
              {lit.papers?.length ?? 0} Papers Extracted
            </div>
          )}
        </div>

        {/* Agent 2: Hypothesis */}
        <div className="agent-card" onClick={() => hyp && setActivePanel('hypothesis')}>
          <div className="flex justify-between items-start mb-4">
            <div className="flex items-center gap-2 font-mono font-semibold">
              <FlaskConical size={18} color="var(--accent-primary)" />
              Agent 2: Hypothesis
            </div>
            {renderStatus(agentStatus('hypothesis'))}
          </div>
          <p className="text-sm text-muted">Synthesizes literature to propose testable primary and null hypotheses.</p>
          {hyp && (
            <div className="mt-4 pt-4 border-t border-subtle text-sm font-semibold" style={{ color: 'var(--success)' }}>
              Hypothesis Generated
            </div>
          )}
        </div>

        {/* Agent 3: Procedure */}
        <div className="agent-card" onClick={() => proc && setActivePanel('design')}>
          <div className="flex justify-between items-start mb-4">
            <div className="flex items-center gap-2 font-mono font-semibold">
              <Network size={18} color="var(--accent-primary)" />
              Agent 3: Protocol Design
            </div>
            {renderStatus(agentStatus('procedure'))}
          </div>
          <p className="text-sm text-muted">Drafts a step-by-step scientific process cycle to test the hypothesis.</p>
          {proc && (
            <div className="mt-4 pt-4 border-t border-subtle text-sm font-semibold" style={{ color: 'var(--success)' }}>
              Protocol Ready
            </div>
          )}
        </div>

      </div>

      {/* Final Research Plan — always-present card */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <h3 className="font-mono text-sm text-muted uppercase">Final Research Plan</h3>
            {synthesis && pipelineState.confidence_level && (
              <span className="badge" style={{
                backgroundColor: pipelineState.confidence_level === 'High' ? 'rgba(16, 185, 129, 0.15)' : pipelineState.confidence_level === 'Moderate' ? 'rgba(245, 158, 11, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                color: pipelineState.confidence_level === 'High' ? '#10b981' : pipelineState.confidence_level === 'Moderate' ? '#f59e0b' : '#ef4444',
                border: `1px solid ${pipelineState.confidence_level === 'High' ? 'rgba(16, 185, 129, 0.3)' : pipelineState.confidence_level === 'Moderate' ? 'rgba(245, 158, 11, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`
              }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'currentColor' }}></span>
                {pipelineState.confidence_level} Confidence
              </span>
            )}
            {!synthesis && (
              renderStatus(isFinalResultLoading ? 'running' : (error ? 'error' : 'waiting'))
            )}
          </div>
          {synthesis && (
            <div className="flex items-center gap-2">
              <div className="export-dropdown" ref={exportRef}>
                <button
                  onClick={() => setExportMenuOpen(!exportMenuOpen)}
                  className="btn-icon flex items-center gap-2 text-sm font-mono"
                  style={{ color: 'var(--accent-primary)', cursor: 'pointer', background: 'rgba(212, 168, 67, 0.1)', border: '1px solid rgba(212, 168, 67, 0.3)', borderRadius: '6px', padding: '6px 14px' }}
                  title="Export"
                >
                  <Download size={16} /> Export <ChevronDown size={12} />
                </button>
                {exportMenuOpen && (
                  <div className="export-dropdown-menu">
                    <button className="export-dropdown-item" onClick={() => exportAs('standard')}>
                      <span className="format-label">PDF</span> Standard
                    </button>
                    <button className="export-dropdown-item" onClick={() => exportAs('apa')}>
                      <span className="format-label">APA</span> APA Format
                    </button>
                    <button className="export-dropdown-item" onClick={() => exportAs('latex')}>
                      <span className="format-label">LaTeX</span> Download .tex
                    </button>
                  </div>
                )}
              </div>
              <button
                onClick={() => setChatOpen(true)}
                className="btn-icon flex items-center gap-2 text-sm font-mono"
                style={{ color: '#10b981', cursor: 'pointer', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: '6px', padding: '6px 14px' }}
                title="Chat with results"
              >
                <MessageSquare size={16} /> Chat
              </button>
            </div>
          )}
        </div>

        {/* Loading state */}
        {!synthesis && isFinalResultLoading && (
          <div className="final-result-loading">
            <div className="agent-spinner">
              <div className="agent-spinner-circle" />
            </div>
            <p className="text-muted text-sm font-mono">Synthesizing final research plan…</p>
          </div>
        )}

        {/* Waiting state */}
        {!synthesis && !isFinalResultLoading && !error && (
          <p className="text-muted text-sm">Waiting for agents to complete…</p>
        )}

        {/* Content */}
        {synthesis && (
          <>
            {synthesis.result && (
              <div className="mb-5">
                <p className="text-xs text-muted font-mono uppercase mb-2" style={{ color: 'var(--accent-primary)' }}>Result</p>
                <p className="text-sm whitespace-pre-wrap">{synthesis.result}</p>
              </div>
            )}

            {synthesis.hypothesis && (
              <div className="mb-5">
                <p className="text-xs text-muted font-mono uppercase mb-2" style={{ color: 'var(--accent-primary)' }}>Hypothesis</p>
                <p className="text-sm whitespace-pre-wrap">{synthesis.hypothesis}</p>
              </div>
            )}

            {synthesis.steps && (() => {
              const raw = synthesis.steps;
              const parts = raw.split(/(?=Step\s+\d+\s*[:.]\s*)/i).filter(s => s.trim());
              if (parts.length > 1) {
                return (
                  <div className="mb-5">
                    <p className="text-xs text-muted font-mono uppercase mb-2" style={{ color: 'var(--accent-primary)' }}>Steps</p>
                    <div className="steps-list">
                      {parts.map((step, i) => {
                        const colonIdx = step.indexOf(':');
                        const dotIdx = step.indexOf('.');
                        const splitIdx = colonIdx > 0 ? colonIdx : (dotIdx > 0 && dotIdx < 40 ? dotIdx : -1);
                        const title = splitIdx > 0 ? step.slice(0, splitIdx).trim() : `Step ${i + 1}`;
                        const body = splitIdx > 0 ? step.slice(splitIdx + 1).trim() : step.trim();
                        return (
                          <div key={i} className="step-card">
                            <div className="step-number">{title}</div>
                            <p className="text-sm">{body}</p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              }
              return (
                <div className="mb-5">
                  <p className="text-xs text-muted font-mono uppercase mb-2" style={{ color: 'var(--accent-primary)' }}>Steps</p>
                  <p className="text-sm whitespace-pre-wrap">{raw}</p>
                </div>
              );
            })()}

            {synthesis.literature_citations && (
              <div className="mb-5">
                <p className="text-xs text-muted font-mono uppercase mb-2" style={{ color: 'var(--accent-primary)' }}>Literature Review Citations</p>
                <p className="text-sm whitespace-pre-wrap">{synthesis.literature_citations}</p>
              </div>
            )}

            {pipelineState.action_items?.length > 0 && (
              <div className="mt-4 pt-4 border-t border-subtle">
                <p className="text-xs text-muted font-mono uppercase mb-1">Action Items</p>
                <ul className="text-sm list-disc pl-4">
                  {pipelineState.action_items.map((item, i) => <li key={i}>{item}</li>)}
                </ul>
              </div>
            )}

            {pipelineState.caveats?.length > 0 && (
              <div className="mt-4 pt-4 border-t border-subtle">
                <p className="text-xs text-muted font-mono uppercase mb-1">Caveats</p>
                <ul className="text-sm list-disc pl-4">
                  {pipelineState.caveats.map((c, i) => <li key={i}>{c}</li>)}
                </ul>
              </div>
            )}
          </>
        )}
      </div>

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

      {/* Chat Panel */}
      <ChatPanel
        isOpen={chatOpen}
        onClose={() => setChatOpen(false)}
        pipelineState={pipelineState}
        projectId={id}
      />
    </div>
  );
}
