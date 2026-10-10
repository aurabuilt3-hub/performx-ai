/**
 * PERFORMX Centralized API Client & Service Gateway.
 *
 * Guarantees & Constraints:
 * 1. Configurable base URL via VITE_API_BASE_URL (defaults to http://localhost:8000).
 * 2. Consistent JSON serialization and response validation.
 * 3. Structured error handling for network offline, timeouts, and non-2xx HTTP responses.
 * 4. Authorization headers added only when a valid session token is available and required.
 * 5. Safe handling of missing/expired sessions with clear auth error callbacks.
 * 6. NO silent demo or fake data substitution on failure — returns explicit, actionable errors.
 * 7. Strictly avoids storing sensitive health, medical notes, or raw vision coordinates in localStorage.
 */

const DEFAULT_TIMEOUT_MS = 10000;

// Resolve API Base URL from Vite environment or safe default
export function getApiBaseUrl() {
  if (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL.replace(/\/+$/, '');
  }
  return 'http://localhost:8000';
}

/**
 * Standardized API Error carrying HTTP status, error code, and server payload.
 */
export class ApiError extends Error {
  constructor(message, { status = 0, code = 'API_ERROR', details = null, endpoint = '' } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
    this.endpoint = endpoint;
  }
}

// In-memory token management with optional session storage
let inMemoryAuthToken = null;

export const authSession = {
  /**
   * Set the active bearer JWT token.
   * Stored in memory and optionally sessionStorage (never persistent localStorage).
   */
  setToken(token) {
    inMemoryAuthToken = token;
    if (typeof window !== 'undefined' && window.sessionStorage) {
      if (token) {
        window.sessionStorage.setItem('performx_access_token', token);
      } else {
        window.sessionStorage.removeItem('performx_access_token');
      }
    }
  },

  /**
   * Retrieve the current active bearer token.
   */
  getToken() {
    if (inMemoryAuthToken) {
      return inMemoryAuthToken;
    }
    if (typeof window !== 'undefined' && window.sessionStorage) {
      const stored = window.sessionStorage.getItem('performx_access_token');
      if (stored) {
        inMemoryAuthToken = stored;
        return stored;
      }
    }
    return null;
  },

  /**
   * Clear session token upon logout or 401 expiration.
   */
  clearToken() {
    inMemoryAuthToken = null;
    if (typeof window !== 'undefined' && window.sessionStorage) {
      window.sessionStorage.removeItem('performx_access_token');
    }
  },

  /**
   * Check if a token exists and is non-empty.
   */
  isAuthenticated() {
    return Boolean(this.getToken());
  },

  /**
   * Resolve client-facing Supabase URL & Anon Key from Vite environment or Node process.env.
   */
  getSupabaseConfig() {
    let url = '';
    let anonKey = '';

    if (typeof import.meta !== 'undefined' && import.meta.env) {
      url = import.meta.env.VITE_SUPABASE_URL || '';
      anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';
    }

    if (!url && typeof process !== 'undefined' && process.env) {
      url = process.env.VITE_SUPABASE_URL || '';
      anonKey = process.env.VITE_SUPABASE_ANON_KEY || '';
    }

    return {
      url: url.replace(/\/+$/, ''),
      anonKey,
      isConfigured: Boolean(url && anonKey && !url.includes('your-project-ref')),
    };
  },

  /**
   * Real Supabase Auth sign-in using email and password.
   * Calls Supabase GoTrue endpoint /auth/v1/token?grant_type=password
   */
  async signInWithPassword(email, password) {
    const config = this.getSupabaseConfig();
    if (!config.isConfigured) {
      throw new ApiError(
        'Supabase authentication is not configured. Please set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in frontend/.env.',
        { status: 503, code: 'AUTH_NOT_CONFIGURED', endpoint: '/auth/v1/token' }
      );
    }

    const endpoint = `${config.url}/auth/v1/token?grant_type=password`;
    let response;
    try {
      response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'apikey': config.anonKey,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });
    } catch (err) {
      throw new ApiError(`Network error reaching Supabase Auth: ${err.message}`, {
        status: 0,
        code: 'NETWORK_ERROR',
        endpoint: '/auth/v1/token',
      });
    }

    const data = await response.json();
    if (!response.ok) {
      const msg = data.error_description || data.msg || data.message || 'Invalid email or password.';
      throw new ApiError(msg, {
        status: response.status,
        code: data.error || 'INVALID_CREDENTIALS',
        details: data,
        endpoint: '/auth/v1/token',
      });
    }

    if (data.access_token) {
      this.setToken(data.access_token);
    }
    return data;
  },

  /**
   * Real Supabase Auth sign-up using email, password, and optional user metadata.
   * Calls Supabase GoTrue endpoint /auth/v1/signup
   */
  async signUp(email, password, { displayName = '' } = {}) {
    const config = this.getSupabaseConfig();
    if (!config.isConfigured) {
      throw new ApiError(
        'Supabase authentication is not configured. Please set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in frontend/.env.',
        { status: 503, code: 'AUTH_NOT_CONFIGURED', endpoint: '/auth/v1/signup' }
      );
    }

    const endpoint = `${config.url}/auth/v1/signup`;
    let response;
    try {
      response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'apikey': config.anonKey,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          password,
          data: { display_name: displayName },
        }),
      });
    } catch (err) {
      throw new ApiError(`Network error reaching Supabase Auth: ${err.message}`, {
        status: 0,
        code: 'NETWORK_ERROR',
        endpoint: '/auth/v1/signup',
      });
    }

    const data = await response.json();
    if (!response.ok) {
      const msg = data.error_description || data.msg || data.message || 'Registration failed.';
      throw new ApiError(msg, {
        status: response.status,
        code: data.error || 'REGISTRATION_FAILED',
        details: data,
        endpoint: '/auth/v1/signup',
      });
    }

    if (data.access_token) {
      this.setToken(data.access_token);
    }
    return data;
  },

  /**
   * Sign out and clear stored session tokens.
   */
  async signOut() {
    this.clearToken();
  },
};

/**
 * Core HTTP Request Execution.
 */
export async function request(endpoint, options = {}) {
  const {
    method = 'GET',
    body = null,
    headers = {},
    requiresAuth = false,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    baseUrl = getApiBaseUrl(),
  } = options;

  const url = `${baseUrl}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  const requestHeaders = {
    Accept: 'application/json',
    ...headers,
  };

  if (body !== null && !(body instanceof FormData)) {
    requestHeaders['Content-Type'] = 'application/json';
  }

  // Handle Authorization
  const token = authSession.getToken();
  if (token) {
    requestHeaders['Authorization'] = `Bearer ${token}`;
  } else if (requiresAuth) {
    throw new ApiError('Authentication required. No valid session token available.', {
      status: 401,
      code: 'UNAUTHORIZED',
      endpoint,
    });
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  let response;
  try {
    response = await fetch(url, {
      method,
      headers: requestHeaders,
      body: body instanceof FormData ? body : (body !== null ? JSON.stringify(body) : null),
      signal: controller.signal,
    });
  } catch (err) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      throw new ApiError(`Request timeout after ${timeoutMs}ms: unable to connect to PERFORMX API at ${url}`, {
        status: 408,
        code: 'TIMEOUT',
        endpoint,
      });
    }
    throw new ApiError(`Network connection failure: unable to reach PERFORMX backend at ${url}. Ensure the FastAPI server is running.`, {
      status: 0,
      code: 'NETWORK_ERROR',
      details: err.message,
      endpoint,
    });
  } finally {
    clearTimeout(timeoutId);
  }

  // Process Response Body
  let data = null;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    try {
      data = await response.json();
    } catch (parseErr) {
      throw new ApiError('Invalid JSON response received from PERFORMX backend.', {
        status: response.status,
        code: 'INVALID_JSON',
        details: parseErr.message,
        endpoint,
      });
    }
  } else {
    data = await response.text();
  }

  // Check HTTP Status
  if (!response.ok) {
    let errorCode = 'HTTP_ERROR';
    let errorMessage = `Request failed with status ${response.status}`;

    if (data && typeof data === 'object') {
      if (data.detail) {
        errorMessage = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      } else if (data.message) {
        errorMessage = data.message;
      }
      if (data.code) {
        errorCode = data.code;
      }
    }

    if (response.status === 401) {
      // Session expired or invalid
      authSession.clearToken();
      errorCode = 'UNAUTHORIZED';
      errorMessage = errorMessage || 'Your session has expired. Please sign in again.';
    }

    throw new ApiError(errorMessage, {
      status: response.status,
      code: errorCode,
      details: data,
      endpoint,
    });
  }

  return data;
}

/**
 * Typed API Endpoint Gateway.
 */
export const apiClient = {
  // System & Capabilities
  system: {
    health: () => request('/health'),
    capabilities: () => request('/api/v1/capabilities'),
  },

  // User Profile
  profile: {
    get: () => request('/api/v1/profile', { requiresAuth: true }),
    update: (data) => request('/api/v1/profile', { method: 'PUT', body: data, requiresAuth: true }),
  },

  // Health Profile & Medical Limitations
  healthProfile: {
    get: () => request('/api/v1/health-profile', { requiresAuth: true }),
    update: (data) => request('/api/v1/health-profile', { method: 'PUT', body: data, requiresAuth: true }),
  },

  // Movement Analysis Sessions (In-Memory Kinematics)
  sessions: {
    create: (config = null) => request('/api/v1/sessions', { method: 'POST', body: config ? { config } : null }),
    getStatus: (sessionId) => request(`/api/v1/sessions/${sessionId}`),
    getSummary: (sessionId) => request(`/api/v1/sessions/${sessionId}/summary`),
    reset: (sessionId) => request(`/api/v1/sessions/${sessionId}/reset`, { method: 'POST' }),
    terminate: (sessionId) => request(`/api/v1/sessions/${sessionId}`, { method: 'DELETE' }),
    sendLandmarks: (sessionId, payload) =>
      request(`/api/v1/sessions/${sessionId}/landmarks`, { method: 'POST', body: payload }),
    calibrateLandmarks: (sessionId, payload) =>
      request(`/api/v1/sessions/${sessionId}/calibration/landmarks`, { method: 'POST', body: payload }),
    resetCalibration: (sessionId) =>
      request(`/api/v1/sessions/${sessionId}/calibration/reset`, { method: 'POST' }),
  },

  // Workout History Persistence
  workouts: {
    list: (limit = 20, offset = 0) =>
      request(`/api/v1/workouts?limit=${limit}&offset=${offset}`, { requiresAuth: true }),
    get: (workoutId) => request(`/api/v1/workouts/${workoutId}`, { requiresAuth: true }),
    save: (payload) => request('/api/v1/workouts', { method: 'POST', body: payload, requiresAuth: true }),
    delete: (workoutId) => request(`/api/v1/workouts/${workoutId}`, { method: 'DELETE', requiresAuth: true }),
  },

  // Workout Plans
  plans: {
    getActive: () => request('/api/v1/plans/active', { requiresAuth: true }),
    save: (plan) => request('/api/v1/plans', { method: 'POST', body: plan, requiresAuth: true }),
  },

  // Adaptive Recommendations
  recommendations: {
    list: () => request('/api/v1/recommendations', { requiresAuth: true }),
    create: (rec) => request('/api/v1/recommendations', { method: 'POST', body: rec, requiresAuth: true }),
    updateStatus: (recId, status) =>
      request(`/api/v1/recommendations/${recId}`, { method: 'PATCH', body: { status }, requiresAuth: true }),
  },

  // Recovery Check-ins
  recovery: {
    getHistory: () => request('/api/v1/recovery', { requiresAuth: true }),
    log: (checkin) => request('/api/v1/recovery', { method: 'POST', body: checkin, requiresAuth: true }),
  },

  // Nutrition & Hydration
  nutrition: {
    getToday: (date = '') => request(`/api/v1/nutrition/today${date ? `?date=${date}` : ''}`, { requiresAuth: true }),
    updateToday: (payload) => request('/api/v1/nutrition/today', { method: 'POST', body: payload, requiresAuth: true }),
  },

  // Medical Documents
  documents: {
    list: () => request('/api/v1/documents', { requiresAuth: true }),
    get: (docId) => request(`/api/v1/documents/${docId}`, { requiresAuth: true }),
    presignUpload: (meta) => request('/api/v1/documents/presign-upload', { method: 'POST', body: meta, requiresAuth: true }),
    confirmUpload: (meta) => request('/api/v1/documents/confirm', { method: 'POST', body: meta, requiresAuth: true }),
    delete: (docId) => request(`/api/v1/documents/${docId}`, { method: 'DELETE', requiresAuth: true }),
  },

  // Grounded AI Chat Assistant
  chat: {
    sendMessage: (message, sessionId = null) =>
      request('/api/v1/chat/message', {
        method: 'POST',
        body: { message, session_id: sessionId },
        requiresAuth: true,
      }),
  },

  // Privacy & Consents
  privacy: {
    getConsent: () => request('/api/v1/privacy/consent', { requiresAuth: true }),
    updateConsent: (consents) => request('/api/v1/privacy/consent', { method: 'POST', body: consents, requiresAuth: true }),
    exportData: () => request('/api/v1/account/data-export', { method: 'POST', requiresAuth: true }),
    deleteAccount: () => request('/api/v1/account', { method: 'DELETE', requiresAuth: true }),
  },
};
