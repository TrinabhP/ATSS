import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import { isSupabaseConfigured } from './lib/supabase';
import SignIn from './pages/SignIn';
import Layout from './components/Layout/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import ProjectList from './pages/ProjectList';
import NewProject from './pages/NewProject';
import ProjectDashboard from './pages/ProjectDashboard';
import './App.css';

function SignInRoute() {
  const { user, loading } = useAuth();

  // No Supabase — skip sign-in, go straight to projects
  if (!isSupabaseConfigured) return <Navigate to="/projects" replace />;

  if (loading) return null;
  if (user) return <Navigate to="/projects" replace />;

  return <SignIn />;
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<SignInRoute />} />

        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route path="/projects" element={<ProjectList />} />
            <Route path="/projects/new" element={<NewProject />} />
            <Route path="/projects/:id" element={<ProjectDashboard />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
