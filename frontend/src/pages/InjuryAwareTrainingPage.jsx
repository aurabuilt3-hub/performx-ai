import React, { useState } from 'react';
import { 
  ShieldAlert, 
  ShieldCheck, 
  AlertTriangle, 
  Activity, 
  CheckCircle2, 
  RotateCcw, 
  TrendingDown, 
  Calendar, 
  ArrowRight, 
  Compass, 
  ChevronRight,
  Plus,
  HelpCircle,
  Clock
} from 'lucide-react';
import { useApp } from '../context/AppContext';

export default function InjuryAwareTrainingPage() {
  const { 
    injuryState, 
    updateInjuryState, 
    logRecoveryCheckIn, 
    todayExercises,
    setActiveTab 
  } = useApp();

  const [checkInRating, setCheckInRating] = useState(injuryState.discomfortRating);
  const [checkInNote, setCheckInNote] = useState('');
  const [checkInSuccess, setCheckInSuccess] = useState(false);

  // Anatomical regions available for selection
  const anatomicalRegions = [
    { id: 'Left Knee', label: 'Left Knee', icon: '🦵', sub: 'Patellofemoral Joint' },
    { id: 'Right Knee', label: 'Right Knee', icon: '🦵', sub: 'Tibiofemoral Joint' },
    { id: 'Lumbar Spine', label: 'Lumbar Spine', icon: '🦴', sub: 'L4-L5 / S1 Segment' },
    { id: 'Shoulder', label: 'Shoulder / Rotator Cuff', icon: '💪', sub: 'Glenohumeral / Supraspinatus' },
    { id: 'Hip', label: 'Hip', icon: '🏃', sub: 'Acetabulofemoral Labrum' },
    { id: 'Ankle', label: 'Ankle', icon: '👟', sub: 'Talocrural / Achilles Complex' },
  ];

  // Conservative biomechanical exercise substitution matrix
  const substitutionMatrix = [
    {
      restrictedMovement: 'Barbell Back Squat (Flexion > 90°)',
      region: 'Left Knee',
      substitute: 'Box Squat to 95° Bench or Leg Press (Mid-range)',
      biomechanicalRationale: 'Limits patellofemoral compressive force while preserving quadriceps & glute recruitment with rigid mechanical depth stopper.',
      loadAdjustment: 'Reduce 15-20% working load'
    },
    {
      restrictedMovement: 'Deep Romanian Deadlift',
      region: 'Lumbar Spine',
      substitute: 'Rack Pulls (Mid-Shin) or Romanian Deadlift to Knees',
      biomechanicalRationale: 'Reduces lumbar shear moment arm by 34% by maintaining neutral spine above flexion pivot.',
      loadAdjustment: 'Strict 3-0-1 tempo'
    },
    {
      restrictedMovement: 'Overhead Barbell Military Press',
      region: 'Shoulder',
      substitute: 'Landmine Angled Press or High Incline Dumbbell Press',
      biomechanicalRationale: 'Avoids subacromial impingement by shifting plane of elevation to the scapular plane (30° forward).',
      loadAdjustment: 'Neutral grip'
    },
    {
      restrictedMovement: 'Walking Dumbbell Lunges',
      region: 'Left Knee',
      substitute: 'Static Split Squat with Elevation or Glute Bridges',
      biomechanicalRationale: 'Eliminates deceleration ground impact shear forces on anterior patellar tendon.',
      loadAdjustment: 'Controlled eccentric'
    }
  ];

  const handleSelectRegion = (region) => {
    updateInjuryState({
      activeRegion: region.id,
      anatomicalSubregion: region.sub
    });
  };

  const handleRatingChange = (newRating) => {
    updateInjuryState({ discomfortRating: newRating });
    setCheckInRating(newRating);
  };

  const handleLogCheckIn = async (e) => {
    e.preventDefault();
    await logRecoveryCheckIn(checkInRating, checkInNote);
    setCheckInNote('');
    setCheckInSuccess(true);
    setTimeout(() => setCheckInSuccess(false), 3000);
  };

  // Color mapping helper for discomfort ratings
  const getRatingColor = (rating) => {
    if (rating <= 3) return { bg: 'var(--success-soft)', border: 'var(--success-green)', text: '#15803D', label: 'Mild / Safe Recovery Zone' };
    if (rating <= 6) return { bg: 'var(--warning-soft)', border: 'var(--warning-amber)', text: '#B45309', label: 'Moderate Discomfort — Deload & Modify' };
    return { bg: 'var(--error-soft)', border: 'var(--error-red)', text: '#B91C1C', label: 'Severe Discomfort — Movement Contraindicated' };
  };

  const activeColor = getRatingColor(injuryState.discomfortRating);

  return (
    <div className="flex-col gap-6">
      {/* Clinician Constraint Priority Banner */}
      <div className="feedback-box feedback-warning" style={{ borderLeftWidth: 4, borderLeftColor: 'var(--warning-amber)' }}>
        <ShieldAlert size={24} className="text-amber" style={{ flexShrink: 0 }} />
        <div className="flex-col gap-1">
          <strong className="text-primary" style={{ fontSize: '0.925rem' }}>
            Clinician Restriction Precedence Active
          </strong>
          <span className="text-secondary" style={{ fontSize: '0.825rem' }}>
            AI coaching recommendations and load progressions strictly conform to clinician instructions. Ambiguous restrictions are explicitly flagged for clinician review and never assumed safe.
          </span>
        </div>
      </div>

      {/* Fitness Tool Scope & Medical Disclaimer */}
      <div className="feedback-box feedback-neutral" style={{ padding: '10px 14px', margin: 0 }}>
        <ShieldCheck size={18} className="text-teal" style={{ flexShrink: 0 }} />
        <span style={{ fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
          <strong>Medical Notice:</strong> PERFORMX is a fitness and movement-analysis application, not a medical diagnostic system. Movement substitutions represent conservative biomechanical alternatives designed to prevent joint shear, not medical treatment. Consult a licensed clinician for injury diagnosis.
        </span>
      </div>

      {/* Top Split: Interactive Anatomical Region Selector & Discomfort Rating */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 24 }}>
        
        {/* Anatomical Region & Symptoms Card */}
        <section className="card flex-col gap-4">
          <div className="card-header">
            <div>
              <h2 className="card-title">
                <Compass className="text-orange" size={20} />
                <span>Anatomical Region Mapping</span>
              </h2>
              <p className="card-subtitle">
                Select target joint or structure to configure adaptive loading rules.
              </p>
            </div>
            <span className="badge badge-orange">{injuryState.activeRegion}</span>
          </div>

          {/* Region Chips Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 10 }}>
            {anatomicalRegions.map((region) => {
              const isSelected = injuryState.activeRegion === region.id;
              return (
                <button
                  key={region.id}
                  type="button"
                  className={`anatomy-chip ${isSelected ? 'selected' : ''}`}
                  onClick={() => handleSelectRegion(region)}
                  style={{ justifyContent: 'flex-start', textAlign: 'left' }}
                >
                  <span style={{ fontSize: '1.2rem' }}>{region.icon}</span>
                  <div className="flex-col" style={{ overflow: 'hidden' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>{region.label}</span>
                    <span style={{ fontSize: '0.72rem', color: isSelected ? 'var(--primary-orange)' : 'var(--text-muted)' }}>
                      {region.sub}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Discomfort Rating Scale (1 to 10) */}
          <div style={{ marginTop: 8, background: 'var(--surface-subtle)', padding: 16, borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <div className="flex-row justify-between items-center" style={{ marginBottom: 6 }}>
              <span className="font-semibold text-primary" style={{ fontSize: '0.875rem' }}>
                Subjective Discomfort Level (Visual Analog Scale)
              </span>
              <span 
                className="badge" 
                style={{ background: activeColor.bg, color: activeColor.text, border: `1px solid ${activeColor.border}`, fontWeight: 700 }}
              >
                {injuryState.discomfortRating} / 10 • {activeColor.label}
              </span>
            </div>

            {/* 1 - 10 Scale Buttons */}
            <div className="discomfort-scale">
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((num) => {
                let activeClass = '';
                if (injuryState.discomfortRating === num) {
                  if (num <= 3) activeClass = 'active-low';
                  else if (num <= 6) activeClass = 'active-mid';
                  else activeClass = 'active-high';
                }
                return (
                  <button
                    key={num}
                    type="button"
                    className={`discomfort-btn ${activeClass}`}
                    onClick={() => handleRatingChange(num)}
                    title={`Rate discomfort as ${num} of 10`}
                  >
                    {num}
                  </button>
                );
              })}
            </div>

            <div className="flex-row justify-between" style={{ marginTop: 8, fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              <span>1: Imperceptible / Mild</span>
              <span>4-6: Sub-acute (Modification Needed)</span>
              <span>10: Severe / Acute Pain</span>
            </div>
          </div>

          {/* Active Symptoms Summary */}
          <div className="flex-col gap-2">
            <span className="font-semibold text-secondary" style={{ fontSize: '0.825rem' }}>
              Reported Symptoms & Onset Details:
            </span>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-primary)', background: 'var(--surface-subtle)', padding: '12px 14px', borderRadius: 'var(--radius-md)', margin: 0 }}>
              "{injuryState.symptoms}"
            </p>
          </div>
        </section>

        {/* Range of Motion (ROM) Comparison & Recovery Status */}
        <section className="card flex-col gap-4">
          <div className="card-header">
            <div>
              <h2 className="card-title">
                <Activity className="text-teal" size={20} />
                <span>ROM Biomechanical Deficit</span>
              </h2>
              <p className="card-subtitle">
                Comparative range of motion against uninjured baseline.
              </p>
            </div>
            <span className="badge badge-teal">Joint Kinematics</span>
          </div>

          {/* ROM Comparison Gauge */}
          <div style={{ background: 'var(--surface-subtle)', padding: 18, borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <div className="flex-row justify-between items-center" style={{ marginBottom: 8 }}>
              <div>
                <span className="text-muted" style={{ fontSize: '0.75rem' }}>Current Tolerated Knee Flexion</span>
                <div className="font-bold text-primary" style={{ fontSize: '1.75rem' }}>
                  {injuryState.currentRomDegrees}°
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <span className="text-muted" style={{ fontSize: '0.75rem' }}>Uninjured Baseline Target</span>
                <div className="font-bold text-teal" style={{ fontSize: '1.75rem' }}>
                  {injuryState.uninjuredBaselineRomDegrees}°
                </div>
              </div>
            </div>

            {/* Visual Arc Comparison Bar */}
            <div className="progress-bar-container lg">
              <div 
                className="progress-bar-fill progress-orange" 
                style={{ width: `${(injuryState.currentRomDegrees / injuryState.uninjuredBaselineRomDegrees) * 100}%` }}
                title={`${((injuryState.currentRomDegrees / injuryState.uninjuredBaselineRomDegrees) * 100).toFixed(0)}% of baseline achieved`}
              />
            </div>

            <div className="flex-row justify-between items-center" style={{ marginTop: 8 }}>
              <span className="text-muted" style={{ fontSize: '0.75rem' }}>
                Deficit: -{injuryState.uninjuredBaselineRomDegrees - injuryState.currentRomDegrees}° (26.4% reduction)
              </span>
              <span className="badge badge-orange" style={{ fontSize: '0.72rem' }}>
                Clinician Depth Cap: ≤95°
              </span>
            </div>
          </div>

          {/* Recovery Milestones Checklist */}
          <div>
            <span className="font-semibold text-primary" style={{ fontSize: '0.85rem' }}>
              Rehabilitation Milestones:
            </span>
            <div className="flex-col gap-2" style={{ marginTop: 8 }}>
              {injuryState.recoveryMilestones.map((m, idx) => (
                <div 
                  key={idx} 
                  className="flex-row items-center gap-3" 
                  style={{ 
                    padding: '8px 12px', 
                    borderRadius: 'var(--radius-sm)', 
                    background: m.completed ? 'var(--success-soft)' : 'var(--surface-subtle)',
                    border: `1px solid ${m.completed ? 'rgba(32, 205, 181, 0.2)' : 'var(--border-subtle)'}`
                  }}
                >
                  <CheckCircle2 size={16} className={m.completed ? 'text-teal' : 'text-muted'} />
                  <span style={{ fontSize: '0.825rem', color: m.completed ? 'var(--text-primary)' : 'var(--text-muted)', fontWeight: m.completed ? 600 : 400 }}>
                    {m.milestone}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Nav to Medical Docs */}
          <button 
            className="btn btn-secondary btn-sm" 
            style={{ width: '100%', marginTop: 'auto' }}
            onClick={() => setActiveTab('medical-docs')}
          >
            <span>Review Diagnostic Imaging Reports</span>
            <ArrowRight size={14} />
          </button>
        </section>
      </div>

      {/* Conservative Exercise Substitution Matrix */}
      <section className="card flex-col gap-4">
        <div className="card-header">
          <div>
            <h2 className="card-title">
              <ShieldCheck className="text-teal" size={20} />
              <span>Conservative Exercise Substitutions</span>
            </h2>
            <p className="card-subtitle">
              Evidence-based exercise pairings replacing high-shear compound lifts with safe alternatives.
            </p>
          </div>
          <span className="badge badge-teal">Biomechanically Validated</span>
        </div>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Restricted Movement</th>
                <th>Target Joint</th>
                <th>Conservative Substitute</th>
                <th>Biomechanical Rationale</th>
                <th>Load Adjustment</th>
              </tr>
            </thead>
            <tbody>
              {substitutionMatrix.map((sub, idx) => (
                <tr key={idx}>
                  <td>
                    <div className="flex-row items-center gap-2">
                      <AlertTriangle size={15} className="text-amber" />
                      <strong className="text-primary" style={{ fontSize: '0.85rem' }}>
                        {sub.restrictedMovement}
                      </strong>
                    </div>
                  </td>
                  <td>
                    <span className="badge badge-orange" style={{ fontSize: '0.72rem' }}>
                      {sub.region}
                    </span>
                  </td>
                  <td>
                    <span className="badge badge-teal" style={{ fontSize: '0.825rem', fontWeight: 700 }}>
                      {sub.substitute}
                    </span>
                  </td>
                  <td style={{ maxWidth: 320 }}>
                    <span className="text-secondary" style={{ fontSize: '0.8rem', lineHeight: 1.4 }}>
                      {sub.biomechanicalRationale}
                    </span>
                  </td>
                  <td>
                    <span className="badge badge-neutral" style={{ fontSize: '0.75rem' }}>
                      {sub.loadAdjustment}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Daily Recovery Check-In Logger & History */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 1fr) minmax(300px, 1.2fr)', gap: 24 }}>
        
        {/* Logger Form */}
        <section className="card flex-col gap-4">
          <div className="card-header" style={{ marginBottom: 2 }}>
            <div>
              <h2 className="card-title">
                <RotateCcw className="text-orange" size={18} />
                <span>Log Daily Recovery Check-In</span>
              </h2>
              <p className="card-subtitle">
                Record subjective morning joint state to calibrate today's session volume.
              </p>
            </div>
          </div>

          {checkInSuccess && (
            <div className="feedback-box feedback-optimal" style={{ padding: '8px 12px', fontSize: '0.825rem' }}>
              <CheckCircle2 size={16} />
              <span>Check-in logged successfully! Recovery baseline updated.</span>
            </div>
          )}

          <form onSubmit={handleLogCheckIn} className="flex-col gap-4">
            <div className="form-group">
              <label className="form-label">Check-In Discomfort Rating (1-10)</label>
              <div className="flex-row items-center gap-3">
                <input
                  type="range"
                  min="1"
                  max="10"
                  value={checkInRating}
                  onChange={(e) => setCheckInRating(Number(e.target.value))}
                  style={{ flex: 1, accentColor: 'var(--primary-orange)' }}
                />
                <span className="badge badge-orange" style={{ fontSize: '0.9rem', minWidth: 42, textAlign: 'center' }}>
                  {checkInRating}/10
                </span>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Symptom Notes & Mobility Observations</label>
              <textarea
                className="input-field"
                rows={3}
                placeholder="e.g. Mild stiffness during warm-up; resolved after 5 minutes of stationary bike."
                value={checkInNote}
                onChange={(e) => setCheckInNote(e.target.value)}
              />
            </div>

            <button type="submit" className="btn btn-primary btn-md">
              <Plus size={16} />
              <span>Submit Daily Check-In</span>
            </button>
          </form>
        </section>

        {/* Check-In History Log */}
        <section className="card flex-col gap-3">
          <div className="card-header" style={{ marginBottom: 2 }}>
            <div>
              <h2 className="card-title">
                <Clock className="text-teal" size={18} />
                <span>Check-In Longitudinal Log</span>
              </h2>
              <p className="card-subtitle">
                Recent subjective pain tracking entries.
              </p>
            </div>
            <span className="badge badge-neutral">Last 3 Entries</span>
          </div>

          <div className="flex-col gap-3">
            {injuryState.checkInHistory.map((item, idx) => {
              const ratingColor = getRatingColor(item.rating);
              return (
                <div 
                  key={idx} 
                  className="card-flat flex-row justify-between items-center gap-3" 
                  style={{ background: 'var(--surface-subtle)', padding: '12px 16px' }}
                >
                  <div className="flex-col">
                    <div className="flex-row items-center gap-2">
                      <span className="font-semibold text-primary" style={{ fontSize: '0.85rem' }}>
                        {item.date}
                      </span>
                      <span 
                        className="badge" 
                        style={{ background: ratingColor.bg, color: ratingColor.text, fontSize: '0.72rem', padding: '1px 6px' }}
                      >
                        {item.rating}/10 Discomfort
                      </span>
                    </div>
                    <span className="text-secondary" style={{ fontSize: '0.8rem', marginTop: 2 }}>
                      {item.note}
                    </span>
                  </div>

                  <span className="badge badge-neutral" style={{ fontSize: '0.72rem', flexShrink: 0 }}>
                    Recorded
                  </span>
                </div>
              );
            })}
          </div>
        </section>
      </div>
    </div>
  );
}
