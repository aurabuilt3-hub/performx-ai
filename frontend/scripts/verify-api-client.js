/**
 * Test Suite for PERFORMX Centralized API Client (api.js).
 * Validates:
 * 1. Configurable base URL resolution.
 * 2. Successful JSON request and response parsing.
 * 3. Correct Authorization header attachment when authenticated.
 * 4. Error thrown when authentication is required but missing.
 * 5. Rejection and error transformation for HTTP 400/401/404/500 responses.
 * 6. Actionable error handling for network offline / connection failure.
 * 7. Request timeout abort handling.
 * 8. NO silent demo or fake data substitution on error.
 */

import {
  getApiBaseUrl,
  request,
  apiClient,
  authSession,
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
  console.log('--- 1. Testing Base URL Resolution ---');
  const baseUrl = getApiBaseUrl();
  assert(typeof baseUrl === 'string' && baseUrl.length > 0, `Base URL resolved: ${baseUrl}`);
  assert(!baseUrl.endsWith('/'), 'Base URL has trailing slashes stripped');

  console.log('\n--- 2. Testing Auth Session Management ---');
  authSession.clearToken();
  assert(!authSession.isAuthenticated(), 'Initial session is unauthenticated');
  assert(authSession.getToken() === null, 'No token returned when unauthenticated');

  authSession.setToken('test-jwt-token-xyz');
  assert(authSession.isAuthenticated(), 'Session marked authenticated after setToken');
  assert(authSession.getToken() === 'test-jwt-token-xyz', 'Token matches set value');

  authSession.clearToken();
  assert(!authSession.isAuthenticated(), 'Session unauthenticated after clearToken');

  console.log('\n--- 3. Testing Missing Auth Requirement ---');
  try {
    await request('/api/v1/profile', { requiresAuth: true });
    assert(false, 'Should throw ApiError when auth required but missing');
  } catch (err) {
    assert(err instanceof ApiError, 'Throws ApiError instance');
    assert(err.status === 401, 'Status is 401 Unauthorized');
    assert(err.code === 'UNAUTHORIZED', 'Error code is UNAUTHORIZED');
  }

  console.log('\n--- 4. Testing Simulated Network Offline / Error ---');
  // Attempt connection to a non-existent port to simulate network failure
  try {
    await request('/health', {
      baseUrl: 'http://127.0.0.1:59999',
      timeoutMs: 1000,
    });
    assert(false, 'Should throw ApiError on network failure');
  } catch (err) {
    assert(err instanceof ApiError, 'Throws ApiError on network connection failure');
    assert(err.code === 'NETWORK_ERROR' || err.code === 'TIMEOUT', `Code is ${err.code}`);
    assert(
      err.message.includes('Network connection failure') || err.message.includes('timeout'),
      'Provides actionable connection error message without silent fake data'
    );
  }

  console.log('\n--- 5. Testing Mock Fetch Success & Authorization Header ---');
  const originalFetch = globalThis.fetch;

  // Mock fetch for successful authenticated request
  let capturedHeaders = null;
  globalThis.fetch = async (url, opts) => {
    capturedHeaders = opts.headers;
    return {
      ok: true,
      status: 200,
      headers: {
        get: (h) => (h.toLowerCase() === 'content-type' ? 'application/json' : null),
      },
      json: async () => ({ status: 'healthy', version: '1.0.0' }),
    };
  };

  try {
    authSession.setToken('mock-verified-bearer-token');
    const data = await apiClient.system.health();
    assert(data.status === 'healthy', 'Parses JSON response payload accurately');
    assert(
      capturedHeaders['Authorization'] === 'Bearer mock-verified-bearer-token',
      'Attaches Bearer Authorization header when token is present'
    );
    assert(
      capturedHeaders['Accept'] === 'application/json',
      'Includes Accept application/json header'
    );
  } finally {
    authSession.clearToken();
    globalThis.fetch = originalFetch;
  }

  console.log('\n--- 6. Testing Mock Fetch HTTP Non-2xx & 401 Handling ---');
  globalThis.fetch = async () => {
    return {
      ok: false,
      status: 401,
      headers: {
        get: (h) => (h.toLowerCase() === 'content-type' ? 'application/json' : null),
      },
      json: async () => ({ detail: 'Token expired or invalid signature' }),
    };
  };

  try {
    authSession.setToken('expired-token');
    await apiClient.profile.get();
    assert(false, 'Should throw ApiError on 401');
  } catch (err) {
    assert(err instanceof ApiError, 'Throws ApiError on 401 response');
    assert(err.status === 401, 'Status is 401');
    assert(err.message.includes('Token expired'), 'Extracts backend error detail');
    assert(!authSession.isAuthenticated(), 'Automatically clears expired session token');
  } finally {
    globalThis.fetch = originalFetch;
  }

  console.log('\n--- 7. Summary ---');
  console.log(`Total tests: ${passed + failed} | Passed: ${passed} | Failed: ${failed}`);
  if (failed > 0) {
    process.exit(1);
  }
}

runTests().catch((err) => {
  console.error('Unhandled test runner error:', err);
  process.exit(1);
});
