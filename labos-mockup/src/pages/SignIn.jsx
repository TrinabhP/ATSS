import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Beaker, ArrowRight } from 'lucide-react';
import { supabase } from '../lib/supabase';

export default function SignIn() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [isSignUp, setIsSignUp] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isSignUp) {
        const { error: signUpError } = await supabase.auth.signUp({
          email,
          password,
        });
        if (signUpError) {
          setError(signUpError.message);
          return;
        }
        // Sign-up succeeded — some Supabase configs auto-confirm,
        // others require email verification. Navigate on success.
        navigate('/projects');
      } else {
        const { error: signInError } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (signInError) {
          setError(signInError.message);
          return;
        }
        navigate('/projects');
      }
    } catch (err) {
      setError(err.message || 'An unexpected error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="signin-container">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="signin-card card"
      >
        <div className="signin-header">
          <Beaker className="signin-logo" size={40} />
          <h1 className="font-mono">SynThesis</h1>
          <p className="text-muted">Scientific Research Engine</p>
        </div>
        
        <form onSubmit={handleSubmit} className="signin-form">
          <div className="form-group">
            <label>Institutional Email</label>
            <input 
              type="email" 
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="researcher@university.edu"
              className="signin-input"
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Enter your password"
              className="signin-input"
              minLength={6}
            />
          </div>

          {error && (
            <div className="auth-error" style={{ color: 'var(--status-error, #ef4444)', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
              {error}
            </div>
          )}

          <button type="submit" className="btn-primary w-full flex justify-between items-center" disabled={loading}>
            <span>{loading ? 'Please wait…' : isSignUp ? 'Create Account' : 'Continue to SynThesis'}</span>
            <ArrowRight size={18} />
          </button>
        </form>
        
        <div className="signin-divider">
          <span>or</span>
        </div>
        
        <button
          type="button"
          className="btn-secondary w-full"
          onClick={() => {
            setIsSignUp(!isSignUp);
            setError('');
          }}
        >
          {isSignUp ? 'Already have an account? Sign In' : "Don't have an account? Sign Up"}
        </button>
      </motion.div>
    </div>
  );
}
