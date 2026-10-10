import React, { useState, useMemo } from 'react';
import Modal from '../components/common/Modal';
import { 
  CalendarRange, 
  Clock, 
  Dumbbell, 
  Layers, 
  Target, 
  Play, 
  ChevronRight, 
  CheckCircle2, 
  Sparkles,
  Filter,
  ShieldAlert,
  ShieldCheck,
  Info,
  Award
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { generatePersonalizedPlans } from '../engine/personalizationEngine';

export default function WorkoutPlansPage() {
  const { 
    userProfile, 
    injuryState, 
    enrolledPlan, 
    enrollInPlan, 
    setActiveTab 
  } = useApp();

  const [selectedCategory, setSelectedCategory] = useState('All');
  const [selectedDifficulty, setSelectedDifficulty] = useState('All');
  const [activePlanModal, setActivePlanModal] = useState(null);
  const [enrollSuccessMessage, setEnrollSuccessMessage] = useState('');

  // Generate personalized plans using the personalization engine
  const personalizedPlans = useMemo(() => {
    return generatePersonalizedPlans({
      userProfile,
      injuryState,
      clinicianRestrictions: injuryState?.clinicianRestrictions || []
    });
  }, [userProfile, injuryState]);

  const filteredPlans = personalizedPlans.filter(p => {
    const matchCat = selectedCategory === 'All' || p.category === selectedCategory;
    const matchDiff = selectedDifficulty === 'All' || p.difficulty === selectedDifficulty;
    return matchCat && matchDiff;
  });

  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleEnroll = async (plan) => {
    try {
      setIsSubmitting(true);
      await enrollInPlan(plan);
      setEnrollSuccessMessage(`Successfully enrolled in "${plan.title}"! Today's routine has been updated.`);
      if (activePlanModal) setActivePlanModal(null);
      setTimeout(() => setEnrollSuccessMessage(''), 4000);
    } catch (err) {
      console.warn('Enrollment error:', err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex-col gap-6">
      {/* Success Notification Banner */}
      {enrollSuccessMessage && (
        <div className="feedback-box feedback-optimal" style={{ borderLeftWidth: 4, borderLeftColor: 'var(--mint-teal)' }}>
          <CheckCircle2 size={20} className="text-teal" />
          <span className="font-semibold text-primary">{enrollSuccessMessage}</span>
        </div>
      )}

      {/* Active Enrolled Plan Card */}
      <section className="card" style={{ border: '1px solid var(--border-medium)' }}>
        <div className="flex-row justify-between items-center" style={{ flexWrap: 'wrap', gap: 16 }}>
          <div className="flex-col gap-2">
            <div className="flex-row items-center gap-2">
              <span className="badge badge-orange">Currently Enrolled Plan</span>
              <span className="badge badge-green">Week {enrolledPlan.week} of {enrolledPlan.totalWeeks}</span>
            </div>
            <h2 style={{ fontSize: '1.4rem' }}>{enrolledPlan.title}</h2>
            <p style={{ maxWidth: 650, fontSize: '0.875rem' }}>
              You have completed {enrolledPlan.completedSessions} of {enrolledPlan.totalSessions} scheduled training sessions. 
              {injuryState.activeRegion && (
                <span className="text-orange font-semibold" style={{ display: 'block', marginTop: 4 }}>
                  🛡️ Clinician guidance active: Movements targeting {injuryState.activeRegion} are automatically replaced with safe biomechanical alternatives.
                </span>
              )}
            </p>
          </div>

          <button 
            className="btn btn-primary btn-lg" 
            onClick={() => setActiveTab('live-workout')}
          >
            <Play size={18} />
            <span>Continue Today's Workout</span>
          </button>
        </div>
      </section>

      {/* Personalization Engine Header Banner */}
      <div className="feedback-box feedback-neutral" style={{ padding: '12px 16px', margin: 0 }}>
        <Sparkles size={18} className="text-orange" style={{ flexShrink: 0 }} />
        <span style={{ fontSize: '0.85rem' }}>
          <strong>Personalization Engine Active:</strong> Plans are synthesized to match your <strong>{userProfile.experienceLevel}</strong> experience, <strong>{userProfile.goal}</strong> goal, and available equipment (<em>{userProfile.equipment.join(', ')}</em>).
        </span>
      </div>

      {/* Filter Chips Bar */}
      <div className="flex-row justify-between items-center" style={{ flexWrap: 'wrap', gap: 14 }}>
        <div className="flex-row items-center gap-2">
          <Filter size={16} className="text-muted" />
          <span className="font-semibold text-secondary" style={{ fontSize: '0.875rem' }}>Category:</span>
          {['All', 'Hypertrophy', 'Strength', 'Mobility', 'Conditioning'].map(cat => (
            <button
              key={cat}
              className={`btn btn-sm ${selectedCategory === cat ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setSelectedCategory(cat)}
            >
              {cat}
            </button>
          ))}
        </div>

        <div className="flex-row items-center gap-2">
          <span className="font-semibold text-secondary" style={{ fontSize: '0.875rem' }}>Difficulty:</span>
          {['All', 'Beginner', 'Intermediate', 'Advanced'].map(diff => (
            <button
              key={diff}
              className={`btn btn-sm ${selectedDifficulty === diff ? 'btn-teal' : 'btn-secondary'}`}
              onClick={() => setSelectedDifficulty(diff)}
            >
              {diff}
            </button>
          ))}
        </div>
      </div>

      {/* Plans Grid */}
      <div className="plans-grid">
        {filteredPlans.map(plan => {
          const isEnrolled = enrolledPlan.title === plan.title;
          return (
            <div key={plan.id} className="plan-card">
              <div className="plan-card-image" style={{ background: `linear-gradient(135deg, ${plan.color} 0%, #111936 100%)` }}>
                <div className="flex-col items-center gap-1 text-center" style={{ padding: 20 }}>
                  <CalendarRange size={36} />
                  <span className="font-bold" style={{ fontSize: '1.1rem' }}>{plan.title}</span>
                  <div className="flex-row gap-2 justify-center" style={{ marginTop: 2 }}>
                    <span className="badge badge-orange" style={{ fontSize: '0.72rem', background: 'rgba(255,255,255,0.2)', color: 'white' }}>
                      {plan.category}
                    </span>
                    <span className="badge badge-teal" style={{ fontSize: '0.72rem', background: 'rgba(255,255,255,0.2)', color: 'white' }}>
                      {plan.difficulty}
                    </span>
                  </div>
                </div>
              </div>

              <div className="plan-card-body">
                <p style={{ fontSize: '0.875rem', lineHeight: 1.5, flex: 1, margin: 0 }}>
                  {plan.desc}
                </p>

                {/* Personalization Reason Callout */}
                <div style={{ background: 'var(--surface-subtle)', padding: '8px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', margin: '8px 0' }}>
                  <small className="text-secondary" style={{ fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Sparkles size={13} className="text-orange" />
                    <span>{plan.personalizationReason}</span>
                  </small>
                </div>

                <div className="flex-row justify-between text-muted" style={{ fontSize: '0.8rem', borderTop: '1px solid var(--border-subtle)', paddingTop: 10 }}>
                  <span className="flex-row items-center gap-1">
                    <Clock size={14} /> {plan.duration}
                  </span>
                  <span className="flex-row items-center gap-1">
                    <CalendarRange size={14} /> {plan.daysPerWeek}
                  </span>
                  <span className="flex-row items-center gap-1">
                    <Dumbbell size={14} /> {plan.exerciseCount} Exercises
                  </span>
                </div>

                <div className="flex-row gap-2" style={{ marginTop: 8 }}>
                  <button 
                    className="btn btn-secondary btn-sm" 
                    style={{ flex: 1 }}
                    onClick={() => setActivePlanModal(plan)}
                  >
                    View Schedule
                  </button>
                  <button 
                    className={`btn btn-sm ${isEnrolled ? 'btn-teal' : 'btn-primary'}`}
                    onClick={() => handleEnroll(plan)}
                    disabled={isEnrolled}
                  >
                    {isEnrolled ? 'Active Plan' : 'Enroll Plan'}
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Plan Schedule Modal */}
      {activePlanModal && (
        <Modal
          isOpen={true}
          onClose={() => setActivePlanModal(null)}
          title={activePlanModal.title}
          subtitle={`${activePlanModal.duration} • ${activePlanModal.difficulty} • Calibrated for: ${activePlanModal.equipment}`}
          wide={true}
        >
          <div className="flex-col gap-4">
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              {activePlanModal.desc}
            </p>

            <div className="feedback-box feedback-optimal" style={{ padding: '8px 14px', margin: 0 }}>
              <ShieldCheck size={18} className="text-teal" />
              <span style={{ fontSize: '0.825rem' }}>
                {activePlanModal.personalizationReason}
              </span>
            </div>

            <h4 style={{ fontSize: '1rem', marginTop: 4 }}>Weekly Personalized Schedule & Parameters</h4>
            <div className="flex-col gap-3">
              {activePlanModal.schedule.map((day, idx) => (
                <div key={idx} className="card-flat" style={{ background: 'var(--surface-subtle)', padding: 16 }}>
                  <div className="flex-row justify-between items-center" style={{ marginBottom: 10 }}>
                    <div className="font-semibold text-primary" style={{ fontSize: '0.95rem' }}>
                      {day.day}
                    </div>
                    <span className="badge badge-orange" style={{ fontSize: '0.72rem' }}>
                      {day.focus}
                    </span>
                  </div>

                  <div className="flex-col gap-2">
                    {day.exercises.map((ex, eIdx) => (
                      <div 
                        key={eIdx} 
                        className="flex-row justify-between items-center" 
                        style={{ 
                          background: 'var(--surface-card)', 
                          padding: '8px 12px', 
                          borderRadius: 'var(--radius-sm)',
                          border: `1px solid ${ex.isSubstituted ? '#FCD34D' : 'var(--border-subtle)'}` 
                        }}
                      >
                        <div className="flex-col">
                          <div className="flex-row items-center gap-2">
                            <strong className="text-primary" style={{ fontSize: '0.85rem' }}>{ex.name}</strong>
                            {ex.isSubstituted && (
                              <span className="badge badge-amber" style={{ fontSize: '0.7rem' }}>
                                Clinician Substitution
                              </span>
                            )}
                          </div>
                          {ex.substitutionNote && (
                            <small className="text-muted" style={{ fontSize: '0.75rem' }}>
                              ↳ {ex.substitutionNote}
                            </small>
                          )}
                        </div>

                        <div className="flex-row gap-3 items-center" style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                          <span><strong>{ex.sets}</strong> sets × <strong>{ex.reps}</strong></span>
                          <span className="badge badge-neutral" style={{ fontSize: '0.72rem' }}>Rest: {ex.rest}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="flex-row justify-end gap-3" style={{ marginTop: 12 }}>
              <button className="btn btn-secondary" onClick={() => setActivePlanModal(null)}>
                Close
              </button>
              <button 
                className="btn btn-primary btn-lg"
                onClick={() => handleEnroll(activePlanModal)}
              >
                <span>Enroll in This Routine</span>
                <ChevronRight size={18} />
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
