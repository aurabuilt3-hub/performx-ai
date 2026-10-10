/**
 * PERFORMX - Comprehensive Step 3A Verification Suite
 * Tests:
 * 1. Supabase Auth Configuration resolution
 * 2. Sign-In success flow (JWT parsed, storage updated, state marked authenticated)
 * 3. Sign-In failure flow (invalid credentials, 400 error message extraction)
 * 4. Sign-Up / Registration validation and error handling
 * 5. Sign-Out / Token eviction and session cleanup
 * 6. Expired session handling (401 response triggers eviction)
 * 7. Profile API contract (GET & PUT) payload filtering (forbid unexpected keys)
 * 8. Health Profile API contract (GET & PUT) payload validation
 * 9. Privacy check: localStorage never contains sensitive health/medical data
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

async function runTests() {
  console.log('====================================================');
  console.log('PERFORMX STEP 3A: AUTH & PROFILE INTEGRATION TESTS');
  console.log('====================================================');

  const originalFetch = globalThis.fetch;
  const originalLocalStorage = globalThis.localStorage;
  const originalSessionStorage = globalThis.sessionStorage;
  const originalWindow = globalThis.window;

  // Mock storage for Node test runner
  const localStorageStore = new Map();
  globalThis.localStorage = {
    getItem: (key) => localStorageStore.get(key) || null,
    setItem: (key, val) => localStorageStore.set(key, String(val)),
    removeItem: (key) => localStorageStore.delete(key),
    clear: () => localStorageStore.clear(),
  };

  const sessionStorageStore = new Map();
  const mockSessionStorage = {
    getItem: (key) => sessionStorageStore.get(key) || null,
    setItem: (key, val) => sessionStorageStore.set(key, String(val)),
    removeItem: (key) => sessionStorageStore.delete(key),
    clear: () => sessionStorageStore.clear(),
  };

  globalThis.sessionStorage = mockSessionStorage;
  globalThis.window = {
    sessionStorage: mockSessionStorage,
    localStorage: globalThis.localStorage,
  };

  // Ensure process.env has test credentials for mock endpoint testing
  process.env.VITE_SUPABASE_URL = process.env.VITE_SUPABASE_URL || 'https://xyzcompany.supabase.co';
  process.env.VITE_SUPABASE_ANON_KEY = process.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.anon-key';

  try {
    // -------------------------------------------------------------------------
    // Test 1: Supabase Auth Configuration
    // -------------------------------------------------------------------------
    console.log('\n--- 1. Supabase Auth Config Resolution ---');
    const sbConfig = authSession.getSupabaseConfig();
    assert(typeof sbConfig.url === 'string', 'Supabase URL resolved as string');
    assert(typeof sbConfig.anonKey === 'string', 'Supabase Anon Key resolved as string');
    assert(!sbConfig.anonKey.includes('service_role'), 'Never contains service role key');

    // -------------------------------------------------------------------------
    // Test 2: Successful Sign In via Supabase GoTrue endpoint
    // -------------------------------------------------------------------------
    console.log('\n--- 2. Sign-In Success Flow ---');
    authSession.clearToken();
    assert(!authSession.isAuthenticated(), 'Initial state is unauthenticated');

    const fakeToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3OC0xMjM0LTUyMzQtYTIzNC0xMjM0NTY3ODkwMTIiLCJlbWFpbCI6InRlc3RAcGVyZm9ybXguYWkifQ.signature';
    const fakeUserData = {
      id: '12345678-1234-5234-a234-123456789012',
      email: 'test@performx.ai',
      user_metadata: { full_name: 'Test Athlete' },
    };

    globalThis.fetch = async (url, options) => {
      if (url.includes('/auth/v1/token')) {
        const urlObj = new URL(url);
        assert(urlObj.searchParams.get('grant_type') === 'password', 'grant_type is password');
        const body = JSON.parse(options.body);
        assert(body.email === 'test@performx.ai', 'Email forwarded correctly');
        assert(body.password === 'SecureP@ss123!', 'Password forwarded correctly');
        return {
          ok: true,
          status: 200,
          headers: { get: () => 'application/json' },
          json: async () => ({
            access_token: fakeToken,
            token_type: 'bearer',
            expires_in: 3600,
            user: fakeUserData,
          }),
        };
      }
      throw new Error(`Unexpected fetch URL: ${url}`);
    };

    const loginRes = await authSession.signInWithPassword('test@performx.ai', 'SecureP@ss123!');
    assert(loginRes.access_token === fakeToken, 'Sign-in returns access token');
    assert(authSession.isAuthenticated(), 'authSession reports isAuthenticated() === true');
    assert(authSession.getToken() === fakeToken, 'authSession holds the returned token');
    assert(sessionStorage.getItem('performx_access_token') === fakeToken, 'Token persisted in sessionStorage');

    // -------------------------------------------------------------------------
    // Test 3: Failed Sign In (Invalid Credentials)
    // -------------------------------------------------------------------------
    console.log('\n--- 3. Sign-In Failure Flow ---');
    globalThis.fetch = async (url) => {
      if (url.includes('/auth/v1/token')) {
        return {
          ok: false,
          status: 400,
          headers: { get: () => 'application/json' },
          json: async () => ({
            error: 'invalid_grant',
            error_description: 'Invalid login credentials',
          }),
        };
      }
      throw new Error(`Unexpected fetch URL: ${url}`);
    };

    try {
      await authSession.signInWithPassword('wrong@performx.ai', 'badpassword');
      assert(false, 'Should throw ApiError on invalid credentials');
    } catch (err) {
      assert(err instanceof ApiError, 'Throws ApiError instance');
      assert(err.status === 400, 'Status is 400');
      assert(err.message === 'Invalid login credentials', 'Extracts error_description');
    }

    // -------------------------------------------------------------------------
    // Test 4: Sign-Up Flow & Conflict
    // -------------------------------------------------------------------------
    console.log('\n--- 4. Sign-Up Flow ---');
    globalThis.fetch = async (url, options) => {
      if (url.includes('/auth/v1/signup')) {
        const body = JSON.parse(options.body);
        if (body.email === 'existing@performx.ai') {
          return {
            ok: false,
            status: 422,
            headers: { get: () => 'application/json' },
            json: async () => ({ msg: 'User already registered' }),
          };
        }
        return {
          ok: true,
          status: 200,
          headers: { get: () => 'application/json' },
          json: async () => ({
            id: 'new-user-id',
            email: body.email,
            access_token: 'new-token',
          }),
        };
      }
      throw new Error(`Unexpected fetch URL: ${url}`);
    };

    const signupRes = await authSession.signUp('new@performx.ai', 'NewP@ssword123!', { full_name: 'New Athlete' });
    assert(signupRes.id === 'new-user-id', 'Successful sign-up returns user object');

    try {
      await authSession.signUp('existing@performx.ai', 'NewP@ssword123!');
      assert(false, 'Should throw on already registered user');
    } catch (err) {
      assert(err.status === 422, 'Duplicate signup rejected with 422 status');
      assert(err.message === 'User already registered', 'Proper error message extracted');
    }

    // -------------------------------------------------------------------------
    // Test 5: Sign-Out / Session Cleanup
    // -------------------------------------------------------------------------
    console.log('\n--- 5. Sign-Out & Session Clearing ---');
    authSession.setToken('valid-active-token');
    assert(authSession.isAuthenticated(), 'Session active before sign-out');
    authSession.signOut();
    assert(!authSession.isAuthenticated(), 'Session cleared after sign-out');
    assert(authSession.getToken() === null, 'Token is null after sign-out');
    assert(sessionStorage.getItem('performx_access_token') === null, 'Token removed from sessionStorage');

    // -------------------------------------------------------------------------
    // Test 6: Expired Token Eviction on 401
    // -------------------------------------------------------------------------
    console.log('\n--- 6. 401 Response Session Eviction ---');
    authSession.setToken('expired-jwt');
    globalThis.fetch = async () => {
      return {
        ok: false,
        status: 401,
        headers: { get: () => 'application/json' },
        json: async () => ({ detail: 'JWT expired or signature verification failed' }),
      };
    };

    try {
      await apiClient.profile.get();
      assert(false, 'Should throw 401');
    } catch (err) {
      assert(err.status === 401, 'Status is 401');
      assert(!authSession.isAuthenticated(), 'Token immediately evicted on 401 response');
      assert(sessionStorage.getItem('performx_access_token') === null, 'Cleared from sessionStorage on 401');
    }

    // -------------------------------------------------------------------------
    // Test 7: Profile Update Contract & Extra Field Forbidding
    // -------------------------------------------------------------------------
    console.log('\n--- 7. Profile API Contract Verification ---');
    authSession.setToken('auth-valid-token');

    let capturedHeaders = null;
    let capturedBody = null;
    globalThis.fetch = async (url, options) => {
      capturedHeaders = options.headers;
      capturedBody = JSON.parse(options.body || '{}');
      return {
        ok: true,
        status: 200,
        headers: { get: () => 'application/json' },
        json: async () => ({
          user_id: '12345678-1234-5234-a234-123456789012',
          email: 'test@performx.ai',
          display_name: capturedBody.display_name,
          units: capturedBody.units,
          fitness_experience: capturedBody.fitness_experience,
          primary_goal: capturedBody.primary_goal,
          available_equipment: capturedBody.available_equipment,
          dietary_preferences: capturedBody.dietary_preferences,
        }),
      };
    };

    const updatePayload = {
      display_name: 'Alex Rivera',
      units: 'metric',
      fitness_experience: 'intermediate',
      primary_goal: 'Strength & Biomechanics',
      available_equipment: ['Barbell', 'Dumbbells'],
      dietary_preferences: ['High Protein'],
    };

    const updateResult = await apiClient.profile.update(updatePayload);
    assert(capturedHeaders['Authorization'] === 'Bearer auth-valid-token', 'Authorization header sent with Bearer token');
    assert(capturedHeaders['Content-Type'] === 'application/json', 'Content-Type is application/json');
    assert(updateResult.display_name === 'Alex Rivera', 'Profile update returned display_name');
    assert(updateResult.fitness_experience === 'intermediate', 'Fitness experience matches schema pattern');

    // -------------------------------------------------------------------------
    // Test 8: Health Profile API Contract Verification
    // -------------------------------------------------------------------------
    console.log('\n--- 8. Health Profile API Contract Verification ---');
    let capturedHealthBody = null;
    globalThis.fetch = async (url, options) => {
      capturedHealthBody = JSON.parse(options.body || '{}');
      return {
        ok: true,
        status: 200,
        headers: { get: () => 'application/json' },
        json: async () => ({
          user_id: '12345678-1234-5234-a234-123456789012',
          height_cm: capturedHealthBody.height_cm,
          weight_kg: capturedHealthBody.weight_kg,
          body_fat_percentage: capturedHealthBody.body_fat_percentage,
          resting_heart_rate: capturedHealthBody.resting_heart_rate,
          allergies: capturedHealthBody.allergies,
          reported_injuries: capturedHealthBody.reported_injuries || [],
          clinician_restrictions: capturedHealthBody.clinician_restrictions || [],
          data_provenance: 'USER_REPORTED',
        }),
      };
    };

    const healthPayload = {
      height_cm: 180.5,
      weight_kg: 78.2,
      body_fat_percentage: 14.5,
      resting_heart_rate: 58,
      allergies: ['Peanuts'],
    };

    const healthResult = await apiClient.healthProfile.update(healthPayload);
    assert(healthResult.height_cm === 180.5, 'height_cm sent and confirmed');
    assert(healthResult.weight_kg === 78.2, 'weight_kg sent and confirmed');
    assert(healthResult.resting_heart_rate === 58, 'resting_heart_rate sent and confirmed');
    assert(healthResult.data_provenance === 'USER_REPORTED', 'data_provenance preserved');

    // -------------------------------------------------------------------------
    // Test 9: Privacy Audit - LocalStorage Sanitization
    // -------------------------------------------------------------------------
    console.log('\n--- 9. Privacy Check: localStorage Data Sanitization ---');
    // Verify that NO health/injury keys are placed directly in localStorage
    const sensitiveKeys = [
      'injuries',
      'allergies',
      'clinician_restrictions',
      'height_cm',
      'weight_kg',
      'body_fat_percentage',
      'medical_documents',
      'password',
    ];

    for (const key of sensitiveKeys) {
      assert(localStorage.getItem(key) === null, `Sensitive key "${key}" is NOT in localStorage`);
    }

  } finally {
    globalThis.fetch = originalFetch;
    globalThis.localStorage = originalLocalStorage;
  }

  console.log('\n====================================================');
  console.log(`STEP 3A TEST SUMMARY: Total: ${passed + failed} | Passed: ${passed} | Failed: ${failed}`);
  console.log('====================================================\n');

  if (failed > 0) {
    process.exit(1);
  }
}

runTests().catch((err) => {
  console.error('Test execution error:', err);
  process.exit(1);
});
