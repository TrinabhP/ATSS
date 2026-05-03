import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';

export default function NewProject() {
  const [abstract, setAbstract] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!abstract.trim()) return;

    setIsSubmitting(true);
    // In a production app, we would await a real API call here to create the project
    const newProjectId = Date.now(); // Generate a unique ID based on timestamp
    navigate(`/projects/${newProjectId}`, { state: { abstract } });
  };

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="new-project-view max-w-2xl mx-auto mt-8">
      <div className="page-header text-center">
        <h1 className="page-title">Initialize Research Project</h1>
        <p className="text-muted">Input your research abstract to kick off the 3-agent pipeline.</p>
      </div>

      <div className="card p-6">
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="abstract">Research Abstract</label>
            <textarea
              id="abstract"
              className="abstract-textarea"
              placeholder="Enter the abstract or background context for your research..."
              value={abstract}
              onChange={(e) => setAbstract(e.target.value)}
              required
            />
          </div>
          <div className="flex justify-between items-center mt-6">
            <button type="button" className="btn-secondary" onClick={() => navigate('/projects')}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={!abstract.trim() || isSubmitting}>
              {isSubmitting ? 'Initializing...' : 'Launch Agents'}
            </button>
          </div>
        </form>
      </div>
    </motion.div>
  );
}
