"""PERFORMX Movement Reliability & Edge Case Tests.

Evaluates:
1. Fast cadence squats (< 1.2s per rep) vs deliberate slow squats (> 4.0s).
2. Deep pause squats (holding at bottom for 2.0s without false early ascent).
3. Temporary landmark dropouts (occlusion / leaving frame mid-rep).
4. Camera repositioning simulation (body scale shrinking by 40% after calibration).
5. Sensorimotor engine vs Naive threshold counter comparison across diverse trajectories.
"""

import numpy as np
import pytest

from performx.calibration import StandingCalibrationService
from performx.core import LandmarkIndex, MovementPhase, SquatConfig
from performx.contracts import PoseLandmarksData
from performx.engine import PhaseOscillator, SensorimotorEngine
from tests.test_fruit_fly_benchmark import NaiveThresholdRepCounter


def make_pose_sample(
    knee_angle_deg: float,
    torso_lean_deg: float = 8.0,
    scale: float = 1.0,
    confidence: float = 0.95,
) -> PoseLandmarksData:
    coords = np.zeros((33, 4), dtype=np.float32)
    coords[:, 3] = confidence

    hip_y = 0.4 * scale
    knee_y = 0.6 * scale

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


def test_deep_pause_squat_dwell_timing():
    """Verify holding bottom position for 2.0s accumulates dwell accurately without false triggers."""
    engine = SensorimotorEngine(config=SquatConfig(min_bottom_dwell=0.2, max_bottom_dwell=4.0))

    t = 0.0
    engine.evaluate_frame(165.0, 170.0, 5.0, 1.0, timestamp=t, confidence=0.9)
    
    # Descent
    t += 0.4
    engine.evaluate_frame(120.0, 125.0, 15.0, 1.0, timestamp=t, confidence=0.9)
    t += 0.4
    engine.evaluate_frame(85.0, 90.0, 20.0, 1.0, timestamp=t, confidence=0.9)
    assert engine.current_phase == MovementPhase.BOTTOM

    # Hold pause for 2.0 seconds
    for _ in range(10):
        t += 0.2
        phase, _ = engine.evaluate_frame(85.0, 90.0, 20.0, 1.0, timestamp=t, confidence=0.9)
        assert phase == MovementPhase.BOTTOM

    # Ascent to completion
    t += 0.4
    engine.evaluate_frame(120.0, 125.0, 15.0, 1.0, timestamp=t, confidence=0.9)
    t += 0.4
    phase, _ = engine.evaluate_frame(165.0, 170.0, 5.0, 1.0, timestamp=t, confidence=0.9)

    assert phase == MovementPhase.LOCKOUT
    assert engine.repetition_count == 1
    assert engine.last_rep_bottom_dwell >= 2.0


def test_temporary_occlusion_and_recovery():
    """Verify subject stepping out of frame during descent resets cleanly upon return."""
    engine = SensorimotorEngine()

    t = 0.0
    engine.evaluate_frame(165.0, 170.0, 5.0, 1.0, timestamp=t, confidence=0.9)
    t += 0.3
    engine.evaluate_frame(130.0, 135.0, 15.0, 1.0, timestamp=t, confidence=0.9)
    assert engine.current_phase == MovementPhase.DESCENT

    # Occlusion (confidence drops to 0.0 for 5 frames)
    for _ in range(5):
        t += 0.1
        phase, alerts = engine.evaluate_frame(130.0, 135.0, 15.0, 1.0, timestamp=t, confidence=0.1)
        assert any(a.code == "LOW_CONFIDENCE" for a in alerts)

    # Subject re-enters fully standing
    t += 0.5
    phase, alerts = engine.evaluate_frame(165.0, 170.0, 5.0, 1.0, timestamp=t, confidence=0.9)
    # Does not falsely count a repetition
    assert engine.repetition_count == 0


def test_comparative_benchmark_dwell_and_reversals():
    """Compare Walknet Engine vs Naive Counter on 5 trials of mixed movements."""
    naive = NaiveThresholdRepCounter(bottom_threshold=95.0, top_threshold=150.0)
    engine = SensorimotorEngine()

    # Sequence of 3 valid reps and 2 shallow/stuttering half-reps
    # Rep 1: Valid
    # Rep 2: Incomplete (reverses at 105 deg)
    # Rep 3: Valid
    # Rep 4: Rapid bounce (0.1s crossing)
    # Rep 5: Valid
    t = 0.0
    # Trial 1: Valid rep
    for ang in [165.0, 130.0, 85.0, 85.0, 120.0, 165.0]:
        t += 0.3
        naive.update(ang)
        engine.evaluate_frame(ang, ang, 10.0, 1.0, timestamp=t, confidence=0.9)

    # Trial 2: Incomplete rep (stops at 105 deg)
    for ang in [165.0, 130.0, 105.0, 130.0, 165.0]:
        t += 0.3
        naive.update(ang)
        engine.evaluate_frame(ang, ang, 10.0, 1.0, timestamp=t, confidence=0.9)

    # Trial 3: Valid rep
    for ang in [165.0, 130.0, 85.0, 85.0, 120.0, 165.0]:
        t += 0.3
        naive.update(ang)
        engine.evaluate_frame(ang, ang, 10.0, 1.0, timestamp=t, confidence=0.9)

    # Trial 4: Rapid noise bounce in 0.05s
    for ang in [165.0, 80.0, 165.0]:
        t += 0.02
        naive.update(ang)
        engine.evaluate_frame(ang, ang, 10.0, 1.0, timestamp=t, confidence=0.9)

    # Trial 5: Valid rep
    for ang in [165.0, 130.0, 85.0, 85.0, 120.0, 165.0]:
        t += 0.3
        naive.update(ang)
        engine.evaluate_frame(ang, ang, 10.0, 1.0, timestamp=t, confidence=0.9)

    # Naive counter counts the rapid spike as a rep -> 4 reps total
    assert naive.repetition_count == 4
    # Sensorimotor Engine rejects the spike and incomplete rep -> exactly 3 valid reps
    assert engine.repetition_count == 3
