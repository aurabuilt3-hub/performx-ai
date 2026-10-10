import React from 'react';
import { 
  User, 
  Target, 
  Dumbbell, 
  Apple, 
  Activity, 
  Heart, 
  ShieldCheck, 
  Edit3, 
  CheckCircle2, 
  Award,
  Sparkles
} from 'lucide-react';
import { useApp } from '../context/AppContext';

export default function ProfilePage() {
  const { userProfile, toggleModal, medicalDocs = [], setActiveTab } = useApp();

  return (
    <div className="flex-col gap-6">
      {/* Athlete Header Card */}
      <section className="card">
        <div className="flex-row justify-between items-center" style={{ flexWrap: 'wrap', gap: 20 }}>
          <div className="flex-row items-center gap-4">
            <div 
              style={{
                width: 72,
                height: 72,
                borderRadius: '50%',
                background: 'linear-gradient(135deg, var(--primary-orange) 0%, #FA8C61 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#FFFFFF',
                fontSize: '1.6rem',
                fontWeight: 800,
                boxShadow: 'var(--shadow-md)',
              }}
            >
              {userProfile.avatar}
            </div>

            <div className="flex-col gap-1">
              <div className="flex-row items-center gap-2">
                <h2 style={{ fontSize: '1.45rem' }}>{userProfile.name}</h2>
                <span className="badge badge-orange">{userProfile.experienceLevel} Tier</span>
              </div>
              <p style={{ fontSize: '0.875rem' }}>{userProfile.email}</p>
              <div className="flex-row gap-2" style={{ marginTop: 2 }}>
                <span className="badge-pill" style={{ background: 'var(--primary-orange-soft)', color: 'var(--primary-orange)' }}>
                  <Sparkles size={13} />
                  <span>Goal: {userProfile.goal}</span>
                </span>
              </div>
            </div>
          </div>

          <button className="btn btn-secondary" onClick={() => toggleModal('editProfile', true)}>
            <Edit3 size={16} />
            <span>Edit Profile & Biometrics</span>
          </button>
        </div>
      </section>

      {/* Biometrics & Physiological Parameters Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 20 }}>
        <div className="card-flat flex-col gap-1" style={{ background: 'var(--surface-card)' }}>
          <span className="text-secondary" style={{ fontSize: '0.8rem' }}>Body Height</span>
          <strong className="text-primary" style={{ fontSize: '1.4rem' }}>{userProfile.heightCm} cm</strong>
          <small className="text-muted">Standard stature baseline</small>
        </div>

        <div className="card-flat flex-col gap-1" style={{ background: 'var(--surface-card)' }}>
          <span className="text-secondary" style={{ fontSize: '0.8rem' }}>Body Weight</span>
          <strong className="text-primary" style={{ fontSize: '1.4rem' }}>{userProfile.weightKg} kg</strong>
          <small className="text-muted">Calibrated load metric</small>
        </div>

        <div className="card-flat flex-col gap-1" style={{ background: 'var(--surface-card)' }}>
          <span className="text-secondary" style={{ fontSize: '0.8rem' }}>Estimated Body Fat</span>
          <strong className="text-primary" style={{ fontSize: '1.4rem' }}>{userProfile.bodyFatPercent}%</strong>
          <small className="text-muted">Athletic lean composition</small>
        </div>

        <div className="card-flat flex-col gap-1" style={{ background: 'var(--surface-card)' }}>
          <span className="text-secondary" style={{ fontSize: '0.8rem' }}>Resting Heart Rate</span>
          <strong className="text-teal" style={{ fontSize: '1.4rem' }}>{userProfile.restingHr} bpm</strong>
          <small className="text-muted">Cardiorespiratory baseline</small>
        </div>
      </div>

      {/* Preferences & Equipment Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        {/* Equipment Access Card */}
        <section className="card flex-col gap-4">
          <div className="card-header" style={{ marginBottom: 2 }}>
            <div>
              <h3 className="card-title">
                <Dumbbell size={20} className="text-orange" />
                <span>Available Training Equipment</span>
              </h3>
              <p className="card-subtitle">Active equipment profile used to filter workout plans</p>
            </div>
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {userProfile.equipment.map((eq, i) => (
              <span key={i} className="badge badge-orange" style={{ padding: '6px 12px', fontSize: '0.85rem' }}>
                <CheckCircle2 size={14} /> {eq}
              </span>
            ))}
          </div>
        </section>

        {/* Nutrition & Allergy Preferences */}
        <section className="card flex-col gap-4">
          <div className="card-header" style={{ marginBottom: 2 }}>
            <div>
              <h3 className="card-title">
                <Apple size={20} className="text-teal" />
                <span>Nutritional Preferences & Allergies</span>
              </h3>
              <p className="card-subtitle">User-declared dietary parameters</p>
            </div>
          </div>

          <div className="flex-col gap-3">
            <div>
              <span className="font-semibold text-secondary" style={{ fontSize: '0.825rem' }}>Dietary Principles:</span>
              <div className="flex-row gap-2" style={{ marginTop: 6, flexWrap: 'wrap' }}>
                {userProfile.dietaryPreferences.map((pref, i) => (
                  <span key={i} className="badge badge-teal">{pref}</span>
                ))}
              </div>
            </div>

            <div>
              <span className="font-semibold text-secondary" style={{ fontSize: '0.825rem' }}>Reported Known Allergies:</span>
              <div className="flex-row gap-2" style={{ marginTop: 6, flexWrap: 'wrap' }}>
                {userProfile.knownAllergies.map((all, i) => (
                  <span key={i} className="badge badge-red">{all}</span>
                ))}
              </div>
            </div>

            {userProfile.unconfirmedAllergies && userProfile.unconfirmedAllergies.length > 0 && (
              <div>
                <span className="font-semibold text-secondary" style={{ fontSize: '0.825rem' }}>Unconfirmed / Suspected Allergies:</span>
                <div className="flex-row gap-2" style={{ marginTop: 6, flexWrap: 'wrap' }}>
                  {userProfile.unconfirmedAllergies.map((all, i) => (
                    <span key={i} className="badge badge-neutral" style={{ border: '1px dashed #CBD5E1' }}>{all}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>
      </div>

      {/* Clinician Movement Restrictions & Clinical Clearance Card */}
      <section className="card flex-col gap-4">
        <div className="card-header">
          <div>
            <h3 className="card-title">
              <ShieldCheck size={20} className="text-teal" />
              <span>Clinician Clearance & Movement Restrictions</span>
            </h3>
            <p className="card-subtitle">Active medical constraints prioritized across all workout generators</p>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={() => setActiveTab('medical-docs')}>
            <span>Manage Records ({medicalDocs.length})</span>
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
          <div className="card-flat flex-col gap-2" style={{ background: 'var(--surface-subtle)', borderLeft: '4px solid var(--primary-orange)', padding: 14 }}>
            <div className="flex-row justify-between items-center">
              <span className="badge badge-orange" style={{ fontSize: '0.75rem' }}>Left Knee Restriction</span>
              <span className="text-muted" style={{ fontSize: '0.75rem' }}>Sep 18, 2026</span>
            </div>
            <p className="font-semibold text-primary" style={{ fontSize: '0.875rem', margin: 0 }}>
              Cap loaded knee flexion at ≤95°; avoid rapid ballistic descent.
            </p>
            <span className="text-teal" style={{ fontSize: '0.8rem', fontWeight: 600 }}>
              Prescribed Substitute: Box Squat to 95° Bench or Leg Press
            </span>
          </div>

          <div className="card-flat flex-col gap-2" style={{ background: 'var(--surface-subtle)', borderLeft: '4px solid var(--mint-teal)', padding: 14 }}>
            <div className="flex-row justify-between items-center">
              <span className="badge badge-teal" style={{ fontSize: '0.75rem' }}>Orthopedic Clearance Status</span>
              <span className="badge-pill" style={{ background: 'var(--success-soft)', color: '#15803D', fontSize: '0.72rem' }}>Conditional</span>
            </div>
            <p className="font-semibold text-primary" style={{ fontSize: '0.875rem', margin: 0 }}>
              Cleared for Progressive Overload on Upper Body & Controlled Posterior Chain
            </p>
            <span className="text-muted" style={{ fontSize: '0.8rem' }}>
              Next follow-up review: In 2 weeks (Oct 24, 2026)
            </span>
          </div>
        </div>
      </section>

      {/* On-Device Edge Biometrics Privacy Statement */}
      <div className="feedback-box feedback-neutral" style={{ marginTop: 0 }}>
        <ShieldCheck size={20} className="text-teal" style={{ flexShrink: 0 }} />
        <span style={{ fontSize: '0.85rem' }}>
          <strong>Biometric Privacy Guarantee:</strong> Your height, body mass, and motion keypoints are stored solely in your local browser storage. PERFORMX never transmits personal biometric telemetry to external servers.
        </span>
      </div>
    </div>
  );
}
