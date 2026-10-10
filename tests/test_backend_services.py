import pytest
import numpy as np

from performx.core import LandmarkIndex, LandmarkValidationError, SquatConfig
from performx.contracts import (
    MovementFeatures,
    MovementResult,
    PoseLandmarksData,
    SessionSummary,
)
from performx.engine import MovementPhase
from performx.services import MovementAnalysisSession


def create_synthetic_landmarks(knee_angle_deg: float, lean_deg: float = 0.0, confidence: float = 0.95) -> PoseLandmarksData:
    """Generate mathematically deterministic synthetic landmarks for a given knee angle."""
    coords = np.zeros((33, 4), dtype=np.float32)
    coords[:, 3] = confidence  # visibility

    # Left hip at (0.5, 0.4)
    coords[LandmarkIndex.LEFT_HIP] = [0.5, 0.4, 0.0, confidence]
    coords[LandmarkIndex.RIGHT_HIP] = [0.6, 0.4, 0.0, confidence]

    # Knee at (0.5, 0.6)
    coords[LandmarkIndex.LEFT_KNEE] = [0.5, 0.6, 0.0, confidence]
    coords[LandmarkIndex.RIGHT_KNEE] = [0.6, 0.6, 0.0, confidence]

    # Calculate ankle location to create exact requested knee angle
    # Vector hip -> knee is (0, 0.2). Direction down is [0, 1].
    # Ankle offset rotates by (180 - knee_angle)
    rad = np.radians(180.0 - knee_angle_deg)
    dx = 0.2 * np.sin(rad)
    dy = 0.2 * np.cos(rad)
    coords[LandmarkIndex.LEFT_ANKLE] = [0.5 + dx, 0.6 + dy, 0.0, confidence]
    coords[LandmarkIndex.RIGHT_ANKLE] = [0.6 + dx, 0.6 + dy, 0.0, confidence]

    # Shoulders above hips with lean
    lean_rad = np.radians(lean_deg)
    shoulder_dx = 0.2 * np.sin(lean_rad)
    shoulder_dy = 0.2 * np.cos(lean_rad)
    coords[LandmarkIndex.LEFT_SHOULDER] = [0.5 + shoulder_dx, 0.4 - shoulder_dy, 0.0, confidence]
    coords[LandmarkIndex.RIGHT_SHOULDER] = [0.6 + shoulder_dx, 0.4 - shoulder_dy, 0.0, confidence]

    return PoseLandmarksData(
        coords=coords,
        world_coords=None,
        mean_confidence=confidence,
        timestamp=0.0,
    )


def test_contract_rejects_non_finite_landmarks():
    coords = np.zeros((33, 4), dtype=np.float32)
    coords[0, 0] = np.nan
    with pytest.raises(LandmarkValidationError):
        PoseLandmarksData(coords=coords, world_coords=None, mean_confidence=0.9, timestamp=1.0)


def test_squat_config_validation_bounds():
    # Valid config
    config = SquatConfig(standing_knee_angle=160.0, bottom_target_angle=90.0)
    assert config.standing_knee_angle == 160.0

    # Invalid angular relationship (bottom > standing)
    with pytest.raises(ValueError):
        SquatConfig(standing_knee_angle=90.0, bottom_target_angle=140.0)

    # Non-finite values
    with pytest.raises(ValueError):
        SquatConfig(standing_knee_angle=float("inf"))


def test_session_isolation_independent_state():
    """Verify two concurrent sessions maintain completely distinct counters and filter states."""
    session_a = MovementAnalysisSession(session_id="session_A")
    session_b = MovementAnalysisSession(session_id="session_B")

    lm_standing = create_synthetic_landmarks(165.0)
    lm_bottom = create_synthetic_landmarks(85.0)

    # Session A executes full rep
    session_a.process_landmarks(lm_standing, timestamp=0.0)
    session_a.process_landmarks(create_synthetic_landmarks(130.0), timestamp=0.3)
    session_a.process_landmarks(lm_bottom, timestamp=0.6)
    session_a.process_landmarks(lm_bottom, timestamp=0.9)  # Dwell
    session_a.process_landmarks(create_synthetic_landmarks(120.0), timestamp=1.2)
    res_a = session_a.process_landmarks(lm_standing, timestamp=1.6)

    # Session B remains standing
    res_b = session_b.process_landmarks(lm_standing, timestamp=1.6)

    assert res_a.repetition_count == 1
    assert res_b.repetition_count == 0
    assert session_a.frames_processed == 6
    assert session_b.frames_processed == 1


def test_session_reset_clears_metrics():
    session = MovementAnalysisSession()
    lm = create_synthetic_landmarks(165.0)
    session.process_landmarks(lm, timestamp=1.0)
    assert session.frames_processed == 1

    session.reset()
    assert session.frames_processed == 0
    assert session.engine.repetition_count == 0
    assert len(session.symmetry_history) == 0


def test_missing_landmarks_preserves_deterministic_response():
    session = MovementAnalysisSession()
    res = session.process_landmarks(None, timestamp=2.0)
    assert not res.is_detected
    assert res.confidence == 0.0
    assert res.features.avg_knee_angle == 180.0
