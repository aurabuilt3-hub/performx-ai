import React, { useState } from 'react';
import { 
  Search, 
  Bell, 
  Camera, 
  CameraOff, 
  Sparkles, 
  HelpCircle, 
  Menu,
  ShieldCheck,
  CheckCircle2,
  Globe,
  LogIn,
  LogOut
} from 'lucide-react';
import { useApp } from '../../context/AppContext';

export default function Header() {
  const { 
    activeTab, 
    setActiveTab,
    userProfile, 
    cameraState, 
    stopCameraStream, 
    toggleModal,
    setMobileMenuOpen,
    isAuthenticated,
    logout
  } = useApp();

  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const pageHeaders = {
    'overview': {
      title: `Welcome back, ${userProfile.name.split(' ')[0]} 👋`,
      desc: "Here is your real-time biomechanical analysis and daily workout summary."
    },
    'ai-coach': {
      title: 'PERFORMX AI Biomechanics Coach',
      desc: 'Evidence-based coaching grounded strictly in your verified movement telemetry, recovery, and nutrition.'
    },
    'live-workout': {
      title: 'Live Exercise Biomechanics Studio',
      desc: 'Real-time joint kinematics, depth validation, and form telemetry.'
    },
    'kinematics': {
      title: 'Drosophila-Inspired 3D Kinematics',
      desc: 'Articulated multi-segment biomechanical model with 3D spatial trajectory vectors.'
    },
    'plans': {
      title: 'Personalized Workout Plans',
      desc: 'Scientifically sequenced training regimens for strength, hypertrophy, and longevity.'
    },
    'library': {
      title: 'Biomechanical Exercise Library',
      desc: 'Validated kinematic cues, optimal joint angle limits, and execution standards.'
    },
    'nutrition': {
      title: 'Nutrition & Energy Balance',
      desc: 'Macronutrient targets, hydration logging, and dietary restriction management.'
    },
    'progress': {
      title: 'Biomechanical Progress & Analytics',
      desc: 'Form accuracy trends, session volume history, and symmetry tracking.'
    },
    'profile': {
      title: 'Health Profile & Biometrics',
      desc: 'Physical biometrics, resting heart rate, and clinician movement restrictions.'
    },
    'medical-docs': {
      title: 'Medical Documents & Clinical Records',
      desc: 'Upload orthopedic imaging, diagnostic reports, and clinician movement clearances.'
    },
    'injury-training': {
      title: 'Injury-Aware Adaptive Training',
      desc: 'Anatomical pain mapping, discomfort tracking, and conservative exercise substitutions.'
    },
    'settings': {
      title: 'Settings & Privacy Controls',
      desc: 'Transparent on-device AI edge processing controls and display preferences.'
    }
  };

  const currentMeta = pageHeaders[activeTab] || { title: 'PERFORMX', desc: 'AI Fitness Platform' };

  // Stop camera handler
  const handleStopCamera = () => {
    stopCameraStream();
  };

  return (
    <header className="top-header">
      {/* Left: Mobile hamburger + Titles */}
      <div className="header-left">
        <button 
          className="btn-ghost btn-icon btn-sm mobile-hamburger-btn" 
          onClick={() => setMobileMenuOpen(true)}
          aria-label="Open navigation menu"
        >
          <Menu size={20} />
        </button>

        <div className="header-title-box">
          <h1 className="header-page-title">{currentMeta.title}</h1>
          <p className="header-page-desc">{currentMeta.desc}</p>
        </div>
      </div>

      {/* Center: Search */}
      <div className="header-search">
        <div className="input-wrapper">
          <Search className="input-icon" size={17} />
          <input
            type="text"
            className="input-field has-icon"
            placeholder="Search exercises, plans, or nutrition..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Right: Actions */}
      <div className="header-actions">
        {/* Back to Public Landing Page */}
        <button 
          className="btn btn-secondary btn-sm" 
          onClick={() => setActiveTab('landing')}
          title="Return to Public Landing Page"
        >
          <Globe size={15} className="text-orange" />
          <span>Landing</span>
        </button>

        {/* Onboarding Tour Trigger */}
        <button 
          className="btn btn-secondary btn-sm" 
          onClick={() => toggleModal('onboarding', true)}
          title="Open Onboarding Walkthrough"
        >
          <Sparkles size={16} className="text-orange" />
          <span>Quick Tour</span>
        </button>

        {/* Auth Action Button (Sign In / Logout) */}
        {isAuthenticated ? (
          <button
            className="btn btn-secondary btn-sm"
            onClick={logout}
            title={`Signed in as ${userProfile.name}. Click to log out.`}
          >
            <LogOut size={15} className="text-secondary" />
            <span>Sign Out</span>
          </button>
        ) : (
          <button
            className="btn btn-primary btn-sm"
            onClick={() => toggleModal('auth', true)}
            title="Sign in with your PERFORMX credentials"
          >
            <LogIn size={15} />
            <span>Sign In</span>
          </button>
        )}

        {/* Camera Quick Status Pill */}
        {cameraState.active ? (
          <div className="camera-status-pill active" title="Camera is actively streaming local frames">
            <span className="live-dot" />
            <span>Camera Active</span>
            <button 
              className="btn btn-danger btn-sm" 
              style={{ padding: '3px 8px', fontSize: '0.75rem', marginLeft: 4 }}
              onClick={handleStopCamera}
              title="Stop camera video feed immediately"
            >
              <CameraOff size={13} />
              <span>Stop</span>
            </button>
          </div>
        ) : (
          <div className="camera-status-pill" title="Camera stream is inactive">
            <Camera size={14} className="text-muted" />
            <span>Camera Idle</span>
          </div>
        )}

        {/* Notifications Dropdown */}
        <div style={{ position: 'relative' }}>
          <button 
            className="btn-secondary btn-icon" 
            onClick={() => setNotificationsOpen(!notificationsOpen)}
            title="Notifications"
            aria-label="View notifications"
          >
            <Bell size={18} />
          </button>

          {notificationsOpen && (
            <div 
              className="card" 
              style={{ 
                position: 'absolute', 
                right: 0, 
                top: '48px', 
                width: 320, 
                zIndex: 100, 
                padding: '16px',
                boxShadow: 'var(--shadow-xl)' 
              }}
            >
              <div className="flex-row justify-between" style={{ marginBottom: 12 }}>
                <span className="font-bold text-primary" style={{ fontSize: '0.9rem' }}>Notifications</span>
                <span className="badge badge-orange">2 New</span>
              </div>
              <div className="flex-col gap-3">
                <div className="flex-row gap-3" style={{ fontSize: '0.825rem', padding: '8px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                  <CheckCircle2 size={16} className="text-green" style={{ flexShrink: 0 }} />
                  <div>
                    <div className="font-semibold text-primary">Form Milestone Achieved</div>
                    <div className="text-secondary">Average squat depth exceeded 90° for 5 consecutive sessions!</div>
                  </div>
                </div>
                <div className="flex-row gap-3" style={{ fontSize: '0.825rem', padding: '8px 0' }}>
                  <ShieldCheck size={16} className="text-teal" style={{ flexShrink: 0 }} />
                  <div>
                    <div className="font-semibold text-primary">Edge AI Guarantee</div>
                    <div className="text-secondary">All motion analysis processed strictly on your hardware.</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
