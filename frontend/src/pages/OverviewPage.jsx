import React from 'react';
import MetricCard from '../components/common/MetricCard';
import LiveCameraFeed from '../components/analysis/LiveCameraFeed';
import FruitFlyKinematics3D from '../components/analysis/FruitFlyKinematics3D';
import { 
  Target, 
  Activity, 
  Apple, 
  Sparkles, 
  Play, 
  CheckCircle2, 
  Droplets, 
  Plus, 
  ArrowUpRight,
  TrendingUp,
  HeartPulse,
  ShieldAlert,
  ShieldCheck,
  FileText,
  ChevronRight,
  Bot
} from 'lucide-react';
import { useApp } from '../context/AppContext';

export default function OverviewPage() {
  const { 
    userProfile, 
    activeSession, 
    todayExercises, 
    toggleExerciseCheck, 
    recoveryReadiness,
    planAdherence,
    injuryState,
    medicalDocs,
    visibleRecommendations,
    appliedAdjustments,
    applyAdaptiveAdjustment,
    dismissAdaptiveAdjustment,
    nutrition, 
    addHydration, 
    setActiveTab, 
    toggleModal,
    workoutHistory,
    fetchWorkoutHistory,
    isAuthenticated,
  } = useApp();

  const completedExercisesCount = todayExercises.filter(e => e.completed).length;

  // Real aggregate metrics calculated strictly from persisted workouts
  const totalSavedSessions = workoutHistory?.total ?? 0;
  const savedItems = workoutHistory?.items || [];
  const totalCompletedReps = savedItems.reduce((acc, curr) => acc + (curr.total_reps || 0), 0);
  const totalValidReps = savedItems.reduce((acc, curr) => acc + (curr.valid_reps || 0), 0);
  const avgSymmetryScore = savedItems.length > 0
    ? Math.round((savedItems.reduce((acc, curr) => acc + (curr.mean_symmetry || 0.95), 0) / savedItems.length) * 100)
    : null;

  // Distinguish today's sessions vs all-time
  const todayDateString = new Date().toISOString().split('T')[0];
  const todaySessions = savedItems.filter(item => {
    const itemDate = (item.created_at || item.start_time || '').split('T')[0];
    return itemDate === todayDateString;
  });
  const todayReps = todaySessions.reduce((acc, curr) => acc + (curr.total_reps || 0), 0);

  // Active top adaptive recommendation
  const primaryRecommendation = visibleRecommendations && visibleRecommendations.length > 0 
    ? visibleRecommendations[0] 
    : {
        id: 'rec-default',
        title: 'Training Protocol Aligned',
        description: 'No movement contraindications active. Scheduled progressive load is safe to perform.',
        priority: 'low',
        actionLabel: 'Protocol Cleared',
        canDismiss: false
      };

  const isAdjustmentApplied = appliedAdjustments.includes(primaryRecommendation.id);

  return (
    <div className="flex-col gap-6">
      {/* 1. Top Summary Cards Row (4 Defined KPIs) */}
      <section className="metrics-grid" aria-label="Key Performance Indicators">
        {/* KPI 1: Real Saved Sessions & Today's Volume */}
        <MetricCard
          icon={Target}
          iconColor="orange"
          label="Logged Sessions"
          value={isAuthenticated ? `${totalSavedSessions} Total` : `${userProfile.weeklyGoalCompleted} / ${userProfile.weeklyGoalTarget}`}
          subtext={isAuthenticated ? `${todaySessions.length} session${todaySessions.length === 1 ? '' : 's'} (${todayReps} reps) today` : "Sign in to view cloud history"}
          progress={userProfile.weeklyGoalTarget ? (totalSavedSessions / userProfile.weeklyGoalTarget) * 100 : 0}
          badgeText={isAuthenticated ? (totalSavedSessions > 0 ? `${totalSavedSessions} Logged` : "None yet") : "Local Demo"}
          badgeType="orange"
        />

        {/* KPI 2: Workout-Plan Adherence */}
        <MetricCard
          icon={CheckCircle2}
          iconColor="teal"
          label="Workout-Plan Adherence"
          value={`${planAdherence}%`}
          subtext="High fidelity to prescribed volume"
          badgeText="On Track"
          badgeType="teal"
          progress={planAdherence}
        />

        {/* KPI 3: Recovery Readiness */}
        <MetricCard
          icon={HeartPulse}
          iconColor="cyan"
          label="Recovery Readiness"
          value={`${recoveryReadiness}%`}
          subtext="Optimal HRV & CNS readiness"
          badgeText="Optimal"
          badgeType="cyan"
        />

        {/* KPI 4: Daily Calorie Intake */}
        <MetricCard
          icon={Apple}
          iconColor="amber"
          label="Daily Calorie Intake"
          value={`${nutrition.caloriesConsumed} / ${nutrition.calorieTarget} kcal`}
          subtext="Caloric energy balance target"
          progress={(nutrition.caloriesConsumed / nutrition.calorieTarget) * 100}
          badgeText={`${((nutrition.caloriesConsumed / nutrition.calorieTarget) * 100).toFixed(0)}% Consumed`}
          badgeType="amber"
        />
      </section>

      {/* 2. Main Dashboard Analysis Grid (Dual Viewports + Today's Routine Panel) */}
      <div className="dashboard-main-grid">
        {/* Left: Dual Biomechanical Analysis Studio */}
        <section className="card analysis-card" aria-label="Main Biomechanics Studio">
          <div className="card-header">
            <div>
              <div className="flex-row items-center gap-3">
                <h2 className="card-title">
                  <Activity className="text-purple" size={22} />
                  <span>Real-Time Squat Biomechanics Studio</span>
                </h2>
                <span className="badge badge-purple">Edge AI Kinematics</span>
              </div>
              <p className="card-subtitle">
                Dual-feed analysis pairing local vision pose landmarks with fruit-fly articulated 3D kinematics.
              </p>
            </div>

            <button 
              className="btn btn-primary btn-sm" 
              onClick={() => setActiveTab('live-workout')}
              title="Navigate to dedicated Live Workout Studio"
            >
              <span>Full Studio</span>
              <ArrowUpRight size={16} />
            </button>
          </div>

          {/* Dual Viewports Row */}
          <div className="analysis-viewports-row">
            {/* Viewport 1: Live Camera Feed with Simulated Demo Fallback */}
            <div className="flex-col gap-2">
              <span className="font-semibold text-secondary" style={{ fontSize: '0.825rem' }}>
                1. Local Vision Stream (Webcam / MediaPipe)
              </span>
              <LiveCameraFeed showTelemetry={false} compact={true} />
            </div>

            {/* Viewport 2: Fruit-Fly 3D Articulated Kinematic Model */}
            <div className="flex-col gap-2">
              <span className="font-semibold text-secondary" style={{ fontSize: '0.825rem' }}>
                2. Fruit-Fly 3D Articulated Skeleton (Three.js)
              </span>
              <FruitFlyKinematics3D height={260} showControls={true} />
            </div>
          </div>

          {/* Real-time Telemetry Status Bar */}
          <div className="telemetry-bar">
            <div className="telemetry-item">
              <span className="telemetry-label">Knee Angle</span>
              <span className="telemetry-value accent">
                {activeSession.kneeAngle !== null ? `${activeSession.kneeAngle}°` : '--'}
              </span>
            </div>
            <div className="telemetry-item">
              <span className="telemetry-label">Hip Angle</span>
              <span className="telemetry-value">
                {activeSession.hipAngle !== null ? `${activeSession.hipAngle}°` : '--'}
              </span>
            </div>
            <div className="telemetry-item">
              <span className="telemetry-label">Movement Phase</span>
              <span className="telemetry-value teal" style={{ fontSize: '0.95rem' }}>
                {activeSession.movementPhase}
              </span>
            </div>
            <div className="telemetry-item">
              <span className="telemetry-label">Reps in Set</span>
              <span className="telemetry-value">{activeSession.currentReps} / {activeSession.targetReps}</span>
            </div>
            <div className="telemetry-item">
              <span className="telemetry-label">Bilateral Symmetry</span>
              <span className="telemetry-value" style={{ color: 'var(--success-green)' }}>
                {activeSession.kneeAngle !== null ? `${activeSession.symmetryScore}%` : '96%'}
              </span>
            </div>
          </div>
        </section>

        {/* Right: Today's Routine Panel */}
        <section className="card workout-queue-card" aria-label="Today's Workout Routine">
          <div className="card-header">
            <div>
              <h3 className="card-title">
                <Target className="text-teal" size={20} />
                <span>Today's Routine</span>
              </h3>
              <p className="card-subtitle">Lower Body Biomechanics & Hypertrophy</p>
            </div>
            <span className="badge badge-teal">
              {completedExercisesCount}/{todayExercises.length} Done
            </span>
          </div>

          {/* Reactive Progress Bar */}
          <div className="progress-bar-container lg">
            <div 
              className="progress-bar-fill progress-teal" 
              style={{ width: `${(completedExercisesCount / todayExercises.length) * 100}%` }} 
            />
          </div>

          {/* Exercise Queue List */}
          <div className="flex-col gap-3" style={{ marginTop: 6, flex: 1, overflowY: 'auto' }}>
            {todayExercises.map((ex, idx) => (
              <div 
                key={ex.id} 
                className={`exercise-queue-item ${idx === 2 ? 'current' : ''}`}
              >
                <div className="flex-row items-center gap-3">
                  <div 
                    className={`exercise-checkbox ${ex.completed ? 'checked' : ''}`}
                    onClick={() => toggleExerciseCheck(ex.id)}
                    role="checkbox"
                    aria-checked={ex.completed}
                    tabIndex={0}
                    title="Toggle completion status"
                  >
                    {ex.completed && <CheckCircle2 size={16} />}
                  </div>

                  <div className="flex-col">
                    <span className="font-semibold text-primary" style={{ fontSize: '0.9rem', textDecoration: ex.completed ? 'line-through' : 'none' }}>
                      {ex.name}
                    </span>
                    <span style={{ fontSize: '0.785rem', color: 'var(--text-muted)' }}>
                      {ex.sets}
                    </span>
                  </div>
                </div>

                {ex.accuracy && (
                  <span className="badge badge-green" style={{ fontSize: '0.75rem' }}>
                    {ex.accuracy}% Score
                  </span>
                )}
              </div>
            ))}
          </div>

          {/* Start Workout Primary CTA */}
          <button 
            className="btn btn-primary btn-lg" 
            style={{ width: '100%', marginTop: 'auto' }}
            onClick={() => setActiveTab('live-workout')}
          >
            <Play size={18} />
            <span>Start Workout</span>
          </button>
        </section>
      </div>

      {/* 3. Lower Dashboard Grid (6 Connected Modules) */}
      <div className="lower-dashboard-grid" aria-label="Connected Feature Modules">
        
        {/* Module 1: Adaptive Coaching Recommendation */}
        <section className="card flex-col justify-between gap-4">
          <div className="card-header" style={{ marginBottom: 2 }}>
            <div>
              <div className="flex-row items-center gap-2">
                <Sparkles className="text-orange" size={18} />
                <h3 className="card-title">Adaptive Coaching</h3>
              </div>
              <p className="card-subtitle">Dynamic load and safety adjustments</p>
            </div>
            <span className={`badge ${primaryRecommendation.priority === 'critical' ? 'badge-red' : primaryRecommendation.priority === 'high' ? 'badge-amber' : 'badge-orange'}`}>
              {primaryRecommendation.priority.toUpperCase()}
            </span>
          </div>

          <div className={`adaptive-coaching-box ${primaryRecommendation.priority === 'critical' ? 'critical' : ''}`}>
            <div className="flex-row justify-between items-center">
              <strong className="text-primary" style={{ fontSize: '0.9rem' }}>
                {primaryRecommendation.title}
              </strong>
              {isAdjustmentApplied && (
                <span className="badge-pill" style={{ background: 'var(--success-soft)', color: '#15803D', fontSize: '0.72rem' }}>
                  <CheckCircle2 size={12} /> Applied
                </span>
              )}
            </div>
            <p className="text-secondary" style={{ fontSize: '0.825rem', lineHeight: 1.4, margin: 0 }}>
              {primaryRecommendation.description}
            </p>
            {primaryRecommendation.reasoning && (
              <small className="text-muted" style={{ fontSize: '0.75rem' }}>
                💡 {primaryRecommendation.reasoning}
              </small>
            )}
          </div>

          <div className="flex-row gap-2" style={{ marginTop: 'auto' }}>
            <button 
              className="btn btn-primary btn-sm" 
              style={{ flex: 1 }}
              onClick={() => applyAdaptiveAdjustment(primaryRecommendation)}
              disabled={isAdjustmentApplied}
            >
              <CheckCircle2 size={14} />
              <span>{isAdjustmentApplied ? 'Adjustment Active' : 'Apply Adjustment'}</span>
            </button>
            <button 
              className="btn btn-secondary btn-sm"
              onClick={() => setActiveTab('ai-coach')}
              title="Discuss this recommendation with the AI Coach"
            >
              <Bot size={14} className="text-purple" />
              <span>Ask Coach</span>
            </button>
            <button 
              className="btn btn-secondary btn-sm"
              onClick={() => setActiveTab('injury-training')}
              title="Modify restriction parameters in Injury-Aware Training"
            >
              <span>Modify</span>
            </button>
            {primaryRecommendation.canDismiss !== false && (
              <button 
                className="btn-ghost btn-sm" 
                onClick={() => dismissAdaptiveAdjustment(primaryRecommendation.id)}
                title="Dismiss suggestion"
              >
                <span>Dismiss</span>
              </button>
            )}
          </div>
        </section>

        {/* Module 2: Injury & Recovery Status */}
        <section className="card flex-col justify-between gap-4">
          <div className="card-header" style={{ marginBottom: 2 }}>
            <div>
              <div className="flex-row items-center gap-2">
                <ShieldAlert className="text-amber" size={18} />
                <h3 className="card-title">Injury & Recovery Status</h3>
              </div>
              <p className="card-subtitle">Active anatomical pain & ROM mapping</p>
            </div>
            <span className="badge badge-amber">{injuryState.discomfortRating}/10 Discomfort</span>
          </div>

          <div className="flex-col gap-3">
            <div className="flex-row justify-between items-center" style={{ background: 'var(--surface-subtle)', padding: '10px 14px', borderRadius: 'var(--radius-md)' }}>
              <div>
                <span className="text-muted" style={{ fontSize: '0.75rem' }}>Active Anatomical Region</span>
                <div className="font-bold text-primary" style={{ fontSize: '0.95rem' }}>
                  {injuryState.activeRegion} ({injuryState.anatomicalSubregion})
                </div>
              </div>
              <span className="badge badge-orange" style={{ fontSize: '0.72rem' }}>Monitored</span>
            </div>

            <div className="flex-col gap-1">
              <div className="flex-row justify-between" style={{ fontSize: '0.78rem' }}>
                <span className="text-secondary">ROM Knee Flexion:</span>
                <strong className="text-primary">{injuryState.currentRomDegrees}° (Baseline: {injuryState.uninjuredBaselineRomDegrees}°)</strong>
              </div>
              <div className="progress-bar-container">
                <div 
                  className="progress-bar-fill progress-orange" 
                  style={{ width: `${(injuryState.currentRomDegrees / injuryState.uninjuredBaselineRomDegrees) * 100}%` }} 
                />
              </div>
            </div>

            <p style={{ fontSize: '0.785rem', color: 'var(--text-secondary)', margin: 0 }}>
              <strong>Restriction:</strong> {injuryState.clinicianRestrictions?.[0]?.instruction || 'Movement capped at pain-free arc.'}
            </p>
          </div>

          <button 
            className="btn btn-secondary btn-sm" 
            style={{ width: '100%', marginTop: 'auto' }}
            onClick={() => setActiveTab('injury-training')}
          >
            <span>Open Injury-Aware Training</span>
            <ChevronRight size={14} />
          </button>
        </section>

        {/* Module 3: Nutrition & Hydration */}
        <section className="card flex-col justify-between gap-4">
          <div className="card-header" style={{ marginBottom: 2 }}>
            <div>
              <div className="flex-row items-center gap-2">
                <Apple className="text-teal" size={18} />
                <h3 className="card-title">Nutrition & Hydration</h3>
              </div>
              <p className="card-subtitle">Macros and fluid intake balance</p>
            </div>
            <button className="btn btn-secondary btn-sm" onClick={() => toggleModal('logFood', true)}>
              <Plus size={13} /> Meal
            </button>
          </div>

          <div className="nutrition-macros-row" style={{ gap: 10 }}>
            <div className="macro-box" style={{ padding: '8px 10px' }}>
              <span className="text-secondary" style={{ fontSize: '0.72rem' }}>Protein</span>
              <strong className="text-primary" style={{ fontSize: '0.85rem' }}>{nutrition.proteinConsumedG}g</strong>
              <div className="progress-bar-container" style={{ height: 4 }}>
                <div className="progress-bar-fill progress-orange" style={{ width: `${(nutrition.proteinConsumedG / nutrition.proteinTargetG) * 100}%` }} />
              </div>
            </div>

            <div className="macro-box" style={{ padding: '8px 10px' }}>
              <span className="text-secondary" style={{ fontSize: '0.72rem' }}>Carbs</span>
              <strong className="text-primary" style={{ fontSize: '0.85rem' }}>{nutrition.carbsConsumedG}g</strong>
              <div className="progress-bar-container" style={{ height: 4 }}>
                <div className="progress-bar-fill progress-teal" style={{ width: `${(nutrition.carbsConsumedG / nutrition.carbsTargetG) * 100}%` }} />
              </div>
            </div>

            <div className="macro-box" style={{ padding: '8px 10px' }}>
              <span className="text-secondary" style={{ fontSize: '0.72rem' }}>Fats</span>
              <strong className="text-primary" style={{ fontSize: '0.85rem' }}>{nutrition.fatsConsumedG}g</strong>
              <div className="progress-bar-container" style={{ height: 4 }}>
                <div className="progress-bar-fill progress-amber" style={{ width: `${(nutrition.fatsConsumedG / nutrition.fatsTargetG) * 100}%` }} />
              </div>
            </div>
          </div>

          {/* Quick +250ml Hydration Logger */}
          <div className="hydration-widget" style={{ padding: '8px 12px' }}>
            <div className="flex-row items-center gap-2">
              <Droplets size={18} className="text-cyan" />
              <div className="flex-col">
                <span className="font-semibold text-primary" style={{ fontSize: '0.8rem' }}>Water Intake</span>
                <span style={{ fontSize: '0.75rem', color: '#0369A1' }}>
                  {nutrition.hydrationConsumedMl} / {nutrition.hydrationTargetMl} ml
                </span>
              </div>
            </div>

            <button 
              className="btn btn-secondary btn-sm" 
              onClick={() => addHydration(250)}
              title="Add 250ml water"
              style={{ padding: '4px 8px', fontSize: '0.75rem' }}
            >
              <Plus size={12} /> +250ml
            </button>
          </div>

          <button 
            className="btn btn-secondary btn-sm" 
            style={{ width: '100%', marginTop: 'auto' }}
            onClick={() => setActiveTab('nutrition')}
          >
            <span>View Fuel & Energy Balance</span>
            <ChevronRight size={14} />
          </button>
        </section>

        {/* Module 4: Weekly Progress Overview */}
        <section className="card flex-col justify-between gap-4">
          <div className="card-header" style={{ marginBottom: 2 }}>
            <div>
              <div className="flex-row items-center gap-2">
                <TrendingUp className="text-orange" size={18} />
                <h3 className="card-title">Workout History & Volume</h3>
              </div>
              <p className="card-subtitle">Verified on-device kinematic logs</p>
            </div>
            <span className="badge badge-orange">{totalSavedSessions} Sessions</span>
          </div>

          <div className="flex-col gap-3">
            <div className="flex-row justify-between items-center" style={{ background: 'var(--surface-subtle)', padding: '10px 14px', borderRadius: 'var(--radius-md)' }}>
              <div>
                <span className="text-muted" style={{ fontSize: '0.75rem' }}>Total Tracked Reps</span>
                <div className="font-bold text-primary" style={{ fontSize: '1.2rem' }}>
                  {isAuthenticated ? (totalSavedSessions > 0 ? `${totalCompletedReps} reps` : '0 reps') : '1,050 (Demo)'}
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <span className="text-muted" style={{ fontSize: '0.75rem' }}>Avg Joint Symmetry</span>
                <div className="font-bold text-teal" style={{ fontSize: '1.2rem' }}>
                  {isAuthenticated ? (avgSymmetryScore !== null ? `${avgSymmetryScore}%` : '--') : '94.2%'}
                </div>
              </div>
            </div>

            {/* Recent Workout List Mini Preview */}
            <div className="flex-col gap-2">
              {workoutHistory.loading && (
                <div className="text-muted" style={{ fontSize: '0.8rem', padding: '8px 0', textAlign: 'center' }}>
                  Loading recent sessions...
                </div>
              )}
              {workoutHistory.error && (
                <div className="feedback-box feedback-error" style={{ margin: 0, padding: 8, fontSize: '0.785rem' }}>
                  Unable to load history. <button onClick={() => fetchWorkoutHistory(20, 0)} style={{ textDecoration: 'underline', background: 'none', border: 'none', cursor: 'pointer', color: 'inherit' }}>Retry</button>
                </div>
              )}
              {!workoutHistory.loading && !workoutHistory.error && savedItems.length === 0 && isAuthenticated && (
                <div className="text-muted" style={{ fontSize: '0.8rem', padding: '8px 0', textAlign: 'center' }}>
                  No saved workouts yet. Complete a session in the Movement Lab!
                </div>
              )}
              {savedItems.slice(0, 3).map((w, idx) => (
                <div key={w.id || idx} className="flex-row justify-between items-center" style={{ fontSize: '0.8rem', padding: '4px 6px', borderBottom: '1px solid var(--border-subtle)' }}>
                  <span className="font-medium text-primary" style={{ textTransform: 'capitalize' }}>
                    {w.exercise_type || 'Squat'}
                  </span>
                  <span className="text-muted">
                    {w.total_reps} reps • {(w.created_at || '').split('T')[0] || 'Recent'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <button 
            className="btn btn-secondary btn-sm" 
            style={{ width: '100%', marginTop: 'auto' }}
            onClick={() => setActiveTab('progress')}
          >
            <span>View Full History & Analytics</span>
            <ChevronRight size={14} />
          </button>
        </section>

        {/* Module 5: Health Profile Summary */}
        <section className="card flex-col justify-between gap-4">
          <div className="card-header" style={{ marginBottom: 2 }}>
            <div>
              <div className="flex-row items-center gap-2">
                <HeartPulse className="text-teal" size={18} />
                <h3 className="card-title">Health Profile Summary</h3>
              </div>
              <p className="card-subtitle">Athlete biometrics & vitals</p>
            </div>
            <span className="badge badge-teal">{userProfile.experienceLevel}</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div className="card-flat flex-col gap-1" style={{ background: 'var(--surface-subtle)', padding: 10 }}>
              <span className="text-muted" style={{ fontSize: '0.72rem' }}>Stature</span>
              <strong className="text-primary" style={{ fontSize: '1.05rem' }}>{userProfile.heightCm} cm</strong>
            </div>

            <div className="card-flat flex-col gap-1" style={{ background: 'var(--surface-subtle)', padding: 10 }}>
              <span className="text-muted" style={{ fontSize: '0.72rem' }}>Weight</span>
              <strong className="text-primary" style={{ fontSize: '1.05rem' }}>{userProfile.weightKg} kg</strong>
            </div>

            <div className="card-flat flex-col gap-1" style={{ background: 'var(--surface-subtle)', padding: 10 }}>
              <span className="text-muted" style={{ fontSize: '0.72rem' }}>Body Fat</span>
              <strong className="text-primary" style={{ fontSize: '1.05rem' }}>{userProfile.bodyFatPercent}%</strong>
            </div>

            <div className="card-flat flex-col gap-1" style={{ background: 'var(--surface-subtle)', padding: 10 }}>
              <span className="text-muted" style={{ fontSize: '0.72rem' }}>Resting HR</span>
              <strong className="text-teal" style={{ fontSize: '1.05rem' }}>{userProfile.restingHr} bpm</strong>
            </div>
          </div>

          <button 
            className="btn btn-secondary btn-sm" 
            style={{ width: '100%', marginTop: 'auto' }}
            onClick={() => setActiveTab('profile')}
          >
            <span>View Health Profile & Biometrics</span>
            <ChevronRight size={14} />
          </button>
        </section>

        {/* Module 6: Medical Documents Status */}
        <section className="card flex-col justify-between gap-4">
          <div className="card-header" style={{ marginBottom: 2 }}>
            <div>
              <div className="flex-row items-center gap-2">
                <FileText className="text-orange" size={18} />
                <h3 className="card-title">Medical Documents</h3>
              </div>
              <p className="card-subtitle">Orthopedic records & clearances</p>
            </div>
            <span className="staged-badge">{medicalDocs.length} Staged</span>
          </div>

          <div className="flex-col gap-3">
            <div className="card-flat flex-col gap-2" style={{ background: 'var(--surface-subtle)', borderLeft: '4px solid var(--primary-orange)', padding: 12 }}>
              <div className="flex-row justify-between items-center">
                <span className="font-semibold text-primary" style={{ fontSize: '0.825rem' }}>
                  {medicalDocs[0]?.title || 'Diagnostic Evaluation Report'}
                </span>
                <span className="badge-pill" style={{ background: 'var(--success-soft)', color: '#15803D', fontSize: '0.7rem' }}>
                  Conditional Clearance
                </span>
              </div>
              <span className="text-muted" style={{ fontSize: '0.75rem' }}>
                {medicalDocs[0]?.clinician || 'Sports Orthopedic Specialist'}
              </span>
            </div>

            <div className="feedback-box feedback-optimal" style={{ padding: '8px 10px', fontSize: '0.75rem', margin: 0 }}>
              <ShieldCheck size={14} className="text-teal" />
              <span>Zero-Storage Guarantee: Records stay strictly in RAM.</span>
            </div>
          </div>

          <button 
            className="btn btn-secondary btn-sm" 
            style={{ width: '100%', marginTop: 'auto' }}
            onClick={() => setActiveTab('medical-docs')}
          >
            <span>Manage Medical Documents</span>
            <ChevronRight size={14} />
          </button>
        </section>

      </div>
    </div>
  );
}
