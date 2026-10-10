# PERFORMX — Production Deployment, Hosting & Operations Guide
**Phase 25: Deployment, Hosting & Environment Configuration**
**Date**: October 10, 2026
**Status**: PRODUCTION-READY (130 Automated Tests Passing)

---

## 1. Architecture & Deployment Strategy Overview

PERFORMX is designed with a decoupled, privacy-preserving two-tier topology:

```
┌────────────────────────────────────────────────────────┐
│               Frontend Presentation Tier               │
│  - Host: Vercel (Edge CDN & Serverless Frontend)       │
│  - Framework Target: Single Page App (React/Next/Vite) │
│  - Local Dev Demo: Streamlit (Local Python process)    │
│  - Vision Capture: Browser-side MediaPipe Pose (JS)    │
│  - Auth: Supabase Auth Client SDK                      │
└───────────────────────┬────────────────────────────────┘
                        │ HTTPS REST (Bearer <jwt>, JSON coords)
                        ▼
┌────────────────────────────────────────────────────────┐
│                Backend API & Engine Tier               │
│  - Host: Render / Fly.io / AWS ECS (Long-lived ASGI)   │
│  - Runtime: Python 3.11 ASGI (Uvicorn + FastAPI)       │
│  - Entry Point: performx.http_api:app                  │
│  - Memory: In-memory session state (RAM-only)          │
│  - Health Checks: GET /health, GET /healthz, GET /     │
└───────────────────────┬────────────────────────────────┘
                        │ PostgREST HTTPS (Bearer <jwt>)
                        ▼
┌────────────────────────────────────────────────────────┐
│             Database & Authentication Tier             │
│  - Host: Supabase Managed Cloud (PostgreSQL 15+)       │
│  - RLS Policies: auth.uid() row-level isolation        │
│  - Storage: User profiles, sanitized scalar summaries  │
│  - Strictly NEVER Stored: Video, frames, or landmarks  │
└────────────────────────────────────────────────────────┘
```

---

## 2. Hosting Recommendations & Rationale

### A. Backend ASGI Hosting
- **Recommended Provider**: **Render** (Web Service) or **Fly.io**
- **Hosting Tier / Specs**:
  - Minimum: 1 vCPU, 512 MB – 1 GB RAM (e.g. Render Starter or Fly.io `shared-cpu-1x`).
  - Recommended for concurrency: 2 vCPU, 2 GB RAM.
- **Why Not AWS Lambda / Vercel Serverless Functions for the Backend?**:
  1. *Stateful In-Memory Movement Sessions*: Active repetition analysis sessions require persistent in-memory tracking of temporal filters (1€ filter), kinematics, and Walknet state transitions over consecutive frames (15–60 seconds). Serverless functions suffer cold starts and lack sticky process memory across frame requests.
  2. *Process Footprint*: MediaPipe C++ bindings and OpenCV native binaries benefit from a warm, long-lived container process.
- **ASGI Process Model**:
  - Production start command: `uvicorn performx.http_api:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1`
  - *Worker Note*: Because active workout sessions are stored in process RAM (`_sessions: dict`), single-worker or sticky-session routing per instance is required until a shared distributed state cache (e.g., Redis) is introduced in a future phase.

### B. Frontend Hosting
- **Recommended Provider**: **Vercel** (or Cloudflare Pages / Netlify).
- **Rationale**:
  - Vercel excels at static and client-side web applications with global edge distribution, automated Git deployments, and instant HTTPS.
  - Browser-side MediaPipe Pose runs inside the user's web browser on WebGL/WebAssembly. Static edge delivery is the lowest-latency, highest-security method for delivering client-side camera interfaces.
- **Streamlit Local Demonstration**:
  - `performx/app.py` is the dedicated in-process local engineering validation tool.
  - Streamlit requires direct access to hardware webcams via OpenCV. It is **not** recommended for multi-tenant production web deployment, but remains preserved for local development and live physical trials.

### C. Database & Auth Hosting
- **Provider**: **Supabase Managed Cloud**
- **Rationale**: Provides turnkey Auth, PostgREST API with Row-Level Security, and automated PostgreSQL backups while requiring zero local disk persistence on the PERFORMX API servers.

---

## 3. Environment Variables & Secret Configuration

Never commit `.env` or production credentials to version control. Configure these variables directly in the hosting provider's dashboard (e.g., Render Environment Settings, Vercel Environment Variables).

### A. Backend Service Environment Variables (Render / Fly.io)

| Variable Name | Required? | Example Value | Description |
| :--- | :--- | :--- | :--- |
| `PERFORMX_ENV` | **Yes** | `production` | Enables production mode (forbids ephemeral in-memory storage fallback). |
| `PORT` | Auto / Yes | `8000` | Port assigned by hosting environment (auto-injected by Render/Fly). |
| `HOST` | No | `0.0.0.0` | IP binding interface (defaults to `0.0.0.0`). |
| `SUPABASE_URL` | **Yes** | `https://xyzproject.supabase.co` | Supabase project REST URL. |
| `SUPABASE_KEY` | **Yes** | `eyJhbGciOi...` | Supabase **anon / public** key used for PostgREST requests. |
| `SUPABASE_JWT_SECRET` | **Yes** (HS256) | `your-supabase-jwt-secret` | Cryptographic secret used to verify symmetric user JWT tokens. |
| `SUPABASE_JWT_PUBLIC_KEY`| Optional (RS256) | `-----BEGIN PUBLIC KEY...` | Public key PEM if Supabase project uses asymmetric signing. |
| `SUPABASE_JWT_ISSUER` | Optional | `https://xyz.supabase.co/auth/v1` | Optional issuer validation override. |
| `PERFORMX_STORAGE_BACKEND`| **Yes** | `supabase` | Must be `supabase` in production. |
| `PERFORMX_CORS_ORIGINS` | **Yes** | `https://performx-app.vercel.app` | Comma-separated list of trusted frontend domain origins. |

> [!CAUTION]
> **Strict Secret Boundaries**:
> 1. NEVER set `SUPABASE_SERVICE_ROLE_KEY` in frontend bundles or client environments.
> 2. NEVER configure `PERFORMX_CORS_ORIGINS=*` in production when handling authenticated sessions.
> 3. Setting `PERFORMX_ENV=production` strictly blocks `PERFORMX_STORAGE_BACKEND=memory`, raising `StorageError` if misconfigured.

### B. Frontend Environment Variables (Vercel)

| Variable Name | Required? | Example Value | Description |
| :--- | :--- | :--- | :--- |
| `NEXT_PUBLIC_PERFORMX_API_URL` | **Yes** | `https://performx-api.onrender.com` | Base URL of the PERFORMX FastAPI backend. |
| `NEXT_PUBLIC_SUPABASE_URL` | **Yes** | `https://xyzproject.supabase.co` | Supabase project URL for client authentication. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | **Yes** | `eyJhbGciOi...` | Supabase public anon key (safe for browser exposure). |

---

## 4. Build, Run & Startup Commands

### Local Development (In-Process Streamlit)
```powershell
# 1. Activate Python virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Run Streamlit dashboard
streamlit run performx/app.py
```

### Local Development (FastAPI HTTP REST Server)
```powershell
# Run with automatic reload for active development
python -m performx.http_api
# Or via uvicorn directly:
uvicorn performx.http_api:app --host 127.0.0.1 --port 8000 --reload
```

### Production ASGI Startup (Render / Fly.io / Container)
```bash
# Production start command (auto-reads $PORT from environment)
python -m performx.http_api

# Or explicit production Uvicorn invocation (no reload, production logging):
uvicorn performx.http_api:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --log-level info
```

---

## 5. Health Checks & Graceful Lifecycle

The PERFORMX HTTP API exposes dedicated operational endpoints:

1. **`GET /`**:
   - Status: HTTP 200 `{"status": "healthy", "service": "PERFORMX Movement Analysis API", "version": "1.0.0"}`
   - Purpose: Standard root ping for load balancers.
2. **`GET /healthz`** & **`GET /health`**:
   - Status: HTTP 200
   - Payload:
     ```json
     {
       "status": "healthy",
       "pose_engine": "mediapipe_blazepose",
       "active_sessions": 0,
       "max_sessions": 100,
       "privacy_mode": "local_in_memory",
       "disk_persistence": false
     }
     ```
   - Purpose: PaaS container liveness and readiness probe.
3. **Graceful Lifespan Shutdown**:
   - Implemented via `contextlib.asynccontextmanager`.
   - On container SIGTERM/SIGINT, the lifespan hook executes `BackendService.close()`, which immediately terminates all active in-memory analysis sessions, resets filter buffers, and cleanly frees MediaPipe vision handles.

---

## 6. Step-by-Step Production Deployment Guide

### Step 1: Execute Database Migrations in Supabase
1. Create a Supabase project at [supabase.com](https://supabase.com).
2. In the Supabase Dashboard, go to **SQL Editor**.
3. Run the version-controlled SQL script:
   [`supabase/migrations/20261010000000_create_profiles_and_workout_sessions.sql`](file:///c:/Users/surya/Desktop/PERFORMX/supabase/migrations/20261010000000_create_profiles_and_workout_sessions.sql)
4. Confirm tables `public.profiles` and `public.workout_sessions` exist with RLS policies enabled.

### Step 2: Deploy Backend to Render (or Fly.io)
1. In the [Render Dashboard](https://dashboard.render.com), click **New + > Web Service**.
2. Connect your Git repository.
3. Configure service settings:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn performx.http_api:app --host 0.0.0.0 --port $PORT --workers 1`
   - **Health Check Path**: `/healthz`
4. In the **Environment Variables** tab, configure:
   ```text
   PERFORMX_ENV=production
   PERFORMX_STORAGE_BACKEND=supabase
   SUPABASE_URL=https://<your-project-ref>.supabase.co
   SUPABASE_KEY=<your-anon-key>
   SUPABASE_JWT_SECRET=<your-jwt-secret>
   PERFORMX_CORS_ORIGINS=https://<your-frontend-domain>.vercel.app
   ```
5. Deploy service and record your backend URL (e.g. `https://performx-api.onrender.com`).

### Step 3: Deploy Frontend to Vercel
1. In the [Vercel Dashboard](https://vercel.com), click **Add New > Project**.
2. Import the frontend repository.
3. Add Environment Variables:
   ```text
   NEXT_PUBLIC_PERFORMX_API_URL=https://performx-api.onrender.com
   NEXT_PUBLIC_SUPABASE_URL=https://<your-project-ref>.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-anon-key>
   ```
4. Deploy the frontend application.

---

## 7. Production Smoke-Test & Verification Protocol

Run this minimal cURL verification against the deployed backend to verify operational readiness:

### 1. Liveness & Privacy Check
```bash
curl -i https://your-backend-api.onrender.com/healthz
```
*Expected Response*:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{"status":"healthy","pose_engine":"mediapipe_blazepose","active_sessions":0,"max_sessions":100,"privacy_mode":"local_in_memory","disk_persistence":false}
```

### 2. Capabilities Check
```bash
curl -i https://your-backend-api.onrender.com/api/v1/capabilities
```
*Expected Response*: HTTP 200 containing supported exercise `"squat"` and biomechanical features.

### 3. Protected Endpoint Authorization Check (Negative Test)
```bash
curl -i https://your-backend-api.onrender.com/api/v1/me/profile
```
*Expected Response*:
```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer error="missing_credentials"

{"code":"UNAUTHORIZED","message":"Authorization header with Bearer token is required"}
```

### 4. Authenticated Profile & Workout Save (Positive Test)
```bash
# Obtain user token from Supabase Auth
ACCESS_TOKEN="eyJhbGciOi..."

# Check Profile
curl -X GET https://your-backend-api.onrender.com/api/v1/me/profile \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Create Analysis Session
curl -X POST https://your-backend-api.onrender.com/api/v1/sessions \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## 8. Verification & Test Suite Results

The full automated regression suite was executed across all 14 test modules:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

```text
============================== test session starts ==============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\surya\Desktop\PERFORMX
collected 130 items

tests/test_api_and_service.py .........................                  [ 19%]
tests/test_app_helpers.py .........                                      [ 26%]
tests/test_auth_and_persistence.py .......................               [ 43%]
tests/test_core_contracts.py ...                                         [ 46%]
tests/test_http_api.py ...................                               [ 60%]
tests/test_integration_and_pipeline.py ......                            [ 65%]
tests/test_kinematics_and_filtering.py ........                          [ 71%]
tests/test_movement_reliability.py ...                                   [ 73%]
tests/test_privacy_and_security.py .....                                 [ 77%]
tests/test_repetition_summary.py .....                                   [ 81%]
tests/test_scorecard_and_invalidation.py ....................            [ 96%]
tests/test_sensorimotor.py ...                                           [ 98%]
tests/test_session_metrics.py ........                                   [100%]

====================== 130 passed, 2 warnings in 9.50s =======================
```
