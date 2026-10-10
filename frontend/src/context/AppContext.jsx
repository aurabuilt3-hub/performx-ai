import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { generateAdaptiveRecommendations } from '../engine/adaptiveCoaching';
import { apiClient, authSession, ApiError } from '../services/api';

const AppContext = createContext();

export function AppProvider({ children }) {
  // Navigation - default to public landing page at '/' with URL sync
  const [activeTab, setActiveTab] = useState(() => {
    if (typeof window === 'undefined') return 'landing';
    const path = window.location.pathname;
    const hash = window.location.hash.replace('#', '');
    if (path.startsWith('/app') || hash === 'app' || hash === 'overview') {
      return 'overview';
    }
    const validTabs = [
      'overview', 'live-workout', 'kinematics', 'plans', 'library',
      'medical-docs', 'injury-training', 'nutrition', 'progress', 'profile', 'settings'
    ];
    if (validTabs.includes(hash)) {
      return hash;
    }
    return 'landing';
  });

  // Keep URL in sync with activeTab
  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (activeTab === 'landing') {
      if (window.location.hash || window.location.pathname.startsWith('/app')) {
        window.history.replaceState(null, '', '/');
      }
    } else {
      window.history.replaceState(null, '', `/#${activeTab}`);
    }
  }, [activeTab]);

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Authentication State
  const [isAuthenticated, setIsAuthenticated] = useState(() => authSession.isAuthenticated());
  const [authLoading, setAuthLoading] = useState(true);
  const [authError, setAuthError] = useState(null);

  // User Profile (Basic in-memory state, synced with backend when authenticated)
  const defaultProfile = {
    name: 'Athlete',
    email: '',
    avatar: 'AT',
    goal: 'general_fitness',
    experienceLevel: 'intermediate',
    equipment: ['bodyweight'],
    dietaryPreferences: [],
    knownAllergies: [],
    unconfirmedAllergies: [],
    heightCm: 175,
    weightKg: 70.0,
    bodyFatPercent: 15.0,
    restingHr: 60,
    streakDays: 0,
    weeklyGoalTarget: 5,
    weeklyGoalCompleted: 0,
    totalActiveMinutes: 0,
  };

  const [userProfile, setUserProfile] = useState(() => {
    const saved = localStorage.getItem('performx_profile_display');
    if (saved) {
      try { return { ...defaultProfile, ...JSON.parse(saved) }; } catch (e) { /* ignore */ }
    }
    return defaultProfile;
  });

  // Settings
  const [settings, setSettings] = useState(() => {
    const saved = localStorage.getItem('performx_settings');
    if (saved) {
      try { return JSON.parse(saved); } catch (e) { /* ignore */ }
    }
    return {
      unitSystem: 'metric', // metric | imperial
      localProcessingOnly: true, // 100% on-device guarantee
      soundCues: true,
      hapticFeedback: false,
      notifications: true,
      autoPauseWhenLost: true,
      kinematicVectorLines: true,
      trajectoryTrails: true,
    };
  });

  // Privacy Rule: Only persist non-sensitive display preference, never clinical annotations or health restrictions
  useEffect(() => {
    const displayOnly = {
      name: userProfile.name,
      avatar: userProfile.avatar,
      goal: userProfile.goal,
      experienceLevel: userProfile.experienceLevel,
      streakDays: userProfile.streakDays,
    };
    localStorage.setItem('performx_profile_display', JSON.stringify(displayOnly));
  }, [userProfile.name, userProfile.avatar, userProfile.goal, userProfile.experienceLevel, userProfile.streakDays]);

  useEffect(() => {
    localStorage.setItem('performx_settings', JSON.stringify(settings));
  }, [settings]);

  // Synchronize authenticated profile & health data from real backend
  const syncProfileFromBackend = useCallback(async () => {
    if (!authSession.isAuthenticated()) {
      setIsAuthenticated(false);
      return;
    }

    try {
      setAuthLoading(true);
      const [backendProfile, backendHealth] = await Promise.allSettled([
        apiClient.profile.get(),
        apiClient.healthProfile.get(),
      ]);

      if (backendProfile.status === 'fulfilled' && backendProfile.value) {
        const bp = backendProfile.value;
        const name = bp.display_name || 'Athlete';
        const avatar = name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || 'AT';

        setUserProfile(prev => ({
          ...prev,
          name,
          avatar,
          goal: bp.primary_goal || prev.goal,
          experienceLevel: bp.fitness_experience || prev.experienceLevel,
          equipment: bp.available_equipment || prev.equipment,
          dietaryPreferences: bp.dietary_preferences || prev.dietaryPreferences,
        }));
      }

      if (backendHealth.status === 'fulfilled' && backendHealth.value) {
        const hp = backendHealth.value;
        setUserProfile(prev => ({
          ...prev,
          heightCm: hp.height_cm ?? prev.heightCm,
          weightKg: hp.weight_kg ?? prev.weightKg,
          bodyFatPercent: hp.body_fat_percentage ?? prev.bodyFatPercent,
          restingHr: hp.resting_heart_rate ?? prev.restingHr,
          knownAllergies: hp.allergies || prev.knownAllergies,
        }));
      }

      setIsAuthenticated(true);
      setAuthError(null);
    } catch (err) {
      if (err.status === 401) {
        authSession.clearToken();
        setIsAuthenticated(false);
      } else {
        setAuthError(err.message);
      }
    } finally {
      setAuthLoading(false);
    }
  }, []);

  // Restore authenticated session on mount / reload
  useEffect(() => {
    if (authSession.isAuthenticated()) {
      syncProfileFromBackend();
    } else {
      setAuthLoading(false);
    }
  }, [syncProfileFromBackend]);

  // Auth Action: Log out and reset session
  const logout = useCallback(() => {
    authSession.clearToken();
    setIsAuthenticated(false);
    setUserProfile(defaultProfile);
    setWorkoutHistory({ items: [], total: 0, limit: 20, offset: 0, loading: false, error: null });
    localStorage.removeItem('performx_profile_display');
    setActiveTab('landing');
  }, [defaultProfile]);

  // Update Profile on Backend & in State
  const updateProfile = useCallback(async (profileData) => {
    // Normalize fitness_experience to match Pydantic pattern: ^(beginner|intermediate|advanced|elite)$
    let expLevel = (profileData.experienceLevel ?? userProfile.experienceLevel ?? 'intermediate').toLowerCase();
    if (!['beginner', 'intermediate', 'advanced', 'elite'].includes(expLevel)) {
      expLevel = 'intermediate';
    }

    const payload = {
      display_name: profileData.name ?? userProfile.name,
      units: settings.unitSystem || 'metric',
      fitness_experience: expLevel,
      primary_goal: profileData.goal ?? userProfile.goal,
      available_equipment: profileData.equipment ?? userProfile.equipment,
      dietary_preferences: profileData.dietaryPreferences ?? userProfile.dietaryPreferences,
    };

    if (authSession.isAuthenticated()) {
      const updated = await apiClient.profile.update(payload);
      const name = updated.display_name || payload.display_name;
      const avatar = name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || 'AT';

      setUserProfile(prev => ({
        ...prev,
        name,
        avatar,
        goal: updated.primary_goal || payload.primary_goal,
        experienceLevel: updated.fitness_experience || payload.fitness_experience,
        equipment: updated.available_equipment || payload.available_equipment,
      }));
      return updated;
    } else {
      // Unauthenticated local state preview
      setUserProfile(prev => ({ ...prev, ...profileData }));
      return payload;
    }
  }, [userProfile, settings.unitSystem]);

  // Update Health Profile on Backend & in State
  const updateHealthProfile = useCallback(async (healthData) => {
    const payload = {};
    if (healthData.heightCm !== undefined && healthData.heightCm !== null) payload.height_cm = Number(healthData.heightCm);
    if (healthData.weightKg !== undefined && healthData.weightKg !== null) payload.weight_kg = Number(healthData.weightKg);
    if (healthData.bodyFatPercent !== undefined && healthData.bodyFatPercent !== null) payload.body_fat_percentage = Number(healthData.bodyFatPercent);
    if (healthData.restingHr !== undefined && healthData.restingHr !== null) payload.resting_heart_rate = Math.round(Number(healthData.restingHr));
    if (healthData.allergies) payload.allergies = healthData.allergies;
    if (healthData.dietaryRestrictions) payload.dietary_restrictions = healthData.dietaryRestrictions;
    if (healthData.reportedInjuries) payload.reported_injuries = healthData.reportedInjuries;
    if (healthData.clinicianRestrictions) payload.clinician_restrictions = healthData.clinicianRestrictions;

    if (authSession.isAuthenticated()) {
      const updated = await apiClient.healthProfile.update(payload);
      setUserProfile(prev => ({
        ...prev,
        heightCm: updated.height_cm ?? prev.heightCm,
        weightKg: updated.weight_kg ?? prev.weightKg,
        bodyFatPercent: updated.body_fat_percentage ?? prev.bodyFatPercent,
        restingHr: updated.resting_heart_rate ?? prev.restingHr,
        knownAllergies: updated.allergies ?? prev.knownAllergies,
      }));
      return updated;
    } else {
      setUserProfile(prev => ({ ...prev, ...healthData }));
      return payload;
    }
  }, []);

  // Active Workout Session
  const [activeSession, setActiveSession] = useState({
    isActive: false,
    isPaused: false,
    backendSessionId: null,
    backendConnected: false,
    calibrationStatus: 'uncalibrated', // uncalibrated | calibrating | calibrated | failed
    calibrationScore: null,
    exerciseName: 'Barbell Back Squat',
    targetSets: 4,
    currentSet: 1,
    targetReps: 12,
    currentReps: 0,
    validReps: 0,
    completedRepAngles: [],
    formScore: null,
    movementPhase: 'Idle', // Idle, Eccentric, Bottom Hold, Concentric, Lockout
    kneeAngle: null,
    hipAngle: null,
    torsoAngle: null,
    symmetryScore: 96,
    repSpeed: '0.0 m/s',
    trackingConfidence: 0,
    trackingStatus: 'idle', // idle | tracking | unreliable | searching
    feedbackLevel: 'neutral', // optimal | warning | error | neutral
    feedbackMessage: 'Camera stream idle. Start camera for real-time tracking or explore simulated demo.',
    durationSeconds: 0,
    caloriesBurned: 0,
    startTime: null,
  });

  // Camera State
  const [cameraState, setCameraState] = useState({
    active: false,
    stream: null,
    deviceId: 'default',
    availableDevices: [],
    permissionGranted: false,
    isDemoMode: false,
    fps: 60,
  });

  // Movement Session Lifecycle Management (FastAPI backend sync)
  const startMovementSession = useCallback(async (customConfig = null) => {
    try {
      const res = await apiClient.sessions.create(customConfig);
      if (res && res.session_id) {
        setActiveSession(prev => ({
          ...prev,
          isActive: true,
          backendSessionId: res.session_id,
          backendConnected: true,
          calibrationStatus: 'uncalibrated',
          startTime: Date.now() / 1000.0,
          currentReps: 0,
          validReps: 0,
        }));
        return res.session_id;
      }
    } catch (err) {
      console.warn('Backend session creation unavailable; running local mode:', err.message);
      setActiveSession(prev => ({
        ...prev,
        isActive: true,
        backendSessionId: null,
        backendConnected: false,
        startTime: Date.now() / 1000.0,
      }));
    }
    return null;
  }, []);

  const resetMovementSession = useCallback(async () => {
    if (activeSession.backendSessionId) {
      try {
        await apiClient.sessions.reset(activeSession.backendSessionId);
      } catch (err) {
        console.warn('Backend session reset failed:', err.message);
      }
    }
    setActiveSession(prev => ({
      ...prev,
      currentReps: 0,
      validReps: 0,
      currentSet: 1,
      completedRepAngles: [],
      formScore: null,
      calibrationStatus: 'uncalibrated',
      calibrationScore: null,
    }));
  }, [activeSession.backendSessionId]);

  const endMovementSession = useCallback(async () => {
    let summary = null;
    if (activeSession.backendSessionId) {
      try {
        summary = await apiClient.sessions.terminate(activeSession.backendSessionId);
      } catch (err) {
        console.warn('Backend session termination failed:', err.message);
      }
    }
    setActiveSession(prev => ({
      ...prev,
      isActive: false,
      backendSessionId: null,
      backendConnected: false,
      trackingStatus: 'idle',
      kneeAngle: null,
      hipAngle: null,
      movementPhase: 'Idle',
    }));
    return summary;
  }, [activeSession.backendSessionId]);

  const calibrateStandingPose = useCallback(async (landmarksPayload) => {
    if (!activeSession.backendSessionId) {
      // Local calibration fallback
      setActiveSession(prev => ({
        ...prev,
        calibrationStatus: 'calibrated',
        calibrationScore: 100,
        feedbackMessage: 'Local standing posture calibrated.',
      }));
      return { success: true };
    }

    try {
      setActiveSession(prev => ({ ...prev, calibrationStatus: 'calibrating' }));
      const res = await apiClient.sessions.calibrateLandmarks(activeSession.backendSessionId, landmarksPayload);
      if (res && res.calibrated) {
        setActiveSession(prev => ({
          ...prev,
          calibrationStatus: 'calibrated',
          calibrationScore: res.calibration_score ?? 100,
          feedbackLevel: 'optimal',
          feedbackMessage: 'Standing calibration locked. Ready for repetitions.',
        }));
        return res;
      } else {
        setActiveSession(prev => ({
          ...prev,
          calibrationStatus: 'failed',
          feedbackLevel: 'warning',
          feedbackMessage: res?.message || 'Calibration did not meet posture requirements. Stand straight and face camera.',
        }));
        return res;
      }
    } catch (err) {
      setActiveSession(prev => ({
        ...prev,
        calibrationStatus: 'failed',
        feedbackLevel: 'error',
        feedbackMessage: `Calibration error: ${err.message}`,
      }));
      throw err;
    }
  }, [activeSession.backendSessionId]);

  // Workout Summary Persistence & History
  const [workoutHistory, setWorkoutHistory] = useState({
    items: [],
    total: 0,
    limit: 20,
    offset: 0,
    loading: false,
    error: null,
  });

  const fetchWorkoutHistory = useCallback(async (limit = 20, offset = 0) => {
    if (!authSession.isAuthenticated()) {
      setWorkoutHistory(prev => ({ ...prev, items: [], total: 0, loading: false, error: null }));
      return { items: [], total: 0 };
    }

    setWorkoutHistory(prev => ({ ...prev, loading: true, error: null }));
    try {
      const res = await apiClient.workouts.list(limit, offset);
      const items = res?.items || [];
      const total = res?.total || items.length;

      setWorkoutHistory({
        items,
        total,
        limit,
        offset,
        loading: false,
        error: null,
      });

      // Synchronize completed session count with userProfile
      setUserProfile(prev => ({
        ...prev,
        weeklyGoalCompleted: Math.min(prev.weeklyGoalTarget, total),
      }));

      return res;
    } catch (err) {
      console.warn('Failed to fetch workout history:', err.message);
      setWorkoutHistory(prev => ({
        ...prev,
        loading: false,
        error: err.message,
      }));
      throw err;
    }
  }, []);

  const saveWorkoutSession = useCallback(async (savePayload) => {
    if (!authSession.isAuthenticated()) {
      throw new ApiError('Authentication required to save workouts to persistent history.', {
        status: 401,
        code: 'UNAUTHORIZED',
        endpoint: '/api/v1/workouts',
      });
    }

    const saved = await apiClient.workouts.save(savePayload);
    // Refresh workout history in background after successful save
    fetchWorkoutHistory(20, 0).catch(() => {});
    return saved;
  }, [fetchWorkoutHistory]);

  // Central Camera Stop Handler ensuring hardware track release
  const stopCameraStream = () => {
    if (cameraState.stream) {
      cameraState.stream.getTracks().forEach(track => {
        try { track.stop(); } catch (e) { /* ignore */ }
      });
    }
    setCameraState(prev => ({
      ...prev,
      active: false,
      stream: null,
      isDemoMode: false,
    }));
    setActiveSession(prev => ({
      ...prev,
      trackingStatus: 'idle',
      kneeAngle: null,
      hipAngle: null,
      movementPhase: 'Idle',
      feedbackLevel: 'neutral',
      feedbackMessage: 'Camera stream stopped. Video processing inactive.',
      trackingConfidence: 0,
    }));
  };

  // Workout Checklist (Today's Routine)
  const [todayExercises, setTodayExercises] = useState([
    { id: 1, name: 'Barbell Back Squat', sets: '4 sets × 10-12 reps', completed: true, accuracy: 94 },
    { id: 2, name: 'Romanian Deadlift', sets: '3 sets × 8-10 reps', completed: true, accuracy: 92 },
    { id: 3, name: 'Bulgarian Split Squat', sets: '3 sets × 12 reps', completed: false, accuracy: null },
    { id: 4, name: 'Standing Calf Raise', sets: '4 sets × 15 reps', completed: false, accuracy: null },
    { id: 5, name: 'Hanging Leg Raise', sets: '3 sets × 15 reps', completed: false, accuracy: null },
  ]);

  // Enrolled Training Plan & Recommendations State
  const [enrolledPlan, setEnrolledPlan] = useState({
    id: 'plan-1',
    title: 'Hypertrophy Biomechanics 101',
    category: 'Hypertrophy',
    difficulty: 'Intermediate',
    week: 2,
    totalWeeks: 4,
    completedSessions: 6,
    totalSessions: 16
  });
  const [plansLoading, setPlansLoading] = useState(false);
  const [plansError, setPlansError] = useState(null);

  const fetchActivePlan = useCallback(async () => {
    if (!authSession.isAuthenticated()) return null;
    try {
      setPlansLoading(true);
      const plan = await apiClient.plans.getActive();
      if (plan && plan.title) {
        setEnrolledPlan(prev => ({
          ...prev,
          id: plan.id || prev.id,
          title: plan.title,
          category: plan.title.includes('Strength') ? 'Strength' : (plan.title.includes('Mobility') ? 'Mobility' : 'Hypertrophy'),
          difficulty: plan.target_experience ? (plan.target_experience.charAt(0).toUpperCase() + plan.target_experience.slice(1)) : prev.difficulty,
          version: plan.version || 1,
        }));
        if (plan.exercises && plan.exercises.length > 0) {
          const newRoutine = plan.exercises.map((ex, idx) => ({
            id: idx + 1,
            name: ex.name,
            sets: `${ex.target_sets} sets × ${ex.target_reps} reps`,
            completed: false,
            accuracy: null,
          }));
          setTodayExercises(newRoutine);
        }
      }
      setPlansError(null);
      return plan;
    } catch (err) {
      console.warn('Failed to fetch active workout plan:', err.message);
      setPlansError(err.message);
      return null;
    } finally {
      setPlansLoading(false);
    }
  }, []);

  const enrollInPlan = useCallback(async (plan) => {
    // 1. Update in-memory state immediately for responsive UX
    setEnrolledPlan({
      id: plan.id,
      title: plan.title,
      category: plan.category,
      difficulty: plan.difficulty,
      week: 1,
      totalWeeks: parseInt(plan.duration) || 4,
      completedSessions: 0,
      totalSessions: (parseInt(plan.duration) || 4) * (parseInt(plan.daysPerWeek) || 4)
    });
    // Set first day's exercises into today's routine if available
    let exerciseList = [];
    if (plan.schedule && plan.schedule[0]?.exercises) {
      const newRoutine = plan.schedule[0].exercises.map((ex, idx) => ({
        id: idx + 1,
        name: ex.name,
        sets: `${ex.sets} sets × ${ex.reps} reps`,
        completed: false,
        accuracy: null
      }));
      setTodayExercises(newRoutine);
      exerciseList = plan.schedule[0].exercises.map((ex, idx) => ({
        exercise_id: `ex_${idx + 1}`,
        name: ex.name,
        target_sets: Math.max(1, Math.min(20, parseInt(ex.sets) || 3)),
        target_reps: Math.max(1, Math.min(100, parseInt(ex.reps) || 10)),
        target_load_kg: null,
        rest_seconds: 60,
        notes: ex.substitutionNote || "",
      }));
    }

    // 2. Persist to real backend if authenticated
    if (authSession.isAuthenticated()) {
      let expLevel = (plan.difficulty || userProfile.experienceLevel || 'intermediate').toLowerCase();
      if (!['beginner', 'intermediate', 'advanced', 'elite'].includes(expLevel)) expLevel = 'intermediate';

      const planPayload = {
        title: plan.title,
        description: plan.desc || `Personalized ${plan.category} plan`,
        is_active: true,
        version: 1,
        exercises: exerciseList,
        equipment_constraints: Array.isArray(userProfile.equipment) ? userProfile.equipment : [],
        target_experience: expLevel,
      };
      try {
        const saved = await apiClient.plans.save(planPayload);
        return saved;
      } catch (err) {
        console.warn('Backend plan save failed; retained locally:', err.message);
      }
    }
    return plan;
  }, [userProfile]);

  // Executive Readiness & Adherence Metrics
  const [recoveryReadiness, setRecoveryReadiness] = useState(88); // 88% Optimal
  const [planAdherence, setPlanAdherence] = useState(92); // 92% On Track

  // Medical Documents State (In-Memory Staged - NEVER in localStorage)
  const [medicalDocs, setMedicalDocs] = useState([
    {
      id: 'doc-1',
      title: 'Left Knee MRI & Orthopedic Diagnostic Evaluation',
      category: 'MRI / Diagnostic Imaging',
      documentDate: '2026-09-18',
      clinician: 'Dr. Rachel Vance, MD (Sports Orthopedics)',
      notes: 'Mild patellofemoral cartilage tracking irritation. Avoid loaded knee flexion past 90° for 4 weeks.',
      fileName: 'Knee_MRI_Evaluation_Report.pdf',
      fileSize: '3.4 MB',
      fileType: 'application/pdf',
      status: 'staged', // Staged in memory awaiting backend upload
      previewUrl: null,
      restrictions: [
        {
          id: 'res-1',
          anatomicalRegion: 'Left Knee',
          instruction: 'Limit knee flexion under load to ≤95°; avoid rapid ballistic descent.',
          substitution: 'Box Squat to 95° Bench or Leg Press',
          documentDate: 'Sep 18, 2026'
        }
      ]
    }
  ]);
  const [docsLoading, setDocsLoading] = useState(false);
  const [docsError, setDocsError] = useState(null);

  const fetchDocuments = useCallback(async () => {
    if (!authSession.isAuthenticated()) return [];
    try {
      setDocsLoading(true);
      const res = await apiClient.documents.list();
      const items = res?.items || [];
      if (items.length > 0) {
        const mapped = items.map(d => ({
          id: d.id,
          title: d.description || d.file_name,
          category: d.document_category || 'Clinical Record',
          documentDate: d.created_at ? d.created_at.split('T')[0] : '2026-10-10',
          clinician: 'Authorized Medical Record',
          notes: d.description || `Uploaded file: ${d.file_name}`,
          fileName: d.file_name,
          fileSize: `${((d.file_size_bytes || 0) / (1024 * 1024)).toFixed(1)} MB`,
          fileType: d.mime_type,
          status: 'confirmed',
          previewUrl: `/api/v1/documents/content/${d.id}`,
          restrictions: []
        }));
        // Merge with existing local staged docs
        setMedicalDocs(prev => {
          const staged = prev.filter(p => p.status === 'staged');
          return [...staged, ...mapped];
        });
      }
      setDocsError(null);
      return items;
    } catch (err) {
      console.warn('Failed to fetch medical documents:', err.message);
      setDocsError(err.message);
      return [];
    } finally {
      setDocsLoading(false);
    }
  }, []);

  const addMedicalDoc = useCallback(async (doc, fileBlob = null) => {
    // Stage immediately in local state
    setMedicalDocs(prev => [doc, ...prev]);

    // If authenticated and real file metadata present, execute presigned upload flow
    if (authSession.isAuthenticated() && doc.fileName && doc.fileSizeRaw) {
      const allowedMimes = ['application/pdf', 'image/png', 'image/jpeg'];
      const mime = allowedMimes.includes(doc.fileType) ? doc.fileType : 'application/pdf';
      const presignMeta = {
        file_name: doc.fileName,
        file_size_bytes: doc.fileSizeRaw,
        mime_type: mime,
        document_category: doc.category || 'general',
        description: doc.title || '',
      };
      try {
        const presign = await apiClient.documents.presignUpload(presignMeta);
        // Confirm metadata in catalog
        const confirmPayload = {
          storage_path: presign.storage_path,
          file_name: doc.fileName,
          file_size_bytes: doc.fileSizeRaw,
          mime_type: mime,
          document_category: doc.category || 'general',
          description: doc.title || '',
        };
        const confirmed = await apiClient.documents.confirmUpload(confirmPayload);
        // Mark confirmed in local state
        setMedicalDocs(prev => prev.map(d => d.id === doc.id ? { ...d, id: confirmed.id, status: 'confirmed' } : d));
        return confirmed;
      } catch (err) {
        console.warn('Document backend upload confirmation failed; kept staged:', err.message);
      }
    }
    return doc;
  }, []);

  const removeMedicalDoc = useCallback(async (id) => {
    setMedicalDocs(prev => {
      const doc = prev.find(d => d.id === id);
      if (doc && doc.previewUrl && doc.previewUrl.startsWith('blob:')) {
        try { URL.revokeObjectURL(doc.previewUrl); } catch (e) { /* ignore */ }
      }
      return prev.filter(d => d.id !== id);
    });

    if (authSession.isAuthenticated() && !id.startsWith('doc-')) {
      try {
        await apiClient.documents.delete(id);
      } catch (err) {
        console.warn('Failed to delete document from backend:', err.message);
      }
    }
  }, []);

  // Injury-Aware Training State
  const [injuryState, setInjuryState] = useState({
    activeRegion: 'Left Knee',
    anatomicalSubregion: 'Patellofemoral Joint',
    discomfortRating: 4, // 1 to 10 scale
    onsetDate: '2026-09-15',
    symptoms: 'Anterior patellar pressure at deep squat turnaround; asymptomatic during normal walking.',
    clinicianClearance: 'Conditional (Modified Range of Motion)',
    currentRomDegrees: 92,
    uninjuredBaselineRomDegrees: 125,
    primarySubstitution: 'Box Squat to 95° Bench or Glute Bridge',
    clinicianRestrictions: [
      {
        id: 'cr-1',
        anatomicalRegion: 'Left Knee',
        instruction: 'Cap loaded knee flexion at 95°; replace barbell back squat with box squat or tempo leg press.',
        substitution: 'Box Squat to 95° Bench',
        documentDate: 'Sep 18, 2026'
      }
    ],
    recoveryMilestones: [
      { milestone: 'Swelling resolved & full unweighted extension', completed: true },
      { milestone: 'Pain-free box squat at 95° with light load', completed: true },
      { milestone: 'Clinician clearance for unassisted parallel squat (≤90°)', completed: false }
    ],
    checkInHistory: [
      { date: 'Oct 08', rating: 5, note: 'Mild stiffness post-workout' },
      { date: 'Oct 09', rating: 4, note: 'Improving with warm-up mobility' },
      { date: 'Oct 10 (Today)', rating: 4, note: 'Stable; box squats feel comfortable' }
    ]
  });
  const [recoveryLoading, setRecoveryLoading] = useState(false);
  const [recoveryError, setRecoveryError] = useState(null);

  const fetchRecoveryHistory = useCallback(async () => {
    if (!authSession.isAuthenticated()) return [];
    try {
      setRecoveryLoading(true);
      const res = await apiClient.recovery.getHistory();
      const items = res?.items || [];
      if (items.length > 0) {
        const historyMapped = items.map(item => ({
          id: item.id,
          date: item.recorded_at ? item.recorded_at.split('T')[0] : 'Today',
          rating: item.discomfort_score,
          note: item.notes || item.symptoms || 'Recovery check-in',
          area: item.affected_area,
          adherence: item.exercise_adherence_score,
        }));
        setInjuryState(prev => ({
          ...prev,
          discomfortRating: items[0].discomfort_score,
          checkInHistory: historyMapped,
        }));
      }
      setRecoveryError(null);
      return items;
    } catch (err) {
      console.warn('Failed to fetch recovery history:', err.message);
      setRecoveryError(err.message);
      return [];
    } finally {
      setRecoveryLoading(false);
    }
  }, []);

  const updateInjuryState = useCallback((updates) => {
    setInjuryState(prev => ({ ...prev, ...updates }));
  }, []);

  const logRecoveryCheckIn = useCallback(async (rating, note = '') => {
    // 1. Immediate UI update
    setInjuryState(prev => ({
      ...prev,
      discomfortRating: rating,
      checkInHistory: [
        { date: 'Just now', rating, note: note || 'Self-reported check-in' },
        ...prev.checkInHistory
      ]
    }));

    // 2. Persist to real backend if authenticated
    if (authSession.isAuthenticated()) {
      const payload = {
        affected_area: injuryState.activeRegion || 'General',
        discomfort_score: Math.max(0, Math.min(10, Math.round(rating))),
        symptoms: injuryState.symptoms || '',
        exercise_adherence_score: planAdherence > 0 ? (planAdherence / 100.0) : 1.0,
        notes: note || '',
      };
      try {
        const saved = await apiClient.recovery.log(payload);
        return saved;
      } catch (err) {
        console.warn('Backend recovery logging failed; maintained locally:', err.message);
      }
    }
    return { discomfort_score: rating, notes: note };
  }, [injuryState.activeRegion, injuryState.symptoms, planAdherence]);

  // Adaptive Recommendations & Decision Updates
  const [backendRecommendations, setBackendRecommendations] = useState([]);
  const [recommendationsLoading, setRecommendationsLoading] = useState(false);

  const fetchRecommendations = useCallback(async () => {
    if (!authSession.isAuthenticated()) return [];
    try {
      setRecommendationsLoading(true);
      const res = await apiClient.recommendations.list();
      const items = res?.items || [];
      setBackendRecommendations(items);
      return items;
    } catch (err) {
      console.warn('Failed to fetch recommendations:', err.message);
      return [];
    } finally {
      setRecommendationsLoading(false);
    }
  }, []);
  const [dismissedRecommendationIds, setDismissedRecommendationIds] = useState([]);
  const [appliedAdjustments, setAppliedAdjustments] = useState([]);

  // Generate dynamic recommendations using adaptiveCoaching engine
  const activeClinicianRestrictions = injuryState.clinicianRestrictions || [];
  const allAdaptiveRecommendations = generateAdaptiveRecommendations({
    injuryState,
    clinicianRestrictions: activeClinicianRestrictions,
    recoveryReadiness,
    planAdherence,
    activeSession
  });

  const visibleRecommendations = allAdaptiveRecommendations.filter(
    rec => !dismissedRecommendationIds.includes(rec.id)
  );

  // Nutrition State & Backend Synchronization
  const [nutrition, setNutrition] = useState({
    calorieTarget: 2400,
    caloriesConsumed: 1840,
    proteinTargetG: 180,
    proteinConsumedG: 165,
    carbsTargetG: 240,
    carbsConsumedG: 195,
    fatsTargetG: 65,
    fatsConsumedG: 54,
    hydrationTargetMl: 3000,
    hydrationConsumedMl: 2250,
    meals: [
      { id: 'm1', name: 'Avocado Toast & Egg Whites', time: '08:30 AM', calories: 480, p: 38, c: 45, f: 14, type: 'Breakfast' },
      { id: 'm2', name: 'Grilled Chicken Quinoa Bowl', time: '01:15 PM', calories: 690, p: 58, c: 75, f: 18, type: 'Lunch' },
      { id: 'm3', name: 'Greek Yogurt with Blueberries', time: '04:30 PM', calories: 220, p: 24, c: 22, f: 4, type: 'Pre-Workout' },
      { id: 'm4', name: 'Atlantic Salmon & Asparagus', time: '07:45 PM', calories: 450, p: 45, c: 53, f: 18, type: 'Dinner' },
    ],
  });
  const [nutritionLoading, setNutritionLoading] = useState(false);
  const [nutritionError, setNutritionError] = useState(null);

  const fetchNutritionToday = useCallback(async () => {
    if (!authSession.isAuthenticated()) return null;
    try {
      setNutritionLoading(true);
      const nlog = await apiClient.nutrition.getToday();
      if (nlog) {
        setNutrition(prev => ({
          ...prev,
          caloriesConsumed: nlog.calories_consumed || prev.caloriesConsumed,
          proteinConsumedG: nlog.protein_g || prev.proteinConsumedG,
          carbsConsumedG: nlog.carbs_g || prev.carbsConsumedG,
          fatsConsumedG: nlog.fat_g || prev.fatsConsumedG,
          hydrationConsumedMl: nlog.water_ml || prev.hydrationConsumedMl,
          meals: (nlog.meals && nlog.meals.length > 0) ? nlog.meals.map((m, idx) => ({
            id: m.id || `m_${idx}`,
            name: m.name,
            time: m.time || '12:00 PM',
            calories: m.calories,
            p: m.protein_g ?? m.p ?? 0,
            c: m.carbs_g ?? m.c ?? 0,
            f: m.fat_g ?? m.f ?? 0,
            type: m.type || 'Meal',
            allergens: Array.isArray(m.allergens) ? m.allergens.join(', ') : (m.allergens || 'None declared'),
          })) : prev.meals,
        }));
      }
      setNutritionError(null);
      return nlog;
    } catch (err) {
      console.warn('Failed to fetch nutrition log:', err.message);
      setNutritionError(err.message);
      return null;
    } finally {
      setNutritionLoading(false);
    }
  }, []);

  const syncNutritionToBackend = useCallback(async (updatedNutrition) => {
    if (!authSession.isAuthenticated()) return;
    const formattedMeals = (updatedNutrition.meals || []).map(m => ({
      name: m.name,
      calories: Math.max(0, Math.round(m.calories || 0)),
      protein_g: Math.max(0, Number(m.p || m.protein_g || 0)),
      carbs_g: Math.max(0, Number(m.c || m.carbs_g || 0)),
      fat_g: Math.max(0, Number(m.f || m.fat_g || 0)),
      ingredients: Array.isArray(m.ingredients) ? m.ingredients : [],
      allergens: Array.isArray(m.allergens) ? m.allergens : (m.allergens ? [m.allergens] : []),
    }));

    const payload = {
      calories_consumed: Math.max(0, Math.round(updatedNutrition.caloriesConsumed || 0)),
      protein_g: Math.max(0, Number(updatedNutrition.proteinConsumedG || 0)),
      carbs_g: Math.max(0, Number(updatedNutrition.carbsConsumedG || 0)),
      fat_g: Math.max(0, Number(updatedNutrition.fatsConsumedG || 0)),
      water_ml: Math.max(0, Math.round(updatedNutrition.hydrationConsumedMl || 0)),
      meals: formattedMeals,
      allergen_verification_status: 'UNKNOWN',
    };
    try {
      await apiClient.nutrition.updateToday(payload);
    } catch (err) {
      console.warn('Nutrition background sync failed; kept locally:', err.message);
    }
  }, []);

  const addHydration = useCallback((amountMl = 250) => {
    setNutrition(prev => {
      const next = {
        ...prev,
        hydrationConsumedMl: Math.min(prev.hydrationConsumedMl + amountMl, 20000)
      };
      syncNutritionToBackend(next);
      return next;
    });
  }, [syncNutritionToBackend]);

  const addMeal = useCallback((newMeal) => {
    setNutrition(prev => {
      const next = {
        ...prev,
        caloriesConsumed: prev.caloriesConsumed + newMeal.calories,
        proteinConsumedG: prev.proteinConsumedG + (newMeal.p || 0),
        carbsConsumedG: prev.carbsConsumedG + (newMeal.c || 0),
        fatsConsumedG: prev.fatsConsumedG + (newMeal.f || 0),
        meals: [newMeal, ...prev.meals],
      };
      syncNutritionToBackend(next);
      return next;
    });
  }, [syncNutritionToBackend]);

  // Privacy & Explicit Consents
  const [privacyConsent, setPrivacyConsent] = useState({
    camera_processing_consent: false,
    document_processing_consent: false,
    data_analytics_consent: false,
  });

  const fetchPrivacyConsent = useCallback(async () => {
    if (!authSession.isAuthenticated()) return null;
    try {
      const consent = await apiClient.privacy.getConsent();
      if (consent) {
        setPrivacyConsent({
          camera_processing_consent: !!consent.camera_processing_consent,
          document_processing_consent: !!consent.document_processing_consent,
          data_analytics_consent: !!consent.data_analytics_consent,
        });
      }
      return consent;
    } catch (err) {
      console.warn('Failed to fetch privacy consents:', err.message);
      return null;
    }
  }, []);

  const updatePrivacyConsent = useCallback(async (consents) => {
    setPrivacyConsent(prev => ({ ...prev, ...consents }));
    if (authSession.isAuthenticated()) {
      try {
        const updated = await apiClient.privacy.updateConsent({
          camera_processing_consent: !!consents.camera_processing_consent,
          document_processing_consent: !!consents.document_processing_consent,
          data_analytics_consent: !!consents.data_analytics_consent,
        });
        return updated;
      } catch (err) {
        console.warn('Backend privacy consent update failed; kept locally:', err.message);
      }
    }
    return consents;
  }, []);

  const exportAllData = useCallback(async () => {
    if (authSession.isAuthenticated()) {
      try {
        const archive = await apiClient.privacy.exportData();
        return archive;
      } catch (err) {
        console.warn('Backend data export failed, falling back to local snapshot:', err.message);
      }
    }
    return {
      app: 'PERFORMX Biomechanics',
      exportDate: new Date().toISOString(),
      athlete: userProfile,
      settings,
      nutritionSummary: nutrition,
      injuryState,
    };
  }, [userProfile, settings, nutrition, injuryState]);

  const deleteAccount = useCallback(async () => {
    if (authSession.isAuthenticated()) {
      await apiClient.privacy.deleteAccount();
    }
    logout();
  }, [logout]);

  const applyAdaptiveAdjustment = useCallback(async (rec) => {
    setAppliedAdjustments(prev => [...prev, rec.id]);
    if (rec.suggestedExerciseSub) {
      setTodayExercises(prev => prev.map(ex => {
        if (ex.name === 'Barbell Back Squat') {
          return {
            ...ex,
            name: rec.suggestedExerciseSub,
            sets: '4 sets × 10 reps (Conservative Depth)',
          };
        }
        return ex;
      }));
    }
    if (authSession.isAuthenticated() && !rec.id.startsWith('rec-local-')) {
      try {
        await apiClient.recommendations.updateStatus(rec.id, 'applied');
      } catch (err) {
        console.warn('Backend recommendation update failed:', err.message);
      }
    }
  }, []);

  const dismissAdaptiveAdjustment = useCallback(async (id) => {
    setDismissedRecommendationIds(prev => [...prev, id]);
    if (authSession.isAuthenticated() && !id.startsWith('rec-local-')) {
      try {
        await apiClient.recommendations.updateStatus(id, 'dismissed');
      } catch (err) {
        console.warn('Backend recommendation dismissal failed:', err.message);
      }
    }
  }, []);

  // Modals
  const [modalState, setModalState] = useState({
    onboarding: false,
    auth: false,
    completion: false,
    logFood: false,
    editProfile: false,
    exerciseDetail: null,
  });

  const toggleModal = (modalName, value = null) => {
    setModalState(prev => ({
      ...prev,
      [modalName]: value !== null ? value : !prev[modalName]
    }));
  };

  const toggleExerciseCheck = (id) => {
    setTodayExercises(prev => prev.map(ex => {
      if (ex.id === id) {
        return { ...ex, completed: !ex.completed, accuracy: !ex.completed ? 95 : null };
      }
      return ex;
    }));
  };

  return (
    <AppContext.Provider value={{
      activeTab,
      setActiveTab,
      sidebarCollapsed,
      setSidebarCollapsed,
      mobileMenuOpen,
      setMobileMenuOpen,
      userProfile,
      setUserProfile,
      settings,
      setSettings,
      activeSession,
      setActiveSession,
      cameraState,
      setCameraState,
      stopCameraStream,
      todayExercises,
      toggleExerciseCheck,
      enrolledPlan,
      enrollInPlan,
      recoveryReadiness,
      setRecoveryReadiness,
      planAdherence,
      setPlanAdherence,
      medicalDocs,
      addMedicalDoc,
      removeMedicalDoc,
      injuryState,
      updateInjuryState,
      logRecoveryCheckIn,
      visibleRecommendations,
      appliedAdjustments,
      applyAdaptiveAdjustment,
      dismissAdaptiveAdjustment,
      nutrition,
      setNutrition,
      addHydration,
      addMeal,
      modalState,
      toggleModal,
      isAuthenticated,
      authLoading,
      authError,
      syncProfileFromBackend,
      updateProfile,
      updateHealthProfile,
      startMovementSession,
      resetMovementSession,
      endMovementSession,
      calibrateStandingPose,
      workoutHistory,
      fetchWorkoutHistory,
      saveWorkoutSession,
      fetchActivePlan,
      plansLoading,
      plansError,
      fetchRecoveryHistory,
      recoveryLoading,
      recoveryError,
      fetchRecommendations,
      backendRecommendations,
      fetchNutritionToday,
      nutritionLoading,
      nutritionError,
      fetchDocuments,
      docsLoading,
      docsError,
      privacyConsent,
      fetchPrivacyConsent,
      updatePrivacyConsent,
      exportAllData,
      deleteAccount,
      logout,
    }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}
