import React, { useState, useRef, useEffect } from 'react';
import { 
  Bot, 
  Send, 
  Sparkles, 
  AlertTriangle, 
  ShieldCheck, 
  RefreshCw, 
  ExternalLink,
  ChevronDown,
  Info,
  Clock,
  CheckCircle2,
  Trash2
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { apiClient } from '../services/api';

export default function AICoachPage() {
  const { 
    userProfile, 
    isAuthenticated, 
    toggleModal, 
    activeSession, 
    enrolledPlan, 
    nutrition, 
    workoutHistory 
  } = useApp();

  const [inputMessage, setInputMessage] = useState('');
  const [messages, setMessages] = useState([
    {
      id: 'welcome-1',
      sender: 'assistant',
      text: `Hello ${userProfile.name?.split(' ')[0] || 'Athlete'}! I'm your PERFORMX Biomechanics & AI Coach. I'm strictly grounded in your verified workout repetitions, movement symmetry, active training plan, and health profile. How can I assist your training today?`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      entities: [],
      warnings: [],
      isFallback: false,
    }
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastPrompt, setLastPrompt] = useState('');

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (textToSend = null) => {
    const text = (textToSend || inputMessage).trim();
    if (!text || loading) return;

    if (!isAuthenticated) {
      setError('Please sign in to communicate with your authenticated AI Coach.');
      toggleModal('auth', true);
      return;
    }

    const userMsg = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages(prev => [...prev, userMsg]);
    setInputMessage('');
    setError(null);
    setLoading(true);
    setLastPrompt(text);

    try {
      const response = await apiClient.chat.sendMessage(text, activeSession?.sessionId || null);

      const assistantMsg = {
        id: `assistant-${Date.now()}`,
        sender: 'assistant',
        text: response.reply,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        entities: response.grounded_entities || [],
        warnings: response.warnings || [],
        isFallback: (response.warnings || []).some(w => w.includes('deterministic rules') || w.includes('temporarily unavailable')),
      };

      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      console.error('Chat request error:', err);
      setError(err.message || 'Unable to reach the AI Coach service. Please try again.');
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  const handleRetry = () => {
    if (lastPrompt) {
      handleSend(lastPrompt);
    }
  };

  const handleClearHistory = () => {
    setMessages([
      {
        id: 'welcome-reset',
        sender: 'assistant',
        text: `Conversation cleared. What would you like to review from your verified PERFORMX data?`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        entities: [],
        warnings: [],
      }
    ]);
    setError(null);
  };

  const quickPrompts = [
    { label: 'Analyze Latest Workout', prompt: 'How was my latest workout performance and symmetry score?' },
    { label: 'Check Plan & Restrictions', prompt: 'What exercises are in my active plan and do any clinician restrictions apply?' },
    { label: 'Nutrition & Allergen Status', prompt: 'What is my recorded nutrition today and is there any allergen advisory?' },
    { label: 'Injury & Recovery Status', prompt: 'What is my current recovery check-in status and joint discomfort rating?' },
  ];

  return (
    <div className="flex-col gap-6" style={{ height: 'calc(100vh - 120px)', minHeight: 650 }}>
      {/* 1. Header / Safety Notice Banner */}
      <div className="card flex-col gap-2" style={{ padding: '16px 20px', background: 'var(--surface-card)' }}>
        <div className="flex-row justify-between items-center">
          <div className="flex-row items-center gap-3">
            <div style={{ 
              width: 40, 
              height: 40, 
              borderRadius: 'var(--radius-md)', 
              background: 'linear-gradient(135deg, var(--primary-purple) 0%, #3B82F6 100%)',
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              color: '#FFF' 
            }}>
              <Bot size={22} />
            </div>
            <div>
              <div className="flex-row items-center gap-2">
                <h2 style={{ fontSize: '1.15rem', fontWeight: 700, margin: 0 }}>PERFORMX AI Coach</h2>
                <span className="badge badge-purple" style={{ fontSize: '0.725rem' }}>Grounded & Private</span>
                {isAuthenticated && <span className="badge badge-teal" style={{ fontSize: '0.725rem' }}>Authenticated Context</span>}
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0 }}>
                Evidence-based biomechanical coaching strictly bound to your verified telemetry, clinical restrictions, and nutrition.
              </p>
            </div>
          </div>

          <div className="flex-row items-center gap-2">
            <button 
              className="btn btn-secondary btn-sm" 
              onClick={handleClearHistory} 
              title="Clear current in-memory chat session"
              style={{ fontSize: '0.785rem' }}
            >
              <Trash2 size={14} />
              <span>Clear</span>
            </button>
          </div>
        </div>

        {/* Safety Invariant Badges */}
        <div className="flex-row items-center gap-4" style={{ 
          fontSize: '0.75rem', 
          color: 'var(--text-muted)', 
          paddingTop: 8, 
          borderTop: '1px solid var(--border-subtle)',
          flexWrap: 'wrap'
        }}>
          <span className="flex-row items-center gap-1">
            <ShieldCheck size={13} className="text-teal" /> Zero Vision Frames Transmitted
          </span>
          <span className="flex-row items-center gap-1">
            <ShieldCheck size={13} className="text-teal" /> Non-Clinical / No Medical Diagnosis
          </span>
          <span className="flex-row items-center gap-1">
            <ShieldCheck size={13} className="text-teal" /> Conservative Allergen Handling
          </span>
          <span className="flex-row items-center gap-1">
            <ShieldCheck size={13} className="text-teal" /> Strict Cross-User Isolation
          </span>
        </div>
      </div>

      {/* 2. Main Chat Conversation Body */}
      <div className="card flex-col" style={{ 
        flex: 1, 
        padding: 0, 
        overflow: 'hidden', 
        display: 'flex', 
        flexDirection: 'column',
        background: 'var(--surface-card)' 
      }}>
        {/* Messages Scroll Area */}
        <div style={{ 
          flex: 1, 
          overflowY: 'auto', 
          padding: '20px 24px', 
          display: 'flex', 
          flexDirection: 'column', 
          gap: 16 
        }}>
          {!isAuthenticated && (
            <div className="feedback-box feedback-warning" style={{ margin: '0 0 12px 0' }}>
              <AlertTriangle size={16} />
              <div className="flex-row items-center justify-between" style={{ flex: 1 }}>
                <span>You are currently not signed in. The AI Coach requires authentication to access your personal data.</span>
                <button 
                  className="btn btn-primary btn-sm" 
                  onClick={() => toggleModal('auth', true)}
                  style={{ marginLeft: 12, padding: '4px 10px', fontSize: '0.75rem' }}
                >
                  Sign In
                </button>
              </div>
            </div>
          )}

          {messages.map((m) => (
            <div 
              key={m.id} 
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: m.sender === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: '100%',
              }}
            >
              <div style={{
                display: 'flex',
                gap: 10,
                flexDirection: m.sender === 'user' ? 'row-reverse' : 'row',
                maxWidth: '82%',
              }}>
                {/* Avatar Icon */}
                <div style={{
                  width: 32,
                  height: 32,
                  borderRadius: '50%',
                  background: m.sender === 'user' ? 'var(--primary-orange)' : 'var(--primary-purple)',
                  color: '#FFF',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.8rem',
                  fontWeight: 700,
                  flexShrink: 0,
                }}>
                  {m.sender === 'user' ? userProfile.avatar || 'U' : <Bot size={16} />}
                </div>

                {/* Message Bubble */}
                <div style={{
                  background: m.sender === 'user' ? 'var(--primary-orange)' : 'var(--surface-subtle)',
                  color: m.sender === 'user' ? '#FFF' : 'var(--text-primary)',
                  padding: '12px 16px',
                  borderRadius: 'var(--radius-lg)',
                  borderTopRightRadius: m.sender === 'user' ? 4 : 'var(--radius-lg)',
                  borderTopLeftRadius: m.sender === 'user' ? 'var(--radius-lg)' : 4,
                  fontSize: '0.9rem',
                  lineHeight: 1.5,
                  border: m.sender === 'user' ? 'none' : '1px solid var(--border-subtle)',
                  boxShadow: 'var(--shadow-sm)',
                }}>
                  <div style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>

                  {/* Safety & Advisory Warnings */}
                  {m.warnings && m.warnings.length > 0 && (
                    <div style={{ 
                      marginTop: 10, 
                      padding: '8px 10px', 
                      background: 'rgba(239, 68, 68, 0.08)', 
                      borderRadius: 'var(--radius-sm)', 
                      borderLeft: '3px solid #EF4444',
                      fontSize: '0.785rem',
                      color: '#B91C1C',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 4
                    }}>
                      {m.warnings.map((w, wIdx) => (
                        <div key={wIdx} className="flex-row items-center gap-1">
                          <AlertTriangle size={13} style={{ flexShrink: 0 }} />
                          <span>{w}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Provenance Citations */}
                  {m.entities && m.entities.length > 0 && (
                    <div style={{ 
                      marginTop: 8, 
                      paddingTop: 8, 
                      borderTop: '1px solid rgba(0,0,0,0.06)', 
                      fontSize: '0.725rem',
                      color: 'var(--text-muted)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      flexWrap: 'wrap'
                    }}>
                      <span className="font-semibold">Grounded in:</span>
                      {m.entities.map((ent, eIdx) => (
                        <span key={eIdx} className="badge-pill" style={{ 
                          fontSize: '0.685rem', 
                          background: 'rgba(99, 102, 241, 0.08)',
                          color: 'var(--primary-purple)'
                        }}>
                          {ent}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Timestamp */}
              <span style={{ 
                fontSize: '0.7rem', 
                color: 'var(--text-muted)', 
                marginTop: 4, 
                marginLeft: m.sender === 'user' ? 0 : 42,
                marginRight: m.sender === 'user' ? 42 : 0,
              }}>
                {m.timestamp}
              </span>
            </div>
          ))}

          {/* Loading Indicator */}
          {loading && (
            <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <div style={{
                width: 32,
                height: 32,
                borderRadius: '50%',
                background: 'var(--primary-purple)',
                color: '#FFF',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <Bot size={16} />
              </div>
              <div style={{
                background: 'var(--surface-subtle)',
                padding: '12px 18px',
                borderRadius: 'var(--radius-lg)',
                borderTopLeftRadius: 4,
                border: '1px solid var(--border-subtle)',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                fontSize: '0.85rem',
                color: 'var(--text-secondary)',
              }}>
                <RefreshCw size={14} className="spin" />
                <span>Assembling grounded context & consulting AI Coach...</span>
              </div>
            </div>
          )}

          {/* Error Banner with Retry */}
          {error && (
            <div className="feedback-box feedback-error" style={{ margin: '8px 0' }}>
              <AlertTriangle size={16} />
              <div className="flex-row items-center justify-between" style={{ flex: 1 }}>
                <span>{error}</span>
                <button 
                  className="btn btn-secondary btn-sm" 
                  onClick={handleRetry}
                  style={{ marginLeft: 12, padding: '4px 10px', fontSize: '0.75rem' }}
                >
                  <RefreshCw size={12} />
                  <span>Retry</span>
                </button>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Quick Question Chips */}
        <div style={{ 
          padding: '10px 24px', 
          borderTop: '1px solid var(--border-subtle)', 
          background: 'var(--surface-card)',
          display: 'flex',
          gap: 8,
          overflowX: 'auto',
          whiteSpace: 'nowrap'
        }}>
          {quickPrompts.map((q, idx) => (
            <button
              key={idx}
              className="btn btn-secondary btn-sm"
              onClick={() => handleSend(q.prompt)}
              disabled={loading}
              style={{ fontSize: '0.75rem', padding: '5px 10px', borderRadius: 'var(--radius-full)' }}
            >
              <Sparkles size={12} className="text-purple" />
              <span>{q.label}</span>
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div style={{ 
          padding: '14px 24px', 
          borderTop: '1px solid var(--border-subtle)', 
          background: 'var(--surface-subtle)',
          display: 'flex',
          gap: 10,
          alignItems: 'center'
        }}>
          <input
            ref={inputRef}
            type="text"
            className="input-field"
            placeholder={isAuthenticated ? "Ask a grounded question about your workouts, form, recovery, or diet..." : "Please sign in to ask questions..."}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            disabled={loading}
            style={{ flex: 1, backgroundColor: 'var(--surface-card)' }}
          />
          <button
            className="btn btn-primary"
            onClick={() => handleSend()}
            disabled={loading || !inputMessage.trim()}
            style={{ padding: '10px 18px', display: 'flex', alignItems: 'center', gap: 6 }}
          >
            <span>Send</span>
            <Send size={15} />
          </button>
        </div>
      </div>
    </div>
  );
}
