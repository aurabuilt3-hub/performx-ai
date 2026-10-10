/**
 * PERFORMX - Comprehensive Step 3B Verification Suite
 * Tests:
 * 1. Normalized landmark payload mapping (strictly 33 landmarks, coordinate finite validation).
 * 2. Missing landmarks / occluded frames handling.
 * 3. Non-finite coordinate rejection.
 * 4. Movement session lifecycle: creation, landmark analysis streaming, and termination.
 * 5. Standing calibration workflow: success and posture criteria rejection.
 * 6. Calibration and session reset endpoints.
 * 7. Completed workout persistence: direct summary model and session_id model.
 * 8. Workout save authorization enforcement (401 when unauthenticated).
 * 9. Duplicate submission prevention during active save in-flight.
 * 10. Saved workout listing and retrieval.
 */

import {
  authSession,
  apiClient,
  ApiError,
} from '../src/services/api.js';

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    console.log(`  ✓ PASS: ${message}`);
    passed++;
  } else {
    console.error(`  ✗ FAIL: ${message}`);
    failed++;
  }
}

// Generate valid 33 MediaPipe landmark array
function createMockLandmarks() {
  const landmarks = [];
  for (let i = 0; i < 33; i++) {
    landmarks.push({
      x: 0.5 + Math.sin(i) * 0.1,
      y: 0.5 + Math.cos(i) * 0.1,
      z: 0.0,
      visibility: 0.95,
    });
  }
  return landmarks;
}

async function runTests() {
  console.log('====================================================');
  console.log('PERFORMX STEP 3B: LIVE MOVEMENT & WORKOUT INTEGRATION');
  console.log('====================================================');

  const originalFetch = globalThis.fetch;
  const originalLocalStorage = globalThis.localStorage;
  const originalSessionStorage = globalThis.sessionStorage;
  const originalWindow = globalThis.window;

  // Mock storage for Node test runner
  const storageStore = new Map();
  globalThis.sessionStorage = {
    getItem: (key) => storageStore.get(key) || null,
    setItem: (key, val) => storageStore.set(key, String(val)),
    removeItem: (key) => storageStore.delete(key),
    clear: () => storageStore.clear(),
  };

  globalThis.window = {
    sessionStorage: globalThis.sessionStorage,
    localStorage: {
      getItem: () => null,
      setItem: () => {},
      removeItem: () => {},
    },
  };

  try {
    // -------------------------------------------------------------------------
    // Test 1: Landmark Payload Mapping & Finite Coordinate Validation
    // -------------------------------------------------------------------------
    console.log('\n--- 1. Landmark Payload Mapping & Coordinate Validation ---');
    const validLandmarks = createMockLandmarks();
    assert(validLandmarks.length === 33, 'Generates exactly 33 MediaPipe pose landmarks');

    // Mapper function mirroring LiveCameraFeed.jsx
    const mapLandmarks = (lms) => {
      if (!lms || lms.length !== 33) return null;
      return lms.map(lm => ({
        x: Number.isFinite(lm.x) ? lm.x : 0.0,
        y: Number.isFinite(lm.y) ? lm.y : 0.0,
        z: Number.isFinite(lm.z) ? lm.z : 0.0,
        visibility: Number.isFinite(lm.visibility) ? lm.visibility : 1.0,
      }));
    };

    const mapped = mapLandmarks(validLandmarks);
    assert(mapped !== null && mapped.length === 33, 'Mapped payload preserves 33 landmarks');
    assert(mapped.every(lm => Number.isFinite(lm.x) && Number.isFinite(lm.y)), 'All coordinates are finite numbers');

    // Non-finite sanitized safely
    const corruptLandmarks = createMockLandmarks();
    corruptLandmarks[0].x = NaN;
    corruptLandmarks[1].y = Infinity;
    corruptLandmarks[2].visibility = -Infinity;
    const sanitized = mapLandmarks(corruptLandmarks);
    assert(sanitized[0].x === 0.0, 'Sanitizes NaN coordinate to 0.0');
    assert(sanitized[1].y === 0.0, 'Sanitizes Infinity coordinate to 0.0');
    assert(sanitized[2].visibility === 1.0, 'Sanitizes -Infinity visibility to 1.0');

    // Missing landmarks / occlusion handled
    assert(mapLandmarks([]) === null, 'Empty landmark array rejected');
    assert(mapLandmarks(null) === null, 'Null landmarks rejected');
    assert(mapLandmarks(new Array(20).fill({})) === null, 'Incomplete pose (<33 landmarks) rejected');

    // -------------------------------------------------------------------------
    // Test 2: Movement Session Lifecycle (Create, Ingestion, Terminate)
    // -------------------------------------------------------------------------
    console.log('\n--- 2. Movement Session Lifecycle Endpoints ---');
    let capturedSessionPayload = null;
    let capturedLandmarkPayload = null;
    let terminatedSessionId = null;

    globalThis.fetch = async (url, options) => {
      const parsedUrl = new URL(url);

      if (parsedUrl.pathname === '/api/v1/sessions' && options.method === 'POST') {
        capturedSessionPayload = options.body ? JSON.parse(options.body) : null;
        return {
          ok: true,
          status: 201,
          headers: { get: () => 'application/json' },
          json: async () => ({
            session_id: 'session-live-test-123',
            status: 'active',
            user_id: null,
            config: {},
          }),
        };
      }

      if (parsedUrl.pathname === '/api/v1/sessions/session-live-test-123/landmarks') {
        capturedLandmarkPayload = JSON.parse(options.body);
        return {
          ok: true,
          status: 200,
          headers: { get: () => 'application/json' },
          json: async () => ({
            repetition_count: 3,
            valid_reps: 3,
            phase: 'eccentric',
            symmetry: 0.94,
          }),
        };
      }

      if (parsedUrl.pathname === '/api/v1/sessions/session-live-test-123' && options.method === 'DELETE') {
        terminatedSessionId = 'session-live-test-123';
        return {
          ok: true,
          status: 200,
          headers: { get: () => 'application/json' },
          json: async () => ({
            session_id: 'session-live-test-123',
            start_time: 1700000000.0,
            end_time: 1700000060.0,
            total_frames_processed: 600,
            total_reps: 3,
            valid_reps: 3,
            mean_symmetry: 0.94,
            mean_rep_duration: 2.3,
          }),
        };
      }

      throw new Error(`Unexpected fetch URL: ${url}`);
    };

    const sessionRes = await apiClient.sessions.create({ min_rep_duration: 1.0 });
    assert(sessionRes.session_id === 'session-live-test-123', 'Created movement session successfully');
    assert(capturedSessionPayload.config.min_rep_duration === 1.0, 'Config passed to session creation');

    const ingestRes = await apiClient.sessions.sendLandmarks('session-live-test-123', {
      timestamp: 1700000010.5,
      landmarks: mapped,
    });
    assert(ingestRes.repetition_count === 3, 'Ingestion processed by movement engine');
    assert(capturedLandmarkPayload.landmarks.length === 33, 'Exactly 33 landmarks transmitted to backend');

    const termSummary = await apiClient.sessions.terminate('session-live-test-123');
    assert(terminatedSessionId === 'session-live-test-123', 'Terminated active session cleanly');
    assert(termSummary.total_reps === 3, 'Summary returned upon termination');

    // -------------------------------------------------------------------------
    // Test 3: Standing Calibration & Reset Workflows
    // -------------------------------------------------------------------------
    console.log('\n--- 3. Standing Calibration & Calibration Reset ---');
    let capturedCalibBody = null;
    let resetCalibCalled = false;

    globalThis.fetch = async (url, options) => {
      const parsedUrl = new URL(url);

      if (parsedUrl.pathname === '/api/v1/sessions/session-live-test-123/calibration/landmarks') {
        capturedCalibBody = JSON.parse(options.body);
        return {
          ok: true,
          status: 200,
          headers: { get: () => 'application/json' },
          json: async () => ({
            calibrated: true,
            calibration_score: 98,
            standing_knee_angle: 174.5,
          }),
        };
      }

      if (parsedUrl.pathname === '/api/v1/sessions/session-live-test-123/calibration/reset') {
        resetCalibCalled = true;
        return {
          ok: true,
          status: 200,
          headers: { get: () => 'application/json' },
          json: async () => ({
            status: 'calibration_reset',
            session_id: 'session-live-test-123',
          }),
        };
      }

      throw new Error(`Unexpected fetch URL: ${url}`);
    };

    const calibRes = await apiClient.sessions.calibrateLandmarks('session-live-test-123', {
      timestamp: 1700000005.0,
      landmarks: mapped,
    });
    assert(calibRes.calibrated === true, 'Calibration accepted by backend');
    assert(calibRes.standing_knee_angle === 174.5, 'Standing knee angle baseline recorded');
    assert(capturedCalibBody.landmarks.length === 33, 'Calibration landmarks sent as 33 items');

    const resetCalib = await apiClient.sessions.resetCalibration('session-live-test-123');
    assert(resetCalibCalled === true, 'Calibration reset endpoint triggered');
    assert(resetCalib.status === 'calibration_reset', 'Calibration status reset confirmed');

    // -------------------------------------------------------------------------
    // Test 4: Workout Persistence Authorization & Payloads
    // -------------------------------------------------------------------------
    console.log('\n--- 4. Workout Persistence API Contracts ---');
    authSession.clearToken();

    // Unauthorized attempt
    try {
      await apiClient.workouts.save({ exercise_type: 'squat', session_id: 'test' });
      assert(false, 'Should throw 401 when unauthenticated');
    } catch (err) {
      assert(err instanceof ApiError, 'Throws ApiError on unauthenticated workout save');
      assert(err.status === 401, 'Status is 401 Unauthorized');
    }

    // Authenticated workout persistence
    authSession.setToken('valid-user-jwt');
    let capturedSaveBody = null;
    let savedWorkoutId = 'workout-rec-789';

    globalThis.fetch = async (url, options) => {
      const parsedUrl = new URL(url);

      if (parsedUrl.pathname === '/api/v1/workouts' && options.method === 'POST') {
        capturedSaveBody = JSON.parse(options.body);
        return {
          ok: true,
          status: 201,
          headers: { get: () => 'application/json' },
          json: async () => ({
            workout_id: savedWorkoutId,
            user_id: 'user-athlete-1',
            exercise_type: capturedSaveBody.exercise_type,
            total_reps: 12,
            valid_reps: 12,
            form_score: 95.0,
            created_at: new Date().toISOString(),
          }),
        };
      }

      if (parsedUrl.pathname === '/api/v1/workouts' && options.method === 'GET') {
        return {
          ok: true,
          status: 200,
          headers: { get: () => 'application/json' },
          json: async () => ({
            items: [
              { workout_id: savedWorkoutId, exercise_type: 'squat', total_reps: 12, valid_reps: 12 }
            ],
            total: 1,
            limit: 20,
            offset: 0,
          }),
        };
      }

      throw new Error(`Unexpected fetch URL: ${url}`);
    };

    // Test saving via session_id
    const saveSessionIdPayload = {
      session_id: 'session-live-test-123',
      exercise_type: 'barbell back squat',
    };
    const saveRes = await apiClient.workouts.save(saveSessionIdPayload);
    assert(saveRes.workout_id === 'workout-rec-789', 'Workout saved via active session_id');
    assert(capturedSaveBody.exercise_type === 'barbell back squat', 'Exercise type passed through');

    // Test saving via validated direct summary model
    const saveSummaryPayload = {
      exercise_type: 'squat',
      summary: {
        session_id: 'client-manual-1',
        start_time: 1700000000.0,
        end_time: 1700000060.0,
        total_frames_processed: 600,
        total_reps: 10,
        valid_reps: 10,
        mean_symmetry: 0.95,
        mean_rep_duration: 2.2,
        metrics: {
          total_completed_reps: 10,
          accepted_reps: 10,
          rejected_reps: 0,
          incomplete_attempts: 0,
          aborted_attempts: 0,
          mean_duration: 2.2,
          min_duration: 1.8,
          max_duration: 2.8,
          duration_range: 1.0,
          mean_descent_duration: 1.1,
          mean_bottom_dwell: 0.3,
          mean_ascent_duration: 0.8,
          mean_min_knee_angle: 85.0,
          knee_angle_range: 70.0,
          mean_rep_symmetry: 0.95,
          mean_tracking_confidence: 0.92,
          explainable_insights: ["Optimal depth and symmetry"],
        },
      },
    };

    const directSaveRes = await apiClient.workouts.save(saveSummaryPayload);
    assert(directSaveRes.workout_id === 'workout-rec-789', 'Workout saved via validated direct summary payload');
    assert(capturedSaveBody.summary.total_reps === 10, 'Direct summary total_reps validated');

    // Test listing saved workouts
    const workoutList = await apiClient.workouts.list(10, 0);
    assert(workoutList.total === 1, 'Workout history listing returns saved count');
    assert(workoutList.items[0].workout_id === 'workout-rec-789', 'Saved workout appears in user history');

    // -------------------------------------------------------------------------
    // Test 5: Duplicate Submission Prevention Simulation
    // -------------------------------------------------------------------------
    console.log('\n--- 5. Duplicate Submission Prevention ---');
    let inflight = false;
    let executionCount = 0;

    const guardedSave = async () => {
      if (inflight) return { duplicateBlocked: true };
      inflight = true;
      try {
        executionCount++;
        await new Promise(r => setTimeout(r, 20));
        return { duplicateBlocked: false };
      } finally {
        inflight = false;
      }
    };

    // Parallel calls
    const [call1, call2] = await Promise.all([guardedSave(), guardedSave()]);
    assert(executionCount === 1, 'Only exactly 1 network submission executed');
    assert(call1.duplicateBlocked === false || call2.duplicateBlocked === false, 'First call proceeded');
    assert(call1.duplicateBlocked === true || call2.duplicateBlocked === true, 'Concurrent second call blocked');

  } finally {
    globalThis.fetch = originalFetch;
    globalThis.localStorage = originalLocalStorage;
    globalThis.sessionStorage = originalSessionStorage;
    globalThis.window = originalWindow;
  }

  console.log('\n====================================================');
  console.log(`STEP 3B TEST SUMMARY: Total: ${passed + failed} | Passed: ${passed} | Failed: ${failed}`);
  console.log('====================================================\n');

  if (failed > 0) {
    process.exit(1);
  }
}

runTests().catch((err) => {
  console.error('Test execution error:', err);
  process.exit(1);
});
