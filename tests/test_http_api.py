"""Tests for PERFORMX FastAPI HTTP REST API."""

import io
import cv2
import numpy as np
import pytest
from starlette.testclient import TestClient

from performx.core import LandmarkIndex
from performx.http_api import create_app


def create_synthetic_landmarks_list(knee_angle_deg: float, lean_deg: float = 0.0, confidence: float = 0.95):
    """Generate 33 landmark dictionaries for HTTP payload."""
    coords = [{"x": 0.0, "y": 0.0, "z": 0.0, "visibility": confidence} for _ in range(33)]

    # Hips
    coords[LandmarkIndex.LEFT_HIP] = {"x": 0.5, "y": 0.4, "z": 0.0, "visibility": confidence}
    coords[LandmarkIndex.RIGHT_HIP] = {"x": 0.6, "y": 0.4, "z": 0.0, "visibility": confidence}

    # Knees
    coords[LandmarkIndex.LEFT_KNEE] = {"x": 0.5, "y": 0.6, "z": 0.0, "visibility": confidence}
    coords[LandmarkIndex.RIGHT_KNEE] = {"x": 0.6, "y": 0.6, "z": 0.0, "visibility": confidence}

    # Ankles
    rad = np.radians(180.0 - knee_angle_deg)
    dx = float(0.2 * np.sin(rad))
    dy = float(0.2 * np.cos(rad))
    coords[LandmarkIndex.LEFT_ANKLE] = {"x": 0.5 + dx, "y": 0.6 + dy, "z": 0.0, "visibility": confidence}
    coords[LandmarkIndex.RIGHT_ANKLE] = {"x": 0.6 + dx, "y": 0.6 + dy, "z": 0.0, "visibility": confidence}

    # Shoulders
    lean_rad = np.radians(lean_deg)
    sdx = float(0.2 * np.sin(lean_rad))
    sdy = float(0.2 * np.cos(lean_rad))
    coords[LandmarkIndex.LEFT_SHOULDER] = {"x": 0.5 + sdx, "y": 0.4 - sdy, "z": 0.0, "visibility": confidence}
    coords[LandmarkIndex.RIGHT_SHOULDER] = {"x": 0.6 + sdx, "y": 0.4 - sdy, "z": 0.0, "visibility": confidence}

    return coords


@pytest.fixture
def client():
    """Create test client with clean isolated backend service."""
    app = create_app()
    return TestClient(app)


def test_health_check_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["pose_engine"] == "mediapipe_blazepose"
    assert data["privacy_mode"] == "local_in_memory"
    assert data["disk_persistence"] is False
    assert "active_sessions" in data


def test_capabilities_endpoint(client):
    res = client.get("/api/v1/capabilities")
    assert res.status_code == 200
    data = res.json()
    assert "squat" in data["supported_exercises"]
    assert "knee_flexion_extension" in data["features"]
    assert "default_squat_envelope" in data


def test_create_session_default(client):
    res = client.post("/api/v1/sessions")
    assert res.status_code == 201
    data = res.json()
    assert "session_id" in data
    assert data["status"] == "active"
    assert data["config"]["standing_knee_angle"] == 155.0


def test_create_session_custom_config(client):
    payload = {
        "config": {
            "standing_knee_angle": 155.0,
            "descent_trigger_angle": 140.0,
            "bottom_target_angle": 90.0,
            "min_bottom_dwell": 0.25,
        }
    }
    res = client.post("/api/v1/sessions", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["config"]["standing_knee_angle"] == 155.0
    assert data["config"]["bottom_target_angle"] == 90.0


def test_create_session_invalid_config(client):
    # bottom_target_angle > standing_knee_angle violates angular hierarchy
    payload = {
        "config": {
            "standing_knee_angle": 100.0,
            "bottom_target_angle": 150.0,
        }
    }
    res = client.post("/api/v1/sessions", json=payload)
    assert res.status_code == 422


def test_get_session_status(client):
    create_res = client.post("/api/v1/sessions")
    session_id = create_res.json()["session_id"]

    res = client.get(f"/api/v1/sessions/{session_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == session_id
    assert data["is_active"] is True
    assert data["frames_processed"] == 0
    assert data["total_reps"] == 0


def test_get_nonexistent_session_returns_404(client):
    res = client.get("/api/v1/sessions/nonexistent-uuid")
    assert res.status_code == 404
    data = res.json()
    assert data["code"] == "SESSION_INACTIVE"


def test_analyze_landmarks_flow(client):
    create_res = client.post("/api/v1/sessions")
    session_id = create_res.json()["session_id"]

    # 1. Standing frame
    lm_standing = create_synthetic_landmarks_list(165.0)
    res = client.post(
        f"/api/v1/sessions/{session_id}/analysis/landmarks",
        json={"timestamp": 0.0, "landmarks": lm_standing},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_detected"] is True
    assert data["current_phase"] == "IDLE"
    assert data["repetition_count"] == 0

    # 2. Descending
    client.post(
        f"/api/v1/sessions/{session_id}/analysis/landmarks",
        json={"timestamp": 0.4, "landmarks": create_synthetic_landmarks_list(130.0)},
    )

    # 3. Bottom with dwell
    client.post(
        f"/api/v1/sessions/{session_id}/analysis/landmarks",
        json={"timestamp": 0.8, "landmarks": create_synthetic_landmarks_list(85.0)},
    )
    client.post(
        f"/api/v1/sessions/{session_id}/analysis/landmarks",
        json={"timestamp": 1.1, "landmarks": create_synthetic_landmarks_list(85.0)},
    )

    # 4. Ascending
    client.post(
        f"/api/v1/sessions/{session_id}/analysis/landmarks",
        json={"timestamp": 1.4, "landmarks": create_synthetic_landmarks_list(130.0)},
    )

    # 5. Standing complete rep
    res_final = client.post(
        f"/api/v1/sessions/{session_id}/analysis/landmarks",
        json={"timestamp": 1.8, "landmarks": lm_standing},
    )
    data_final = res_final.json()
    assert data_final["repetition_count"] == 1
    assert data_final["repetition_summary"] is not None
    assert data_final["repetition_summary"]["is_valid"] is True


def test_analyze_landmarks_missing_subject(client):
    create_res = client.post("/api/v1/sessions")
    session_id = create_res.json()["session_id"]

    res = client.post(
        f"/api/v1/sessions/{session_id}/analysis/landmarks",
        json={"timestamp": 0.5, "landmarks": None},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_detected"] is False
    assert data["confidence"] == 0.0


def test_analyze_landmarks_invalid_count(client):
    create_res = client.post("/api/v1/sessions")
    session_id = create_res.json()["session_id"]

    # Only 5 landmarks
    short_landmarks = [{"x": 0.1, "y": 0.2, "z": 0.0, "visibility": 0.9} for _ in range(5)]
    res = client.post(
        f"/api/v1/sessions/{session_id}/analysis/landmarks",
        json={"timestamp": 0.5, "landmarks": short_landmarks},
    )
    assert res.status_code == 422


def test_analyze_landmarks_non_numeric(client):
    create_res = client.post("/api/v1/sessions")
    session_id = create_res.json()["session_id"]

    lm = create_synthetic_landmarks_list(165.0)
    lm[0]["x"] = "not_a_valid_float"
    res = client.post(
        f"/api/v1/sessions/{session_id}/analysis/landmarks",
        json={"timestamp": 0.5, "landmarks": lm},
    )
    assert res.status_code == 422


def test_analyze_frame_endpoint(client):
    create_res = client.post("/api/v1/sessions")
    session_id = create_res.json()["session_id"]

    # Synthetic black image
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    _, encoded = cv2.imencode(".jpg", img)
    img_bytes = encoded.tobytes()

    response = client.post(
        f"/api/v1/sessions/{session_id}/analysis/frame",
        files={"file": ("frame.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        data={"timestamp": 1.25},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["timestamp"] == 1.25
    assert "repetition_count" in data


def test_analyze_frame_corrupt_file(client):
    create_res = client.post("/api/v1/sessions")
    session_id = create_res.json()["session_id"]

    response = client.post(
        f"/api/v1/sessions/{session_id}/analysis/frame",
        files={"file": ("corrupt.jpg", io.BytesIO(b"not_an_image"), "image/jpeg")},
        data={"timestamp": 1.25},
    )
    assert response.status_code == 400


def test_calibration_landmarks_and_reset(client):
    create_res = client.post("/api/v1/sessions")
    session_id = create_res.json()["session_id"]

    lm = create_synthetic_landmarks_list(165.0)
    calib_res = client.post(
        f"/api/v1/sessions/{session_id}/calibration/landmarks",
        json={"timestamp": 0.1, "landmarks": lm},
    )
    assert calib_res.status_code == 200
    assert "status" in calib_res.json()

    reset_res = client.post(f"/api/v1/sessions/{session_id}/calibration/reset")
    assert reset_res.status_code == 200
    assert reset_res.json()["status"] == "calibration_reset"


def test_session_summary_reset_and_delete_lifecycle(client):
    create_res = client.post("/api/v1/sessions")
    session_id = create_res.json()["session_id"]

    # Ingest one frame
    lm = create_synthetic_landmarks_list(165.0)
    client.post(
        f"/api/v1/sessions/{session_id}/analysis/landmarks",
        json={"timestamp": 0.0, "landmarks": lm},
    )

    # Check summary
    sum_res = client.get(f"/api/v1/sessions/{session_id}/summary")
    assert sum_res.status_code == 200
    summary = sum_res.json()
    assert summary["total_frames_processed"] == 1
    assert "metrics" in summary

    # Reset
    rst_res = client.post(f"/api/v1/sessions/{session_id}/reset")
    assert rst_res.status_code == 200

    status_res = client.get(f"/api/v1/sessions/{session_id}")
    assert status_res.json()["frames_processed"] == 0

    # Delete session
    del_res = client.delete(f"/api/v1/sessions/{session_id}")
    assert del_res.status_code == 200
    assert del_res.json()["session_id"] == session_id

    # Post-deletion lookup fails
    get_res = client.get(f"/api/v1/sessions/{session_id}")
    assert get_res.status_code == 404


def test_cors_headers_allowed_origin(client):
    res = client.options(
        "/api/v1/capabilities",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_root_and_healthz_endpoints(client):
    """Verify production orchestrator /healthz and root health pings."""
    root_res = client.get("/")
    assert root_res.status_code == 200
    assert root_res.json()["status"] == "healthy"

    healthz_res = client.get("/healthz")
    assert healthz_res.status_code == 200
    assert healthz_res.json()["status"] == "healthy"


def test_production_env_forbids_in_memory_persistence(monkeypatch):
    """Verify that setting PERFORMX_ENV=production strictly forbids ephemeral memory backend."""
    from performx.storage import StorageError, create_storage

    monkeypatch.setenv("PERFORMX_ENV", "production")
    monkeypatch.setenv("PERFORMX_STORAGE_BACKEND", "memory")

    with pytest.raises(StorageError) as exc_info:
        create_storage()
    assert "strictly forbidden" in str(exc_info.value)


def test_lifespan_cleanup_releases_backend_resources():
    """Verify that application lifespan cleanup invokes backend service closure."""
    from performx.api import BackendService

    service = BackendService()
    sid = service.create_session("squat")
    assert sid in service._sessions

    app = create_app(backend_service=service)
    with TestClient(app):
        # Client context entered
        assert sid in service._sessions

    # Client context exited (shutdown executed)
    assert len(service._sessions) == 0

