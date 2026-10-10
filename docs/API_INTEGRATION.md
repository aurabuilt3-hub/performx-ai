# PERFORMX Production HTTP REST API & Frontend Integration Guide

## 1. Overview & Architecture

The **PERFORMX HTTP API** exposes the bio-inspired movement analysis engine as a modern, high-performance REST service built on **FastAPI**. It connects frontend web applications (React, Next.js, Vue, Svelte, or native mobile clients) to the PERFORMX sensorimotor pipeline.

```
┌────────────────────────────────────────────────────────┐
│               Frontend Web Client                     │
│  (React / Next.js / Mobile Browser / Native App)      │
└───────────────┬────────────────────────┬───────────────┘
                │                        │
       Privacy Mode (Preferred)         Server Fallback Mode
       Client-Side MediaPipe            Raw Image Upload
       (33 Normalized Landmarks)        (Strict 5MB RAM Limit)
                │                        │
                ▼                        ▼
┌────────────────────────────────────────────────────────┐
│             FastAPI HTTP Layer (performx.http_api)     │
│  - CORS & Rate Limiting                                │
│  - Pydantic Input Validation                           │
│  - Session Management & Security Isolation             │
└───────────────────────┬────────────────────────────────┘
                        ▼
┌────────────────────────────────────────────────────────┐
│       Sensorimotor Engine & Biomechanical Core         │
│  - OneEuroFilter Adaptive Smoothing                    │
│  - Kuramoto Phase Oscillator (CPG Rhythm)              │
│  - Walknet Finite State Gating (IDLE->DESCENT->BOTTOM) │
│  - Standing Pose Calibration Service                   │
│  - Zero Disk Media Persistence (Volatile RAM Only)     │
└────────────────────────────────────────────────────────┘
```

### Key Architectural Guarantees:
1. **Privacy-Preserving Client-Side Vision (Recommended)**:
   - Frontends extract 33 landmarks on-device using `@mediapipe/pose` or MediaPipe Vision WebAssembly.
   - Only numerical coordinates $(x, y, z, \text{visibility})$ are sent over HTTP.
   - **Zero video or image frames ever leave the user's browser.**
2. **Server-Side Fallback Vision**:
   - Clients without WebAssembly support can stream image frames via multipart POST.
   - Frames are decoded strictly in volatile RAM, processed, and immediately garbage-collected.
   - **Zero disk writes or server-side media storage.**
3. **Session State Isolation**:
   - Every user or test runs in an isolated `MovementAnalysisSession` with independent filters, rep counters, and calibration state.
4. **Finite Number Guarantees**:
   - All input coordinates, timestamps, and parameters reject $\text{NaN}$ and $\pm\infty$.

---

## 2. Server Startup & OpenAPI Documentation

### Launching the API Server

Run uvicorn pointing to the ASGI factory:

```powershell
# Using the virtual environment
.\.venv\Scripts\uvicorn performx.http_api:app --host 0.0.0.0 --port 8000 --reload
```

### Interactive Documentation Endpoints:
- **Swagger UI (Interactive)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc (Specification)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema (JSON)**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 3. Configuration & CORS

### Cross-Origin Resource Sharing (CORS)
Configured via the `PERFORMX_CORS_ORIGINS` environment variable (comma-separated origins).

```powershell
# Default allowed origins if unset:
# http://localhost:3000, http://localhost:5173, http://127.0.0.1:3000, http://127.0.0.1:5173

# Custom configuration example:
$env:PERFORMX_CORS_ORIGINS = "https://app.performx.ai,http://localhost:3000"
.\.venv\Scripts\uvicorn performx.http_api:app --port 8000
```

---

## 4. Endpoints Reference

### 4.1 System & Capabilities

#### `GET /health`
Returns the operational health, pose engine type, active session count, and privacy commitments.

```bash
curl -X GET http://localhost:8000/health
```

**Response (`200 OK`):**
```json
{
  "status": "healthy",
  "pose_engine": "mediapipe_blazepose",
  "active_sessions": 0,
  "privacy_mode": "local_in_memory",
  "disk_persistence": false
}
```

#### `GET /api/v1/capabilities`
Returns supported exercises, biomechanical features, and default movement envelopes.

```bash
curl -X GET http://localhost:8000/api/v1/capabilities
```

**Response (`200 OK`):**
```json
{
  "supported_exercises": ["squat"],
  "features": [
    "knee_flexion_extension",
    "hip_flexion_extension",
    "torso_inclination",
    "bilateral_symmetry",
    "cpg_phase_oscillation",
    "bottom_dwell_time",
    "walknet_state_gating",
    "standing_pose_calibration"
  ],
  "default_squat_envelope": {
    "standing_knee_angle_deg": 155.0,
    "target_bottom_depth_deg": 95.0,
    "min_dwell_seconds": 0.2,
    "max_torso_lean_deg": 48.0,
    "min_symmetry_score": 0.78
  }
}
```

---

### 4.2 Session Lifecycle

#### `POST /api/v1/sessions`
Creates a new analysis session with default or custom biomechanical parameters.

```bash
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "standing_knee_angle": 155.0,
      "descent_trigger_angle": 140.0,
      "bottom_target_angle": 90.0,
      "min_bottom_dwell": 0.25,
      "max_torso_lean_deg": 45.0
    }
  }'
```

**Response (`201 Created`):**
```json
{
  "session_id": "b0825c95-3bc1-4e4b-9e47-e146eb767e91",
  "status": "active",
  "config": {
    "standing_knee_angle": 155.0,
    "descent_trigger_angle": 140.0,
    "bottom_target_angle": 90.0,
    "deep_squat_angle": 75.0,
    "min_bottom_dwell": 0.25,
    "max_bottom_dwell": 4.0,
    "min_rep_duration": 1.0,
    "max_torso_lean_deg": 45.0,
    "min_symmetry_score": 0.78,
    "min_visibility_conf": 0.5
  }
}
```

#### `GET /api/v1/sessions/{session_id}`
Returns the current active state, frames processed, and repetition counts.

```bash
curl -X GET http://localhost:8000/api/v1/sessions/b0825c95-3bc1-4e4b-9e47-e146eb767e91
```

**Response (`200 OK`):**
```json
{
  "session_id": "b0825c95-3bc1-4e4b-9e47-e146eb767e91",
  "is_active": true,
  "frames_processed": 120,
  "total_reps": 3,
  "valid_reps": 3,
  "current_phase": "IDLE"
}
```

#### `GET /api/v1/sessions/{session_id}/summary`
Retrieves aggregate metrics and explainable insights without ending the session.

```bash
curl -X GET http://localhost:8000/api/v1/sessions/b0825c95-3bc1-4e4b-9e47-e146eb767e91/summary
```

**Response (`200 OK`):**
```json
{
  "session_id": "b0825c95-3bc1-4e4b-9e47-e146eb767e91",
  "start_time": 1728574800.0,
  "end_time": 1728574825.0,
  "duration_seconds": 25.0,
  "total_frames_processed": 750,
  "total_reps": 5,
  "valid_reps": 5,
  "mean_symmetry": 0.94,
  "mean_rep_duration": 2.45,
  "error_count": 0,
  "metrics": {
    "total_completed_reps": 5,
    "accepted_reps": 5,
    "rejected_reps": 0,
    "incomplete_attempts": 0,
    "aborted_attempts": 0,
    "mean_duration": 2.45,
    "min_duration": 2.2,
    "max_duration": 2.8,
    "duration_range": 0.6,
    "mean_descent_duration": 1.1,
    "mean_bottom_dwell": 0.35,
    "mean_ascent_duration": 1.0,
    "mean_min_knee_angle": 88.5,
    "knee_angle_range": 4.0,
    "mean_rep_symmetry": 0.94,
    "mean_tracking_confidence": 0.96,
    "explainable_insights": [
      "5 repetitions successfully validated.",
      "Tempo consistency is excellent with 0.60s duration variation.",
      "Depth control is highly consistent with 4.0° range around 88.5°."
    ]
  }
}
```

#### `POST /api/v1/sessions/{session_id}/reset`
Resets the session's repetition count, filters, and calibration without recreating the session ID.

```bash
curl -X POST http://localhost:8000/api/v1/sessions/b0825c95-3bc1-4e4b-9e47-e146eb767e91/reset
```

**Response (`200 OK`):**
```json
{
  "status": "session_reset",
  "session_id": "b0825c95-3bc1-4e4b-9e47-e146eb767e91"
}
```

#### `DELETE /api/v1/sessions/{session_id}`
Safely terminates the session and returns its final summary. Frees all session memory.

```bash
curl -X DELETE http://localhost:8000/api/v1/sessions/b0825c95-3bc1-4e4b-9e47-e146eb767e91
```

---

### 4.3 Movement Analysis

#### `POST /api/v1/sessions/{session_id}/analysis/landmarks` (Preferred)
Direct landmark ingestion from client-side vision.

```bash
curl -X POST http://localhost:8000/api/v1/sessions/b0825c95-3bc1-4e4b-9e47-e146eb767e91/analysis/landmarks \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": 12.35,
    "landmarks": [
      {"x": 0.5, "y": 0.2, "z": 0.0, "visibility": 0.98},
      ...
    ]
  }'
```

**Response (`200 OK`):**
```json
{
  "timestamp": 12.35,
  "is_detected": true,
  "confidence": 0.95,
  "current_phase": "BOTTOM",
  "repetition_count": 2,
  "features": {
    "left_knee_angle": 88.2,
    "right_knee_angle": 89.1,
    "avg_knee_angle": 88.65,
    "left_hip_angle": 82.1,
    "right_hip_angle": 81.8,
    "torso_lean_angle": 28.4,
    "symmetry_score": 0.96,
    "normalized_hip_depth": 0.74
  },
  "oscillator_phase": 3.14,
  "bottom_dwell_time": 0.32,
  "last_rep_duration": 2.4,
  "active_alerts": [],
  "repetition_summary": null
}
```

#### `POST /api/v1/sessions/{session_id}/analysis/frame` (Server Vision Fallback)
Accepts an image file (`multipart/form-data`) with strict 5MB limit.

```bash
curl -X POST http://localhost:8000/api/v1/sessions/b0825c95-3bc1-4e4b-9e47-e146eb767e91/analysis/frame \
  -F "file=@frame.jpg;type=image/jpeg" \
  -F "timestamp=12.35"
```

---

### 4.4 Standing Calibration

#### `POST /api/v1/sessions/{session_id}/calibration/landmarks`
Feed standing landmark samples to calibrate body height proxy and resting knee angle.

```bash
curl -X POST http://localhost:8000/api/v1/sessions/b0825c95-3bc1-4e4b-9e47-e146eb767e91/calibration/landmarks \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": 1.0,
    "landmarks": [...]
  }'
```

**Response (`200 OK`):**
```json
{
  "status": "CALIBRATED",
  "confidence": 0.95,
  "standing_knee_angle": 165.2,
  "standing_torso_lean": 4.1,
  "femur_length_2d": 0.22,
  "tibia_length_2d": 0.23,
  "torso_length_2d": 0.32,
  "body_height_proxy_2d": 0.77,
  "sample_count": 30,
  "failure_reason": null
}
```

#### `POST /api/v1/sessions/{session_id}/calibration/reset`
Resets standing calibration.

```bash
curl -X POST http://localhost:8000/api/v1/sessions/b0825c95-3bc1-4e4b-9e47-e146eb767e91/calibration/reset
```

---

### 4.5 User Profiles & Workout Session Persistence (Supabase Auth)

Protected endpoints require a valid Supabase access token in the `Authorization: Bearer <TOKEN>` header. See [docs/SUPABASE_SETUP.md](SUPABASE_SETUP.md) for full authentication configuration and database schema.

#### `GET /api/v1/me/profile`
Retrieves the authenticated user's profile.

```bash
curl -X GET http://localhost:8000/api/v1/me/profile \
  -H "Authorization: Bearer <JWT_ACCESS_TOKEN>"
```

**Response (`200 OK`):**
```json
{
  "id": "11111111-1111-4111-8111-111111111111",
  "display_name": "Athlete Alpha",
  "created_at": "2026-10-10T12:00:00+00:00",
  "updated_at": "2026-10-10T12:05:00+00:00"
}
```

#### `PUT /api/v1/me/profile`
Updates the authenticated user's display name.

```bash
curl -X PUT http://localhost:8000/api/v1/me/profile \
  -H "Authorization: Bearer <JWT_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"display_name": "Jordan P."}'
```

#### `POST /api/v1/workouts`
Persists a completed workout summary to the user's permanent history with RLS enforcement. Can persist an active in-memory session by `session_id` or directly with a validated `summary` payload.

```bash
curl -X POST http://localhost:8000/api/v1/workouts \
  -H "Authorization: Bearer <JWT_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "b0825c95-3bc1-4e4b-9e47-e146eb767e91",
    "exercise_type": "squat"
  }'
```

**Response (`201 Created`):**
```json
{
  "id": "b0825c95-3bc1-4e4b-9e47-e146eb767e91",
  "user_id": "11111111-1111-4111-8111-111111111111",
  "exercise_type": "squat",
  "start_time": "2026-10-10T12:00:00+00:00",
  "end_time": "2026-10-10T12:00:25+00:00",
  "duration_seconds": 25.0,
  "total_frames_processed": 750,
  "total_reps": 5,
  "valid_reps": 5,
  "mean_symmetry": 0.94,
  "mean_rep_duration": 2.45,
  "summary_metrics": {
    "total_completed_reps": 5,
    "accepted_reps": 5,
    "rejected_reps": 0,
    "mean_duration": 2.45,
    "mean_min_knee_angle": 88.5,
    "mean_rep_symmetry": 0.94,
    "explainable_insights": [
      "5 repetitions successfully validated.",
      "Tempo consistency is excellent with 0.60s duration variation."
    ]
  },
  "created_at": "2026-10-10T12:00:26+00:00"
}
```

#### `GET /api/v1/workouts`
Lists the authenticated user's saved workout summaries with pagination (`limit` and `offset`).

```bash
curl -X GET "http://localhost:8000/api/v1/workouts?limit=10&offset=0" \
  -H "Authorization: Bearer <JWT_ACCESS_TOKEN>"
```

#### `GET /api/v1/workouts/{workout_id}`
Retrieves a specific workout session owned by the authenticated user.

```bash
curl -X GET "http://localhost:8000/api/v1/workouts/b0825c95-3bc1-4e4b-9e47-e146eb767e91" \
  -H "Authorization: Bearer <JWT_ACCESS_TOKEN>"
```

#### `DELETE /api/v1/workouts/{workout_id}`
Deletes a specific workout session owned by the authenticated user.

```bash
curl -X DELETE "http://localhost:8000/api/v1/workouts/b0825c95-3bc1-4e4b-9e47-e146eb767e91" \
  -H "Authorization: Bearer <JWT_ACCESS_TOKEN>"
```

---

## 5. Client Integration Example (TypeScript / React)

Below is an implementation of browser-side landmark extraction streamed to PERFORMX:

```typescript
import { Pose, Results } from '@mediapipe/pose';

const API_BASE = 'http://localhost:8000/api/v1';

export class PerformxClient {
  private sessionId: string | null = null;

  async startSession(): Promise<string> {
    const res = await fetch(`${API_BASE}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        config: {
          standing_knee_angle: 155.0,
          bottom_target_angle: 95.0,
        },
      }),
    });
    const data = await res.json();
    this.sessionId = data.session_id;
    return this.sessionId;
  }

  async sendLandmarks(results: Results, timestampSeconds: number) {
    if (!this.sessionId) throw new Error('Session not initialized');

    // Extract 33 landmarks from MediaPipe results
    const landmarks = results.poseLandmarks?.map((lm) => ({
      x: lm.x,
      y: lm.y,
      z: lm.z,
      visibility: lm.visibility ?? 1.0,
    })) ?? null;

    const res = await fetch(`${API_BASE}/sessions/${this.sessionId}/analysis/landmarks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        timestamp: timestampSeconds,
        landmarks,
      }),
    });

    return await res.json();
  }

  async finishSession() {
    if (!this.sessionId) return null;
    const res = await fetch(`${API_BASE}/sessions/${this.sessionId}`, {
      method: 'DELETE',
    });
    const summary = await res.json();
    this.sessionId = null;
    return summary;
  }
}
```

---

## 6. Error Handling

All errors return JSON with structured error codes:

```json
{
  "code": "SESSION_INACTIVE",
  "message": "Session 'nonexistent-uuid' not found or inactive",
  "timestamp": 1728574830.12,
  "details": {}
}
```

| HTTP Status | Error Code | Description |
| :--- | :--- | :--- |
| `400 Bad Request` | `INVALID_INPUT` / `FRAME_CORRUPT` | Invalid image bytes or corrupted payload |
| `401 Unauthorized` | `AUTHENTICATION_REQUIRED` | Missing, expired, or invalid Supabase JWT Bearer token |
| `404 Not Found` | `SESSION_INACTIVE` / `NOT_FOUND` | Session or resource does not exist |
| `413 Payload Too Large` | `FRAME_TOO_LARGE` / `FILE_TOO_LARGE` | Image (>5MB) or document (>15MB) exceeds size limit |
| `422 Unprocessable Content` | `INVALID_LANDMARK_DATA` / `VALIDATION_ERROR` | Malformed schemas or out-of-range parameters |

---

## 7. Extended Platform Endpoints Catalog

In addition to real-time session streaming, the PERFORMX API provides full platform support for user profiles, injury-aware health records, personalized workout plans, adaptive coaching recommendations, recovery check-ins, nutrition tracking, medical documents, and privacy controls.

All platform endpoints require `Authorization: Bearer <token>`:

- **User Profile**: `GET /api/v1/profile`, `PATCH /api/v1/profile`, `GET /api/v1/me/profile`
- **Health Profile & Sensitive Injuries**: `GET /api/v1/health-profile`, `PUT /api/v1/health-profile`
- **Workout Plans**: `GET /api/v1/plans/active`, `POST /api/v1/plans`
- **Adaptive Recommendations**: `GET /api/v1/recommendations`, `POST /api/v1/recommendations`, `PATCH /api/v1/recommendations/{id}`
- **Recovery Check-ins**: `GET /api/v1/recovery`, `POST /api/v1/recovery`
- **Daily Nutrition & Allergens**: `GET /api/v1/nutrition/today`, `POST /api/v1/nutrition/today`
- **Medical Document Presigned Flow**: `POST /api/v1/documents/presign-upload`, `POST /api/v1/documents/confirm`, `GET /api/v1/documents`, `DELETE /api/v1/documents/{id}`
- **Privacy Consents**: `GET /api/v1/privacy/consent`, `POST /api/v1/privacy/consent`
- **GDPR Data Export & Account Deletion**: `POST /api/v1/account/data-export`, `DELETE /api/v1/account`

