import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Plus, FolderKanban, Sun, Moon, LogOut, User, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useAuth } from '../../context/AuthContext';
import { supabase } from '../../lib/supabase';

export default function Sidebar() {
  const { theme, toggleTheme } = useTheme();
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [isCollapsed, setIsCollapsed] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [recentProjects, setRecentProjects] = useState([]);

  // Fetch user's projects from Supabase
  useEffect(() => {
    if (!user) return;

    const fetchProjects = async () => {
      if (!supabase) return;
      const { data } = await supabase
        .from('projects')
        .select('id, name')
        .order('created_at', { ascending: false })
        .limit(10);
      if (data) setRecentProjects(data);
    };

    fetchProjects();
  }, [user, location.pathname]);

  return (
    <div className={`sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header" style={{ display: 'flex', width: '100%', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer', flex: 1, overflow: 'hidden' }} onClick={() => navigate('/projects')}>
          <div style={{ color: 'var(--accent-primary)', fontSize: '1.5rem', minWidth: '24px' }}>⬡</div>
          {!isCollapsed && <span>SynThesis</span>}
        </div>
        <button className="sidebar-header-collapse-btn" onClick={() => setIsCollapsed(!isCollapsed)}>
          {isCollapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
        </button>
      </div>

      <button className="new-analysis-btn" onClick={() => navigate('/projects/new')} style={{ justifyContent: isCollapsed ? 'center' : 'flex-start' }}>
        <Plus size={18} style={{ minWidth: '18px' }} />
        {!isCollapsed && "New Project"}
      </button>

      <div className="sidebar-section">
        {!isCollapsed && <div className="sidebar-label">Your Projects</div>}
        <ul className="history-list">
          <li 
            className={`history-item ${location.pathname === '/projects' ? 'active' : ''}`}
            onClick={() => navigate('/projects')}
            style={{ justifyContent: isCollapsed ? 'center' : 'flex-start' }}
            title="All Projects"
          >
            <FolderKanban size={14} style={{ minWidth: '14px' }} />
            {!isCollapsed && <span>All Projects</span>}
          </li>
          {recentProjects.map(proj => (
            <li 
              key={proj.id} 
              className={`history-item ${location.pathname === `/projects/${proj.id}` ? 'active' : ''}`}
              onClick={() => navigate(`/projects/${proj.id}`)}
              style={{ justifyContent: isCollapsed ? 'center' : 'flex-start' }}
              title={proj.name}
            >
              <span className="text-muted" style={{ fontSize: '10px', minWidth: '10px' }}>•</span>
              {!isCollapsed && <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{proj.name}</span>}
            </li>
          ))}
        </ul>
      </div>

      <div className="sidebar-footer" style={{ position: 'relative', flexDirection: isCollapsed ? 'column' : 'row', gap: isCollapsed ? '1rem' : '0' }}>
        <button className="theme-toggle" onClick={toggleTheme}>
          {theme === 'light' ? <Moon size={20} /> : <Sun size={20} />}
        </button>
        <div style={{ position: 'relative', display: 'flex', justifyContent: 'center' }}>
          <button className="theme-toggle" onClick={() => setShowProfileMenu(!showProfileMenu)}>
            <User size={20} />
          </button>
          
          {showProfileMenu && (
            <div className="profile-menu">
              <button onClick={() => { setShowProfileMenu(false); /* navigate to profile */ }}>
                <User size={16} /> Profile
              </button>
              <button onClick={async () => {
                setShowProfileMenu(false);
                if (supabase) await supabase.auth.signOut();
                navigate('/');
              }}>
                <LogOut size={16} /> Log Out
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
