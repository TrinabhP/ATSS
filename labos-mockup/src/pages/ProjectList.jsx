import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Plus, Folder, ArrowRight } from 'lucide-react';

export default function ProjectList() {
  const navigate = useNavigate();

  const projects = [];

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

      <div className="projects-grid">
        {projects.map((proj) => (
          <div key={proj.id} className="project-card" onClick={() => navigate(`/projects/${proj.id}`)}>
            <div className="flex justify-between items-start mb-4">
              <Folder className="text-muted" size={24} />
              <span className={`badge ${proj.status === 'Completed' ? 'badge-success' : 'badge-moderate'}`}>
                {proj.status}
              </span>
            </div>
            <h3 className="font-semibold mb-2">{proj.title}</h3>
            <div className="mt-auto pt-4 border-t border-subtle flex justify-between items-center text-sm text-muted">
              <span>{proj.date}</span>
              <span className="flex items-center gap-1">{proj.agents}/3 Agents <ArrowRight size={14}/></span>
            </div>
          </div>
        ))}

        {/* Upload/Create New Bucket */}
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
    </motion.div>
  );
}
