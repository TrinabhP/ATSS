import { useState, useEffect } from 'react';
import { useLocation, useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, FlaskConical, Network, X, ExternalLink, CheckCircle2, CircleDashed } from 'lucide-react';

export default function ProjectDashboard() {
  const { id } = useParams();
  const location = useLocation();
  const initialAbstract = location.state?.abstract || 'No abstract provided for this project. Loading from database...';
  
  const [activePanel, setActivePanel] = useState(null); // 'lit', 'hypothesis', 'design'
  const [progress, setProgress] = useState({ lit: 'running', hypothesis: 'waiting', design: 'waiting' });

  // Mock data loaded over time to simulate agents
  useEffect(() => {
    const timer1 = setTimeout(() => setProgress(p => ({ ...p, lit: 'done', hypothesis: 'running' })), 2000);
    const timer2 = setTimeout(() => setProgress(p => ({ ...p, hypothesis: 'done', design: 'running' })), 4000);
    const timer3 = setTimeout(() => setProgress(p => ({ ...p, design: 'done' })), 6000);
    return () => { clearTimeout(timer1); clearTimeout(timer2); clearTimeout(timer3); };
  }, []);

  const mockLitDocs = [
    { id: 1, title: 'Multi-Agent Debate Improves Reasoning', abstract: 'We show that...', score: 0.95 },
    { id: 2, title: 'Autonomous Research Protocols', abstract: 'An evaluation of LLMs...', score: 0.88 },
    { id: 3, title: 'Agentic Workflows in Science', abstract: 'Survey of methods...', score: 0.82 }
  ];

  const mockHypotheses = [
    { id: 1, type: 'Primary', text: 'Multi-agent frameworks utilizing independent critic agents will produce a 15% reduction in hallucination rates compared to single-agent setups.' },
    { id: 2, type: 'Null', text: 'There is no statistically significant difference in hallucination rates between multi-agent and single-agent frameworks.' }
  ];

  const renderStatus = (status) => {
    if (status === 'done') return <CheckCircle2 className="text-success" size={20} color="var(--success)" />;
    if (status === 'running') return <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 2, ease: "linear" }}><CircleDashed size={20} color="var(--accent-primary)" /></motion.div>;
    return <CircleDashed size={20} color="var(--text-secondary)" />;
  };

  return (
    <div className="project-dashboard relative">
      <div className="page-header">
        <h1 className="page-title">Project #{id} Dashboard</h1>
        <p className="text-muted">Research overview and agent status.</p>
      </div>

      <div className="card p-6 mb-6">
        <h3 className="font-mono mb-2 text-sm text-muted uppercase">Input Abstract</h3>
        <p className="text-sm">{initialAbstract}</p>
      </div>

      <h3 className="font-mono mb-4 mt-6 text-sm text-muted uppercase">Agent Modules</h3>
      <div className="overview-cards">
        
        {/* Agent 1: Literature */}
        <div className="agent-card flex flex-col" onClick={() => setActivePanel('lit')}>
          <div className="flex justify-between items-start mb-4">
            <div className="flex items-center gap-2 font-mono font-semibold">
              <Search size={18} color="var(--accent-primary)" />
              Agent 1: Lit Review
            </div>
            {renderStatus(progress.lit)}
          </div>
          <p className="text-sm text-muted flex-grow">Searches academic databases to extract relevant context and prior methodologies.</p>
          {progress.lit === 'done' && <div className="mt-4 pt-4 border-t border-subtle text-sm font-semibold" style={{ color: 'var(--success)' }}>3 Papers Extracted</div>}
        </div>

        {/* Agent 2: Hypothesis */}
        <div className="agent-card flex flex-col" onClick={() => setActivePanel('hypothesis')}>
          <div className="flex justify-between items-start mb-4">
            <div className="flex items-center gap-2 font-mono font-semibold">
              <FlaskConical size={18} color="var(--accent-primary)" />
              Agent 2: Hypothesis
            </div>
            {renderStatus(progress.hypothesis)}
          </div>
          <p className="text-sm text-muted flex-grow">Synthesizes literature to propose testable primary and null hypotheses.</p>
          {progress.hypothesis === 'done' && <div className="mt-4 pt-4 border-t border-subtle text-sm font-semibold" style={{ color: 'var(--success)' }}>2 Hypotheses Generated</div>}
        </div>

        {/* Agent 3: Research Design */}
        <div className="agent-card flex flex-col" onClick={() => setActivePanel('design')}>
          <div className="flex justify-between items-start mb-4">
            <div className="flex items-center gap-2 font-mono font-semibold">
              <Network size={18} color="var(--accent-primary)" />
              Agent 3: Protocol Design
            </div>
            {renderStatus(progress.design)}
          </div>
          <p className="text-sm text-muted flex-grow">Drafts a step-by-step scientific process cycle to test the hypothesis.</p>
          {progress.design === 'done' && <div className="mt-4 pt-4 border-t border-subtle text-sm font-semibold" style={{ color: 'var(--success)' }}>Protocol Ready</div>}
        </div>

      </div>

      {/* Slide-out Deep Dive Panel */}
      <AnimatePresence>
        {activePanel && (
          <>
            <motion.div 
              initial={{ opacity: 0 }} 
              animate={{ opacity: 1 }} 
              exit={{ opacity: 0 }} 
              className="slide-panel-backdrop"
              onClick={() => setActivePanel(null)}
            />
            <motion.div 
              initial={{ x: '100%' }} 
              animate={{ x: 0 }} 
              exit={{ x: '100%' }} 
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
                
                {/* Lit Review Panel */}
                {activePanel === 'lit' && (
                  <div>
                    {progress.lit !== 'done' ? <p className="text-muted text-sm">Agent is currently running searches...</p> : (
                      mockLitDocs.map(doc => (
                        <div key={doc.id} className="paper-card">
                          <div className="flex justify-between items-center mb-2">
                            <span className="font-semibold">{doc.title}</span>
                            <span className="badge badge-success">Score: {doc.score}</span>
                          </div>
                          <p className="text-sm text-muted mb-2">{doc.abstract}</p>
                          <a href="#" className="text-sm flex items-center gap-1" style={{ color: 'var(--accent-primary)' }}><ExternalLink size={14}/> View Source</a>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {/* Hypothesis Panel */}
                {activePanel === 'hypothesis' && (
                  <div>
                    {progress.hypothesis !== 'done' ? <p className="text-muted text-sm">Waiting for literature to synthesize hypotheses...</p> : (
                      mockHypotheses.map(hyp => (
                        <div key={hyp.id} className="hypothesis-card">
                          <h4 className="font-mono text-sm mb-2 uppercase" style={{ color: hyp.type === 'Primary' ? 'var(--accent-primary)' : 'var(--text-secondary)' }}>
                            {hyp.type} Hypothesis
                          </h4>
                          <p className="text-sm">{hyp.text}</p>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {/* Research Design Panel */}
                {activePanel === 'design' && (
                  <div>
                    {progress.design !== 'done' ? <p className="text-muted text-sm">Waiting for hypotheses to generate protocol...</p> : (
                      <div className="research-design-board">
                        <p className="text-sm text-muted mb-6">Generated step-by-step scientific process cycle.</p>
                        
                        <div className="design-step">
                          <h4 className="font-mono text-sm uppercase">1. Variables Definition</h4>
                          <ul className="text-sm list-disc pl-4 mt-2">
                            <li><strong>Independent:</strong> Agent architecture (Single vs Multi).</li>
                            <li><strong>Dependent:</strong> Hallucination rate (%).</li>
                            <li><strong>Controls:</strong> LLM model, prompt context, dataset.</li>
                          </ul>
                        </div>

                        <div className="design-step">
                          <h4 className="font-mono text-sm uppercase">2. Methodology Selection</h4>
                          <p className="text-sm mt-2">Quantitative Experimental Setup. Running A/B benchmark tests across 500 prompts from the standard evaluation set.</p>
                        </div>

                        <div className="design-step">
                          <h4 className="font-mono text-sm uppercase">3. Sampling Strategy</h4>
                          <p className="text-sm mt-2">Stratified sampling of 500 research abstracts spanning physics, biology, and computer science to ensure domain-agnostic results.</p>
                        </div>

                        <div className="design-step">
                          <h4 className="font-mono text-sm uppercase">4. Data Collection</h4>
                          <p className="text-sm mt-2">Automated script to evaluate outputs using a strict LLM-as-a-judge scoring matrix for factuality.</p>
                        </div>

                        <div className="design-step">
                          <h4 className="font-mono text-sm uppercase">5. Analysis Plan</h4>
                          <p className="text-sm mt-2">Two-sample t-test to determine if the 15% reduction is statistically significant (p &lt; 0.05).</p>
                        </div>
                        
                      </div>
                    )}
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
