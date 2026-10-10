"""Tests for Phase 14 Session-Level Movement Intelligence.

Validates:
1. Empty session metrics behavior (no crash, unavailable scalars default to None).
2. Single accepted repetition session metrics.
3. Multiple accepted repetitions session metrics (duration variance, dwell shifts, depth ranges).
4. Mixed accepted vs rejected repetitions partitioning.
5. Incomplete attempts tracking (reversals in descent above trigger).
6. Aborted attempts tracking (occlusion dropout during active movement).
7. Session reset completely clears SessionMetrics and attempt counters.
8. Serialization integrity (to_dict() matches contracts).
"""

import numpy as np
import pytest

from performx.core import LandmarkIndex, MovementPhase, SquatConfig
from performx.contracts import (
    PoseLandmarksData,
    SessionMetrics,
    SessionSummary,
)
from performx.engine import SensorimotorEngine
from performx.services import MovementAnalysisSession


def create_synthetic_landmarks(
    knee_angle_deg: float = 170.0,
    confidence: float = 0.95,
    timestamp: float = 0.0,
) -> PoseLandmarksData:
    """Generate synthetic 33-point PoseLandmarksData with controlled knee flexion."""
    coords = np.zeros((33, 4), dtype=np.float32)
    coords[:, 3] = confidence

    rad = np.radians(knee_angle_deg)
    # Hip at (0.5, 0.4)
    coords[LandmarkIndex.LEFT_HIP][:3] = [0.45, 0.4, 0.0]
    coords[LandmarkIndex.RIGHT_HIP][:3] = [0.55, 0.4, 0.0]

    # Knee at (0.5, 0.6)
    coords[LandmarkIndex.LEFT_KNEE][:3] = [0.45, 0.6, 0.0]
    coords[LandmarkIndex.RIGHT_KNEE][:3] = [0.55, 0.6, 0.0]

    # Ankle angled relative to tibia
    tibia_len = 0.25
    ankle_x = 0.45 + tibia_len * float(np.sin(np.pi - rad))
    ankle_y = 0.6 + tibia_len * float(np.cos(np.pi - rad))
    coords[LandmarkIndex.LEFT_ANKLE][:3] = [ankle_x, ankle_y, 0.0]
    coords[LandmarkIndex.RIGHT_ANKLE][:3] = [ankle_x + 0.1, ankle_y, 0.0]

    # Torso/Shoulders vertical above hip
    coords[LandmarkIndex.LEFT_SHOULDER][:3] = [0.45, 0.15, 0.0]
    coords[LandmarkIndex.RIGHT_SHOULDER][:3] = [0.55, 0.15, 0.0]

    return PoseLandmarksData(
        coords=coords,
        world_coords=None,
        mean_confidence=confidence,
        timestamp=timestamp,
    )


def simulate_full_squat(
    session: MovementAnalysisSession,
    start_time: float,
    descent_sec: float = 1.0,
    bottom_dwell_sec: float = 0.5,
    ascent_sec: float = 1.0,
    min_knee_angle: float = 80.0,
    fps: int = 30,
) -> float:
    """Simulate a biomechanically realistic squat trajectory through session.evaluate_landmarks."""
    dt = 1.0 / fps
    current_time = start_time

    # 1. Descent from 170 deg to min_knee_angle
    descent_steps = max(1, int(descent_sec * fps))
    for angle in np.linspace(170.0, min_knee_angle, descent_steps):
        current_time += dt
        lm = create_synthetic_landmarks(knee_angle_deg=float(angle))
        session.process_landmarks(lm, timestamp=current_time)

    # 2. Bottom dwell
    dwell_steps = max(1, int(bottom_dwell_sec * fps))
    for _ in range(dwell_steps):
        current_time += dt
        lm = create_synthetic_landmarks(knee_angle_deg=float(min_knee_angle))
        session.process_landmarks(lm, timestamp=current_time)

    # 3. Ascent back to 170 deg
    ascent_steps = max(1, int(ascent_sec * fps))
    for angle in np.linspace(min_knee_angle, 170.0, ascent_steps):
        current_time += dt
        lm = create_synthetic_landmarks(knee_angle_deg=float(angle))
        session.process_landmarks(lm, timestamp=current_time)

    return current_time


def test_empty_session_metrics_defaults():
    """An empty session must produce SessionMetrics with 0 counts and None for all scalar aggregates."""
    session = MovementAnalysisSession()
    summary = session.get_summary()

    assert summary.metrics is not None
    m = summary.metrics
    assert m.total_completed_reps == 0
    assert m.accepted_reps == 0
    assert m.rejected_reps == 0
    assert m.incomplete_attempts == 0
    assert m.aborted_attempts == 0
    assert m.mean_duration is None
    assert m.min_duration is None
    assert m.max_duration is None
    assert m.duration_range is None
    assert m.mean_descent_duration is None
    assert m.mean_bottom_dwell is None
    assert m.mean_ascent_duration is None
    assert m.mean_min_knee_angle is None
    assert m.knee_angle_range is None
    assert m.mean_rep_symmetry is None
    assert m.mean_tracking_confidence is None
    assert len(m.explainable_insights) == 1
    assert "Insufficient valid repetitions" in m.explainable_insights[0]

    # Verify serialization
    data = summary.to_dict()
    assert "metrics" in data
    assert data["metrics"]["accepted_reps"] == 0
    assert data["metrics"]["mean_duration"] is None


def test_single_accepted_rep_session_metrics():
    """A session with a single accepted rep calculates exact scalar metrics with range 0.0."""
    session = MovementAnalysisSession()
    t = 100.0

    # Execute 1 valid rep (~2.5s duration)
    end_t = simulate_full_squat(
        session,
        start_time=t,
        descent_sec=1.0,
        bottom_dwell_sec=0.5,
        ascent_sec=1.0,
        min_knee_angle=78.0,
    )

    summary = session.get_summary()
    assert summary.valid_reps == 1
    m = summary.metrics
    assert m is not None
    assert m.total_completed_reps == 1
    assert m.accepted_reps == 1
    assert m.rejected_reps == 0
    assert m.incomplete_attempts == 0
    assert m.aborted_attempts == 0

    assert m.mean_duration is not None
    assert pytest.approx(m.duration_range, abs=1e-3) == 0.0
    assert m.min_duration == m.mean_duration
    assert m.max_duration == m.mean_duration
    assert m.mean_bottom_dwell is not None
    assert m.mean_bottom_dwell >= 0.45
    assert pytest.approx(m.knee_angle_range, abs=1e-3) == 0.0
    assert m.mean_min_knee_angle is not None
    assert m.mean_min_knee_angle < 85.0
    assert len(m.explainable_insights) >= 1


def test_multiple_accepted_reps_metrics_and_dwell_shift():
    """Multiple reps with pacing differences compute accurate duration and knee ranges and dwell insights."""
    session = MovementAnalysisSession()
    t = 100.0

    # Rep 1: 1.0s descent, 0.3s dwell, 1.0s ascent -> ~2.3s, min knee 80
    t = simulate_full_squat(
        session,
        start_time=t,
        descent_sec=1.0,
        bottom_dwell_sec=0.3,
        ascent_sec=1.0,
        min_knee_angle=80.0,
    )

    # Rep 2: 1.0s descent, 0.7s dwell, 1.0s ascent -> ~2.7s, min knee 70 (longer dwell, deeper depth)
    t = simulate_full_squat(
        session,
        start_time=t + 0.5,
        descent_sec=1.0,
        bottom_dwell_sec=0.7,
        ascent_sec=1.0,
        min_knee_angle=70.0,
    )

    summary = session.get_summary()
    assert summary.valid_reps == 2
    m = summary.metrics
    assert m is not None
    assert m.total_completed_reps == 2
    assert m.accepted_reps == 2
    assert m.rejected_reps == 0

    assert m.duration_range is not None and m.duration_range > 0.1
    assert m.knee_angle_range is not None and m.knee_angle_range >= 5.0

    # Check dwell shift insight: dwell[-1] > dwell[0] + 0.2
    dwell_shift_reported = any("Bottom dwell duration was longer in later repetitions" in ins for ins in m.explainable_insights)
    assert dwell_shift_reported, f"Expected dwell shift insight, got: {m.explainable_insights}"

    depth_var_reported = any("Squat depth varied by" in ins for ins in m.explainable_insights)
    assert depth_var_reported, f"Expected depth variation insight, got: {m.explainable_insights}"


def test_mixed_accepted_and_rejected_reps():
    """A rapid sensor spike (<1.0s) is rejected, partitioned cleanly from accepted reps."""
    session = MovementAnalysisSession()
    t = 100.0

    # Rep 1: Valid (~2.5s)
    t = simulate_full_squat(
        session,
        start_time=t,
        descent_sec=1.0,
        bottom_dwell_sec=0.5,
        ascent_sec=1.0,
        min_knee_angle=80.0,
    )

    # Rep 2: Too rapid (0.2s descent, 0.25s dwell, 0.2s ascent = 0.65s total < 1.0s) -> Rejected ERRATIC_TEMPO
    t = simulate_full_squat(
        session,
        start_time=t + 0.5,
        descent_sec=0.2,
        bottom_dwell_sec=0.25,
        ascent_sec=0.2,
        min_knee_angle=80.0,
    )

    summary = session.get_summary()
    assert summary.valid_reps == 1  # Only 1 valid
    assert summary.total_reps == 1

    m = summary.metrics
    assert m is not None
    assert m.total_completed_reps == 2
    assert m.accepted_reps == 1
    assert m.rejected_reps == 1
    assert m.incomplete_attempts == 0
    assert m.aborted_attempts == 0


def test_incomplete_attempts_tracking():
    """Shallow reversal during DESCENT increments incomplete_attempts without adding completed summary."""
    session = MovementAnalysisSession()
    t = 100.0

    # Descend to 115 deg (trigger is 145 deg)
    for angle in np.linspace(170.0, 115.0, 15):
        t += 0.033
        lm = create_synthetic_landmarks(knee_angle_deg=float(angle), timestamp=t)
        session.process_landmarks(lm, timestamp=t)

    assert session.engine.current_phase.value == "DESCENT"

    # Reverse back up above 145 + 5 = 150 deg without reaching bottom (<=95 deg)
    for angle in np.linspace(115.0, 155.0, 15):
        t += 0.033
        lm = create_synthetic_landmarks(knee_angle_deg=float(angle), timestamp=t)
        session.process_landmarks(lm, timestamp=t)

    # Walknet engine should abort back to IDLE with INCOMPLETE_DEPTH alert
    assert session.engine.current_phase.value == "IDLE"
    assert session.engine.incomplete_attempts_count == 1
    assert len(session.engine.completed_summaries) == 0

    m = session.get_summary().metrics
    assert m is not None
    assert m.incomplete_attempts == 1
    assert m.accepted_reps == 0
    assert m.rejected_reps == 0


def test_aborted_attempts_tracking_on_occlusion():
    """Occlusion dropout >1.5s during movement increments aborted_attempts."""
    session = MovementAnalysisSession()
    t = 100.0

    # Descend to 110 deg (in active DESCENT)
    for angle in np.linspace(170.0, 110.0, 15):
        t += 0.033
        lm = create_synthetic_landmarks(knee_angle_deg=float(angle), timestamp=t)
        session.process_landmarks(lm, timestamp=t)

    assert session.engine.current_phase.value == "DESCENT"

    # Sudden landmark occlusion: confidence 0.0 for 1.8 seconds (>1.5s timeout)
    blank_lm = PoseLandmarksData(
        coords=np.zeros((33, 4), dtype=np.float32),
        world_coords=None,
        mean_confidence=0.0,
        timestamp=t,
    )
    for _ in range(30):
        t += 0.06
        session.process_landmarks(blank_lm, timestamp=t)

    assert session.engine.current_phase.value == "IDLE"
    assert session.engine.aborted_attempts_count == 1
    assert len(session.engine.completed_summaries) == 0

    m = session.get_summary().metrics
    assert m is not None
    assert m.aborted_attempts == 1
    assert m.incomplete_attempts == 0
    assert m.accepted_reps == 0


def test_session_reset_clears_metrics_and_counters():
    """Resetting the session completely clears SessionMetrics and all attempt counters."""
    session = MovementAnalysisSession()
    t = 100.0

    # Perform 1 valid rep
    t = simulate_full_squat(session, start_time=t)
    assert session.engine.repetition_count == 1

    # Incur 1 incomplete attempt
    for angle in np.linspace(170.0, 115.0, 15):
        t += 0.033
        session.process_landmarks(create_synthetic_landmarks(knee_angle_deg=float(angle), timestamp=t), timestamp=t)
    for angle in np.linspace(115.0, 155.0, 15):
        t += 0.033
        session.process_landmarks(create_synthetic_landmarks(knee_angle_deg=float(angle), timestamp=t), timestamp=t)

    assert session.engine.incomplete_attempts_count == 1

    # Reset
    session.reset()

    assert session.engine.repetition_count == 0
    assert session.engine.valid_reps == 0
    assert session.engine.incomplete_attempts_count == 0
    assert session.engine.aborted_attempts_count == 0
    assert len(session.engine.completed_summaries) == 0
    assert session.engine.latest_rep_summary is None

    # Summary should be fresh
    summary = session.get_summary()
    assert summary.valid_reps == 0
    assert summary.total_reps == 0
    assert summary.metrics is not None
    assert summary.metrics.accepted_reps == 0
    assert summary.metrics.rejected_reps == 0
    assert summary.metrics.incomplete_attempts == 0
    assert summary.metrics.aborted_attempts == 0
    assert summary.metrics.mean_duration is None


def test_consecutive_sessions_isolation():
    """Verify that multiple independent sessions instantiated consecutively have zero crosstalk."""
    session1 = MovementAnalysisSession()
    simulate_full_squat(session1, start_time=100.0, descent_sec=1.0, bottom_dwell_sec=0.5, ascent_sec=1.0)
    assert session1.engine.valid_reps == 1

    session2 = MovementAnalysisSession()
    assert session2.engine.valid_reps == 0
    assert session2.engine.repetition_count == 0
    assert session2.engine.incomplete_attempts_count == 0
    assert session2.engine.aborted_attempts_count == 0
    assert len(session2.engine.completed_summaries) == 0

    sum2 = session2.get_summary()
    assert sum2.metrics is not None
    assert sum2.metrics.accepted_reps == 0
    assert sum2.metrics.mean_duration is None


def test_pipeline_session_reset_integration():
    """Verify MovementPipeline.reset_session atomically resets engine, counters, and metrics."""
    from performx.pipeline import MovementPipeline
    pipeline = MovementPipeline()

    t = 100.0
    # Simulate rep through pipeline
    simulate_full_squat(pipeline.session, start_time=t)
    assert pipeline.session.engine.valid_reps == 1

    pipeline.reset_session()
    assert pipeline.session.engine.valid_reps == 0
    assert pipeline.session.engine.repetition_count == 0
    assert pipeline.session.engine.incomplete_attempts_count == 0
    assert pipeline.session.engine.aborted_attempts_count == 0
    assert len(pipeline.session.engine.completed_summaries) == 0

    metrics = pipeline.get_session_summary().metrics
    assert metrics is not None
    assert metrics.accepted_reps == 0
    assert metrics.mean_duration is None

