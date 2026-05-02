import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Beaker, ArrowRight } from 'lucide-react';

export default function SignIn() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  
  const handleSignIn = (e) => {
    e.preventDefault();
    if(email) navigate('/projects');
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
          <h1 className="font-mono">LabOS</h1>
          <p className="text-muted">Scientific Research Engine</p>
        </div>
        
        <form onSubmit={handleSignIn} className="signin-form">
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
          <button type="submit" className="btn-primary w-full flex justify-between items-center">
            <span>Continue to LabOS</span>
            <ArrowRight size={18} />
          </button>
        </form>
        
        <div className="signin-divider">
          <span>or continue with</span>
        </div>
        
        <button className="btn-secondary w-full">Single Sign-On (SSO)</button>
      </motion.div>
    </div>
  );
}
