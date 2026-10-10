import cv2
import numpy as np

from performx.pipeline import MovementMetrics
from performx.sensorimotor import MovementPhase


def draw_hud(frame: np.ndarray, metrics: MovementMetrics) -> np.ndarray:
    """Draw biomechanical Heads-Up Display directly on frame in memory.
    
    Renders:
    - Current behavioral movement phase
    - Repetition counter
    - Knee angle gauge and symmetry indicator
    - CPG rhythm indicator
    - Active form feedback alerts
    """
    canvas = frame.copy()
    h, w = canvas.shape[:2]

    # Semi-transparent top HUD banner
    overlay = canvas.copy()
    cv2.rectangle(overlay, (0, 0), (w, 90), (15, 23, 42), -1)
    cv2.addWeighted(overlay, 0.75, canvas, 0.25, 0, canvas)

    # Title & Phase
    phase_colors = {
        MovementPhase.IDLE: (160, 160, 160),
        MovementPhase.SETUP: (255, 200, 0),
        MovementPhase.DESCENT: (255, 140, 0),
        MovementPhase.BOTTOM: (0, 215, 255),
        MovementPhase.ASCENT: (50, 205, 50),
        MovementPhase.LOCKOUT: (0, 255, 127),
    }
    phase_col = phase_colors.get(metrics.current_phase, (255, 255, 255))

    cv2.putText(canvas, "PERFORMX", (20, 35), cv2.FONT_HERSHEY_DUPLEX, 0.9, (255, 255, 255), 2)
    cv2.putText(canvas, f"PHASE: {metrics.current_phase.value}", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, phase_col, 2)

    # Repetition Count Card
    cv2.putText(canvas, "REPS", (w - 140, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    cv2.putText(canvas, f"{metrics.repetition_count}", (w - 140, 75), cv2.FONT_HERSHEY_DUPLEX, 1.4, (0, 255, 127), 3)

    # Knee Angle & Symmetry
    angle_text = f"Knee: {metrics.avg_knee_angle:.1f} deg"
    sym_text = f"Symmetry: {metrics.symmetry_score:.0%}"
    cv2.putText(canvas, angle_text, (w // 2 - 120, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
    cv2.putText(canvas, sym_text, (w // 2 - 120, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 220, 255), 1)

    # Active Form Alerts Overlay (Banner at bottom)
    if metrics.active_alerts:
        alert = metrics.active_alerts[0]
        alert_y = h - 35
        cv2.rectangle(canvas, (0, h - 55), (w, h), (20, 20, 180), -1)
        cv2.putText(canvas, f"ALERT: {alert.message}", (20, alert_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    return canvas
