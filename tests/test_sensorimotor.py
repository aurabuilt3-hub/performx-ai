import pytest
from performx.sensorimotor import (
    MovementPhase,
    SensorimotorEngine,
    SquatConfig,
)


def test_sensorimotor_full_squat_repetition_cycle():
    """Verify state machine progresses: IDLE -> DESCENT -> BOTTOM -> ASCENT -> LOCKOUT -> IDLE."""
    config = SquatConfig(
        standing_knee_angle=160.0,
        descent_trigger_angle=140.0,
        bottom_target_angle=90.0,
        min_bottom_dwell=0.2,
        min_rep_duration=1.0,
    )
    engine = SensorimotorEngine(config=config)

    t = 0.0
    # 1. Standing posture
    phase, alerts = engine.evaluate_frame(
        knee_angle=165.0, hip_angle=170.0, torso_lean=10.0, symmetry_score=1.0, timestamp=t, confidence=0.9
    )
    assert phase == MovementPhase.IDLE
    assert engine.repetition_count == 0

    # 2. Descent initiation
    t += 0.3
    phase, alerts = engine.evaluate_frame(
        knee_angle=130.0, hip_angle=135.0, torso_lean=20.0, symmetry_score=1.0, timestamp=t, confidence=0.9
    )
    assert phase == MovementPhase.DESCENT

    # 3. Reaching bottom depth
    t += 0.4
    phase, alerts = engine.evaluate_frame(
        knee_angle=85.0, hip_angle=90.0, torso_lean=25.0, symmetry_score=1.0, timestamp=t, confidence=0.9
    )
    assert phase == MovementPhase.BOTTOM

    # 4. Controlling bottom dwell (meeting min_bottom_dwell requirement)
    t += 0.25
    phase, alerts = engine.evaluate_frame(
        knee_angle=87.0, hip_angle=92.0, torso_lean=25.0, symmetry_score=1.0, timestamp=t, confidence=0.9
    )
    assert phase == MovementPhase.BOTTOM

    # 5. Ascending phase
    t += 0.3
    phase, alerts = engine.evaluate_frame(
        knee_angle=110.0, hip_angle=115.0, torso_lean=20.0, symmetry_score=1.0, timestamp=t, confidence=0.9
    )
    assert phase == MovementPhase.ASCENT

    # 6. Lockout and completion
    t += 0.4
    phase, alerts = engine.evaluate_frame(
        knee_angle=162.0, hip_angle=165.0, torso_lean=10.0, symmetry_score=1.0, timestamp=t, confidence=0.9
    )
    assert phase == MovementPhase.LOCKOUT
    assert engine.repetition_count == 1
    assert engine.valid_reps == 1


def test_walknet_rejection_of_shallow_half_rep():
    """Verify Walknet sensory rule prevents premature ascent if depth threshold was not reached."""
    config = SquatConfig(
        standing_knee_angle=160.0,
        descent_trigger_angle=140.0,
        bottom_target_angle=90.0,
    )
    engine = SensorimotorEngine(config=config)

    t = 0.0
    # Standing
    engine.evaluate_frame(knee_angle=165.0, hip_angle=170.0, torso_lean=5.0, symmetry_score=1.0, timestamp=t, confidence=0.9)

    # Descends only to 110 deg (fails to reach target <=90 deg)
    t += 0.3
    phase, _ = engine.evaluate_frame(knee_angle=115.0, hip_angle=120.0, torso_lean=20.0, symmetry_score=1.0, timestamp=t, confidence=0.9)
    assert phase == MovementPhase.DESCENT

    # Early reversal back up without hitting bottom
    t += 0.3
    phase, alerts = engine.evaluate_frame(knee_angle=150.0, hip_angle=155.0, torso_lean=15.0, symmetry_score=1.0, timestamp=t, confidence=0.9)
    
    # Must abort rep, not increment rep count
    assert phase == MovementPhase.IDLE
    assert engine.repetition_count == 0
    assert any(a.code == "INCOMPLETE_DEPTH" for a in alerts)


def test_proprioceptive_reflex_alerts():
    """Test immediate reflexive alerts for form deviations (torso lean, asymmetry)."""
    config = SquatConfig(max_torso_lean_deg=45.0, min_symmetry_score=0.8)
    engine = SensorimotorEngine(config=config)

    # Trigger excessive forward lean
    _, alerts = engine.evaluate_frame(
        knee_angle=150.0,
        hip_angle=120.0,
        torso_lean=52.0,  # Exceeds 45 deg limit
        symmetry_score=0.95,
        timestamp=0.1,
        confidence=0.9,
    )
    assert any(a.code == "TORSO_LEAN" for a in alerts)

    # Trigger asymmetry alert
    _, alerts_sym = engine.evaluate_frame(
        knee_angle=150.0,
        hip_angle=120.0,
        torso_lean=20.0,
        symmetry_score=0.65,  # Below 0.8 limit
        timestamp=0.2,
        confidence=0.9,
    )
    assert any(a.code == "ASYMMETRY" for a in alerts_sym)
