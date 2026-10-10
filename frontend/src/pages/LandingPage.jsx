import React, { useState } from 'react';
import { 
  Activity, 
  Box, 
  CalendarRange, 
  ShieldAlert, 
  Sparkles, 
  Apple, 
  TrendingUp, 
  FileText, 
  ArrowRight, 
  ShieldCheck, 
  Cpu, 
  Eye, 
  CheckCircle2, 
  Menu, 
  X,
  Lock,
  Layers,
  Zap
} from 'lucide-react';
import { useApp } from '../context/AppContext';

export default function LandingPage() {
  const { setActiveTab, toggleModal } = useApp();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleGetStarted = (destination = 'overview') => {
    setActiveTab(destination);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleLogin = () => {
    toggleModal('auth', true);
  };

  const scrollToSection = (id) => {
    setMobileMenuOpen(false);
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const features = [
    {
      id: 'live-workout',
      title: 'Live Movement Analysis',
      desc: 'On-device camera tracking computes real-time knee, hip, and torso angles with repetition phase feedback.',
      icon: Activity,
      badge: 'MediaPipe AI'
    },
    {
      id: 'kinematics',
      title: '3D Kinematics Studio',
      desc: 'Articulated multi-segment 3D movement model inspired by fruit-fly biomechanics with coordinate trajectories.',
      icon: Box,
      badge: 'Three.js 3D'
    },
    {
      id: 'plans',
      title: 'Personalized Workout Plans',
      desc: 'Evidence-based training regimens adapted dynamically for strength, hypertrophy, and functional longevity.',
      icon: CalendarRange,
      badge: 'Dynamic Plans'
    },
    {
      id: 'injury-training',
      title: 'Injury-Aware Training',
      desc: 'Smart ROM guardrails and anatomical pain mapping that enforce strict clinician-defined movement restrictions.',
      icon: ShieldAlert,
      badge: 'Clinician ROM'
    },
    {
      id: 'overview',
      title: 'Adaptive Coaching',
      desc: 'Real-time load adjustments, recovery readiness scoring, and automated exercise substitutions.',
      icon: Sparkles,
      badge: 'Smart Engine'
    },
    {
      id: 'nutrition',
      title: 'Nutrition & Energy Balance',
      desc: 'Precision macronutrient targets, quick hydration tracking, and dietary restriction management.',
      icon: Apple,
      badge: 'Macro Intel'
    },
    {
      id: 'progress',
      title: 'Progress Analytics',
      desc: 'Historical form accuracy scores, session completion volume, and bilateral symmetry metrics over time.',
      icon: TrendingUp,
      badge: 'Telemetry'
    },
    {
      id: 'medical-docs',
      title: 'Health Profile & Medical Docs',
      desc: 'In-memory staging of clinical evaluations, orthopedic MRI notes, and physician clearance guidelines.',
      icon: FileText,
      badge: 'Secure Storage'
    }
  ];

  return (
    <div className="landing-wrapper">
      {/* Top Navigation */}
      <header className="landing-header">
        <div className="landing-header-inner">
          <div className="landing-brand">
            <div className="landing-brand-logo">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="12 2 2 7 12 12 22 7 12 2" />
                <polyline points="2 17 12 22 22 17" />
                <polyline points="2 12 12 17 22 12" />
              </svg>
            </div>
            <div>
              <span className="landing-brand-name">PERFORMX</span>
              <span className="landing-brand-tag" style={{ display: 'block', fontSize: '0.62rem' }}>BIOMECHANICS</span>
            </div>
          </div>

          {/* Desktop Nav */}
          <nav className="landing-nav-links" aria-label="Landing Navigation">
            <button className="landing-nav-link btn-ghost" onClick={() => scrollToSection('how-it-works')}>
              How It Works
            </button>
            <button className="landing-nav-link btn-ghost" onClick={() => scrollToSection('features')}>
              Features
            </button>
            <button className="landing-nav-link btn-ghost" onClick={() => scrollToSection('science')}>
              Science
            </button>
            <button className="landing-nav-link btn-ghost" onClick={() => scrollToSection('privacy')}>
              Privacy
            </button>
          </nav>

          {/* Header Actions */}
          <div className="landing-header-actions">
            <button 
              className="btn btn-secondary btn-sm" 
              onClick={handleLogin}
            >
              Log In
            </button>
            <button 
              className="btn btn-primary btn-sm" 
              onClick={() => handleGetStarted('overview')}
            >
              Get Started
            </button>

            {/* Mobile Menu Button */}
            <button 
              className="btn-ghost btn-icon btn-sm landing-mobile-menu-btn" 
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="Toggle Navigation Menu"
            >
              {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
            </button>
          </div>
        </div>

        {/* Mobile Dropdown Menu */}
        {mobileMenuOpen && (
          <div 
            style={{ 
              position: 'absolute', 
              top: '76px', 
              left: 0, 
              right: 0, 
              backgroundColor: 'var(--surface-card)', 
              borderBottom: '1px solid var(--border-subtle)',
              padding: '20px 24px',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
              zIndex: 99
            }}
          >
            <button 
              className="landing-nav-link" 
              style={{ textAlign: 'left', background: 'none', border: 'none', padding: '8px 0', fontSize: '1rem' }}
              onClick={() => scrollToSection('how-it-works')}
            >
              How It Works
            </button>
            <button 
              className="landing-nav-link" 
              style={{ textAlign: 'left', background: 'none', border: 'none', padding: '8px 0', fontSize: '1rem' }}
              onClick={() => scrollToSection('features')}
            >
              Features
            </button>
            <button 
              className="landing-nav-link" 
              style={{ textAlign: 'left', background: 'none', border: 'none', padding: '8px 0', fontSize: '1rem' }}
              onClick={() => scrollToSection('science')}
            >
              Science
            </button>
            <button 
              className="landing-nav-link" 
              style={{ textAlign: 'left', background: 'none', border: 'none', padding: '8px 0', fontSize: '1rem' }}
              onClick={() => scrollToSection('privacy')}
            >
              Privacy
            </button>
            <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
              <button className="btn btn-secondary flex-1" onClick={handleLogin}>Log In</button>
              <button className="btn btn-primary flex-1" onClick={() => handleGetStarted('overview')}>Get Started</button>
            </div>
          </div>
        )}
      </header>

      {/* Hero Section */}
      <section className="landing-hero">
        <div className="landing-hero-grid">
          <div>
            <div className="landing-eyebrow">
              <Zap size={14} className="text-orange" />
              <span>Next-Generation Movement Intelligence</span>
            </div>

            <h1 className="landing-hero-headline">
              Move smarter.<br />
              <span className="highlight-orange">Train stronger.</span>
              Understand your movement.
            </h1>

            <p className="landing-hero-subtext">
              PERFORMX combines local computer vision, Drosophila-inspired 3D biomechanics, 
              and adaptive training engines to evaluate your form in real time—delivering clinical precision 
              without compromising your privacy.
            </p>

            <div className="landing-hero-ctas">
              <button 
                className="btn btn-primary btn-lg"
                onClick={() => handleGetStarted('overview')}
              >
                <span>Start Your Journey</span>
                <ArrowRight size={18} />
              </button>

              <button 
                className="btn btn-secondary btn-lg"
                onClick={() => scrollToSection('science')}
              >
                <span>Explore the Science</span>
              </button>
            </div>
          </div>

          {/* Editorial Showcase Imagery Container */}
          <div className="landing-hero-showcase">
            <img 
              src="/images/hero-movement.png" 
              alt="PERFORMX Movement Biomechanics and Kinematics Training" 
              className="landing-hero-image"
            />

            <div className="landing-hero-overlay-card">
              <div className="landing-stat-item">
                <span className="landing-stat-num">17</span>
                <span className="landing-stat-label">Kinematic Keypoints</span>
              </div>
              <div style={{ width: 1, height: 36, backgroundColor: 'var(--border-subtle)' }} />
              <div className="landing-stat-item">
                <span className="landing-stat-num">60 FPS</span>
                <span className="landing-stat-label">On-Device Tracking</span>
              </div>
              <div style={{ width: 1, height: 36, backgroundColor: 'var(--border-subtle)' }} />
              <div className="landing-stat-item">
                <span className="landing-stat-num">100%</span>
                <span className="landing-stat-label">Local Edge Privacy</span>
              </div>
              <div style={{ width: 1, height: 36, backgroundColor: 'var(--border-subtle)' }} />
              <div className="landing-stat-item">
                <span className="landing-stat-num">0 ms</span>
                <span className="landing-stat-label">Cloud Video Latency</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="landing-section">
        <div className="landing-section-header">
          <span className="landing-section-eyebrow">Methodology</span>
          <h2 className="landing-section-title">How PERFORMX works</h2>
          <p className="landing-section-desc">
            A three-step feedback loop bridging physical exercise execution with mathematical biomechanics.
          </p>
        </div>

        <div className="landing-steps-grid">
          <div className="landing-step-card">
            <span className="landing-step-num">01</span>
            <h3 className="landing-step-title">Capture movement</h3>
            <p className="landing-step-text">
              Analyze supported movements using on-device pose tracking. Real-time joint coordinates are calculated directly in your browser using MediaPipe WebAssembly.
            </p>
          </div>

          <div className="landing-step-card">
            <span className="landing-step-num">02</span>
            <h3 className="landing-step-title">Understand biomechanics</h3>
            <p className="landing-step-text">
              Explore an articulated 3D movement visualization inspired by fruit-fly biomechanics. Track spatial kinematic arcs, depth angles, and bilateral symmetry in interactive Three.js space.
            </p>
          </div>

          <div className="landing-step-card">
            <span className="landing-step-num">03</span>
            <h3 className="landing-step-title">Train with insight</h3>
            <p className="landing-step-text">
              Execute personalized workouts and adaptive coaching that dynamically adjust loads and exercises within user-reported and clinician-defined restrictions.
            </p>
          </div>
        </div>
      </section>

      {/* Features Grid Section */}
      <section id="features" className="landing-section">
        <div className="landing-section-header">
          <span className="landing-section-eyebrow">Product Capabilities</span>
          <h2 className="landing-section-title">Designed for optimal movement health</h2>
          <p className="landing-section-desc">
            Explore our comprehensive suite of movement science tools. Click any capability to launch the active studio.
          </p>
        </div>

        <div className="landing-features-grid">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <div 
                key={feature.id} 
                className="landing-feature-card"
                onClick={() => handleGetStarted(feature.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && handleGetStarted(feature.id)}
              >
                <div className="flex-row justify-between items-center">
                  <div className="landing-feature-icon">
                    <Icon size={22} />
                  </div>
                  <span className="badge badge-orange" style={{ fontSize: '0.7rem' }}>
                    {feature.badge}
                  </span>
                </div>
                <h3 className="landing-feature-title">{feature.title}</h3>
                <p className="landing-feature-desc">{feature.desc}</p>
                <div className="landing-feature-action">
                  <span>Open Tool</span>
                  <ArrowRight size={14} />
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Science & Privacy Section */}
      <section id="science" className="landing-section">
        <div className="landing-science-container">
          <div>
            <span className="landing-section-eyebrow">Computational Biomechanics</span>
            <h2 className="landing-section-title" style={{ fontSize: '2.4rem' }}>
              The Science Behind PERFORMX
            </h2>
            <p className="landing-section-desc">
              We leverage computational kinematics principles to make complex human movement telemetry accessible and intuitive.
            </p>

            <div className="landing-science-list">
              <div className="landing-science-item">
                <div className="landing-science-icon-box">
                  <Cpu size={18} />
                </div>
                <div>
                  <h4 style={{ fontWeight: 700, fontSize: '0.98rem', marginBottom: 4 }}>
                    MediaPipe Pose Estimation
                  </h4>
                  <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.55 }}>
                    33 pose landmarks tracked in real-time at up to 60 FPS directly within the client browser, without external latency or server processing.
                  </p>
                </div>
              </div>

              <div className="landing-science-item">
                <div className="landing-science-icon-box">
                  <Layers size={18} />
                </div>
                <div>
                  <h4 style={{ fontWeight: 700, fontSize: '0.98rem', marginBottom: 4 }}>
                    Fruit-Fly Inspired Articulation
                  </h4>
                  <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.55 }}>
                    Inspired by Drosophila locomotion research, our Three.js kinematic skeleton visualizes multi-segment joint linkages and trajectory ribbons as an educational framework.
                  </p>
                </div>
              </div>

              <div className="landing-science-item">
                <div className="landing-science-icon-box">
                  <Sparkles size={18} />
                </div>
                <div>
                  <h4 style={{ fontWeight: 700, fontSize: '0.98rem', marginBottom: 4 }}>
                    Adaptive Restriction Engines
                  </h4>
                  <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.55 }}>
                    Rule-based algorithmic coaching respects clinician range-of-motion ceilings (e.g. knee flexion ≤95°) and automatically replaces contra-indicated exercises.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Privacy Guarantee Card */}
          <div id="privacy" className="landing-privacy-card">
            <span className="landing-privacy-badge">
              <ShieldCheck size={14} />
              <span>Zero-Recording Promise</span>
            </span>
            <h3 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)' }}>
              100% On-Device Privacy Architecture
            </h3>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              Your camera feed never leaves your device. Raw video frames are processed locally inside browser memory using WebAssembly and WebGL shaders, then immediately discarded.
            </p>
            <ul style={{ listStyle: 'none', padding: 0, margin: '8px 0', display: 'flex', flexDirection: 'column', gap: 10 }}>
              <li style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                <CheckCircle2 size={16} className="text-teal" />
                <span>Zero video frames recorded or uploaded</span>
              </li>
              <li style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                <CheckCircle2 size={16} className="text-teal" />
                <span>Zero cloud biometric data storage</span>
              </li>
              <li style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                <CheckCircle2 size={16} className="text-teal" />
                <span>Medical documents remain in memory only</span>
              </li>
            </ul>
            <div style={{ marginTop: 8, padding: '10px 14px', backgroundColor: 'var(--surface-card)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              <strong>Scientific Disclaimer:</strong> PERFORMX is an educational movement-analysis and training tool. Drosophila-inspired 3D models provide biomechanical visualizations and do not diagnose human medical conditions.
            </div>
          </div>
        </div>
      </section>

      {/* CTA Banner */}
      <section className="landing-cta-banner">
        <h2 className="landing-cta-title">
          Ready to experience intelligent movement analysis?
        </h2>
        <p className="landing-cta-subtext">
          Join thousands of athletes, clinicians, and fitness enthusiasts optimizing their form and preventing injuries with PERFORMX.
        </p>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', justifyContent: 'center', marginTop: 8 }}>
          <button 
            className="btn btn-primary btn-lg"
            onClick={() => handleGetStarted('overview')}
            style={{ fontSize: '1.05rem', padding: '16px 36px' }}
          >
            <span>Start Training Now</span>
            <ArrowRight size={18} />
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="landing-footer-inner">
          <div className="landing-brand">
            <div className="landing-brand-logo" style={{ width: 32, height: 32 }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="12 2 2 7 12 12 22 7 12 2" />
                <polyline points="2 17 12 22 22 17" />
                <polyline points="2 12 12 17 22 12" />
              </svg>
            </div>
            <div>
              <span className="landing-brand-name" style={{ fontSize: '1.1rem' }}>PERFORMX</span>
            </div>
          </div>

          <div className="landing-footer-links">
            <button className="landing-footer-link btn-ghost" onClick={() => scrollToSection('how-it-works')}>
              How It Works
            </button>
            <button className="landing-footer-link btn-ghost" onClick={() => scrollToSection('features')}>
              Features
            </button>
            <button className="landing-footer-link btn-ghost" onClick={() => scrollToSection('science')}>
              Science
            </button>
            <button className="landing-footer-link btn-ghost" onClick={() => scrollToSection('privacy')}>
              Privacy Promise
            </button>
            <button className="landing-footer-link btn-ghost" onClick={() => handleGetStarted('settings')}>
              Settings
            </button>
          </div>

          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            © {new Date().getFullYear()} PERFORMX Biomechanics. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
