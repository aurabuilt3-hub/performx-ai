import React, { useState, useEffect } from 'react';
import Modal from '../common/Modal';
import { User, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { useApp } from '../../context/AppContext';

export default function EditProfileModal({ isOpen, onClose }) {
  const { userProfile, updateProfile, updateHealthProfile } = useApp();

  const [formData, setFormData] = useState({
    name: userProfile.name || '',
    goal: userProfile.goal || 'general_fitness',
    experienceLevel: userProfile.experienceLevel || 'intermediate',
    heightCm: userProfile.heightCm || 175,
    weightKg: userProfile.weightKg || 70.0,
    bodyFatPercent: userProfile.bodyFatPercent || 15.0,
    restingHr: userProfile.restingHr || 60,
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [savedSuccess, setSavedSuccess] = useState(false);

  // Sync state whenever modal opens or userProfile changes
  useEffect(() => {
    if (isOpen) {
      setFormData({
        name: userProfile.name || '',
        goal: userProfile.goal || 'general_fitness',
        experienceLevel: userProfile.experienceLevel || 'intermediate',
        heightCm: userProfile.heightCm || 175,
        weightKg: userProfile.weightKg || 70.0,
        bodyFatPercent: userProfile.bodyFatPercent || 15.0,
        restingHr: userProfile.restingHr || 60,
      });
      setError('');
      setSavedSuccess(false);
    }
  }, [isOpen, userProfile]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Input validations according to Pydantic constraints
    if (!formData.name.trim()) {
      setError('Full name is required.');
      return;
    }
    const h = Number(formData.heightCm);
    if (isNaN(h) || h < 50 || h > 300) {
      setError('Height must be between 50 and 300 cm.');
      return;
    }
    const w = Number(formData.weightKg);
    if (isNaN(w) || w < 20 || w > 500) {
      setError('Weight must be between 20 and 500 kg.');
      return;
    }
    const bf = Number(formData.bodyFatPercent);
    if (isNaN(bf) || bf < 2 || bf > 70) {
      setError('Body fat percentage must be between 2% and 70%.');
      return;
    }
    const hr = Number(formData.restingHr);
    if (isNaN(hr) || hr < 30 || hr > 220) {
      setError('Resting heart rate must be between 30 and 220 bpm.');
      return;
    }

    setLoading(true);
    try {
      // 1. Update Profile (display_name, goal, experience)
      await updateProfile({
        name: formData.name.trim(),
        goal: formData.goal,
        experienceLevel: formData.experienceLevel,
      });

      // 2. Update Health Profile (height, weight, body_fat, heart_rate)
      await updateHealthProfile({
        heightCm: h,
        weightKg: w,
        bodyFatPercent: bf,
        restingHr: Math.round(hr),
      });

      setSavedSuccess(true);
      setTimeout(() => {
        setSavedSuccess(false);
        setLoading(false);
        onClose();
      }, 700);
    } catch (err) {
      setLoading(false);
      setError(err.message || 'Failed to update profile. Please verify connection.');
    }
  };

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose} 
      title="Edit Athlete Profile & Biometrics"
      subtitle="Update your physical parameters and training baseline."
    >
      {error && (
        <div className="feedback-box feedback-error" style={{ marginBottom: 16 }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {savedSuccess && (
        <div className="feedback-box feedback-success" style={{ marginBottom: 16 }}>
          <CheckCircle2 size={18} />
          <span>Profile biometrics successfully saved to PERFORMX.</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex-col gap-4">
        <div>
          <label className="font-semibold text-primary" style={{ display: 'block', marginBottom: 6, fontSize: '0.85rem' }}>
            Full Name
          </label>
          <input
            type="text"
            className="input-field"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            required
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
          <div>
            <label className="font-semibold text-primary" style={{ display: 'block', marginBottom: 6, fontSize: '0.85rem' }}>
              Height (cm)
            </label>
            <input
              type="number"
              className="input-field"
              value={formData.heightCm}
              onChange={(e) => setFormData({ ...formData, heightCm: Number(e.target.value) })}
              required
            />
          </div>
          <div>
            <label className="font-semibold text-primary" style={{ display: 'block', marginBottom: 6, fontSize: '0.85rem' }}>
              Weight (kg)
            </label>
            <input
              type="number"
              step="0.1"
              className="input-field"
              value={formData.weightKg}
              onChange={(e) => setFormData({ ...formData, weightKg: Number(e.target.value) })}
              required
            />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
          <div>
            <label className="font-semibold text-primary" style={{ display: 'block', marginBottom: 6, fontSize: '0.85rem' }}>
              Body Fat (%)
            </label>
            <input
              type="number"
              step="0.1"
              className="input-field"
              value={formData.bodyFatPercent}
              onChange={(e) => setFormData({ ...formData, bodyFatPercent: Number(e.target.value) })}
            />
          </div>
          <div>
            <label className="font-semibold text-primary" style={{ display: 'block', marginBottom: 6, fontSize: '0.85rem' }}>
              Resting Heart Rate (bpm)
            </label>
            <input
              type="number"
              className="input-field"
              value={formData.restingHr}
              onChange={(e) => setFormData({ ...formData, restingHr: Number(e.target.value) })}
            />
          </div>
        </div>

        <div>
          <label className="font-semibold text-primary" style={{ display: 'block', marginBottom: 6, fontSize: '0.85rem' }}>
            Primary Fitness Goal
          </label>
          <select 
            className="input-field"
            value={formData.goal}
            onChange={(e) => setFormData({ ...formData, goal: e.target.value })}
          >
            <option value="Strength & Biomechanics">Strength & Biomechanics</option>
            <option value="Muscle Building">Muscle Building (Hypertrophy)</option>
            <option value="Fat Loss & Conditioning">Fat Loss & Overall Conditioning</option>
            <option value="Endurance & Stamina">Endurance & Stamina</option>
            <option value="Mobility & Joint Longevity">Mobility & Joint Longevity</option>
          </select>
        </div>

        <div className="flex-row justify-between items-center" style={{ marginTop: 12, paddingTop: 16, borderTop: '1px solid var(--border-subtle)' }}>
          <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={loading} style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
            {loading && <Loader2 size={16} className="animate-spin" />}
            {loading ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
