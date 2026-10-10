import React from 'react';
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
  ChevronLeft, 
  ChevronRight,
  Flame,
  Globe,
  Bot
} from 'lucide-react';
import { useApp } from '../../context/AppContext';

export default function Sidebar() {
  const { 
    activeTab, 
    setActiveTab, 
    sidebarCollapsed, 
    setSidebarCollapsed, 
    userProfile, 
    cameraState
  } = useApp();

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

  return (
    <aside className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
      {/* Brand Header */}
      <div className="sidebar-header">
        <a href="#overview" className="brand-logo" onClick={(e) => { e.preventDefault(); setActiveTab('overview'); }}>
          <div className="brand-icon-box">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="12 2 2 7 12 12 22 7 12 2" />
              <polyline points="2 17 12 22 22 17" />
              <polyline points="2 12 12 17 22 12" />
            </svg>
          </div>
          {!sidebarCollapsed && (
            <div className="brand-text">
              <span className="brand-title">PERFORMX</span>
              <span className="brand-subtitle">AI BIOMECHANICS</span>
            </div>
          )}
        </a>

        <button 
          className="btn-ghost btn-icon btn-sm" 
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-label="Toggle sidebar collapse"
        >
          {sidebarCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      {/* Grouped Navigation Items */}
      <nav className="sidebar-nav" aria-label="Main Navigation">
        {navGroups.map((group, gIdx) => (
          <div key={gIdx} className="sidebar-group">
            {!sidebarCollapsed && (
              <span className="sidebar-group-label">{group.title}</span>
            )}
            {group.items.map((item) => {
              const IconComponent = item.icon;
              const isActive = activeTab === item.id;
              return (
                <div
                  key={item.id}
                  className={`nav-item ${isActive ? 'active' : ''}`}
                  onClick={() => setActiveTab(item.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === 'Enter' && setActiveTab(item.id)}
                  title={sidebarCollapsed ? item.label : undefined}
                >
                  <IconComponent className="nav-icon" size={19} />
                  {!sidebarCollapsed && <span>{item.label}</span>}
                  {!sidebarCollapsed && item.badge && (
                    <span className="nav-badge">{item.badge}</span>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Footer / User Profile Summary */}
      <div className="sidebar-footer">
        {!sidebarCollapsed && (
          <div className="flex-row items-center justify-between" style={{ padding: '0 4px' }}>
            <div className="badge-pill" style={{ background: '#FFF7ED', color: '#EA580C' }}>
              <Flame size={14} />
              <span>{userProfile.streakDays} Day Streak</span>
            </div>
            {cameraState.active && (
              <div className="badge-pill" style={{ background: 'var(--success-soft)', color: 'var(--success-green)' }}>
                <span className="live-dot" style={{ width: 6, height: 6 }} />
                <span>Camera On</span>
              </div>
            )}
          </div>
        )}

        <div 
          className="sidebar-user-card" 
          onClick={() => setActiveTab('profile')}
          title="Open Health Profile"
        >
          <div className="user-avatar">{userProfile.avatar}</div>
          {!sidebarCollapsed && (
            <div className="flex-col" style={{ overflow: 'hidden' }}>
              <span style={{ fontWeight: 700, fontSize: '0.9rem', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                {userProfile.name}
              </span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {userProfile.experienceLevel}
              </span>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
