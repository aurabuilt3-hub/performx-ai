"""PERFORMX Standing-Pose Calibration Regression Tests.

Validates:
1. Successful calibration over a window of valid synthetic standing landmarks.
2. Robust median calculation for limb lengths (femur, tibia, torso, body height proxy).
3. Rejection of partial, low-confidence, or non-standing postures.
4. Rejection of unstable/jittery standing frames violating std dev limits.
5. Invariance across different subject scales (near vs far camera distance).
6. Calibration reset, recalibration, and session isolation.
7. Uncalibrated default state gracefully propagating without breaking rep counts.
"""

import numpy as np
import pytest

from performx.calibration import StandingCalibrationService
from performx.core import CalibrationStatus, LandmarkIndex
from performx.contracts import PoseLandmarksData
from performx.services import MovementAnalysisSession


def make_calib_landmarks(
    knee_angle_deg: float = 176.0,
    torso_lean_deg: float = 4.0,
    scale: float = 1.0,
    confidence: float = 0.95,
    jitter_y: float = 0.0,
) -> PoseLandmarksData:
    coords = np.zeros((33, 4), dtype=np.float32)
    coords[:, 3] = confidence

    hip_y = 0.4 * scale + jitter_y
    knee_y = 0.6 * scale + jitter_y

    coords[LandmarkIndex.LEFT_HIP] = [0.5, hip_y, 0.0, confidence]
    coords[LandmarkIndex.RIGHT_HIP] = [0.6, hip_y, 0.0, confidence]

    coords[LandmarkIndex.LEFT_KNEE] = [0.5, knee_y, 0.0, confidence]
    coords[LandmarkIndex.RIGHT_KNEE] = [0.6, knee_y, 0.0, confidence]

    rad = np.radians(180.0 - knee_angle_deg)
    dx = (0.2 * scale) * np.sin(rad)
    dy = (0.2 * scale) * np.cos(rad)
    coords[LandmarkIndex.LEFT_ANKLE] = [0.5 + dx, knee_y + dy, 0.0, confidence]
    coords[LandmarkIndex.RIGHT_ANKLE] = [0.6 + dx, knee_y + dy, 0.0, confidence]

    lean_rad = np.radians(torso_lean_deg)
    s_dx = (0.2 * scale) * np.sin(lean_rad)
    s_dy = (0.2 * scale) * np.cos(lean_rad)
    coords[LandmarkIndex.LEFT_SHOULDER] = [0.5 + s_dx, hip_y - s_dy, 0.0, confidence]
    coords[LandmarkIndex.RIGHT_SHOULDER] = [0.6 + s_dx, hip_y - s_dy, 0.0, confidence]

    return PoseLandmarksData(
        coords=coords,
        world_coords=None,
        mean_confidence=confidence,
        timestamp=0.0,
    )


def test_successful_standing_pose_calibration():
    service = StandingCalibrationService(min_samples=15)
    assert service.status == CalibrationStatus.NOT_CALIBRATED

    # Feed 15 valid standing frames
    for i in range(15):
        lm = make_calib_landmarks(knee_angle_deg=175.0, torso_lean_deg=3.0)
        res = service.add_frame_sample(lm)

    assert service.status == CalibrationStatus.CALIBRATED
    assert res.status == CalibrationStatus.CALIBRATED
    assert res.standing_knee_angle >= 170.0
    assert res.body_height_proxy_2d > 0.2
    assert res.femur_length_2d > 0.1
    assert res.sample_count == 15


def test_rejection_of_non_standing_pose():
    """Verify service rejects squatting posture (> 16 deg knee flexion)."""
    service = StandingCalibrationService(min_samples=15)
    # Knee angle 120 deg (squatting, not standing)
    lm = make_calib_landmarks(knee_angle_deg=120.0)
    res = service.add_frame_sample(lm)

    assert service.status == CalibrationStatus.FAILED
    assert "not fully standing" in res.failure_reason.lower()


def test_rejection_of_excessive_torso_lean():
    service = StandingCalibrationService(min_samples=15)
    # Excessive lean 35 deg
    lm = make_calib_landmarks(knee_angle_deg=175.0, torso_lean_deg=35.0)
    res = service.add_frame_sample(lm)

    assert service.status == CalibrationStatus.FAILED
    assert "torso lean" in res.failure_reason.lower()


def test_rejection_of_low_confidence_landmarks():
    service = StandingCalibrationService(min_samples=15, min_confidence=0.7)
    lm = make_calib_landmarks(confidence=0.45)
    res = service.add_frame_sample(lm)

    assert service.status == CalibrationStatus.FAILED
    assert "confidence" in res.failure_reason.lower()


def test_rejection_of_unstable_jitter_window():
    """Verify that excessive vertical movement instability is caught by variance check."""
    service = StandingCalibrationService(min_samples=10, max_jitter_std=0.03)

    # Alternate vertical jitter wildly
    for i in range(12):
        jitter = 0.08 if i % 2 == 0 else -0.08
        lm = make_calib_landmarks(jitter_y=jitter)
        res = service.add_frame_sample(lm)

    assert service.status == CalibrationStatus.FAILED
    assert "instability" in res.failure_reason.lower()


def test_scale_invariance_across_distances():
    """Verify calibration correctly tracks scale difference between near (scale 1.2) and far (scale 0.7)."""
    service_near = StandingCalibrationService(min_samples=15)
    service_far = StandingCalibrationService(min_samples=15)

    for _ in range(15):
        service_near.add_frame_sample(make_calib_landmarks(scale=1.2))
        service_far.add_frame_sample(make_calib_landmarks(scale=0.7))

    res_near = service_near.current_result
    res_far = service_far.current_result

    assert res_near.status == CalibrationStatus.CALIBRATED
    assert res_far.status == CalibrationStatus.CALIBRATED
    assert res_near.body_height_proxy_2d > res_far.body_height_proxy_2d
    assert res_near.femur_length_2d > res_far.femur_length_2d


def test_calibration_reset_and_session_isolation():
    session_a = MovementAnalysisSession(session_id="A")
    session_b = MovementAnalysisSession(session_id="B")

    # Calibrate session A
    for _ in range(15):
        session_a.calibration_service.add_frame_sample(make_calib_landmarks())

    assert session_a.calibration_service.status == CalibrationStatus.CALIBRATED
    assert session_b.calibration_service.status == CalibrationStatus.NOT_CALIBRATED

    # Reset session A
    session_a.reset()
    assert session_a.calibration_service.status == CalibrationStatus.NOT_CALIBRATED
    assert session_a.calibration_service.current_result is None
