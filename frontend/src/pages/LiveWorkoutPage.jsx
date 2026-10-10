import React, { useState } from 'react';
import LiveCameraFeed from '../components/analysis/LiveCameraFeed';
import FruitFlyKinematics3D from '../components/analysis/FruitFlyKinematics3D';
import { 
  Play, 
  Pause, 
  RotateCcw, 
  CheckCircle, 
  AlertTriangle, 
  CheckCircle2, 
  Activity, 
  Info,
  ShieldCheck,
  ChevronDown
} from 'lucide-react';
import { useApp } from '../context/AppContext';

export default function LiveWorkoutPage() {
  const { 
    activeSession, 
    setActiveSession, 
    cameraState, 
    stopCameraStream,
    toggleModal,
    resetMovementSession
  } = useApp();

  const [selectedExercise, setSelectedExercise] = useState('Barbell Back Squat');

  const exerciseOptions = [
    {
      name: 'Barbell Back Squat',
      targetDepth: '≤ 90° Knee Flexion',
      primaryJoints: 'Knee & Hip Bilateral Flexion',
      keyCue: 'Break at knees & hips simultaneously; drive knees out over toes.'
    },
    {
      name: 'Romanian Deadlift',
      targetDepth: '65° - 75° Hip Hinge',
      primaryJoints: 'Hip Hinge & Lumbar Extension',
      keyCue: 'Maintain neutral lumbar curvature; push hips backwards toward wall.'
    },
    {
      name: 'Bulgarian Split Squat',
      targetDepth: '85° Lead Knee Flexion',
      primaryJoints: 'Unilateral Knee & Ankle Kinematics',
      keyCue: 'Keep front foot flat; descend with upright torso.'
    },
    {
      name: 'Push-Up & Core Plank',
      targetDepth: '90° Elbow Flexion',
      primaryJoints: 'Glenohumeral & Scapular Rhythm',
      keyCue: 'Elbows at 45° angle to torso; core locked without hip sag.'
    }
  ];

  const currentExerciseData = exerciseOptions.find(e => e.name === selectedExercise) || exerciseOptions[0];

  const handleExerciseChange = (e) => {
    setSelectedExercise(e.target.value);
    setActiveSession(prev => ({
      ...prev,
      exerciseName: e.target.value,
      currentReps: 0,
      currentSet: 1,
    }));
  };

  const handleTogglePause = () => {
    setActiveSession(prev => ({
      ...prev,
      isPaused: !prev.isPaused,
    }));
  };

  const handleResetSession = () => {
    if (window.confirm("Are you sure you want to reset current repetition count and set progress?")) {
      resetMovementSession();
    }
  };

  return (
    <div className="flex-col gap-6">
      {/* Exercise Selection & Instructions Header */}
      <section className="card" style={{ padding: '20px 24px' }}>
        <div className="flex-row justify-between items-center" style={{ flexWrap: 'wrap', gap: 16 }}>
          <div className="flex-col gap-1">
            <span className="badge badge-orange" style={{ width: 'fit-content' }}>Active Exercise Biomechanics</span>
            <div className="flex-row items-center gap-3">
              <select 
                className="input-field" 
                style={{ fontSize: '1.25rem', fontWeight: 700, padding: '6px 14px', width: 'auto', minWidth: 260 }}
                value={selectedExercise}
                onChange={handleExerciseChange}
              >
                {exerciseOptions.map(opt => (
                  <option key={opt.name} value={opt.name}>{opt.name}</option>
                ))}
              </select>
            </div>
            <p style={{ fontSize: '0.875rem', marginTop: 4 }}>
              <strong>Biomechanical Cue:</strong> {currentExerciseData.keyCue}
            </p>
          </div>

          {/* Session Progress Indicators */}
          <div className="flex-row gap-4 items-center">
            <div className="card-flat flex-col items-center" style={{ padding: '8px 18px', background: 'var(--surface-subtle)' }}>
              <span className="telemetry-label">Current Set</span>
              <span className="font-bold text-primary" style={{ fontSize: '1.25rem' }}>
                {activeSession.currentSet} of {activeSession.targetSets}
              </span>
            </div>

            <div className="card-flat flex-col items-center" style={{ padding: '8px 18px', background: 'var(--surface-subtle)' }}>
              <span className="telemetry-label">Completed Reps</span>
              <span className="font-bold text-orange" style={{ fontSize: '1.25rem' }}>
                {activeSession.currentReps} / {activeSession.targetReps}
              </span>
            </div>

            <button 
              className="btn btn-teal btn-lg" 
              onClick={() => {
                stopCameraStream();
                toggleModal('completion', true);
              }}
              title="Finish workout and view celebration"
            >
              <CheckCircle size={18} />
              <span>Finish Workout</span>
            </button>
          </div>
        </div>
      </section>

      {/* Main Studio Viewport Grid (Camera on Left, 3D Drosophila Kinematics on Right) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.15fr 0.85fr', gap: 24 }}>
        {/* Left Studio Viewport: Camera Feed */}
        <section className="card flex-col gap-4">
          <div className="card-header" style={{ marginBottom: 4 }}>
            <div>
              <h3 className="card-title">
                <Activity size={20} className="text-orange" />
                <span>Camera Pose Landmarker</span>
              </h3>
              <p className="card-subtitle">
                MediaPipe on-device skeletal keypoints and joint vector tracking
              </p>
            </div>
            <span className="badge badge-orange">Local Stream</span>
          </div>

          <LiveCameraFeed showTelemetry={true} compact={false} />

          {/* Session Playback Controls */}
          <div className="flex-row justify-between items-center" style={{ paddingTop: 12, borderTop: '1px solid var(--border-subtle)' }}>
            <div className="flex-row gap-2">
              <button 
                className={`btn ${activeSession.isPaused ? 'btn-primary' : 'btn-secondary'}`}
                onClick={handleTogglePause}
              >
                {activeSession.isPaused ? <Play size={16} /> : <Pause size={16} />}
                <span>{activeSession.isPaused ? 'Resume Session' : 'Pause'}</span>
              </button>

              <button className="btn btn-ghost" onClick={handleResetSession}>
                <RotateCcw size={16} />
                <span>Reset Count</span>
              </button>
            </div>

            <div className="flex-row items-center gap-2 text-muted" style={{ fontSize: '0.825rem' }}>
              <ShieldCheck size={16} className="text-teal" />
              <span>100% In-Browser Privacy</span>
            </div>
          </div>
        </section>

        {/* Right Studio Viewport: Fruit-Fly 3D Kinematics */}
        <section className="card flex-col gap-4">
          <div className="card-header" style={{ marginBottom: 4 }}>
            <div>
              <h3 className="card-title">
                <Activity size={20} className="text-teal" />
                <span>Articulated 3D Kinematics</span>
              </h3>
              <p className="card-subtitle">
                Drosophila research-inspired multi-segment spatial biomechanics
              </p>
            </div>
            <span className="badge badge-teal">Three.js Engine</span>
          </div>

          <FruitFlyKinematics3D height={380} showControls={true} />

          {/* Biomechanical Target Standards */}
          <div className="card-flat" style={{ background: 'var(--surface-subtle)', padding: 16 }}>
            <h4 style={{ fontSize: '0.9rem', marginBottom: 10 }}>Target Movement Parameters</h4>
            <div className="flex-col gap-2" style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              <div className="flex-row justify-between">
                <span>Parallel Depth Target:</span>
                <strong className="text-primary">{currentExerciseData.targetDepth}</strong>
              </div>
              <div className="flex-row justify-between">
                <span>Primary Kinematic Axis:</span>
                <strong className="text-primary">{currentExerciseData.primaryJoints}</strong>
              </div>
              <div className="flex-row justify-between">
                <span>Current Bilateral Symmetry:</span>
                <strong className="text-teal">
                  {activeSession.kneeAngle !== null ? `${activeSession.symmetryScore}% Balanced` : '-- (Awaiting Stream)'}
                </strong>
              </div>
            </div>
          </div>
        </section>
      </div>

      {/* Movement Feedback & Guidance Banners */}
      <section className="card" style={{ padding: '20px 24px' }}>
        <h4 style={{ fontSize: '1rem', marginBottom: 14 }}>Real-Time Form Analysis & Safety Criteria</h4>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16 }}>
          <div className="feedback-box feedback-success" style={{ margin: 0 }}>
            <CheckCircle2 size={20} style={{ flexShrink: 0 }} />
            <div>
              <div className="font-semibold">Optimal Depth Attained</div>
              <div style={{ fontSize: '0.8rem', opacity: 0.9 }}>
                Knee flexion angle passed 90° parallel line with full foot contact maintained.
              </div>
            </div>
          </div>

          <div className="feedback-box feedback-warning" style={{ margin: 0 }}>
            <AlertTriangle size={20} style={{ flexShrink: 0 }} />
            <div>
              <div className="font-semibold">Torso Incline Caution</div>
              <div style={{ fontSize: '0.8rem', opacity: 0.9 }}>
                Excessive forward lean shifts mechanical load to lumbar spine. Keep chest tall.
              </div>
            </div>
          </div>

          <div className="feedback-box feedback-error" style={{ margin: 0 }}>
            <AlertTriangle size={20} style={{ flexShrink: 0 }} />
            <div>
              <div className="font-semibold">Knee Valgus Warning</div>
              <div style={{ fontSize: '0.8rem', opacity: 0.9 }}>
                Knees collapsing inward during concentric phase. Push outward over lateral toes.
              </div>
            </div>
          </div>

          <div className="feedback-box feedback-neutral" style={{ margin: 0 }}>
            <Info size={20} style={{ flexShrink: 0 }} />
            <div>
              <div className="font-semibold">Tracking Confidence</div>
              <div style={{ fontSize: '0.8rem', opacity: 0.9 }}>
                High confidence ({activeSession.trackingConfidence}%). Local pose landmarks verified.
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
