import cv2
import numpy as np

from performx.contracts import MovementResult
from performx.core import MovementPhase


def draw_hud(frame: np.ndarray, result: MovementResult) -> np.ndarray:
    """Draw biomechanical Heads-Up Display directly on frame in memory.
    
    Renders:
    - Current behavioral movement phase
    - Repetition counter
    - Knee angle gauge and symmetry indicator
    - Active form feedback alerts
    """
    canvas = frame.copy()
    h, w = canvas.shape[:2]

    # Semi-transparent top HUD banner
    overlay = canvas.copy()
    cv2.rectangle(overlay, (0, 0), (w, 90), (15, 23, 42), -1)
    cv2.addWeighted(overlay, 0.75, canvas, 0.25, 0, canvas)

    phase_colors = {
        MovementPhase.IDLE: (160, 160, 160),
        MovementPhase.SETUP: (255, 200, 0),
        MovementPhase.DESCENT: (255, 140, 0),
        MovementPhase.BOTTOM: (0, 215, 255),
        MovementPhase.ASCENT: (50, 205, 50),
        MovementPhase.LOCKOUT: (0, 255, 127),
    }
    phase_col = phase_colors.get(result.current_phase, (255, 255, 255))

    cv2.putText(canvas, "PERFORMX", (20, 35), cv2.FONT_HERSHEY_DUPLEX, 0.9, (255, 255, 255), 2)
    cv2.putText(canvas, f"PHASE: {result.current_phase.value}", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, phase_col, 2)

    # Calibration Status Badge
    calib_str = "CALIB: ACTIVE" if (result.calibration and result.calibration.status.value == "CALIBRATED") else "CALIB: NONE"
    calib_col = (100, 255, 100) if "ACTIVE" in calib_str else (180, 180, 180)
    cv2.putText(canvas, calib_str, (170, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.45, calib_col, 1)

    # Repetition Count Card
    cv2.putText(canvas, "REPS", (w - 140, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    cv2.putText(canvas, f"{result.repetition_count}", (w - 140, 75), cv2.FONT_HERSHEY_DUPLEX, 1.4, (0, 255, 127), 3)

    # Knee Angle & Symmetry from features
    angle_text = f"Knee: {result.features.avg_knee_angle:.1f} deg"
    sym_text = f"Symmetry: {result.features.symmetry_score:.0%}"
    cpg_text = f"CPG: {result.oscillator_phase:.2f} rad"
    cv2.putText(canvas, angle_text, (w // 2 - 130, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(canvas, sym_text, (w // 2 - 130, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 220, 255), 1)
    cv2.putText(canvas, cpg_text, (w // 2 - 130, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (100, 230, 255), 1)

    # Active Form Alerts Overlay (Banner at bottom)
    if result.active_alerts:
        alert = result.active_alerts[0]
        alert_y = h - 30
        cv2.rectangle(canvas, (0, h - 50), (w, h), (20, 20, 180), -1)
        metric_str = f" [{alert.metric_value:.1f}]" if alert.metric_value is not None else ""
        cv2.putText(canvas, f"ALERT ({alert.code}){metric_str}: {alert.message}", (20, alert_y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

    return canvas
