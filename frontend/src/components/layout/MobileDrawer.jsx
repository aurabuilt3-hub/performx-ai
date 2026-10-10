import React, { useEffect } from 'react';
import { 
  LayoutDashboard, 
  Activity, 
  Box, 
  CalendarRange, 
  Dumbbell, 
  Apple, 
  TrendingUp, 
  HeartPulse,
  FileText,
  ShieldAlert,
  Settings, 
  X,
  Globe,
  Bot
} from 'lucide-react';
import { useApp } from '../../context/AppContext';

export default function MobileDrawer() {
  const { 
    activeTab, 
    setActiveTab, 
    mobileMenuOpen, 
    setMobileMenuOpen, 
    userProfile, 
    cameraState 
  } = useApp();

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && mobileMenuOpen) {
        setMobileMenuOpen(false);
      }
    };
    if (mobileMenuOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [mobileMenuOpen, setMobileMenuOpen]);

  if (!mobileMenuOpen) return null;

  const navGroups = [
    {
      title: 'Workspace',
      items: [
        { id: 'overview', label: 'Overview', icon: LayoutDashboard },
        { id: 'ai-coach', label: 'AI Coach', icon: Bot, badge: 'AI' },
        { id: 'live-workout', label: 'Live Workout', icon: Activity, badge: cameraState.active ? 'LIVE' : null },
        { id: 'kinematics', label: '3D Kinematics', icon: Box },
        { id: 'plans', label: 'Workout Plans', icon: CalendarRange },
        { id: 'library', label: 'Exercise Library', icon: Dumbbell },
      ]
    },
    {
      title: 'Health',
      items: [
        { id: 'profile', label: 'Health Profile', icon: HeartPulse },
        { id: 'medical-docs', label: 'Medical Documents', icon: FileText },
        { id: 'injury-training', label: 'Injury-Aware Training', icon: ShieldAlert },
        { id: 'nutrition', label: 'Nutrition & Energy', icon: Apple },
        { id: 'progress', label: 'Progress & Analytics', icon: TrendingUp },
      ]
    },
    {
      title: 'Preferences',
      items: [
        { id: 'settings', label: 'Settings & Privacy', icon: Settings },
        { id: 'landing', label: 'Public Landing', icon: Globe },
      ]
    }
  ];

  const handleSelect = (id) => {
    setActiveTab(id);
    setMobileMenuOpen(false);
  };

  return (
    <div 
      className="modal-overlay" 
      onClick={() => setMobileMenuOpen(false)}
      style={{ justifyContent: 'flex-start', padding: 0 }}
      role="dialog"
      aria-modal="true"
      aria-label="Mobile Navigation Menu"
    >
      <div 
        style={{
          width: 300,
          height: '100%',
          backgroundColor: 'var(--surface-card)',
          boxShadow: 'var(--shadow-xl)',
          display: 'flex',
          flexDirection: 'column',
          padding: '24px 18px',
          animation: 'fadeIn 200ms ease',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex-row justify-between items-center" style={{ marginBottom: 20, borderBottom: '1px solid var(--border-subtle)', paddingBottom: 14 }}>
          <div className="brand-logo">
            <div className="brand-icon-box" style={{ width: 34, height: 34 }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="12 2 2 7 12 12 22 7 12 2" />
                <polyline points="2 17 12 22 22 17" />
                <polyline points="2 12 12 17 22 12" />
              </svg>
            </div>
            <span style={{ fontWeight: 800, fontSize: '1.15rem' }}>PERFORMX</span>
          </div>

          <button 
            className="btn-ghost btn-icon btn-sm" 
            onClick={() => setMobileMenuOpen(false)}
            aria-label="Close menu"
          >
            <X size={20} />
          </button>
        </div>

        <nav className="flex-col gap-3" style={{ flex: 1, overflowY: 'auto' }}>
          {navGroups.map((group, gIdx) => (
            <div key={gIdx} className="sidebar-group">
              <span className="sidebar-group-label">{group.title}</span>
              {group.items.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <div
                    key={item.id}
                    className={`nav-item ${isActive ? 'active' : ''}`}
                    onClick={() => handleSelect(item.id)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => e.key === 'Enter' && handleSelect(item.id)}
                  >
                    <Icon size={19} className="nav-icon" />
                    <span>{item.label}</span>
                    {item.badge && <span className="nav-badge">{item.badge}</span>}
                  </div>
                );
              })}
            </div>
          ))}
        </nav>

        <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 16 }}>
          <div className="sidebar-user-card" onClick={() => handleSelect('profile')}>
            <div className="user-avatar">{userProfile.avatar}</div>
            <div className="flex-col">
              <strong style={{ fontSize: '0.9rem' }}>{userProfile.name}</strong>
              <small style={{ color: 'var(--text-muted)' }}>{userProfile.experienceLevel}</small>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
