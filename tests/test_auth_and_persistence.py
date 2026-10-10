"""Tests for PERFORMX Supabase Authentication, Profiles, and Workout Session Persistence."""

from datetime import datetime, timezone
import time
import uuid

import jwt
import pytest
from starlette.testclient import TestClient

from performx.api import BackendService
from performx.contracts import SessionMetrics, SessionSummary
from performx.core import SquatConfig
from performx.http_api import create_app
from performx.storage import InMemoryWorkoutStorage, sanitize_summary_metrics


TEST_JWT_SECRET = "super-secret-supabase-jwt-key-for-testing-12345678"
USER_A_ID = "11111111-1111-4111-8111-111111111111"
USER_B_ID = "22222222-2222-4222-8222-222222222222"


def generate_jwt(
    user_id: str = USER_A_ID,
    secret: str = TEST_JWT_SECRET,
    expires_in_seconds: int = 3600,
    audience: str = "authenticated",
    sub: str | None = None,
) -> str:
    """Generate a test Supabase-format HS256 JWT access token."""
    now = int(time.time())
    payload = {
        "sub": sub if sub is not None else user_id,
        "aud": audience,
        "iat": now,
        "exp": now + expires_in_seconds,
        "role": "authenticated",
        "email": f"user-{user_id[:8]}@example.com",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture
def auth_env(monkeypatch):
    """Ensure test JWT secret is configured in the environment."""
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)


@pytest.fixture
def test_setup(auth_env):
    """Provide isolated BackendService, InMemoryWorkoutStorage, and TestClient."""
    backend_service = BackendService()
    storage = InMemoryWorkoutStorage()
    app = create_app(backend_service=backend_service, storage=storage)
    client = TestClient(app)
    return client, backend_service, storage


# ==========================================
# 1. Authentication Token Verification Tests
# ==========================================

def test_protected_route_missing_token_returns_401(test_setup):
    client, _, _ = test_setup
    res = client.get("/api/v1/me/profile")
    assert res.status_code == 401
    assert "Missing required authentication credentials" in res.json()["detail"]


def test_protected_route_malformed_token_returns_401(test_setup):
    client, _, _ = test_setup
    res = client.get("/api/v1/me/profile", headers={"Authorization": "Bearer not-a-valid-jwt"})
    assert res.status_code == 401
    assert "Invalid authentication token" in res.json()["detail"]


def test_protected_route_expired_token_returns_401(test_setup):
    client, _, _ = test_setup
    expired_token = generate_jwt(expires_in_seconds=-60)  # Expired 60s ago
    res = client.get("/api/v1/me/profile", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401
    assert "expired" in res.json()["detail"].lower()


def test_protected_route_wrong_secret_signature_returns_401(test_setup):
    client, _, _ = test_setup
    tampered_token = generate_jwt(secret="wrong-secret-signature-key-at-least-32-bytes-long")
    res = client.get("/api/v1/me/profile", headers={"Authorization": f"Bearer {tampered_token}"})
    assert res.status_code == 401
    assert "Invalid authentication token" in res.json()["detail"]


def test_protected_route_invalid_audience_returns_401(test_setup):
    client, _, _ = test_setup
    wrong_aud_token = generate_jwt(audience="wrong-audience")
    res = client.get("/api/v1/me/profile", headers={"Authorization": f"Bearer {wrong_aud_token}"})
    assert res.status_code == 401


def test_protected_route_non_uuid_subject_returns_401(test_setup):
    client, _, _ = test_setup
    invalid_sub_token = generate_jwt(sub="not-a-valid-uuid-string")
    res = client.get("/api/v1/me/profile", headers={"Authorization": f"Bearer {invalid_sub_token}"})
    assert res.status_code == 401
    assert "must be a valid UUID" in res.json()["detail"]


# ==========================================
# 2. User Profiles Tests
# ==========================================

def test_profile_initial_and_update_workflow(test_setup):
    client, _, _ = test_setup
    token_a = generate_jwt(user_id=USER_A_ID)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 1. Fetch initial profile (auto-provisions blank profile)
    res_get = client.get("/api/v1/me/profile", headers=headers_a)
    assert res_get.status_code == 200
    assert res_get.json()["id"] == USER_A_ID

    # 2. Update display name
    res_put = client.put(
        "/api/v1/me/profile",
        json={"display_name": "Athlete Alpha"},
        headers=headers_a,
    )
    assert res_put.status_code == 200
    assert res_put.json()["display_name"] == "Athlete Alpha"

    # 3. Retrieve updated profile
    res_get2 = client.get("/api/v1/me/profile", headers=headers_a)
    assert res_get2.json()["display_name"] == "Athlete Alpha"


def test_profile_isolation_between_users(test_setup):
    client, _, _ = test_setup
    token_a = generate_jwt(user_id=USER_A_ID)
    token_b = generate_jwt(user_id=USER_B_ID)

    # Set user A profile
    client.put("/api/v1/me/profile", json={"display_name": "User A"}, headers={"Authorization": f"Bearer {token_a}"})
    # Set user B profile
    client.put("/api/v1/me/profile", json={"display_name": "User B"}, headers={"Authorization": f"Bearer {token_b}"})

    # Verify User A only sees User A
    res_a = client.get("/api/v1/me/profile", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.json()["display_name"] == "User A"
    assert res_a.json()["id"] == USER_A_ID

    # Verify User B only sees User B
    res_b = client.get("/api/v1/me/profile", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.json()["display_name"] == "User B"
    assert res_b.json()["id"] == USER_B_ID


# ==========================================
# 3. In-Memory Session Ownership & Gating Tests
# ==========================================

def test_authenticated_session_creation_binds_ownership(test_setup):
    client, _, _ = test_setup
    token_a = generate_jwt(user_id=USER_A_ID)
    res = client.post("/api/v1/sessions", headers={"Authorization": f"Bearer {token_a}"})
    assert res.status_code == 201
    data = res.json()
    assert data["user_id"] == USER_A_ID
    session_id = data["session_id"]

    # User A can access session status
    res_a = client.get(f"/api/v1/sessions/{session_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == 200

    # User B attempting to access User A's session receives 403 Forbidden
    token_b = generate_jwt(user_id=USER_B_ID)
    res_b = client.get(f"/api/v1/sessions/{session_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 403
    assert "owned by another user" in res_b.json()["detail"]

    # Unauthenticated client attempting to access User A's session receives 401
    res_anon = client.get(f"/api/v1/sessions/{session_id}")
    assert res_anon.status_code == 401


# ==========================================
# 4. Workout Session Persistence & Privacy Tests
# ==========================================

def test_save_workout_from_active_session(test_setup):
    client, _, _ = test_setup
    token_a = generate_jwt(user_id=USER_A_ID)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 1. Create session bound to User A
    create_res = client.post("/api/v1/sessions", headers=headers_a)
    session_id = create_res.json()["session_id"]

    # 2. Save workout directly via session_id
    save_res = client.post(
        "/api/v1/workouts",
        json={"session_id": session_id, "exercise_type": "squat"},
        headers=headers_a,
    )
    assert save_res.status_code == 201
    saved_data = save_res.json()
    assert saved_data["id"] == session_id
    assert saved_data["user_id"] == USER_A_ID
    assert saved_data["exercise_type"] == "squat"
    assert "summary_metrics" in saved_data


def test_save_workout_direct_payload(test_setup):
    client, _, _ = test_setup
    token_a = generate_jwt(user_id=USER_A_ID)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    workout_id = str(uuid.uuid4())
    payload = {
        "summary": {
            "session_id": workout_id,
            "start_time": 1728574800.0,
            "end_time": 1728574845.0,
            "total_frames_processed": 1350,
            "total_reps": 10,
            "valid_reps": 10,
            "mean_symmetry": 0.94,
            "mean_rep_duration": 2.3,
            "metrics": {
                "total_completed_reps": 10,
                "accepted_reps": 10,
                "rejected_reps": 0,
                "incomplete_attempts": 0,
                "aborted_attempts": 0,
                "mean_duration": 2.3,
                "min_duration": 2.1,
                "max_duration": 2.5,
                "duration_range": 0.4,
                "mean_descent_duration": 1.1,
                "mean_bottom_dwell": 0.25,
                "mean_ascent_duration": 0.95,
                "mean_min_knee_angle": 88.0,
                "knee_angle_range": 3.5,
                "mean_rep_symmetry": 0.94,
                "mean_tracking_confidence": 0.96,
                "explainable_insights": ["Cadence consistent.", "Form excellent."],
            },
        },
        "exercise_type": "squat",
    }

    res = client.post("/api/v1/workouts", json=payload, headers=headers_a)
    assert res.status_code == 201
    data = res.json()
    assert data["id"] == workout_id
    assert data["user_id"] == USER_A_ID
    assert data["total_reps"] == 10
    assert data["summary_metrics"]["mean_min_knee_angle"] == 88.0


def test_privacy_guarantee_zero_raw_vision_persisted(test_setup):
    """Verify that stored summary metrics strictly contain derived scalars and zero video/landmarks."""
    client, _, storage = test_setup
    token_a = generate_jwt(user_id=USER_A_ID)

    workout_id = str(uuid.uuid4())
    metrics = SessionMetrics(
        total_completed_reps=5,
        accepted_reps=5,
        rejected_reps=0,
        incomplete_attempts=0,
        aborted_attempts=0,
        mean_duration=2.5,
        min_duration=2.2,
        max_duration=2.8,
        duration_range=0.6,
        mean_descent_duration=1.2,
        mean_bottom_dwell=0.3,
        mean_ascent_duration=1.0,
        mean_min_knee_angle=90.0,
        knee_angle_range=4.0,
        mean_rep_symmetry=0.92,
        mean_tracking_confidence=0.95,
        explainable_insights=["5 repetitions validated."],
    )
    summary = SessionSummary(
        session_id=workout_id,
        start_time=100.0,
        end_time=125.0,
        total_frames_processed=750,
        total_reps=5,
        valid_reps=5,
        mean_symmetry=0.92,
        mean_rep_duration=2.5,
        config=SquatConfig(),
        metrics=metrics,
    )

    clean_metrics = sanitize_summary_metrics(summary)

    # Verification: check forbidden keys
    forbidden_keys = {"coords", "world_coords", "frame", "frames", "landmarks", "image", "rgb"}
    for key in forbidden_keys:
        assert key not in clean_metrics


def test_workout_idempotency_on_repeated_save(test_setup):
    """Ensure saving the same session summary twice returns the existing record without error."""
    client, _, _ = test_setup
    token_a = generate_jwt(user_id=USER_A_ID)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    workout_id = str(uuid.uuid4())
    payload = {
        "summary": {
            "session_id": workout_id,
            "start_time": 100.0,
            "end_time": 115.0,
            "total_frames_processed": 450,
            "total_reps": 3,
            "valid_reps": 3,
            "mean_symmetry": 0.95,
            "mean_rep_duration": 2.4,
        },
        "exercise_type": "squat",
    }

    # First save
    res1 = client.post("/api/v1/workouts", json=payload, headers=headers_a)
    assert res1.status_code == 201

    # Second save with identical payload (retry)
    res2 = client.post("/api/v1/workouts", json=payload, headers=headers_a)
    assert res2.status_code == 201
    assert res2.json()["id"] == res1.json()["id"]


def test_cross_user_workout_isolation(test_setup):
    """User B cannot view or delete workouts belonging to User A."""
    client, _, _ = test_setup
    token_a = generate_jwt(user_id=USER_A_ID)
    token_b = generate_jwt(user_id=USER_B_ID)

    workout_id = str(uuid.uuid4())
    payload = {
        "summary": {
            "session_id": workout_id,
            "start_time": 100.0,
            "end_time": 115.0,
            "total_frames_processed": 450,
            "total_reps": 3,
            "valid_reps": 3,
            "mean_symmetry": 0.95,
            "mean_rep_duration": 2.4,
        },
    }

    # User A saves workout
    client.post("/api/v1/workouts", json=payload, headers={"Authorization": f"Bearer {token_a}"})

    # User B lists workouts -> should be empty
    res_b_list = client.get("/api/v1/workouts", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b_list.status_code == 200
    assert res_b_list.json()["total"] == 0
    assert len(res_b_list.json()["items"]) == 0

    # User B attempts to get User A's workout -> 404
    res_b_get = client.get(f"/api/v1/workouts/{workout_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b_get.status_code == 404

    # User B attempts to delete User A's workout -> 404
    res_b_del = client.delete(f"/api/v1/workouts/{workout_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b_del.status_code == 404


def test_workout_pagination(test_setup):
    client, _, _ = test_setup
    token_a = generate_jwt(user_id=USER_A_ID)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Save 5 workouts
    for i in range(5):
        w_id = str(uuid.uuid4())
        client.post(
            "/api/v1/workouts",
            json={
                "summary": {
                    "session_id": w_id,
                    "start_time": float(100 + i * 20),
                    "end_time": float(115 + i * 20),
                    "total_frames_processed": 300,
                    "total_reps": i + 1,
                    "valid_reps": i + 1,
                    "mean_symmetry": 0.9,
                    "mean_rep_duration": 2.0,
                }
            },
            headers=headers_a,
        )

    # Page 1: limit 2
    res_p1 = client.get("/api/v1/workouts?limit=2&offset=0", headers=headers_a)
    assert res_p1.status_code == 200
    data_p1 = res_p1.json()
    assert data_p1["total"] == 5
    assert len(data_p1["items"]) == 2

    # Page 2: limit 2, offset 2
    res_p2 = client.get("/api/v1/workouts?limit=2&offset=2", headers=headers_a)
    assert res_p2.status_code == 200
    data_p2 = res_p2.json()
    assert len(data_p2["items"]) == 2

    # Verify pagination bounds validation
    res_invalid_limit = client.get("/api/v1/workouts?limit=200", headers=headers_a)
    assert res_invalid_limit.status_code == 422


def test_workout_deletion_lifecycle(test_setup):
    client, _, _ = test_setup
    token_a = generate_jwt(user_id=USER_A_ID)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    w_id = str(uuid.uuid4())
    client.post(
        "/api/v1/workouts",
        json={
            "summary": {
                "session_id": w_id,
                "start_time": 100.0,
                "end_time": 115.0,
                "total_frames_processed": 300,
                "total_reps": 2,
                "valid_reps": 2,
                "mean_symmetry": 0.9,
                "mean_rep_duration": 2.0,
            }
        },
        headers=headers_a,
    )

    # Verify exists
    assert client.get(f"/api/v1/workouts/{w_id}", headers=headers_a).status_code == 200

    # Delete
    del_res = client.delete(f"/api/v1/workouts/{w_id}", headers=headers_a)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Subsequent lookup returns 404
    assert client.get(f"/api/v1/workouts/{w_id}", headers=headers_a).status_code == 404


# ==========================================
# 5. Security & Threat Hardening Regression Tests
# ==========================================

def test_jwt_unsigned_alg_none_rejected(test_setup):
    """Ensure unsigned tokens with alg='none' are strictly rejected with 401."""
    client, _, _ = test_setup
    payload = {
        "sub": USER_A_ID,
        "aud": "authenticated",
        "exp": int(time.time()) + 3600,
        "role": "authenticated",
    }
    unsigned_token = jwt.encode(payload, key="", algorithm="none")
    res = client.get("/api/v1/me/profile", headers={"Authorization": f"Bearer {unsigned_token}"})
    assert res.status_code == 401


def test_jwt_algorithm_confusion_rejected(test_setup):
    """Ensure tokens signed with mismatched algorithms are strictly rejected with 401."""
    client, _, _ = test_setup
    # Token claiming to be HS384 or RS256 when only HS256 is permitted for symmetric secret
    header = {"alg": "HS384", "typ": "JWT"}
    payload = {
        "sub": USER_A_ID,
        "aud": "authenticated",
        "exp": int(time.time()) + 3600,
    }
    confused_token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS384", headers=header)
    res = client.get("/api/v1/me/profile", headers={"Authorization": f"Bearer {confused_token}"})
    assert res.status_code == 401


def test_error_responses_never_expose_secrets_or_tokens(test_setup):
    """Ensure authentication failures and server errors do not leak secrets or token bodies."""
    client, _, _ = test_setup
    tampered_token = generate_jwt(secret="invalid-key-at-least-32-bytes-long-1234")
    res = client.get("/api/v1/me/profile", headers={"Authorization": f"Bearer {tampered_token}"})
    assert res.status_code == 401
    body_text = res.text
    assert TEST_JWT_SECRET not in body_text
    assert "super-secret" not in body_text
    assert tampered_token not in body_text


def test_profile_mass_assignment_prevented(test_setup):
    """Ensure attempts to overwrite read-only profile fields (e.g. id, created_at) are rejected with 422."""
    client, _, _ = test_setup
    token_a = generate_jwt(user_id=USER_A_ID)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    malicious_payload = {
        "display_name": "Valid Name",
        "id": "malicious-injected-id",
        "created_at": "1970-01-01T00:00:00Z",
    }
    res = client.put("/api/v1/me/profile", json=malicious_payload, headers=headers_a)
    assert res.status_code == 422


def test_summary_sanitizer_rejects_non_finite_and_forbids_vision_injection(test_setup):
    """Ensure non-finite floats and injected vision arrays in summary metrics are rejected with 422."""
    client, _, _ = test_setup
    token_a = generate_jwt(user_id=USER_A_ID)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 1. Non-finite knee angle
    payload_nan = {
        "summary": {
            "session_id": str(uuid.uuid4()),
            "start_time": 100.0,
            "end_time": 120.0,
            "total_frames_processed": 600,
            "total_reps": 5,
            "valid_reps": 5,
            "mean_symmetry": 0.95,
            "mean_rep_duration": 2.4,
            "metrics": {
                "total_completed_reps": 5,
                "accepted_reps": 5,
                "rejected_reps": 0,
                "mean_min_knee_angle": "NaN",
            },
        }
    }
    res_nan = client.post("/api/v1/workouts", json=payload_nan, headers=headers_a)
    assert res_nan.status_code == 422

    # 2. Injected forbidden vision landmark field
    payload_vision = {
        "summary": {
            "session_id": str(uuid.uuid4()),
            "start_time": 100.0,
            "end_time": 120.0,
            "total_frames_processed": 600,
            "total_reps": 5,
            "valid_reps": 5,
            "mean_symmetry": 0.95,
            "mean_rep_duration": 2.4,
            "metrics": {
                "total_completed_reps": 5,
                "accepted_reps": 5,
                "rejected_reps": 0,
                "coords": [[0.5, 0.5, 0.0, 0.9] for _ in range(33)],
            },
        }
    }
    res_vision = client.post("/api/v1/workouts", json=payload_vision, headers=headers_a)
    assert res_vision.status_code == 422


def test_backend_capacity_exhaustion_returns_429(auth_env):
    """Verify BackendService enforces session capacity and returns 429 when overloaded."""
    # Create service with tiny capacity of 2
    small_service = BackendService(max_sessions=2, session_idle_timeout=3600.0)
    storage = InMemoryWorkoutStorage()
    app = create_app(backend_service=small_service, storage=storage)
    client = TestClient(app)

    # Create 2 sessions successfully
    res1 = client.post("/api/v1/sessions")
    assert res1.status_code == 201
    res2 = client.post("/api/v1/sessions")
    assert res2.status_code == 201

    # Third session exceeds capacity -> 429 Too Many Requests
    res3 = client.post("/api/v1/sessions")
    assert res3.status_code == 429
    assert "capacity" in res3.json()["message"].lower()


def test_storage_error_sanitized_in_http_response(auth_env):
    """Verify raw database exceptions never expose database credentials or stack traces."""
    from performx.storage import StorageError

    class FailingStorage(InMemoryWorkoutStorage):
        async def get_profile(self, user_id, auth_token=None):
            raise StorageError("PostgREST raw error: user=postgres host=db.internal.cloud pass=SuperSecretDBPass")

    backend_service = BackendService()
    app = create_app(backend_service=backend_service, storage=FailingStorage())
    client = TestClient(app)

    token_a = generate_jwt(user_id=USER_A_ID)
    res = client.get("/api/v1/me/profile", headers={"Authorization": f"Bearer {token_a}"})
    assert res.status_code == 500
    assert "SuperSecretDBPass" not in res.text
    assert "postgres" not in res.text
    assert res.json()["message"] == "Database storage operation failed. Please try again later."

