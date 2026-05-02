import { useLocation, useNavigate } from 'react-router-dom';
import { Plus, FolderKanban, Sun, Moon, LogOut } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';

export default function Sidebar() {
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();

  const recentProjects = [
    { id: 1, title: 'Multi-Agent Debate Frameworks' },
    { id: 2, title: 'CRISPR Off-target Effects' },
    { id: 3, title: 'Quantum Error Correction' }
  ];

  return (
    <div className="sidebar">
      <div className="sidebar-header" style={{ cursor: 'pointer' }} onClick={() => navigate('/projects')}>
        <div style={{ color: 'var(--accent-primary)', fontSize: '1.5rem' }}>⬡</div>
        <span>LabOS</span>
      </div>

      <button className="new-analysis-btn" onClick={() => navigate('/projects/new')}>
        <Plus size={18} />
        New Project
      </button>

      <div className="sidebar-section">
        <div className="sidebar-label">Your Projects</div>
        <ul className="history-list">
          <li 
            className={`history-item ${location.pathname === '/projects' ? 'active' : ''}`}
            onClick={() => navigate('/projects')}
          >
            <FolderKanban size={14} />
            <span>All Projects</span>
          </li>
          {recentProjects.map(proj => (
            <li 
              key={proj.id} 
              className={`history-item ${location.pathname === `/projects/${proj.id}` ? 'active' : ''}`}
              onClick={() => navigate(`/projects/${proj.id}`)}
            >
              <span className="text-muted" style={{ fontSize: '10px' }}>•</span>
              <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{proj.title}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="sidebar-footer">
        <button className="theme-toggle" onClick={toggleTheme}>
          {theme === 'light' ? <Moon size={20} /> : <Sun size={20} />}
        </button>
        <button className="theme-toggle" onClick={() => navigate('/')}>
          <LogOut size={20} />
        </button>
      </div>
    </div>
  );
}
