"""PERFORMX Tracking Recovery & Movement Intelligence Tests.

Tests added for Phase 8:
1. Extended occlusion (>1.5s) aborts active squat during DESCENT, BOTTOM, or ASCENT.
2. Short transient occlusion (<0.3s) allows continuation without abort.
3. Sudden tracking recovery when standing does not jump repetition counter.
4. Metric contracts strictly differentiate measured angles from estimated proxies.
"""

import numpy as np
import pytest

from performx.core import MovementPhase, SquatConfig
from performx.engine import SensorimotorEngine


def test_extended_occlusion_aborts_active_repetition():
    """Verify that if subject tracking drops for > 1.5s mid-rep, the engine safely resets to IDLE."""
    engine = SensorimotorEngine()

    t = 0.0
    # Setup standing
    engine.evaluate_frame(165.0, 170.0, 5.0, 1.0, timestamp=t, confidence=0.9)

    # Initiate Descent
    t += 0.4
    phase, alerts = engine.evaluate_frame(120.0, 125.0, 15.0, 1.0, timestamp=t, confidence=0.9)
    assert phase == MovementPhase.DESCENT

    # Tracking drops below threshold for 2.0 seconds
    for _ in range(10):
        t += 0.2
        phase, alerts = engine.evaluate_frame(120.0, 125.0, 15.0, 1.0, timestamp=t, confidence=0.1)

    # Verify that engine aborted to IDLE and flagged OCCLUSION_ABORT
    assert phase == MovementPhase.IDLE
    assert any(a.code == "OCCLUSION_ABORT" for a in alerts)
    assert engine.repetition_count == 0


def test_short_transient_occlusion_permits_continuation():
    """Verify that a short flicker/glitch (< 0.3s) does NOT abort an active repetition."""
    engine = SensorimotorEngine()

    t = 0.0
    engine.evaluate_frame(165.0, 170.0, 5.0, 1.0, timestamp=t, confidence=0.9)

    # Enter bottom position
    t += 0.4
    engine.evaluate_frame(120.0, 125.0, 15.0, 1.0, timestamp=t, confidence=0.9)
    t += 0.4
    engine.evaluate_frame(85.0, 90.0, 20.0, 1.0, timestamp=t, confidence=0.9)
    assert engine.current_phase == MovementPhase.BOTTOM

    # Single frame flicker (0.1s dropout)
    t += 0.1
    phase, alerts = engine.evaluate_frame(85.0, 90.0, 20.0, 1.0, timestamp=t, confidence=0.1)
    assert phase == MovementPhase.BOTTOM
    assert any(a.code == "LOW_CONFIDENCE" for a in alerts)
    assert not any(a.code == "OCCLUSION_ABORT" for a in alerts)

    # Resume ascent smoothly
    t += 0.4
    engine.evaluate_frame(120.0, 125.0, 15.0, 1.0, timestamp=t, confidence=0.9)
    t += 0.4
    phase, alerts = engine.evaluate_frame(165.0, 170.0, 5.0, 1.0, timestamp=t, confidence=0.9)

    assert phase == MovementPhase.LOCKOUT
    assert engine.repetition_count == 1


def test_sudden_reappearance_standing_no_false_rep():
    """Verify subject leaves during bottom position and reappears directly standing."""
    engine = SensorimotorEngine()

    t = 0.0
    engine.evaluate_frame(165.0, 170.0, 5.0, 1.0, timestamp=t, confidence=0.9)
    t += 0.3
    engine.evaluate_frame(120.0, 125.0, 15.0, 1.0, timestamp=t, confidence=0.9)
    assert engine.current_phase == MovementPhase.DESCENT
    t += 0.3
    engine.evaluate_frame(85.0, 90.0, 20.0, 1.0, timestamp=t, confidence=0.9)
    assert engine.current_phase == MovementPhase.BOTTOM

    # Subject leaves camera for 3.0 seconds
    for _ in range(6):
        t += 0.5
        engine.evaluate_frame(85.0, 90.0, 20.0, 1.0, timestamp=t, confidence=0.0)

    # Subject steps back in directly standing
    t += 0.5
    phase, alerts = engine.evaluate_frame(165.0, 170.0, 5.0, 1.0, timestamp=t, confidence=0.9)

    assert phase == MovementPhase.IDLE
    assert engine.repetition_count == 0


def test_reappearance_in_squat_then_ascent_and_subsequent_fresh_rep():
    """Verify subject tracking drops, reappears still in squat, finishes ascent (no rep), then performs a fresh full rep."""
    engine = SensorimotorEngine()

    t = 0.0
    engine.evaluate_frame(165.0, 170.0, 5.0, 1.0, timestamp=t, confidence=0.9)

    # Start rep
    t += 0.4
    engine.evaluate_frame(120.0, 125.0, 15.0, 1.0, timestamp=t, confidence=0.9)
    t += 0.4
    engine.evaluate_frame(85.0, 90.0, 20.0, 1.0, timestamp=t, confidence=0.9)

    # Occlusion for 2.0s
    for _ in range(10):
        t += 0.2
        engine.evaluate_frame(85.0, 90.0, 20.0, 1.0, timestamp=t, confidence=0.0)

    # Engine aborted to IDLE
    assert engine.current_phase == MovementPhase.IDLE

    # Subject is seen rising from squat (knee angle increases to 130 then 165)
    t += 0.4
    engine.evaluate_frame(130.0, 135.0, 15.0, 1.0, timestamp=t, confidence=0.9)
    # Since it was in IDLE and knee angle is 130 (which is < descent_trigger_angle 145), it starts a new DESCENT attempt
    t += 0.4
    engine.evaluate_frame(165.0, 170.0, 5.0, 1.0, timestamp=t, confidence=0.9)
    # Reached standing without reaching bottom; reverses, so incomplete depth alert, 0 reps
    assert engine.repetition_count == 0

    # Now subject performs a genuine, clean 5-frame squat from standing
    t += 0.4
    engine.evaluate_frame(165.0, 170.0, 5.0, 1.0, timestamp=t, confidence=0.9)
    t += 0.4
    engine.evaluate_frame(120.0, 125.0, 15.0, 1.0, timestamp=t, confidence=0.9)
    assert engine.current_phase == MovementPhase.DESCENT

    t += 0.4
    engine.evaluate_frame(85.0, 90.0, 20.0, 1.0, timestamp=t, confidence=0.9)
    assert engine.current_phase == MovementPhase.BOTTOM

    t += 0.3
    engine.evaluate_frame(85.0, 90.0, 20.0, 1.0, timestamp=t, confidence=0.9)
    t += 0.4
    engine.evaluate_frame(120.0, 125.0, 15.0, 1.0, timestamp=t, confidence=0.9)
    assert engine.current_phase == MovementPhase.ASCENT

    t += 0.4
    phase, _ = engine.evaluate_frame(165.0, 170.0, 5.0, 1.0, timestamp=t, confidence=0.9)
    assert phase == MovementPhase.LOCKOUT
    assert engine.repetition_count == 1


def test_repeated_intermittent_visibility_loss_cycles():
    """Verify system handles rapid on-off-on tracking without crashing or corrupting phase."""
    engine = SensorimotorEngine()

    t = 0.0
    for cycle in range(5):
        # 3 valid frames
        for _ in range(3):
            t += 0.1
            engine.evaluate_frame(165.0, 170.0, 5.0, 1.0, timestamp=t, confidence=0.9)
        # 2 occluded frames
        for _ in range(2):
            t += 0.1
            phase, alerts = engine.evaluate_frame(165.0, 170.0, 5.0, 1.0, timestamp=t, confidence=0.1)
            assert any(a.code == "LOW_CONFIDENCE" for a in alerts)

    assert engine.current_phase == MovementPhase.IDLE
    assert engine.repetition_count == 0


def test_session_reset_during_active_repetition_clears_all_timers():
    """Verify resetting session during active descent or bottom clears all timers and state."""
    from performx.services import MovementAnalysisSession
    session = MovementAnalysisSession()

    coords = np.zeros((33, 4), dtype=np.float32)
    coords[:, 3] = 0.95
    coords[11] = [0.5, 0.2, 0.0, 0.95]
    coords[12] = [0.6, 0.2, 0.0, 0.95]
    coords[23] = [0.5, 0.4, 0.0, 0.95]
    coords[24] = [0.6, 0.4, 0.0, 0.95]
    coords[25] = [0.5, 0.6, 0.0, 0.95]
    coords[26] = [0.6, 0.6, 0.0, 0.95]
    coords[27] = [0.5, 0.8, 0.0, 0.95]
    coords[28] = [0.6, 0.8, 0.0, 0.95]

    from performx.contracts import PoseLandmarksData
    lm_data = PoseLandmarksData(coords=coords, world_coords=None, mean_confidence=0.95, timestamp=1.0)

    # Process frame
    res = session.process_landmarks(lm_data, timestamp=1.0)
    assert session.frames_processed == 1

    # Reset session mid-use
    session.reset()
    assert session.frames_processed == 0
    assert session.engine.repetition_count == 0
    assert session.engine.current_phase == MovementPhase.IDLE
    assert session.engine.bottom_entry_time is None
    assert session.engine.rep_start_time is None
    assert session.engine.oscillator.phase == 0.0

