import React, { useState } from 'react';
import { 
  Settings, 
  ShieldCheck, 
  Camera, 
  CameraOff, 
  Download, 
  Trash2, 
  Bell, 
  Sliders, 
  Cpu, 
  Lock, 
  CheckCircle2,
  AlertTriangle 
} from 'lucide-react';
import { useApp } from '../context/AppContext';

export default function SettingsPage() {
  const { 
    settings, 
    setSettings, 
    cameraState, 
    stopCameraStream, 
    userProfile, 
    nutrition,
    privacyConsent,
    updatePrivacyConsent,
    exportAllData,
    deleteAccount,
  } = useApp();

  const [exportNotice, setExportNotice] = useState(false);
  const [deleteWarning, setDeleteWarning] = useState(false);

  // Stop camera handler
  const handleStopCamera = () => {
    stopCameraStream();
  };

  // Toggle settings
  const toggleSetting = (key) => {
    setSettings(prev => ({ ...prev, [key]: !prev[key] }));
  };

  // Toggle explicit privacy consent
  const handleToggleConsent = async (key) => {
    const updated = {
      ...privacyConsent,
      [key]: !privacyConsent[key],
    };
    await updatePrivacyConsent(updated);
  };

  // Export machine-readable JSON logs via API or client snapshot
  const handleExportData = async () => {
    const payload = await exportAllData();
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `performx_user_data_export_${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);

    setExportNotice(true);
    setTimeout(() => setExportNotice(false), 3000);
  };

  // Delete account permanently
  const handleDeleteAccount = async () => {
    if (window.confirm("PERMANENT ACTION: Are you sure you want to permanently delete your PERFORMX account? All profile, workout, document, and nutrition records will be permanently purged.")) {
      try {
        await deleteAccount();
      } catch (err) {
        alert("Failed to delete account: " + err.message);
      }
    }
  };

  // Clear local storage
  const handleClearCache = () => {
    if (window.confirm("Are you sure you want to reset local storage? This will reset custom preferences to default values.")) {
      localStorage.removeItem('performx_profile');
      localStorage.removeItem('performx_settings');
      window.location.reload();
    }
  };

  return (
    <div className="flex-col gap-6">
      {/* 1. Camera & Edge Privacy Section */}
      <section className="card flex-col gap-4">
        <div className="card-header" style={{ marginBottom: 2 }}>
          <div>
            <h3 className="card-title">
              <ShieldCheck size={22} className="text-teal" />
              <span>Camera & Edge AI Biometrics Privacy Center</span>
            </h3>
            <p className="card-subtitle">
              Hardware access transparency and real-time on-device computation audit
            </p>
          </div>

          {cameraState.active ? (
            <span className="badge badge-green">Hardware Sensor Active</span>
          ) : (
            <span className="badge badge-neutral">Hardware Sensor Inactive</span>
          )}
        </div>

        <div className="card-flat" style={{ background: 'var(--surface-subtle)', padding: 18 }}>
          <div className="flex-row justify-between items-center" style={{ flexWrap: 'wrap', gap: 14 }}>
            <div className="flex-col gap-1">
              <strong className="text-primary" style={{ fontSize: '0.95rem' }}>Active Camera Stream Status</strong>
              <p style={{ fontSize: '0.85rem' }}>
                {cameraState.active 
                  ? "Camera stream is active. Video frames are analyzed locally in-memory and discarded immediately after landmark extraction."
                  : "Camera is disconnected. No image or video stream is currently active."}
              </p>
            </div>

            {cameraState.active && (
              <button className="btn btn-danger btn-sm" onClick={handleStopCamera}>
                <CameraOff size={15} />
                <span>Stop Camera Stream Now</span>
              </button>
            )}
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 14 }}>
          <div className="card-flat" style={{ background: 'var(--surface-subtle)', padding: 16 }}>
            <div className="flex-row items-center gap-2" style={{ marginBottom: 6 }}>
              <Cpu size={18} className="text-orange" />
              <strong style={{ fontSize: '0.875rem' }}>Client-Side Edge Execution</strong>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Pose landmarking executes via WebAssembly on your device's CPU/GPU. Zero network bandwidth is consumed for video frames.
            </p>
          </div>

          <div className="card-flat" style={{ background: '#F8FAFC', padding: 16 }}>
            <div className="flex-row items-center gap-2" style={{ marginBottom: 6 }}>
              <Lock size={18} className="text-teal" />
              <strong style={{ fontSize: '0.875rem' }}>Zero Server Transmission</strong>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              No video, audio, or biometric frames are transmitted to external servers, cloud storage, or third-party analytics.
            </p>
          </div>
        </div>

        {/* Explicit Processing Consents */}
        <div className="card-flat flex-col gap-3" style={{ background: 'var(--surface-subtle)', padding: 16, marginTop: 8 }}>
          <strong className="text-primary" style={{ fontSize: '0.9rem' }}>Granular Privacy & Data Processing Consents</strong>
          <p className="text-secondary" style={{ fontSize: '0.8rem', margin: 0 }}>
            Configure explicit opt-in permissions required for hardware sensory analysis and analytics.
          </p>

          <div className="flex-row justify-between items-center" style={{ padding: '8px 0', borderBottom: '1px solid var(--border-subtle)' }}>
            <div className="flex-col">
              <span className="font-semibold text-primary" style={{ fontSize: '0.85rem' }}>Camera Sensor Landmark Ingestion</span>
              <small className="text-secondary">Allow browser to stream 33 landmark coordinates to backend during active workouts</small>
            </div>
            <button 
              className={`btn btn-sm ${privacyConsent.camera_processing_consent ? 'btn-teal' : 'btn-secondary'}`}
              onClick={() => handleToggleConsent('camera_processing_consent')}
            >
              {privacyConsent.camera_processing_consent ? 'Consented' : 'Revoked'}
            </button>
          </div>

          <div className="flex-row justify-between items-center" style={{ padding: '8px 0', borderBottom: '1px solid var(--border-subtle)' }}>
            <div className="flex-col">
              <span className="font-semibold text-primary" style={{ fontSize: '0.85rem' }}>Medical Document Restriction Ingestion</span>
              <small className="text-secondary">Allow cataloging uploaded clinical files to adjust exercise substitution bounds</small>
            </div>
            <button 
              className={`btn btn-sm ${privacyConsent.document_processing_consent ? 'btn-teal' : 'btn-secondary'}`}
              onClick={() => handleToggleConsent('document_processing_consent')}
            >
              {privacyConsent.document_processing_consent ? 'Consented' : 'Revoked'}
            </button>
          </div>

          <div className="flex-row justify-between items-center" style={{ padding: '8px 0' }}>
            <div className="flex-col">
              <span className="font-semibold text-primary" style={{ fontSize: '0.85rem' }}>Longitudinal Analytics Aggregation</span>
              <small className="text-secondary">Allow computing weekly goal adherence, reps, and symmetry trend metrics</small>
            </div>
            <button 
              className={`btn btn-sm ${privacyConsent.data_analytics_consent ? 'btn-teal' : 'btn-secondary'}`}
              onClick={() => handleToggleConsent('data_analytics_consent')}
            >
              {privacyConsent.data_analytics_consent ? 'Consented' : 'Revoked'}
            </button>
          </div>
        </div>
      </section>

      {/* 2. Preferences & Units */}
      <section className="card flex-col gap-4">
        <div className="card-header" style={{ marginBottom: 2 }}>
          <div>
            <h3 className="card-title">
              <Sliders size={20} className="text-orange" />
              <span>Measurement Units & Display Preferences</span>
            </h3>
            <p className="card-subtitle">Configure measurement standards and visual feedback</p>
          </div>
        </div>

        <div className="flex-col gap-3">
          <div className="flex-row justify-between items-center" style={{ padding: '12px 0', borderBottom: '1px solid var(--border-subtle)' }}>
            <div className="flex-col">
              <span className="font-semibold text-primary">Measurement System</span>
              <small className="text-secondary">Select Metric (kg, cm) or Imperial (lbs, in)</small>
            </div>
            <div className="tabs-container">
              <button 
                type="button"
                className={`tab-btn ${settings.unitSystem === 'metric' ? 'active' : ''}`}
                onClick={() => setSettings({ ...settings, unitSystem: 'metric' })}
              >
                Metric (kg/cm)
              </button>
              <button 
                type="button"
                className={`tab-btn ${settings.unitSystem === 'imperial' ? 'active' : ''}`}
                onClick={() => setSettings({ ...settings, unitSystem: 'imperial' })}
              >
                Imperial (lbs/in)
              </button>
            </div>
          </div>

          <div className="flex-row justify-between items-center" style={{ padding: '12px 0', borderBottom: '1px solid var(--border-subtle)' }}>
            <div className="flex-col">
              <span className="font-semibold text-primary">Audio Feedback Cues</span>
              <small className="text-secondary">Chime on verified 90° parallel depth and lockout</small>
            </div>
            <button 
              className={`btn btn-sm ${settings.soundCues ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => toggleSetting('soundCues')}
            >
              {settings.soundCues ? 'Enabled' : 'Disabled'}
            </button>
          </div>

          <div className="flex-row justify-between items-center" style={{ padding: '12px 0' }}>
            <div className="flex-col">
              <span className="font-semibold text-primary">Auto-Pause on Subject Occlusion</span>
              <small className="text-secondary">Automatically pauses session when body tracking becomes unreliable</small>
            </div>
            <button 
              className={`btn btn-sm ${settings.autoPauseWhenLost ? 'btn-teal' : 'btn-secondary'}`}
              onClick={() => toggleSetting('autoPauseWhenLost')}
            >
              {settings.autoPauseWhenLost ? 'Enabled' : 'Disabled'}
            </button>
          </div>
        </div>
      </section>

      {/* 3. Data Management & Export */}
      <section className="card flex-col gap-4">
        <div className="card-header" style={{ marginBottom: 2 }}>
          <div>
            <h3 className="card-title">
              <Download size={20} className="text-primary" />
              <span>Data Export & Storage Management</span>
            </h3>
            <p className="card-subtitle">Export your telemetry or clear browser storage</p>
          </div>
        </div>

        {exportNotice && (
          <div className="feedback-box feedback-success">
            <CheckCircle2 size={18} />
            <span>Biomechanics telemetry data successfully exported as machine-readable JSON archive.</span>
          </div>
        )}

        <div className="flex-row gap-4" style={{ flexWrap: 'wrap' }}>
          <button className="btn btn-primary" onClick={handleExportData}>
            <Download size={16} />
            <span>Export Complete User Archive (GDPR / CCPA)</span>
          </button>

          <button className="btn btn-secondary" onClick={handleClearCache}>
            <span>Reset Local Preferences</span>
          </button>

          <button className="btn btn-danger" onClick={handleDeleteAccount}>
            <Trash2 size={16} />
            <span>Delete Account & Purge Data</span>
          </button>
        </div>
      </section>
    </div>
  );
}
