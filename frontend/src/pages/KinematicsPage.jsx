import React, { useState } from 'react';
import FruitFlyKinematics3D from '../components/analysis/FruitFlyKinematics3D';
import { 
  Box, 
  Layers, 
  Activity, 
  Compass, 
  Info, 
  Cpu, 
  Sparkles,
  ArrowRight,
  ShieldCheck
} from 'lucide-react';
import { useApp } from '../context/AppContext';

export default function KinematicsPage() {
  const { activeSession, setActiveTab } = useApp();
  const [selectedJoint, setSelectedJoint] = useState('kneeL');

  const jointTelemetry = {
    'kneeL': {
      name: 'Left Tibiofemoral Joint (Knee)',
      angle: activeSession.kneeAngle !== null ? `${activeSession.kneeAngle}°` : '-- (Stream Idle)',
      rom: '0° - 140° Flexion',
      stressAxis: 'Sagittal (Shear & Compressive force)',
      status: activeSession.kneeAngle !== null && activeSession.kneeAngle <= 90 ? 'Optimal Depth (≤90° attained)' : 'Tracking Inactive',
    },
    'hipL': {
      name: 'Left Acetabulofemoral Joint (Hip)',
      angle: activeSession.hipAngle !== null ? `${activeSession.hipAngle}°` : '-- (Stream Idle)',
      rom: '0° - 120° Hinge',
      stressAxis: 'Multi-axial (Sagittal & Transverse)',
      status: activeSession.hipAngle !== null ? 'Neutral Lumbar Alignment' : 'Tracking Inactive',
    },
    'spine': {
      name: 'Torso / Lumbar Kinematic Vector',
      angle: activeSession.torsoAngle !== null ? `${activeSession.torsoAngle}°` : '-- (Stream Idle)',
      rom: '75° - 85° Inclination',
      stressAxis: 'Axial Compression',
      status: 'Stable Core Stiffness',
    },
    'pelvis': {
      name: 'Pelvic Center of Mass (CoM)',
      angle: '0° Tilt',
      rom: 'Neutral Pelvic Tilt',
      stressAxis: 'Vertical Kinetic Chain',
      status: activeSession.kneeAngle !== null ? `${activeSession.symmetryScore}% Bilateral Balance` : 'Equilibrium',
    }
  };

  const currentJoint = jointTelemetry[selectedJoint] || jointTelemetry['kneeL'];

  return (
    <div className="flex-col gap-6">
      {/* Overview Banner */}
      <section className="card">
        <div className="flex-row justify-between items-center" style={{ flexWrap: 'wrap', gap: 16 }}>
          <div className="flex-col gap-1" style={{ maxWidth: 780 }}>
            <div className="flex-row items-center gap-2">
              <span className="badge badge-orange">Scientific Biomechanics</span>
              <span className="badge badge-cyan">Drosophila Kinematic Model</span>
            </div>
            <h2 style={{ fontSize: '1.45rem', marginTop: 4 }}>
              Multi-Segment Articulated Movement Mechanics
            </h2>
            <p style={{ fontSize: '0.925rem', lineHeight: 1.6 }}>
              In biological kinematics research, high-speed multi-camera computer vision tracks 3D articulated joints, limb displacement vectors, and trajectory trails of <em>Drosophila melanogaster</em> to analyze complex multi-degree-of-freedom locomotion. PERFORMX adapts these exact computational principles to human athletic movement.
            </p>
          </div>

          <button className="btn btn-primary btn-lg" onClick={() => setActiveTab('live-workout')}>
            <span>Launch Live Analysis</span>
            <ArrowRight size={18} />
          </button>
        </div>
      </section>

      {/* Main 3D Viewport with Telemetry Side Panel */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 0.6fr', gap: 24 }}>
        {/* 3D Viewport */}
        <section className="card flex-col gap-3" style={{ padding: 20 }}>
          <div className="card-header" style={{ marginBottom: 2 }}>
            <div>
              <h3 className="card-title">
                <Box size={20} className="text-orange" />
                <span>Interactive 3D Kinematic Viewport</span>
              </h3>
              <p className="card-subtitle">
                Drag to orbit, scroll to zoom, or select anatomical camera presets
              </p>
            </div>
            <span className="badge badge-orange">Three.js WebGL</span>
          </div>

          <FruitFlyKinematics3D height={480} showControls={true} />
        </section>

        {/* Joint Telemetry Inspector Panel */}
        <section className="card flex-col gap-4">
          <div className="card-header" style={{ marginBottom: 4 }}>
            <div>
              <h3 className="card-title">
                <Layers size={18} className="text-teal" />
                <span>Kinematic Joint Inspector</span>
              </h3>
              <p className="card-subtitle">Select node to inspect mechanical degrees of freedom</p>
            </div>
          </div>

          {/* Joint Selection Tabs */}
          <div className="tabs-container" style={{ width: '100%' }}>
            {[
              { id: 'kneeL', label: 'Knee' },
              { id: 'hipL', label: 'Hip' },
              { id: 'spine', label: 'Torso' },
              { id: 'pelvis', label: 'Pelvis' },
            ].map(j => (
              <button
                key={j.id}
                type="button"
                className={`tab-btn ${selectedJoint === j.id ? 'active' : ''}`}
                style={{ flex: 1, textAlign: 'center' }}
                onClick={() => setSelectedJoint(j.id)}
              >
                {j.label}
              </button>
            ))}
          </div>

          {/* Active Joint Telemetry Details */}
          <div className="card-flat flex-col gap-3" style={{ background: 'var(--surface-subtle)' }}>
            <span className="font-bold text-primary" style={{ fontSize: '1rem' }}>
              {currentJoint.name}
            </span>

            <div className="flex-row justify-between" style={{ borderBottom: '1px solid var(--border-subtle)', paddingBottom: 8 }}>
              <span className="text-secondary" style={{ fontSize: '0.85rem' }}>Instantaneous Angle:</span>
              <strong className="text-orange" style={{ fontSize: '1.25rem' }}>{currentJoint.angle}</strong>
            </div>

            <div className="flex-row justify-between" style={{ borderBottom: '1px solid var(--border-subtle)', paddingBottom: 8 }}>
              <span className="text-secondary" style={{ fontSize: '0.85rem' }}>Physiological ROM:</span>
              <span className="font-semibold text-primary">{currentJoint.rom}</span>
            </div>

            <div className="flex-row justify-between" style={{ borderBottom: '1px solid var(--border-subtle)', paddingBottom: 8 }}>
              <span className="text-secondary" style={{ fontSize: '0.85rem' }}>Primary Loading Axis:</span>
              <span className="font-semibold text-primary">{currentJoint.stressAxis}</span>
            </div>

            <div className="flex-row justify-between">
              <span className="text-secondary" style={{ fontSize: '0.85rem' }}>Kinematic Status:</span>
              <span className="badge badge-green">{currentJoint.status}</span>
            </div>
          </div>

          {/* Drosophila Mathematical Foundations */}
          <div className="card-flat flex-col gap-2" style={{ background: 'var(--surface-subtle)' }}>
            <div className="flex-row items-center gap-2">
              <Sparkles size={16} className="text-orange" />
              <strong style={{ fontSize: '0.875rem' }}>Kinematic Principles</strong>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              By computing multi-segment inverse kinematics across the 17 coordinate nodes, PERFORMX calculates instantaneous joint angles without markers, validating mechanical work and movement safety in real-time.
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
