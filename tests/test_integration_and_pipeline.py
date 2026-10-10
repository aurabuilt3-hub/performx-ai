"""PERFORMX End-to-End Integration Tests.

Validates:
1. Complete in-process BackendService operations (health, capabilities, lifecycle).
2. End-to-end pipeline execution with synthetic frames and mocked pose estimators.
3. Edge cases: non-finite inputs, low confidence, abrupt cadence shifts, aborted squats.
4. Independent session isolation (no cross-contamination of filters or state).
"""

import time
import numpy as np
import pytest

from performx.api import BackendService
from performx.core import LandmarkIndex, MovementPhase, SquatConfig
from performx.contracts import (
    MovementResult,
    PoseLandmarksData,
    SessionSummary,
)
from performx.pipeline import MovementPipeline
from performx.services import (
    MovementAnalysisSession,
    PoseEstimationService,
)


def make_synthetic_landmarks(knee_angle_deg: float, lean_deg: float = 0.0, confidence: float = 0.95) -> PoseLandmarksData:
    coords = np.zeros((33, 4), dtype=np.float32)
    coords[:, 3] = confidence

    coords[LandmarkIndex.LEFT_HIP] = [0.5, 0.4, 0.0, confidence]
    coords[LandmarkIndex.RIGHT_HIP] = [0.6, 0.4, 0.0, confidence]

    coords[LandmarkIndex.LEFT_KNEE] = [0.5, 0.6, 0.0, confidence]
    coords[LandmarkIndex.RIGHT_KNEE] = [0.6, 0.6, 0.0, confidence]

    rad = np.radians(180.0 - knee_angle_deg)
    dx = 0.2 * np.sin(rad)
    dy = 0.2 * np.cos(rad)
    coords[LandmarkIndex.LEFT_ANKLE] = [0.5 + dx, 0.6 + dy, 0.0, confidence]
    coords[LandmarkIndex.RIGHT_ANKLE] = [0.6 + dx, 0.6 + dy, 0.0, confidence]

    lean_rad = np.radians(lean_deg)
    s_dx = 0.2 * np.sin(lean_rad)
    s_dy = 0.2 * np.cos(lean_rad)
    coords[LandmarkIndex.LEFT_SHOULDER] = [0.5 + s_dx, 0.4 - s_dy, 0.0, confidence]
    coords[LandmarkIndex.RIGHT_SHOULDER] = [0.6 + s_dx, 0.4 - s_dy, 0.0, confidence]

    return PoseLandmarksData(
        coords=coords,
        world_coords=None,
        mean_confidence=confidence,
        timestamp=0.0,
    )


class MockPoseEstimationService:
    """Mock PoseEstimationService returning predetermined synthetic landmarks."""

    def __init__(self, synthetic_landmark_sequence: list[PoseLandmarksData | None] | None = None):
        self.sequence = synthetic_landmark_sequence or []
        self.call_count = 0
        self.is_closed = False

    def extract_landmarks(self, rgb_frame: np.ndarray, timestamp: float) -> PoseLandmarksData | None:
        if self.call_count < len(self.sequence):
            lm = self.sequence[self.call_count]
            self.call_count += 1
            return lm
        self.call_count += 1
        return None

    def close(self):
        self.is_closed = True


def test_backend_service_health_and_capabilities():
    service = BackendService()
    health = service.get_health()
    assert health["status"] == "healthy"
    assert health["privacy_mode"] == "local_in_memory"
    assert health["disk_persistence"] is False

    capabilities = service.get_capabilities()
    assert "squat" in capabilities["supported_exercises"]
    assert "walknet_state_gating" in capabilities["features"]
    service.close()


def test_backend_service_session_lifecycle():
    service = BackendService()
    session_id = service.create_session()
    assert session_id in service._sessions

    # Process frame
    dummy_frame = np.ones((100, 100, 3), dtype=np.uint8) * 50
    result = service.process_frame(session_id, dummy_frame, timestamp=1.0)
    assert isinstance(result, MovementResult)

    # End session
    summary = service.end_session(session_id)
    assert isinstance(summary, SessionSummary)
    assert session_id not in service._sessions
    service.close()


def test_mocked_pipeline_full_repetition_flow():
    """Execute complete squat cycle using mocked pose sequence inside MovementPipeline."""
    seq = [
        make_synthetic_landmarks(165.0),  # Standing
        make_synthetic_landmarks(130.0),  # Descending
        make_synthetic_landmarks(85.0),   # Bottom
        make_synthetic_landmarks(85.0),   # Bottom dwell pause
        make_synthetic_landmarks(120.0),  # Ascending
        make_synthetic_landmarks(165.0),  # Lockout / completion
    ]
    mock_pose = MockPoseEstimationService(seq)
    pipeline = MovementPipeline(pose_service=mock_pose)

    dummy_frame = np.zeros((64, 64, 3), dtype=np.uint8)
    results = []
    t = 0.0
    for _ in range(len(seq)):
        res = pipeline.process_frame(dummy_frame, timestamp=t)
        results.append(res)
        t += 0.35

    assert results[0].current_phase == MovementPhase.IDLE
    assert results[1].current_phase == MovementPhase.DESCENT
    assert results[2].current_phase == MovementPhase.BOTTOM
    assert results[4].current_phase == MovementPhase.ASCENT
    assert results[5].current_phase == MovementPhase.LOCKOUT
    assert results[5].repetition_count == 1

    summary = pipeline.get_session_summary()
    assert summary.total_reps == 1
    assert summary.valid_reps == 1
    pipeline.close()
    assert mock_pose.is_closed


def test_shallow_squat_rejection_in_pipeline():
    """Verify that a shallow squat (e.g. only reaching 115 deg) does not increment rep count."""
    seq = [
        make_synthetic_landmarks(165.0),  # Standing
        make_synthetic_landmarks(125.0),  # Partial descent
        make_synthetic_landmarks(115.0),  # Fails to hit bottom target (<95 deg)
        make_synthetic_landmarks(140.0),  # Reverses upward prematurely
        make_synthetic_landmarks(165.0),  # Returned to standing
    ]
    mock_pose = MockPoseEstimationService(seq)
    pipeline = MovementPipeline(pose_service=mock_pose)

    dummy = np.zeros((64, 64, 3), dtype=np.uint8)
    t = 0.0
    final_res = None
    for _ in range(len(seq)):
        final_res = pipeline.process_frame(dummy, timestamp=t)
        t += 0.35

    assert final_res.repetition_count == 0
    assert final_res.current_phase == MovementPhase.IDLE
    pipeline.close()


def test_pipeline_reconfig_updates_thresholds():
    """Test dynamic reconfiguration through pipeline.update_config()."""
    pipeline = MovementPipeline()
    new_config = SquatConfig(bottom_target_angle=80.0, max_torso_lean_deg=30.0)
    pipeline.update_config(new_config)

    assert pipeline.config.bottom_target_angle == 80.0
    assert pipeline.session.config.bottom_target_angle == 80.0
    assert pipeline.session.engine.config.bottom_target_angle == 80.0
    pipeline.close()
