import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronRight, CheckCircle2, CircleDashed, Download, ExternalLink } from 'lucide-react';

const STAGES = [
  { id: 'agent1', label: 'Literature' },
  { id: 'agent2', label: 'Extract' },
  { id: 'agent3', label: 'Analysis' },
  { id: 'debate1', label: 'Debate 1' },
  { id: 'debate2', label: 'Debate 2' },
  { id: 'debate3', label: 'Debate 3' },
  { id: 'final', label: 'Recommendation' }
];

function Accordion({ title, children, defaultOpen = true }) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="accordion-item">
      <button className="accordion-header" onClick={() => setIsOpen(!isOpen)}>
        <span>{title}</span>
        {isOpen ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
      </button>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="accordion-content"
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function AnalysisView() {
  const location = useLocation();
  const abstract = location.state?.abstract || 'No abstract provided. This is a mock analysis.';

  const [currentStageIndex, setCurrentStageIndex] = useState(0);
  const [isFinished, setIsFinished] = useState(false);

  // Mock Data
  const [papers, setPapers] = useState([]);
  const [extractedResults, setExtractedResults] = useState([]);
  const [initialSynthesis, setInitialSynthesis] = useState(null);
  const [debateRounds, setDebateRounds] = useState([]);
  const [finalRec, setFinalRec] = useState(null);

  useEffect(() => {
    if (isFinished) return;

    if (currentStageIndex < STAGES.length) {
      const timer = setTimeout(() => {
        const stageId = STAGES[currentStageIndex].id;
        
        if (stageId === 'agent1') {
          setPapers([{ title: 'Multi-Agent Debate Improves Reasoning', url: '#', abstract: 'We show that...', relevance_score: 0.95 }]);
        } else if (stageId === 'agent2') {
          setExtractedResults([{ paper_title: 'Multi-Agent Debate Improves Reasoning', key_findings: ['Debate improves accuracy by 15%'], methods: 'Empirical evaluation' }]);
        } else if (stageId === 'agent3') {
          setInitialSynthesis({ text: 'Initial evidence suggests multi-agent systems outperform single agents.', gaps: ['Sample sizes are limited'] });
        } else if (stageId.startsWith('debate')) {
          setDebateRounds(prev => [...prev, { round_number: prev.length + 1, critic_feedback: 'Sample size concerns.', results_refinement: 'Re-evaluating data.', analysis_update: 'Updated synthesis.' }]);
        } else if (stageId === 'final') {
          setFinalRec({ recommendation: 'We recommend utilizing multi-agent debate.', confidence_level: 'Moderate', action_items: ['Implement loop'], caveats: ['High cost'] });
          setIsFinished(true);
        }

        setCurrentStageIndex(prev => prev + 1);
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [currentStageIndex, isFinished]);

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="analysis-view">
      <div className="page-header flex justify-between items-center">
        <div>
          <h1 className="page-title">Analysis Pipeline</h1>
          <p className="text-muted">Real-time execution tracker</p>
        </div>
        <div className="flex gap-4">
          <button className="btn-secondary flex items-center gap-2" disabled={!isFinished}>
            <Download size={16} /> Export PDF
          </button>
        </div>
      </div>

      <div className="split-view">
        {/* Left Pane */}
        <div>
          <div className="card p-6 mb-6">
            <h3 className="font-mono mb-4 text-sm text-muted uppercase">Input Abstract</h3>
            <p className="text-sm">{abstract}</p>
          </div>

          <div className="card p-6">
            <h3 className="font-mono mb-4 text-sm text-muted uppercase">Pipeline Status</h3>
            <div className="flex flex-wrap gap-4">
              {STAGES.map((stage, idx) => {
                const isActive = idx === currentStageIndex && !isFinished;
                const isCompleted = idx < currentStageIndex || isFinished;
                
                return (
                  <div key={stage.id} className="flex items-center gap-3">
                    {isCompleted ? (
                      <CheckCircle2 size={20} className="text-success" color="var(--success)" />
                    ) : isActive ? (
                      <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 2, ease: "linear" }}>
                        <CircleDashed size={20} color="var(--accent-primary)" />
                      </motion.div>
                    ) : (
                      <CircleDashed size={20} color="var(--text-secondary)" />
                    )}
                    <span 
                      className={`text-sm ${isActive ? 'font-semibold' : ''}`} 
                      style={{ color: isActive || isCompleted ? 'var(--text-primary)' : 'var(--text-secondary)' }}
                    >
                      {stage.label}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Pane (Results) */}
        <div className="results-pane flex flex-col gap-4">
          {papers.length > 0 && (
            <Accordion title="Agent 1: Literature Found">
              {papers.map((p, i) => {
                return (
                  <div key={i} className="paper-card">
                    <div className="flex justify-between mb-2">
                      <span className="font-semibold">{p.title}</span>
                      <span className="badge badge-success">Score: {p.relevance_score}</span>
                    </div>
                    <p className="text-sm text-muted mb-2">{p.abstract}</p>
                    <a href={p.url} className="text-sm flex items-center gap-1" style={{ color: 'var(--accent-primary)' }}>
                      <ExternalLink size={14}/> View Paper
                    </a>
                  </div>
                );
              })}
            </Accordion>
          )}

          {extractedResults.length > 0 && (
            <Accordion title="Agent 2: Extracted Data">
              {extractedResults.map((r, i) => {
                return (
                  <div key={i} className="paper-card">
                    <span className="font-semibold">{r.paper_title}</span>
                    <div className="text-sm mt-2"><strong>Findings:</strong> {r.key_findings.join(', ')}</div>
                  </div>
                );
              })}
            </Accordion>
          )}

          {initialSynthesis && (
            <Accordion title="Agent 3: Initial Synthesis">
              <p className="text-sm">{initialSynthesis.text}</p>
              <div className="mt-2 text-sm" style={{ color: 'var(--warning)' }}>
                <strong>Gaps:</strong> {initialSynthesis.gaps.join(', ')}
              </div>
            </Accordion>
          )}

          {debateRounds.length > 0 && debateRounds.map((r, i) => {
            return (
              <Accordion key={i} title={`Debate Round ${r.round_number}`}>
                <div className="debate-block debate-critic text-sm mb-2"><strong>Critic:</strong> {r.critic_feedback}</div>
                <div className="debate-block debate-results text-sm mb-2"><strong>Results:</strong> {r.results_refinement}</div>
                <div className="debate-block debate-analysis text-sm"><strong>Analysis:</strong> {r.analysis_update}</div>
              </Accordion>
            );
          })}

          {finalRec && (
            <motion.div initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} className="card p-6" style={{ borderLeft: '4px solid var(--success)' }}>
              <div className="flex justify-between items-center mb-4">
                <h2 className="font-mono text-lg">Final Recommendation</h2>
                <span className={`badge badge-${finalRec.confidence_level.toLowerCase()}`}>{finalRec.confidence_level} Confidence</span>
              </div>
              <p className="text-sm mb-4">{finalRec.recommendation}</p>
              
              <div className="flex gap-4">
                <div className="w-full">
                  <h4 className="font-mono text-sm mb-2" style={{ color: 'var(--success)' }}>Action Items</h4>
                  <ul className="text-sm" style={{ paddingLeft: '1.5rem' }}>
                    {finalRec.action_items.map((item, i) => { return <li key={i}>{item}</li>; })}
                  </ul>
                </div>
                <div className="w-full">
                  <h4 className="font-mono text-sm mb-2" style={{ color: 'var(--warning)' }}>Caveats</h4>
                  <ul className="text-sm" style={{ paddingLeft: '1.5rem' }}>
                    {finalRec.caveats.map((item, i) => { return <li key={i}>{item}</li>; })}
                  </ul>
                </div>
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
