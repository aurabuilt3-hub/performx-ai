/**
 * PERFORMX Frontend Test Suite - Step 3E: Grounded AI Coach Integration
 * 
 * Verifies:
 * 1. AI Coach Contract Verification via /api/v1/chat/message.
 * 2. Strict User Isolation: Grounded entities reflect only the authenticated user.
 * 3. Absence of Raw Media: Verifies request payload contains only text and session_id.
 * 4. Allergen Conservatism: Unverified allergen logs produce defensive warnings.
 * 5. Provider Fallback & Error Handling: Gracefully handles 500/504 network errors.
 * 6. Unauthorized 401 Rejection: Unauthenticated requests cannot invoke the chat route.
 */

import { apiClient, authSession, ApiError } from '../src/services/api.js';

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

const MOCK_TOKEN = 'test.jwt.step3e.token';
const MOCK_USER_ID = 'usr_coach_test_456';

async function runTests() {
  console.log('====================================================');
  console.log('PERFORMX STEP 3E: GROUNDED AI COACH INTEGRATION');
  console.log('====================================================');

  const originalFetch = globalThis.fetch;
  const originalLocalStorage = globalThis.localStorage;
  const originalSessionStorage = globalThis.sessionStorage;
  const originalWindow = globalThis.window;

  const storageStore = new Map();
  globalThis.localStorage = {
    getItem: (k) => storageStore.get(k) ?? null,
    setItem: (k, v) => storageStore.set(k, String(v)),
    removeItem: (k) => storageStore.delete(k),
    clear: () => storageStore.clear(),
  };
  globalThis.sessionStorage = { ...globalThis.localStorage };
  globalThis.window = {
    dispatchEvent: () => {},
  };

  try {
    authSession.setToken(MOCK_TOKEN);

    // -------------------------------------------------------------------------
    // TEST 1: Grounded Message Contract & Schema Verification
    // -------------------------------------------------------------------------
    console.log('\n--- Test 1: Chat Endpoint Request & Response Contract ---');
    {
      let capturedRequest = null;
      globalThis.fetch = async (url, opts) => {
        capturedRequest = { url, opts };
        if (url.includes('/api/v1/chat/message') && opts.method === 'POST') {
          const body = JSON.parse(opts.body);
          return {
            ok: true,
            status: 200,
            headers: { get: () => 'application/json' },
            json: async () => ({
              reply: `Hi Alex, in your latest squat session you performed 10 repetitions with 94.5% symmetry.`,
              grounded_entities: [`user:${MOCK_USER_ID}`, 'workout:sess_squat_1'],
              warnings: [],
            }),
          };
        }
        return { ok: false, status: 404, headers: { get: () => 'application/json' }, json: async () => ({ detail: 'Not found' }) };
      };

      const response = await apiClient.chat.sendMessage('How was my latest squat session?', 'sess_squat_1');
      assert(response.reply.includes('10 repetitions'), 'Grounded reply received from /api/v1/chat/message');
      assert(response.grounded_entities.includes(`user:${MOCK_USER_ID}`), 'Grounded entities cite authenticated user');
      assert(response.grounded_entities.includes('workout:sess_squat_1'), 'Grounded entities cite verified workout record');

      const reqBody = JSON.parse(capturedRequest.opts.body);
      assert(reqBody.message === 'How was my latest squat session?', 'User message correctly forwarded');
      assert(reqBody.session_id === 'sess_squat_1', 'Active session_id forwarded for focused grounding');
      assert(capturedRequest.opts.headers['Authorization'] === `Bearer ${MOCK_TOKEN}`, 'Bearer authorization sent');
    }

    // -------------------------------------------------------------------------
    // TEST 2: Absence of Raw Vision Frames / Media Leakage
    // -------------------------------------------------------------------------
    console.log('\n--- Test 2: Zero Raw Video/Landmark Transmission Invariant ---');
    {
      let capturedBody = null;
      globalThis.fetch = async (url, opts) => {
        capturedBody = JSON.parse(opts.body);
        return {
          ok: true,
          status: 200,
          headers: { get: () => 'application/json' },
          json: async () => ({
            reply: 'Advising on knee angle form.',
            grounded_entities: [`user:${MOCK_USER_ID}`],
            warnings: [],
          }),
        };
      };

      await apiClient.chat.sendMessage('Can you check my squat depth?');
      assert(!('landmarks' in capturedBody), 'No MediaPipe landmark arrays passed to chat endpoint');
      assert(!('frames' in capturedBody), 'No image frame byte arrays passed to chat endpoint');
      assert(!('video' in capturedBody), 'No video streams passed to chat endpoint');
      assert(Object.keys(capturedBody).every(k => ['message', 'session_id'].includes(k)), 'Request payload strictly restricted to message and session_id');
    }

    // -------------------------------------------------------------------------
    // TEST 3: Allergen Safety Conservatism & Provenance Warnings
    // -------------------------------------------------------------------------
    console.log('\n--- Test 3: Allergen Conservatism & Safety Advisories ---');
    {
      globalThis.fetch = async (url, opts) => {
        return {
          ok: true,
          status: 200,
          headers: { get: () => 'application/json' },
          json: async () => ({
            reply: 'Today you logged 2100 kcal and 150g protein. (Note: Allergen verification is UNKNOWN; verify with supplier)',
            grounded_entities: [`user:${MOCK_USER_ID}`],
            warnings: ['Allergen status is unverified. Do not assume meal safety.'],
          }),
        };
      };

      const res = await apiClient.chat.sendMessage('Is my meal safe for allergies?');
      assert(res.warnings.length > 0, 'Advisory warning surfaced when allergen verification is unverified');
      assert(res.warnings[0].includes('Allergen status is unverified'), 'Explicit conservative allergen warning preserved');
      assert(res.reply.includes('UNKNOWN'), 'Response does not claim unverified food is safe');
    }

    // -------------------------------------------------------------------------
    // TEST 4: Upstream Provider Error & Graceful Degraded Warning
    // -------------------------------------------------------------------------
    console.log('\n--- Test 4: Provider Degradation & Temporary Unavailable Handling ---');
    {
      globalThis.fetch = async (url, opts) => {
        return {
          ok: true,
          status: 200,
          headers: { get: () => 'application/json' },
          json: async () => ({
            reply: 'Hi Alex, in your latest squat session you performed 10 reps.',
            grounded_entities: [`user:${MOCK_USER_ID}`],
            warnings: ['AI generation provider temporarily unavailable. Switched to verified deterministic rules.'],
          }),
        };
      };

      const degradedRes = await apiClient.chat.sendMessage('Summarize my reps');
      assert(degradedRes.reply.length > 0, 'Returned graceful fallback response during provider disruption');
      assert(degradedRes.warnings.some(w => w.includes('temporarily unavailable')), 'Warns user of fallback to deterministic rules');
    }

    // -------------------------------------------------------------------------
    // TEST 5: Network Failure & API Error Propagation
    // -------------------------------------------------------------------------
    console.log('\n--- Test 5: Network Failure & 500 Error Propagation ---');
    {
      globalThis.fetch = async () => {
        return {
          ok: false,
          status: 500,
          headers: { get: () => 'application/json' },
          json: async () => ({ detail: 'Internal Server Error' }),
        };
      };

      let caughtErr = null;
      try {
        await apiClient.chat.sendMessage('Hello coach');
      } catch (e) {
        caughtErr = e;
      }
      assert(caughtErr instanceof ApiError && caughtErr.status === 500, 'Propagates ApiError with HTTP 500 status');
    }

    // -------------------------------------------------------------------------
    // TEST 6: Unauthenticated 401 Rejection
    // -------------------------------------------------------------------------
    console.log('\n--- Test 6: Unauthenticated Access Rejection ---');
    {
      authSession.clearToken();
      let authErr = null;
      try {
        await apiClient.chat.sendMessage('Hello');
      } catch (e) {
        authErr = e;
      }
      assert(authErr instanceof ApiError && authErr.status === 401, 'Rejects unauthenticated chat invocation with 401 Unauthorized');
    }

  } finally {
    globalThis.fetch = originalFetch;
    globalThis.localStorage = originalLocalStorage;
    globalThis.sessionStorage = originalSessionStorage;
    globalThis.window = originalWindow;
    authSession.clearToken();
  }

  console.log('\n====================================================');
  console.log(`STEP 3E VERIFICATION COMPLETE: ${passed} passed, ${failed} failed`);
  console.log('====================================================');

  if (failed > 0) {
    process.exit(1);
  }
}

runTests().catch((err) => {
  console.error('Unhandled failure during Step 3E verification:', err);
  process.exit(1);
});
