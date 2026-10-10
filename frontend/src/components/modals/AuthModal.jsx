import React, { useState } from 'react';
import Modal from '../common/Modal';
import { Mail, Lock, Eye, EyeOff, User, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { authSession, ApiError } from '../../services/api';

export default function AuthModal({ isOpen, onClose }) {
  const { syncProfileFromBackend } = useApp();
  const [isRegister, setIsRegister] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    const cleanEmail = email.trim();
    if (!cleanEmail || !cleanEmail.includes('@')) {
      setError('Please provide a valid email address.');
      return;
    }
    if (!password || password.length < 6) {
      setError('Password must contain at least 6 characters.');
      return;
    }
    if (isRegister && !name.trim()) {
      setError('Full name is required for account registration.');
      return;
    }

    setLoading(true);
    try {
      if (isRegister) {
        await authSession.signUp(cleanEmail, password, { displayName: name.trim() });
      } else {
        await authSession.signInWithPassword(cleanEmail, password);
      }

      setSuccess(true);
      // Synchronize backend profile into AppContext
      await syncProfileFromBackend();

      setTimeout(() => {
        setSuccess(false);
        setLoading(false);
        setPassword('');
        onClose();
      }, 800);
    } catch (err) {
      setLoading(false);
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Authentication request failed. Please check network connectivity.');
      }
    }
  };

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose} 
      title={isRegister ? "Create Your PERFORMX Account" : "Sign In to PERFORMX"}
      subtitle={isRegister ? "Start tracking real-time movement biomechanics today." : "Access your personalized training routines and form logs."}
    >
      <div className="tabs-container" style={{ width: '100%', marginBottom: 20 }}>
        <button 
          type="button"
          className={`tab-btn ${!isRegister ? 'active' : ''}`} 
          style={{ flex: 1, textAlign: 'center' }}
          disabled={loading}
          onClick={() => { setIsRegister(false); setError(''); }}
        >
          Sign In
        </button>
        <button 
          type="button"
          className={`tab-btn ${isRegister ? 'active' : ''}`} 
          style={{ flex: 1, textAlign: 'center' }}
          disabled={loading}
          onClick={() => { setIsRegister(true); setError(''); }}
        >
          Register
        </button>
      </div>

      {error && (
        <div className="feedback-box feedback-error" style={{ marginBottom: 16 }}>
          <AlertCircle size={18} style={{ flexShrink: 0 }} />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="feedback-box feedback-success" style={{ marginBottom: 16 }}>
          <CheckCircle2 size={18} style={{ flexShrink: 0 }} />
          <span>Authentication successful. Synchronizing athlete profile...</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex-col gap-4">
        {isRegister && (
          <div>
            <label className="font-semibold text-primary" style={{ display: 'block', marginBottom: 6, fontSize: '0.85rem' }}>
              Full Name
            </label>
            <div className="input-wrapper">
              <User className="input-icon" size={17} />
              <input
                type="text"
                className="input-field has-icon"
                placeholder="e.g. Alex Morgan"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
          </div>
        )}

        <div>
          <label className="font-semibold text-primary" style={{ display: 'block', marginBottom: 6, fontSize: '0.85rem' }}>
            Email Address
          </label>
          <div className="input-wrapper">
            <Mail className="input-icon" size={17} />
            <input
              type="email"
              className="input-field has-icon"
              placeholder="athlete@performx.ai"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
        </div>

        <div>
          <label className="font-semibold text-primary" style={{ display: 'block', marginBottom: 6, fontSize: '0.85rem' }}>
            Password
          </label>
          <div className="input-wrapper">
            <Lock className="input-icon" size={17} />
            <input
              type={showPassword ? 'text' : 'password'}
              className="input-field has-icon"
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <button
              type="button"
              className="btn-ghost btn-icon btn-sm"
              style={{ position: 'absolute', right: 10 }}
              onClick={() => setShowPassword(!showPassword)}
              aria-label="Toggle password visibility"
            >
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
        </div>

        <div className="flex-row justify-between items-center" style={{ fontSize: '0.825rem' }}>
          <label className="flex-row items-center gap-2" style={{ cursor: 'pointer', color: 'var(--text-secondary)' }}>
            <input type="checkbox" defaultChecked />
            <span>Remember this device</span>
          </label>
          <a href="#forgot" onClick={(e) => { e.preventDefault(); alert("Password reset link will be sent to your registered email."); }}>
            Forgot password?
          </a>
        </div>

        <button 
          type="submit" 
          className="btn btn-primary btn-lg" 
          style={{ width: '100%', marginTop: 8 }}
          disabled={loading}
        >
          {loading ? (
            <span className="flex-row items-center justify-center gap-2">
              <Loader2 size={18} className="animate-spin" />
              <span>{isRegister ? "Creating Account..." : "Signing In..."}</span>
            </span>
          ) : (
            <span>{isRegister ? "Complete Registration" : "Sign In to Dashboard"}</span>
          )}
        </button>

        <div style={{ textAlign: 'center', margin: '8px 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          <span>Protected by On-Device Edge Biometrics Security</span>
        </div>
      </form>
    </Modal>
  );
}
