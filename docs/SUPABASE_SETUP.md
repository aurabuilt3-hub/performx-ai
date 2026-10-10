# PERFORMX Supabase Setup, Authentication & Persistence Guide

## 1. Overview & Architecture

PERFORMX integrates **Supabase** for user authentication, profile management, and persistent workout session history while strictly maintaining its privacy-first computer vision design.

```
┌────────────────────────────────────────────────────────┐
│                   Frontend Client                      │
│      - Authenticates via Supabase Auth (OAuth/Email)   │
│      - Holds user JWT access token in memory           │
└───────────────────────┬────────────────────────────────┘
                        │ Authorization: Bearer <jwt>
                        ▼
┌────────────────────────────────────────────────────────┐
│               PERFORMX FastAPI Backend                 │
│  - Verifies JWT (HMAC-SHA256 via SUPABASE_JWT_SECRET)  │
│  - Extracts authenticated user_id from token 'sub'     │
│  - Validates session contracts (finite values, scalars)│
└───────────────────────┬────────────────────────────────┘
                        │ PostgREST Client (with Bearer Token)
                        ▼
┌────────────────────────────────────────────────────────┐
│            Supabase Database & Row-Level Security      │
│  - public.profiles (auth.uid() = id)                   │
│  - public.workout_sessions (auth.uid() = user_id)      │
│  - Zero raw images, frames, or landmarks stored        │
└────────────────────────────────────────────────────────┘
```

---

## 2. Supabase Project Setup

### A. Create Project
1. Log in to your [Supabase Dashboard](https://supabase.com/dashboard).
2. Click **New Project**, specify an organization, project name (e.g. `performx-prod`), database password, and preferred region.
3. Wait for database provisioning to complete.

### B. Retrieve API Credentials
Navigate to **Project Settings > API**:
- **Project URL**: `https://<your-project-ref>.supabase.co`
- **anon / public key**: Used by frontend clients and backend PostgREST requests.
Navigate to **Project Settings > API > JWT Settings**:
- **JWT Secret**: Used by the PERFORMX backend to cryptographically verify token signatures.

---

## 3. SQL Migration Execution

The version-controlled database migration is located at:
[`supabase/migrations/20261010000000_create_profiles_and_workout_sessions.sql`](file:///c:/Users/surya/Desktop/PERFORMX/supabase/migrations/20261010000000_create_profiles_and_workout_sessions.sql)

### Option 1: Supabase CLI (Recommended)
```powershell
# Link CLI to your project
supabase link --project-ref <your-project-ref>

# Push the migration
supabase db push
```

### Option 2: Supabase Web Dashboard
1. Open the **SQL Editor** in your Supabase dashboard.
2. Paste the contents of `supabase/migrations/20261010000000_create_profiles_and_workout_sessions.sql`.
3. Click **Run**.

---

## 4. Database Schema & Row-Level Security (RLS)

### Table: `public.profiles`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `uuid` | Primary Key, References `auth.users(id) ON DELETE CASCADE` | Authenticated user ID |
| `display_name` | `text` | Nullable | User display name |
| `created_at` | `timestamptz` | Not Null, Default UTC `now()` | Account creation time |
| `updated_at` | `timestamptz` | Not Null, Default UTC `now()` | Last profile update |

**Row-Level Security Policies:**
- `SELECT`: `auth.uid() = id`
- `INSERT`: `auth.uid() = id`
- `UPDATE`: `auth.uid() = id`
- `DELETE`: `auth.uid() = id`

### Table: `public.workout_sessions`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `uuid` | Primary Key | Workout session identifier |
| `user_id` | `uuid` | Not Null, References `auth.users(id) ON DELETE CASCADE` | Session owner |
| `exercise_type` | `text` | Not Null, Default `'squat'` | Exercise type |
| `start_time` | `timestamptz` | Not Null | UTC workout start time |
| `end_time` | `timestamptz` | Not Null | UTC workout end time |
| `duration_seconds`| `float8` | Not Null, $\ge 0$ | Total duration in seconds |
| `total_frames_processed` | `integer` | Not Null, $\ge 0$ | Total analyzed frames |
| `total_reps` | `integer` | Not Null, $\ge 0$ | Repetition attempts |
| `valid_reps` | `integer` | Not Null, $\ge 0$ | Valid repetitions |
| `mean_symmetry` | `float8` | Not Null, $\in [0, 1]$ | Bilateral symmetry score |
| `mean_rep_duration` | `float8` | Not Null, $\ge 0$ | Mean repetition tempo |
| `summary_metrics` | `jsonb` | Not Null, Default `'{}'` | Clean scalar summary metrics |
| `created_at` | `timestamptz` | Not Null, Default UTC `now()` | Database insertion time |

**Row-Level Security Policies:**
- `SELECT`: `auth.uid() = user_id`
- `INSERT`: `auth.uid() = user_id`
- `UPDATE`: `auth.uid() = user_id`
- `DELETE`: `auth.uid() = user_id`

When a user account is deleted from `auth.users`, the foreign keys configured with `ON DELETE CASCADE` automatically purge the user's profile and all associated workout summaries.

---

## 5. Private Medical Documents Storage Bucket Configuration

PERFORMX uses a private Supabase Storage bucket (`medical-documents`) to store confidential medical clearances, physician notes, and injury documentation with strict user isolation:

### Bucket Properties:
- **Bucket ID**: `medical-documents`
- **Public**: `false` (Private bucket; files are NOT accessible via public URLs)
- **File size limit**: `15MB` (15,728,640 bytes)
- **Allowed MIME types**: `application/pdf`, `image/png`, `image/jpeg`

### SQL Configuration for Storage RLS:
```sql
-- Create private storage bucket
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
    'medical-documents',
    'medical-documents',
    false,
    15728640,
    array['application/pdf', 'image/png', 'image/jpeg']::text[]
)
on conflict (id) do nothing;

-- RLS: Users can upload documents only to their own directory (users/<user_id>/*)
create policy "Users can upload their own medical documents"
    on storage.objects for insert
    with check (
        bucket_id = 'medical-documents'
        and (storage.foldername(name))[1] = 'users'
        and (storage.foldername(name))[2] = auth.uid()::text
    );

-- RLS: Users can view and download only their own medical documents
create policy "Users can read their own medical documents"
    on storage.objects for select
    using (
        bucket_id = 'medical-documents'
        and (storage.foldername(name))[1] = 'users'
        and (storage.foldername(name))[2] = auth.uid()::text
    );

-- RLS: Users can delete only their own medical documents
create policy "Users can delete their own medical documents"
    on storage.objects for delete
    using (
        bucket_id = 'medical-documents'
        and (storage.foldername(name))[1] = 'users'
        and (storage.foldername(name))[2] = auth.uid()::text
    );
```

---

## 5. Privacy Guarantees: What Is Stored vs. What Is Never Stored

### Stored in Database:
- Aggregate repetition counts (`total_reps`, `valid_reps`, `rejected_reps`).
- Timing statistics (`mean_duration`, `min_duration`, `max_duration`, `bottom_dwell`).
- Derived kinematic angles (`mean_min_knee_angle`, `knee_angle_range`, `mean_symmetry`).
- Neutral explainable feedback strings (e.g., `"Depth control consistent around 88°."`).

### Strictly NEVER Stored:
- **No camera video streams or video files.**
- **No single image frames, photos, or raw pixels.**
- **No landmark coordinate arrays** (e.g. MediaPipe $x, y, z$ coordinates).
- **No biometrics or facial geometry.**

All landmark processing occurs ephemeral in volatile memory.

---

## 6. Environment Variables

Configure your local `.env` file (copied from `.env.example`):

```bash
# Supabase Project Credentials
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_JWT_SECRET=your-supabase-jwt-secret

# Storage Backend ('supabase' for cloud, 'memory' for local test runs)
PERFORMX_STORAGE_BACKEND=supabase

# CORS Origins
PERFORMX_CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

> **Security Rule:** Never commit `.env` to git or expose `SUPABASE_JWT_SECRET` to browser code.

---

## 7. Example Authenticated Requests

### Frontend JavaScript (Obtaining Token & Calling PERFORMX):
```typescript
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  'https://your-project-ref.supabase.co',
  'your-anon-key'
);

// 1. Sign in
const { data, error } = await supabase.auth.signInWithPassword({
  email: 'athlete@example.com',
  password: 'secure-password',
});
const accessToken = data.session?.access_token;

// 2. Fetch User Profile from PERFORMX API
const profileRes = await fetch('http://localhost:8000/api/v1/me/profile', {
  headers: {
    Authorization: `Bearer ${accessToken}`,
  },
});
const profile = await profileRes.json();

// 3. Save Workout Summary
const saveRes = await fetch('http://localhost:8000/api/v1/workouts', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${accessToken}`,
  },
  body: JSON.stringify({
    session_id: 'your-active-session-id',
    exercise_type: 'squat',
  }),
});
const savedWorkout = await saveRes.json();
```

### cURL Examples:

#### Get Profile:
```bash
curl -X GET http://localhost:8000/api/v1/me/profile \
  -H "Authorization: Bearer <USER_ACCESS_TOKEN>"
```

#### Update Profile:
```bash
curl -X PUT http://localhost:8000/api/v1/me/profile \
  -H "Authorization: Bearer <USER_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"display_name": "Jordan P."}'
```

#### List Saved Workouts:
```bash
curl -X GET "http://localhost:8000/api/v1/workouts?limit=10&offset=0" \
  -H "Authorization: Bearer <USER_ACCESS_TOKEN>"
```

---

## 8. Local Testing & Verification

Run automated security and authentication tests:

```powershell
.\.venv\Scripts\pytest -v tests/test_auth_and_persistence.py
```

The test suite uses isolated mock repositories to verify token expiration, wrong secret signatures, malformed payloads, cross-user isolation, idempotency, and privacy filtering without requiring an active internet connection.
