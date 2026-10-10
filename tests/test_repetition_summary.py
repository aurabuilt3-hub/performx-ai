"""PERFORMX Adaptive Sensorimotor Intelligence & Repetition Summary Tests.

Tests added for Phase 12:
1. Generation and correctness of compact, typed RepetitionSummary upon rep completion.
2. Accurate tracking of sub-phase intervals (descent_duration, bottom_dwell, ascent_duration).
3. Plain-language explainability for completed and rejected repetitions.
4. Repetition summary invalidation / cleanup across session resets.
5. Incomplete repetitions do NOT produce valid completed repetition summaries.
"""

import numpy as np
import pytest

from performx.core import MovementPhase, SquatConfig
from performx.contracts import RepetitionSummary
from performx.engine import SensorimotorEngine


def test_repetition_summary_generation_and_subphase_timing():
    """Verify that a valid squat produces a typed RepetitionSummary with accurate sub-phase breakdowns."""
    engine = SensorimotorEngine(config=SquatConfig(min_bottom_dwell=0.2, min_rep_duration=1.0))

    t = 0.0
    # Standing baseline
    engine.evaluate_frame(165.0, 170.0, 5.0, 0.95, timestamp=t, confidence=0.92)

    # 1. Descent phase: 1.0s (t=0.0 -> t=1.0)
    for ang in [150.0, 135.0, 115.0, 95.0]:
        t += 0.25
        engine.evaluate_frame(ang, ang + 5.0, 15.0, 0.90, timestamp=t, confidence=0.90)
    assert engine.current_phase == MovementPhase.BOTTOM

    # 2. Bottom dwell phase: 0.5s (t=1.0 -> t=1.5)
    for _ in range(2):
        t += 0.25
        engine.evaluate_frame(85.0, 90.0, 20.0, 0.92, timestamp=t, confidence=0.91)
    assert engine.current_phase == MovementPhase.BOTTOM

    # 3. Ascent phase: intermediate values (105, 125, 145) which are < standing_knee_angle (155)
    for ang in [105.0, 125.0, 145.0]:
        t += 0.25
        engine.evaluate_frame(ang, ang + 5.0, 10.0, 0.95, timestamp=t, confidence=0.92)
    assert engine.current_phase == MovementPhase.ASCENT

    # 4. Lockout at t=2.5 when reaching standing angle (165 >= 155)
    t += 0.25
    phase, alerts = engine.evaluate_frame(165.0, 170.0, 5.0, 0.98, timestamp=t, confidence=0.95)
    assert phase == MovementPhase.LOCKOUT
    assert engine.repetition_count == 1

    summary = engine.latest_rep_summary
    assert summary is not None
    assert isinstance(summary, RepetitionSummary)
    assert summary.rep_number == 1
    assert summary.is_valid is True
    assert summary.min_knee_angle == 85.0

    # Total duration: 2.0s (from t=0.5 when descent triggered at 135 deg to t=2.5)
    assert 1.9 <= summary.duration_seconds <= 2.1
    # Sub-phase durations
    assert 0.4 <= summary.descent_duration <= 0.6
    assert 0.7 <= summary.bottom_dwell <= 0.85
    assert 0.7 <= summary.ascent_duration <= 0.85

    # Averages
    assert summary.mean_symmetry >= 0.85
    assert summary.mean_confidence >= 0.88
    assert "Repetition 1 accepted" in summary.explanation


def test_rejected_too_brief_repetition_summary():
    """Verify that an erratic/sensor-glitch rapid repetition marks is_valid=False with explanatory text."""
    engine = SensorimotorEngine(config=SquatConfig(min_bottom_dwell=0.05, min_rep_duration=1.0))

    t = 0.0
    engine.evaluate_frame(165.0, 170.0, 5.0, 1.0, timestamp=t, confidence=0.9)

    # Rush through squat in 0.2 seconds total
    t += 0.05
    engine.evaluate_frame(120.0, 125.0, 10.0, 1.0, timestamp=t, confidence=0.9)
    t += 0.05
    engine.evaluate_frame(85.0, 90.0, 10.0, 1.0, timestamp=t, confidence=0.9)
    assert engine.current_phase == MovementPhase.BOTTOM

    t += 0.06
    engine.evaluate_frame(110.0, 115.0, 10.0, 1.0, timestamp=t, confidence=0.9)
    assert engine.current_phase == MovementPhase.ASCENT

    t += 0.05
    phase, alerts = engine.evaluate_frame(165.0, 170.0, 5.0, 1.0, timestamp=t, confidence=0.9)

    assert phase == MovementPhase.LOCKOUT
    assert engine.repetition_count == 0  # Not incremented

    summary = engine.latest_rep_summary
    assert summary is not None
    assert summary.is_valid is False
    assert "duration too brief" in summary.explanation
    assert any(a.code == "ERRATIC_TEMPO" for a in alerts)


def test_session_reset_clears_latest_rep_summary():
    """Verify that resetting session cleanses latest_rep_summary."""
    from performx.services import MovementAnalysisSession
    session = MovementAnalysisSession()

    # Complete a valid rep directly
    t = 0.0
    session.engine.evaluate_frame(165.0, 170.0, 5.0, 1.0, timestamp=t, confidence=0.9)
    t += 0.4
    session.engine.evaluate_frame(120.0, 125.0, 10.0, 1.0, timestamp=t, confidence=0.9)
    t += 0.4
    session.engine.evaluate_frame(85.0, 90.0, 10.0, 1.0, timestamp=t, confidence=0.9)
    t += 0.3
    session.engine.evaluate_frame(85.0, 90.0, 10.0, 1.0, timestamp=t, confidence=0.9)
    t += 0.4
    session.engine.evaluate_frame(120.0, 125.0, 10.0, 1.0, timestamp=t, confidence=0.9)
    t += 0.4
    session.engine.evaluate_frame(165.0, 170.0, 5.0, 1.0, timestamp=t, confidence=0.9)

    assert session.engine.latest_rep_summary is not None
    assert session.engine.repetition_count == 1

    # Reset
    session.reset()
    assert session.engine.latest_rep_summary is None
    assert session.engine.repetition_count == 0


def test_back_to_back_repetitions_no_metric_contamination():
    """Verify consecutive reps record independent depths, durations, and counts without leaking state."""
    engine = SensorimotorEngine(config=SquatConfig(min_bottom_dwell=0.1, min_rep_duration=0.8))

    t = 0.0
    # Rep 1: Deep squat (75 deg), 2.0s
    engine.evaluate_frame(165.0, 170.0, 5.0, 1.0, timestamp=t, confidence=0.95)
    t += 0.5
    engine.evaluate_frame(120.0, 125.0, 10.0, 1.0, timestamp=t, confidence=0.95)
    t += 0.5
    engine.evaluate_frame(75.0, 80.0, 15.0, 1.0, timestamp=t, confidence=0.95)
    t += 0.2
    engine.evaluate_frame(75.0, 80.0, 15.0, 1.0, timestamp=t, confidence=0.95)
    t += 0.4
    engine.evaluate_frame(115.0, 120.0, 10.0, 1.0, timestamp=t, confidence=0.95)
    t += 0.4
    engine.evaluate_frame(165.0, 170.0, 5.0, 1.0, timestamp=t, confidence=0.95)

    assert engine.repetition_count == 1
    rep1_summary = engine.latest_rep_summary
    assert rep1_summary is not None
    assert rep1_summary.rep_number == 1
    assert rep1_summary.min_knee_angle == 75.0

    # Step back into IDLE
    t += 0.1
    engine.evaluate_frame(165.0, 170.0, 5.0, 1.0, timestamp=t, confidence=0.95)

    # Rep 2: Moderate squat (90 deg), 1.6s
    t += 0.4
    engine.evaluate_frame(120.0, 125.0, 10.0, 1.0, timestamp=t, confidence=0.90)
    t += 0.4
    engine.evaluate_frame(90.0, 95.0, 15.0, 1.0, timestamp=t, confidence=0.90)
    t += 0.2
    engine.evaluate_frame(90.0, 95.0, 15.0, 1.0, timestamp=t, confidence=0.90)
    t += 0.3
    engine.evaluate_frame(115.0, 120.0, 10.0, 1.0, timestamp=t, confidence=0.90)
    t += 0.3
    engine.evaluate_frame(165.0, 170.0, 5.0, 1.0, timestamp=t, confidence=0.90)

    assert engine.repetition_count == 2
    rep2_summary = engine.latest_rep_summary
    assert rep2_summary is not None
    assert rep2_summary.rep_number == 2
    assert rep2_summary.min_knee_angle == 90.0  # Does NOT leak 75.0 from Rep 1!
    assert rep2_summary.duration_seconds < rep1_summary.duration_seconds


def test_repetition_summary_rejects_negative_or_nan_metrics():
    """Verify that RepetitionSummary dataclass rejects negative durations or NaN values."""
    with pytest.raises(ValueError, match="must be non-negative"):
        RepetitionSummary(
            rep_number=1,
            duration_seconds=-1.0,
            descent_duration=0.5,
            bottom_dwell=0.2,
            ascent_duration=0.3,
            min_knee_angle=80.0,
            mean_symmetry=0.9,
            mean_confidence=0.9,
        )

    with pytest.raises(ValueError, match="must be finite"):
        RepetitionSummary(
            rep_number=1,
            duration_seconds=float("nan"),
            descent_duration=0.5,
            bottom_dwell=0.2,
            ascent_duration=0.3,
            min_knee_angle=80.0,
            mean_symmetry=0.9,
            mean_confidence=0.9,
        )
