import React, { useState } from 'react';
import Modal from '../common/Modal';
import { 
  Target, 
  Dumbbell, 
  ShieldCheck, 
  Check, 
  Flame, 
  Zap, 
  Heart, 
  Compass, 
  ArrowRight, 
  ArrowLeft,
  Sparkles 
} from 'lucide-react';
import { useApp } from '../../context/AppContext';

export default function OnboardingModal({ isOpen, onClose }) {
  const { userProfile, setUserProfile, setActiveTab, updateProfile } = useApp();
  const [step, setStep] = useState(1);

  // Selected State
  const [selectedGoal, setSelectedGoal] = useState(userProfile.goal || 'Strength & Biomechanics');
  const [selectedExperience, setSelectedExperience] = useState(userProfile.experienceLevel || 'Intermediate');
  const [selectedEquipment, setSelectedEquipment] = useState(userProfile.equipment || ['Barbell', 'Dumbbells']);

  const goals = [
    {
      id: 'Fat Loss & Conditioning',
      title: 'Fat Loss & Conditioning',
      desc: 'Overall fat reduction, metabolic output, and cardiovascular health.',
      icon: Flame,
      color: 'amber',
    },
    {
      id: 'Muscle Building',
      title: 'Muscle Building (Hypertrophy)',
      desc: 'Targeted mechanical tension and volume optimization.',
      icon: Zap,
      color: 'orange',
    },
    {
      id: 'Strength & Biomechanics',
      title: 'Strength & Biomechanics',
      desc: 'Kinematic efficiency, neuromuscular drive, and power output.',
      icon: Target,
      color: 'teal',
    },
    {
      id: 'Endurance & Stamina',
      title: 'Endurance & Stamina',
      desc: 'Aerobic threshold improvement and movement economy.',
      icon: Heart,
      color: 'cyan',
    },
    {
      id: 'Mobility & Joint Longevity',
      title: 'Mobility & Joint Longevity',
      desc: 'Full range of motion, articular health, and symmetry.',
      icon: Compass,
      color: 'green',
    },
  ];

  const equipmentOptions = [
    'Barbell', 'Dumbbells', 'Squat Rack', 'Pull-up Bar', 'Resistance Bands', 'Cable Machine', 'Bodyweight Only'
  ];

  const handleFinish = async () => {
    try {
      await updateProfile({
        goal: selectedGoal,
        experienceLevel: selectedExperience,
        equipment: selectedEquipment,
      });
    } catch (err) {
      console.error('Failed to sync profile during onboarding:', err);
    }
    onClose();
    setActiveTab('overview');
  };

  const toggleEquipment = (eq) => {
    if (selectedEquipment.includes(eq)) {
      setSelectedEquipment(selectedEquipment.filter(item => item !== eq));
    } else {
      setSelectedEquipment([...selectedEquipment, eq]);
    }
  };

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose} 
      title={step === 1 ? "Welcome to PERFORMX" : `Step ${step} of 4: Setup Your Profile`}
      subtitle={
        step === 1 ? "AI-powered biomechanical movement analysis inspired by high-precision kinematic science." :
        step === 2 ? "Select your primary training objective to calibrate kinematic feedback." :
        step === 3 ? "Configure your current experience tier and training environment." :
        "Review on-device edge AI privacy and camera validation."
      }
      wide={true}
    >
      {/* Step Indicators */}
      <div className="flex-row items-center justify-between" style={{ marginBottom: 24 }}>
        {[1, 2, 3, 4].map(s => (
          <div key={s} className="flex-row items-center gap-2" style={{ flex: 1 }}>
            <div 
              style={{
                width: 32,
                height: 32,
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 700,
                fontSize: '0.85rem',
                backgroundColor: step === s ? 'var(--primary-orange)' : step > s ? 'var(--success-green)' : '#EDF2FA',
                color: step >= s ? '#FFFFFF' : 'var(--text-secondary)',
                transition: 'all 200ms ease',
              }}
            >
              {step > s ? <Check size={16} /> : s}
            </div>
            {s < 4 && (
              <div 
                style={{
                  flex: 1,
                  height: 3,
                  backgroundColor: step > s ? 'var(--success-green)' : '#EDF2FA',
                  margin: '0 8px',
                  borderRadius: 2,
                }} 
              />
            )}
          </div>
        ))}
      </div>

      {/* Step 1: Welcome & Kinematic Value Prop */}
      {step === 1 && (
        <div className="flex-col gap-4 text-center items-center" style={{ padding: '16px 0' }}>
          <div 
            style={{
              width: 80,
              height: 80,
              borderRadius: 'var(--radius-xl)',
              background: 'linear-gradient(135deg, var(--primary-orange) 0%, #FA8C61 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#FFFFFF',
              boxShadow: 'var(--shadow-glow)',
              marginBottom: 8,
            }}
          >
            <Sparkles size={40} />
          </div>

          <h3 style={{ fontSize: '1.4rem' }}>Movement Intelligence, Perfected</h3>
          <p style={{ maxWidth: 520, lineHeight: 1.6 }}>
            PERFORMX applies high-speed multi-segment kinematic tracking—inspired by Drosophila (fruit-fly) biomechanics research—to analyze your exercise depth, joint angles, and symmetry in real time.
          </p>

          <div 
            className="card-flat" 
            style={{ 
              width: '100%', 
              background: 'var(--surface-subtle)', 
              textAlign: 'left',
              marginTop: 12,
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: 16
            }}
          >
            <div>
              <div className="badge badge-orange" style={{ marginBottom: 6 }}>17 Keypoints</div>
              <div className="font-semibold text-primary" style={{ fontSize: '0.9rem' }}>Articulated 3D Mesh</div>
              <small>Real-time 60 FPS joint angle reconstruction.</small>
            </div>
            <div>
              <div className="badge badge-teal" style={{ marginBottom: 6 }}>Edge AI</div>
              <div className="font-semibold text-primary" style={{ fontSize: '0.9rem' }}>Local On-Device</div>
              <small>Zero video frames uploaded to external servers.</small>
            </div>
            <div>
              <div className="badge badge-cyan" style={{ marginBottom: 6 }}>Form Cues</div>
              <div className="font-semibold text-primary" style={{ fontSize: '0.9rem' }}>Real-time Audio & Visual</div>
              <small>Optimal depth validation and injury prevention.</small>
            </div>
          </div>
        </div>
      )}

      {/* Step 2: Goal Selection */}
      {step === 2 && (
        <div className="flex-col gap-3">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 14 }}>
            {goals.map(g => {
              const Icon = g.icon;
              const isSelected = selectedGoal === g.id;
              return (
                <div
                  key={g.id}
                  className={`card card-hoverable ${isSelected ? 'selected-goal' : ''}`}
                  onClick={() => setSelectedGoal(g.id)}
                  style={{
                    padding: 16,
                    cursor: 'pointer',
                    borderColor: isSelected ? 'var(--primary-orange)' : 'var(--border-subtle)',
                    background: isSelected ? 'var(--primary-orange-soft)' : 'var(--surface-card)',
                    borderWidth: isSelected ? 2 : 1,
                  }}
                >
                  <div className="flex-row items-center justify-between" style={{ marginBottom: 10 }}>
                    <div className={`metric-icon-box metric-icon-${g.color}`} style={{ width: 38, height: 38 }}>
                      <Icon size={18} />
                    </div>
                    {isSelected && (
                      <div className="badge badge-orange">
                        <Check size={12} /> Selected
                      </div>
                    )}
                  </div>
                  <h4 style={{ fontSize: '0.95rem', marginBottom: 4 }}>{g.title}</h4>
                  <small style={{ color: 'var(--text-secondary)' }}>{g.desc}</small>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Step 3: Experience & Equipment */}
      {step === 3 && (
        <div className="flex-col gap-5">
          <div>
            <label className="font-semibold text-primary" style={{ display: 'block', marginBottom: 8, fontSize: '0.925rem' }}>
              Your Training Experience
            </label>
            <div className="flex-row gap-3">
              {['Beginner (< 1 yr)', 'Intermediate (2-4 yrs)', 'Advanced (5+ yrs)'].map(exp => (
                <button
                  key={exp}
                  type="button"
                  className={`btn ${selectedExperience.startsWith(exp.split(' ')[0]) ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ flex: 1 }}
                  onClick={() => setSelectedExperience(exp.split(' ')[0])}
                >
                  {exp}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="font-semibold text-primary" style={{ display: 'block', marginBottom: 8, fontSize: '0.925rem' }}>
              Available Equipment
            </label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
              {equipmentOptions.map(eq => {
                const isSelected = selectedEquipment.includes(eq);
                return (
                  <button
                    key={eq}
                    type="button"
                    className={`btn btn-sm ${isSelected ? 'btn-teal' : 'btn-secondary'}`}
                    onClick={() => toggleEquipment(eq)}
                  >
                    {isSelected && <Check size={14} />}
                    <span>{eq}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Step 4: Camera & Privacy Preview */}
      {step === 4 && (
        <div className="flex-col gap-4">
          <div className="card-flat" style={{ background: 'var(--surface-subtle)', padding: 20 }}>
            <div className="flex-row gap-3 items-center" style={{ marginBottom: 12 }}>
              <ShieldCheck size={28} className="text-teal" />
              <div>
                <h4 style={{ color: 'var(--text-primary)' }}>100% In-Browser Edge Processing</h4>
                <p style={{ fontSize: '0.85rem' }}>Your video stream is analyzed locally using WebAssembly & MediaPipe.</p>
              </div>
            </div>

            <ul style={{ paddingLeft: 20, fontSize: '0.875rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: 8 }}>
              <li>No video or images are ever transmitted to or stored on remote servers.</li>
              <li>Camera access can be stopped with a single click at any time.</li>
              <li>You can also train in Simulated Demo Mode without camera access.</li>
            </ul>
          </div>

          <div className="feedback-box feedback-success">
            <Check size={18} style={{ flexShrink: 0 }} />
            <div>
              <strong>Setup Complete:</strong> Your personalized profile for {userProfile.name} is configured for {selectedGoal}.
            </div>
          </div>
        </div>
      )}

      {/* Wizard Footer Controls */}
      <div className="flex-row justify-between" style={{ marginTop: 28, paddingTop: 16, borderTop: '1px solid var(--border-subtle)' }}>
        {step > 1 ? (
          <button className="btn btn-secondary" onClick={() => setStep(step - 1)}>
            <ArrowLeft size={16} /> Back
          </button>
        ) : (
          <div />
        )}

        {step < 4 ? (
          <button className="btn btn-primary" onClick={() => setStep(step + 1)}>
            Continue <ArrowRight size={16} />
          </button>
        ) : (
          <button className="btn btn-primary btn-lg" onClick={handleFinish}>
            Launch PERFORMX Dashboard <Sparkles size={18} />
          </button>
        )}
      </div>
    </Modal>
  );
}
