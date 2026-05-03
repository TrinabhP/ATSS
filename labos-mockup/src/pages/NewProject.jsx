import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { supabase } from '../lib/supabase';
import { useAuth } from '../context/AuthContext';

export default function NewProject() {
  const [abstract, setAbstract] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const { user } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!abstract.trim()) return;

    setIsSubmitting(true);
    setError(null);

    // If Supabase is not configured, skip DB insert and navigate directly
    if (!supabase) {
      const newProjectId = Date.now();
      navigate(`/projects/${newProjectId}`, { state: { abstract } });
      return;
    }

    const { data, error: insertError } = await supabase
      .from('projects')
      .insert({
        user_id: user.id,
        name: 'Untitled Project',
        abstract,
        status: 'running',
      })
      .select()
      .single();

    if (insertError) {
      setError(insertError.message);
      setIsSubmitting(false);
      return;
    }

    navigate(`/projects/${data.id}`, { state: { abstract } });
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
          {error && (
            <div className="text-red-500 text-sm mt-2" role="alert">
              {error}
            </div>
          )}
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
