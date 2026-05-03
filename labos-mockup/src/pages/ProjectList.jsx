import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Plus, Folder, ArrowRight, Loader } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { useAuth } from '../context/AuthContext';

/**
 * Returns the appropriate badge class for a project status.
 * - 'completed' → green (badge-success)
 * - 'running'   → yellow/orange (badge-moderate)
 * - 'error'     → red (badge-warning)
 */
function getStatusBadgeClass(status) {
  switch (status) {
    case 'completed':
      return 'badge-success';
    case 'error':
      return 'badge-warning';
    case 'running':
    default:
      return 'badge-moderate';
  }
}

/**
 * Formats an ISO date string into a human-readable format.
 */
function formatDate(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export default function ProjectList() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchProjects() {
      if (!user) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        const { data, error: queryError } = supabase
          ? await supabase
            .from('projects')
            .select('*')
            .order('created_at', { ascending: false })
          : { data: [], error: null };

        if (queryError) {
          throw queryError;
        }

        setProjects(data || []);
      } catch (err) {
        console.error('Failed to fetch projects:', err);
        setError('Failed to load projects. Please try again.');
      } finally {
        setLoading(false);
      }
    }

    fetchProjects();
  }, [user]);

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="project-list">
      <div className="page-header flex justify-between items-center">
        <div>
          <h1 className="page-title">Projects</h1>
          <p className="text-muted">Manage your research workspaces.</p>
        </div>
        <button className="btn-primary flex items-center gap-2" onClick={() => navigate('/projects/new')}>
          <Plus size={16} /> New Project
        </button>
      </div>

      {/* Loading State */}
      {loading && (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '4rem 0' }}>
          <Loader className="spin" size={24} style={{ color: 'var(--text-secondary)' }} />
          <span style={{ marginLeft: '0.75rem', color: 'var(--text-secondary)' }}>Loading projects…</span>
        </div>
      )}

      {/* Error State */}
      {!loading && error && (
        <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--warning)' }}>
          <p>{error}</p>
        </div>
      )}

      {/* Projects Grid */}
      {!loading && !error && (
        <div className="projects-grid">
          {projects.map((proj) => (
            <div key={proj.id} className="project-card" onClick={() => navigate(`/projects/${proj.id}`)}>
              <div className="flex justify-between items-start mb-4">
                <Folder className="text-muted" size={24} />
                <span className={`badge ${getStatusBadgeClass(proj.status)}`}>
                  {proj.status}
                </span>
              </div>
              <h3 className="font-semibold mb-2" style={{ fontSize: '1.1rem' }}>{proj.name}</h3>
              <div className="mt-auto pt-4 border-t border-subtle flex justify-between items-center text-sm text-muted">
                <span>{formatDate(proj.created_at)}</span>
                <span className="flex items-center gap-1"><ArrowRight size={14} /></span>
              </div>
            </div>
          ))}

          {/* Create New Project Card — always shown as last card */}
          <div
            className="project-card"
            style={{ borderStyle: 'dashed', backgroundColor: 'transparent', justifyContent: 'center', alignItems: 'center', textAlign: 'center' }}
            onClick={() => navigate('/projects/new')}
          >
            <Plus size={32} className="text-muted mb-2" />
            <h3 className="font-semibold">Create New Project</h3>
            <p className="text-sm text-muted mt-2">Initialize a new 3-agent research pipeline.</p>
          </div>
        </div>
      )}
    </motion.div>
  );
}
