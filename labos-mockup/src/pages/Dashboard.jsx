import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FileText, ArrowRight } from 'lucide-react';

export default function Dashboard() {
  const [abstract, setAbstract] = useState('');
  const navigate = useNavigate();

  const handleLaunch = () => {
    if (abstract.length >= 20) {
      navigate('/analysis/new', { state: { abstract } });
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="dashboard"
    >
      <div className="page-header flex justify-between items-center">
        <div>
          <h1 className="page-title">New Analysis</h1>
          <p className="text-muted">Initialize a multi-agent literature review pipeline.</p>
        </div>
      </div>

      <div className="card p-6">
        <div className="form-group">
          <label className="flex items-center gap-2">
            <FileText size={16} />
            Research Abstract or Question
          </label>
          <textarea
            className="abstract-textarea"
            placeholder="Paste your abstract here to begin the analysis... (min 20 chars)"
            value={abstract}
            onChange={(e) => setAbstract(e.target.value)}
          />
          <div className="flex justify-between items-center mt-2">
            <span className="text-sm text-muted">{abstract.length} / 4000</span>
            <button 
              className="btn-primary flex items-center gap-2"
              disabled={abstract.length < 20 || abstract.length > 4000}
              onClick={handleLaunch}
            >
              Launch Pipeline
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
