import { useLocation, useNavigate } from 'react-router-dom';
import { Plus, History, Sun, Moon, LogOut } from 'lucide-react';
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
      <div className="sidebar-header">
        <div style={{ color: 'var(--accent-primary)', fontSize: '1.5rem' }}>⬡</div>
        <span>LabOS</span>
      </div>

      <button className="new-analysis-btn" onClick={() => navigate('/dashboard')}>
        <Plus size={18} />
        New Analysis
      </button>

      <div className="sidebar-section">
        <div className="sidebar-label">Recent Projects</div>
        <ul className="history-list">
          {recentProjects.map(proj => (
            <li 
              key={proj.id} 
              className={`history-item ${location.pathname.includes('/analysis') ? '' : ''}`}
            >
              <History size={14} />
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
