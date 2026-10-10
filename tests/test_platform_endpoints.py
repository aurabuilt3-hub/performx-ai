"""
Tests for full platform endpoints implemented in Phase 26 master backend audit:
- User profile & fitness preferences (/api/v1/profile, /api/v1/me/profile)
- Health profile & sensitive medical annotations (/api/v1/health-profile)
- Workout plans & exercise prescriptions (/api/v1/plans, /api/v1/plans/active)
- Adaptive recommendations lifecycle (/api/v1/recommendations, PATCH /api/v1/recommendations/{id})
- Recovery check-ins (/api/v1/recovery)
- Nutrition & hydration tracking (/api/v1/nutrition/today)
- Medical documents upload flow (/api/v1/documents/presign-upload, confirm, list, delete)
- Privacy consents (/api/v1/privacy/consent)
- GDPR data export & account deletion (/api/v1/account/data-export, DELETE /api/v1/account)
- Authentication enforcement & cross-user data isolation
"""

import time
import uuid

import jwt
import pytest
from starlette.testclient import TestClient

from performx.api import BackendService
from performx.http_api import create_app
from performx.storage import InMemoryWorkoutStorage

TEST_JWT_SECRET = "super-secret-supabase-jwt-key-for-testing-12345678"
USER_A_ID = "11111111-1111-4111-8111-111111111111"
USER_B_ID = "22222222-2222-4222-8222-222222222222"


def generate_jwt(user_id: str = USER_A_ID, secret: str = TEST_JWT_SECRET) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "aud": "authenticated",
        "iat": now,
        "exp": now + 3600,
        "role": "authenticated",
        "email": f"user-{user_id[:8]}@example.com",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture
def auth_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)


@pytest.fixture
def test_setup(auth_env):
    storage = InMemoryWorkoutStorage()
    backend_service = BackendService()
    app = create_app(backend_service=backend_service, storage=storage)
    client = TestClient(app)

    token_user1 = generate_jwt(USER_A_ID)
    token_user2 = generate_jwt(USER_B_ID)

    headers_user1 = {"Authorization": f"Bearer {token_user1}"}
    headers_user2 = {"Authorization": f"Bearer {token_user2}"}

    return {
        "client": client,
        "storage": storage,
        "headers_user1": headers_user1,
        "headers_user2": headers_user2,
    }


def test_unauthenticated_requests_rejected(test_setup):
    client = test_setup["client"]
    protected_endpoints = [
        ("GET", "/api/v1/profile"),
        ("PATCH", "/api/v1/profile"),
        ("GET", "/api/v1/health-profile"),
        ("PUT", "/api/v1/health-profile"),
        ("GET", "/api/v1/plans/active"),
        ("POST", "/api/v1/plans"),
        ("GET", "/api/v1/recommendations"),
        ("POST", "/api/v1/recommendations"),
        ("GET", "/api/v1/recovery"),
        ("POST", "/api/v1/recovery"),
        ("GET", "/api/v1/nutrition/today"),
        ("POST", "/api/v1/nutrition/today"),
        ("POST", "/api/v1/documents/presign-upload"),
        ("POST", "/api/v1/documents/confirm"),
        ("GET", "/api/v1/documents"),
        ("GET", "/api/v1/privacy/consent"),
        ("POST", "/api/v1/privacy/consent"),
        ("POST", "/api/v1/account/data-export"),
        ("DELETE", "/api/v1/account"),
    ]

    for method, path in protected_endpoints:
        if method == "GET":
            response = client.get(path)
        elif method == "POST":
            response = client.post(path, json={})
        elif method == "PUT":
            response = client.put(path, json={})
        elif method == "PATCH":
            response = client.patch(path, json={})
        elif method == "DELETE":
            response = client.delete(path)
        assert response.status_code == 401, f"{method} {path} should return 401 without auth"


def test_user_profile_crud_and_validation(test_setup):
    client = test_setup["client"]
    headers = test_setup["headers_user1"]

    # Initial profile get
    res = client.get("/api/v1/profile", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == USER_A_ID
    assert data["units"] == "metric"

    # Update profile
    payload = {
        "display_name": "Alpha Runner",
        "units": "imperial",
        "fitness_experience": "intermediate",
        "primary_goal": "strength",
        "secondary_goal": "hypertrophy",
        "available_equipment": ["barbell", "dumbbells"],
        "preferred_training_days": [1, 3, 5],
        "preferred_session_duration": 50,
        "dietary_preferences": ["high_protein"],
    }
    update_res = client.patch("/api/v1/profile", json=payload, headers=headers)
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["display_name"] == "Alpha Runner"
    assert updated_data["units"] == "imperial"
    assert updated_data["fitness_experience"] == "intermediate"
    assert updated_data["preferred_training_days"] == [1, 3, 5]

    # Alias /api/v1/me/profile returns same
    alias_res = client.get("/api/v1/me/profile", headers=headers)
    assert alias_res.status_code == 200
    assert alias_res.json()["display_name"] == "Alpha Runner"


def test_health_profile_sensitive_annotations(test_setup):
    client = test_setup["client"]
    headers = test_setup["headers_user1"]

    health_payload = {
        "height_cm": 182.5,
        "weight_kg": 84.0,
        "body_fat_percentage": 14.5,
        "resting_heart_rate": 58,
        "reported_injuries": [
            {
                "injury_id": "inj_001",
                "body_part": "knee_left",
                "description": "Repaired ACL, avoid valgus collapse and knee flexion > 135 deg",
                "severity": "MODERATE",
                "date_occurred": "2023-05-10",
                "data_provenance": "USER_REPORTED",
                "cleared_by_physician": False,
            }
        ],
        "reported_symptoms": ["mild_left_patellar_crepitus"],
        "clinician_restrictions": ["no_deep_impact_box_jumps"],
        "clinician_approved_plan": "Orthopedic clearance approved with 90 deg depth cap",
        "allergies": ["penicillin", "peanuts"],
        "dietary_restrictions": ["lactose_sensitive"],
        "medications": [],
        "data_provenance": "USER_REPORTED",
    }

    put_res = client.put("/api/v1/health-profile", json=health_payload, headers=headers)
    assert put_res.status_code == 200
    data = put_res.json()
    assert data["user_id"] == USER_A_ID
    assert data["height_cm"] == 182.5
    assert len(data["reported_injuries"]) == 1
    assert data["reported_injuries"][0]["data_provenance"] == "USER_REPORTED"
    assert "no_deep_impact_box_jumps" in data["clinician_restrictions"]

    # Verify retrieval
    get_res = client.get("/api/v1/health-profile", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["clinician_approved_plan"] == "Orthopedic clearance approved with 90 deg depth cap"


def test_workout_plan_creation_and_retrieval(test_setup):
    client = test_setup["client"]
    headers = test_setup["headers_user1"]

    # Initially retrieves active baseline plan
    res0 = client.get("/api/v1/plans/active", headers=headers)
    assert res0.status_code == 200
    assert res0.json()["title"] == "Full Body Baseline"

    # Create plan
    plan_payload = {
        "title": "Hypertrophy Wave 1",
        "description": "4-week quad-focused hypertrophy with knee-friendly adaptations",
        "is_active": True,
        "version": 1,
        "exercises": [
            {
                "exercise_id": "squat_01",
                "name": "Box Squat",
                "target_sets": 4,
                "target_reps": 8,
                "target_load_kg": 100.0,
                "rest_seconds": 120,
                "scheduled_day": 1,
                "notes": "Sit back to box; maintain neutral spine",
            }
        ],
        "equipment_constraints": ["barbell", "box"],
        "target_experience": "intermediate",
    }

    post_res = client.post("/api/v1/plans", json=plan_payload, headers=headers)
    assert post_res.status_code == 201
    created_plan = post_res.json()
    assert created_plan["title"] == "Hypertrophy Wave 1"
    assert created_plan["is_active"] is True
    assert len(created_plan["exercises"]) == 1

    # Active plan endpoint now returns it
    res1 = client.get("/api/v1/plans/active", headers=headers)
    assert res1.status_code == 200
    assert res1.json()["title"] == "Hypertrophy Wave 1"


def test_adaptive_recommendation_lifecycle(test_setup):
    client = test_setup["client"]
    headers = test_setup["headers_user1"]

    # Create recommendation
    rec_payload = {
        "recommendation_type": "LOAD_MODULATION",
        "rationale": "High angular velocity detected during deceleration phase.",
        "status": "proposed",
        "source_session_id": "sess_12345",
        "applied_changes": {"depth_target_degrees": 90},
    }
    create_res = client.post("/api/v1/recommendations", json=rec_payload, headers=headers)
    assert create_res.status_code == 201
    rec = create_res.json()
    rec_id = rec["id"]
    assert rec["status"] == "proposed"
    assert rec["recommendation_type"] == "LOAD_MODULATION"

    # List recommendations
    list_res = client.get("/api/v1/recommendations", headers=headers)
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == rec_id

    # Update status to accepted
    patch_res = client.patch(
        f"/api/v1/recommendations/{rec_id}",
        json={"status": "accepted"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "accepted"


def test_recovery_checkin_symptoms_and_readiness(test_setup):
    client = test_setup["client"]
    headers = test_setup["headers_user1"]

    recovery_payload = {
        "affected_area": "left_knee",
        "discomfort_score": 2,
        "symptoms": "Mild stiffness after morning squats",
        "exercise_adherence_score": 0.95,
        "notes": "Pain cleared after 5 minutes of mobility warm-up.",
    }

    post_res = client.post("/api/v1/recovery", json=recovery_payload, headers=headers)
    assert post_res.status_code == 201
    data = post_res.json()
    assert data["affected_area"] == "left_knee"
    assert data["discomfort_score"] == 2
    assert data["symptoms"] == "Mild stiffness after morning squats"

    # Get recent check-ins
    get_res = client.get("/api/v1/recovery", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["total"] >= 1


def test_nutrition_tracking_and_allergen_verification(test_setup):
    client = test_setup["client"]
    headers = test_setup["headers_user1"]

    nutrition_payload = {
        "log_date": "2026-10-11",
        "calories_consumed": 2450,
        "protein_g": 180.0,
        "carbs_g": 260.0,
        "fat_g": 70.0,
        "water_ml": 3200,
        "meals": [
            {
                "name": "Post-Workout Shake",
                "calories": 450,
                "protein_g": 50.0,
                "carbs_g": 40.0,
                "fat_g": 5.0,
                "ingredients": ["whey", "oats", "almond milk"],
                "allergens": [],
            },
            {
                "name": "Protein Bar",
                "calories": 250,
                "protein_g": 20.0,
                "carbs_g": 25.0,
                "fat_g": 8.0,
                "ingredients": ["peanut butter", "dates"],
                "allergens": ["peanut"],
            },
        ],
        "allergen_verification_status": "VERIFIED_PRESENT",
    }

    post_res = client.post("/api/v1/nutrition/today", json=nutrition_payload, headers=headers)
    assert post_res.status_code == 200
    data = post_res.json()
    assert data["water_ml"] == 3200
    assert len(data["meals"]) == 2
    assert data["allergen_verification_status"] == "VERIFIED_PRESENT"

    # Retrieval
    get_res = client.get("/api/v1/nutrition/today?date=2026-10-11", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["protein_g"] == 180.0


def test_medical_document_presigned_flow_and_limits(test_setup):
    client = test_setup["client"]
    headers = test_setup["headers_user1"]

    # Reject file too large (> 15MB) via Pydantic validator (422)
    too_large_payload = {
        "file_name": "huge_mri_scan.pdf",
        "mime_type": "application/pdf",
        "file_size_bytes": 16 * 1024 * 1024,
    }
    err_res = client.post(
        "/api/v1/documents/presign-upload",
        json=too_large_payload,
        headers=headers,
    )
    assert err_res.status_code == 422

    # Reject forbidden mime type (e.g. video)
    invalid_mime_payload = {
        "file_name": "exercise_video.mp4",
        "mime_type": "video/mp4",
        "file_size_bytes": 1024 * 1024,
    }
    err_res2 = client.post(
        "/api/v1/documents/presign-upload",
        json=invalid_mime_payload,
        headers=headers,
    )
    assert err_res2.status_code == 422

    # Valid presign request
    valid_payload = {
        "file_name": "knee_clearance.pdf",
        "mime_type": "application/pdf",
        "file_size_bytes": 1024 * 500,
        "document_category": "physician_clearance",
        "description": "Post-ACL surgery orthopedics signoff",
    }
    presign_res = client.post(
        "/api/v1/documents/presign-upload",
        json=valid_payload,
        headers=headers,
    )
    assert presign_res.status_code == 200
    presign_data = presign_res.json()
    doc_id = presign_data["document_id"]
    storage_path = presign_data["storage_path"]
    assert "upload_url" in presign_data

    # Confirm upload
    confirm_payload = {
        "storage_path": storage_path,
        "file_name": "knee_clearance.pdf",
        "mime_type": "application/pdf",
        "file_size_bytes": 1024 * 500,
        "document_category": "physician_clearance",
        "description": "Post-ACL surgery orthopedics signoff",
    }
    confirm_res = client.post(
        "/api/v1/documents/confirm",
        json=confirm_payload,
        headers=headers,
    )
    assert confirm_res.status_code == 201
    confirmed_doc = confirm_res.json()
    confirmed_id = confirmed_doc["id"]
    assert confirmed_doc["status"] == "confirmed"

    # List documents
    docs_res = client.get("/api/v1/documents", headers=headers)
    assert docs_res.status_code == 200
    docs_data = docs_res.json()
    assert docs_data["total"] == 1
    assert docs_data["items"][0]["id"] == confirmed_id

    # Delete document
    del_res = client.delete(f"/api/v1/documents/{confirmed_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # List documents after deletion
    docs_after = client.get("/api/v1/documents", headers=headers).json()
    assert docs_after["total"] == 0


def test_privacy_consent_and_telemetry_isolation(test_setup):
    client = test_setup["client"]
    headers = test_setup["headers_user1"]

    consent_payload = {
        "camera_processing_consent": True,
        "document_processing_consent": True,
        "data_analytics_consent": False,
    }
    save_res = client.post(
        "/api/v1/privacy/consent",
        json=consent_payload,
        headers=headers,
    )
    assert save_res.status_code == 200
    data = save_res.json()
    assert data["camera_processing_consent"] is True
    assert data["data_analytics_consent"] is False

    get_res = client.get("/api/v1/privacy/consent", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["data_analytics_consent"] is False


def test_cross_user_isolation(test_setup):
    client = test_setup["client"]
    headers_u1 = test_setup["headers_user1"]
    headers_u2 = test_setup["headers_user2"]

    # User 1 creates a private health profile and recommendation
    client.put(
        "/api/v1/health-profile",
        json={
            "height_cm": 180.0,
            "weight_kg": 80.0,
            "reported_symptoms": ["chronic_lumbar_tightness"],
            "clinician_restrictions": ["no_conventional_deadlifts"],
            "clinician_approved_plan": "User 1 private clinical note",
            "data_provenance": "USER_REPORTED",
        },
        headers=headers_u1,
    )

    rec_res = client.post(
        "/api/v1/recommendations",
        json={
            "recommendation_type": "INJURY_PREVENTION",
            "rationale": "High shear forces on spine",
            "status": "proposed",
            "applied_changes": {},
        },
        headers=headers_u1,
    )
    assert rec_res.status_code == 201
    rec1_id = rec_res.json()["id"]

    # User 2 views health profile - must NOT see user 1's clinician approved plan
    u2_health = client.get("/api/v1/health-profile", headers=headers_u2).json()
    assert u2_health["clinician_approved_plan"] is None
    assert u2_health["clinician_restrictions"] == []

    # User 2 lists recommendations - must NOT see user 1's recommendation
    u2_recs = client.get("/api/v1/recommendations", headers=headers_u2).json()
    assert u2_recs["total"] == 0

    # User 2 attempts to patch User 1's recommendation - must fail 404
    err_patch = client.patch(
        f"/api/v1/recommendations/{rec1_id}",
        json={"status": "accepted"},
        headers=headers_u2,
    )
    assert err_patch.status_code == 404


def test_gdpr_data_export_and_account_deletion(test_setup):
    client = test_setup["client"]
    headers = test_setup["headers_user1"]

    # Populate some data across tables
    client.patch("/api/v1/profile", json={"display_name": "Export Subject"}, headers=headers)
    client.put(
        "/api/v1/health-profile",
        json={
            "height_cm": 175.0,
            "weight_kg": 72.0,
            "clinician_approved_plan": "Sample plan note",
        },
        headers=headers,
    )

    # 1. GDPR Export
    export_res = client.post("/api/v1/account/data-export", headers=headers)
    assert export_res.status_code == 200
    bundle = export_res.json()
    assert bundle["user_id"] == USER_A_ID
    assert "profile" in bundle
    assert bundle["profile"]["display_name"] == "Export Subject"
    assert bundle["health_profile"]["clinician_approved_plan"] == "Sample plan note"
    assert "workout_history" in bundle
    assert "workout_plans" in bundle
    assert "medical_documents_metadata" in bundle

    # 2. Account Deletion (Right to be Forgotten)
    del_res = client.delete("/api/v1/account", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "account_purged"
    assert del_res.json()["user_id"] == USER_A_ID

    # Confirm health profile is wiped
    after_health = client.get("/api/v1/health-profile", headers=headers).json()
    assert after_health["clinician_approved_plan"] is None
    assert after_health["height_cm"] is None
