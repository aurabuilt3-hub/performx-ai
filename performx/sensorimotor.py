from dataclasses import dataclass
from enum import Enum
import numpy as np


class MovementPhase(str, Enum):
    """Behavioral movement states representing exercise progression."""
    IDLE = "IDLE"              # Standing still, preparing
    SETUP = "SETUP"            # Aligned, descent initiating
    DESCENT = "DESCENT"        # Eccentric lowering phase
    BOTTOM = "BOTTOM"          # Inflection zone / deepest dwell / hole
    ASCENT = "ASCENT"          # Concentric rising phase
    LOCKOUT = "LOCKOUT"        # Returned to top, rep completed


class FormAlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ALERT = "ALERT"


@dataclass
class FormAlert:
    """Proprioceptive form alert triggered by sensorimotor rules."""
    code: str
    message: str
    severity: FormAlertSeverity
    timestamp: float


@dataclass
class SquatConfig:
    """Configurable biomechanical thresholds for squat movement."""
    # Knee angle thresholds (degrees)
    # Standing is ~165-180 deg; parallel squat is ~90 deg; deep squat is <80 deg
    standing_knee_angle: float = 155.0
    descent_trigger_angle: float = 145.0
    bottom_target_angle: float = 95.0
    deep_squat_angle: float = 75.0
    
    # Timing and dwell thresholds (seconds)
    min_bottom_dwell: float = 0.20   # Must pause or control at bottom (Walknet pause rule)
    max_bottom_dwell: float = 4.00   # Fatigue / stuck warning
    min_rep_duration: float = 1.00   # Avoid jitter counting (false positive rep rejection)
    
    # Biomechanical safety limits
    max_torso_lean_deg: float = 48.0 # Excessive forward trunk lean
    min_symmetry_score: float = 0.78 # Bilateral asymmetry threshold
    min_visibility_conf: float = 0.50 # Keypoint confidence gate


class PhaseOscillator:
    """Coupled Phase Oscillator for rhythmic movement tracking.
    
    Inspired by Drosophila CPG (Central Pattern Generator) networks in FlyGym:
    Tracks an internal cyclical phase theta in [0, 2*pi).
    Phase 0 = top standing, pi/2 = descent midpoint, pi = bottom inflection,
    3*pi/2 = ascent midpoint, 2*pi = lockout / completion.
    
    Allows calculating instantaneous movement tempo, cadence, and phase lag.
    """

    def __init__(self, target_frequency_hz: float = 0.35):
        self.freq = target_frequency_hz  # ~1 rep every 2.8-3.0 seconds
        self.phase: float = 0.0          # theta in [0, 2*pi)
        self.last_timestamp: float | None = None
        self.cadence_bpm: float = target_frequency_hz * 60.0

    def update(self, observed_depth_ratio: float, dt: float):
        """Coupled oscillator phase update.
        
        depth_ratio in [0.0, 1.0]: 0.0 is standing, 1.0 is full bottom depth.
        Couples oscillator phase to kinematic depth to maintain rhythmic sync.
        """
        # Autonomous natural frequency step
        omega = 2.0 * np.pi * self.freq
        
        # Kinematic attractor phase
        # If moving down (depth increasing), target is in [0, pi]
        # If moving up, target is in [pi, 2*pi]
        target_phase = observed_depth_ratio * np.pi if self.phase < np.pi else (2.0 - observed_depth_ratio) * np.pi
        
        # Phase coupling force (Kuramoto-style coupling)
        coupling_strength = 1.8
        phase_diff = np.sin(target_phase - self.phase)
        
        d_theta = omega + coupling_strength * phase_diff
        self.phase = (self.phase + d_theta * dt) % (2.0 * np.pi)

    def reset(self):
        self.phase = 0.0
        self.last_timestamp = None


class SensorimotorEngine:
    """Fruit-fly inspired Sensorimotor Decision Engine for human movement.
    
    Core Principles translated from Drosophila neurobiology:
    1. Sensorimotor Feedback Loop: Real-time proprioceptive cues for joint alignment.
    2. Walknet State Gating: Rigid state progression preventing false counts.
       (e.g., Cannot transition from Descent -> Ascent without satisfying Bottom threshold).
    3. Coupled CPG Rhythm: Tracks movement cadence and identifies hesitation or rush.
    4. Adaptive Refractory Filtering: Temporal dwell checks prevent false rep triggers.
    """

    def __init__(self, config: SquatConfig | None = None):
        self.config = config or SquatConfig()
        self.current_phase = MovementPhase.IDLE
        self.oscillator = PhaseOscillator()
        
        # Repetition metrics
        self.repetition_count = 0
        self.valid_reps = 0
        self.rep_start_time: float | None = None
        self.bottom_entry_time: float | None = None
        self.last_phase_change_time: float = 0.0
        
        # Depth tracking
        self.min_knee_angle_in_rep: float = 180.0
        self.last_rep_bottom_dwell: float = 0.0
        self.last_rep_duration: float = 0.0
        self.last_rep_symmetry: float = 1.0
        
        # Active form alerts for current frame
        self.active_alerts: list[FormAlert] = []

    def evaluate_frame(
        self,
        knee_angle: float,
        hip_angle: float,
        torso_lean: float,
        symmetry_score: float,
        timestamp: float,
        confidence: float,
    ) -> tuple[MovementPhase, list[FormAlert]]:
        """Processes biomechanical features through sensory gating and state rules."""
        self.active_alerts = []

        # 0. Confidence gate (chordotonal signal loss check)
        if confidence < self.config.min_visibility_conf:
            self.active_alerts.append(
                FormAlert(
                    code="LOW_CONFIDENCE",
                    message="Landmark tracking degraded. Ensure full body is visible.",
                    severity=FormAlertSeverity.INFO,
                    timestamp=timestamp,
                )
            )
            return self.current_phase, self.active_alerts

        # Initialize timing if first frame
        if self.last_phase_change_time == 0.0:
            self.last_phase_change_time = timestamp

        dt = timestamp - self.last_phase_change_time if self.last_phase_change_time > 0 else 0.033
        dt = max(min(dt, 0.2), 0.001)

        # Update coupled CPG oscillator
        depth_span = max(self.config.standing_knee_angle - self.config.bottom_target_angle, 10.0)
        norm_depth = float(np.clip((self.config.standing_knee_angle - knee_angle) / depth_span, 0.0, 1.0))
        self.oscillator.update(norm_depth, dt)

        # 1. Proprioceptive Feedback Loops (Reflex Alerts)
        if torso_lean > self.config.max_torso_lean_deg:
            self.active_alerts.append(
                FormAlert(
                    code="TORSO_LEAN",
                    message=f"Excessive forward torso lean ({torso_lean:.1f}° > {self.config.max_torso_lean_deg}°). Keep chest proud.",
                    severity=FormAlertSeverity.WARNING,
                    timestamp=timestamp,
                )
            )

        if symmetry_score < self.config.min_symmetry_score:
            self.active_alerts.append(
                FormAlert(
                    code="ASYMMETRY",
                    message=f"Bilateral asymmetry detected ({symmetry_score:.0%}). Balance weight evenly.",
                    severity=FormAlertSeverity.WARNING,
                    timestamp=timestamp,
                )
            )

        # 2. Walknet-Inspired State Transition Rules
        prev_phase = self.current_phase

        if self.current_phase == MovementPhase.IDLE:
            if knee_angle < self.config.descent_trigger_angle:
                self.current_phase = MovementPhase.DESCENT
                self.rep_start_time = timestamp
                self.min_knee_angle_in_rep = knee_angle
                self.last_phase_change_time = timestamp

        elif self.current_phase == MovementPhase.SETUP:
            if knee_angle < self.config.descent_trigger_angle:
                self.current_phase = MovementPhase.DESCENT
                self.rep_start_time = timestamp
                self.min_knee_angle_in_rep = knee_angle
                self.last_phase_change_time = timestamp

        elif self.current_phase == MovementPhase.DESCENT:
            self.min_knee_angle_in_rep = min(self.min_knee_angle_in_rep, knee_angle)

            # Rule: Transition to BOTTOM requires reaching depth threshold
            if knee_angle <= self.config.bottom_target_angle:
                self.current_phase = MovementPhase.BOTTOM
                self.bottom_entry_time = timestamp
                self.last_phase_change_time = timestamp
            # Rule: Reversal before reaching target depth (aborted or shallow rep)
            elif knee_angle > self.config.descent_trigger_angle + 5.0:
                self.current_phase = MovementPhase.IDLE
                self.active_alerts.append(
                    FormAlert(
                        code="INCOMPLETE_DEPTH",
                        message="Squat did not reach target depth before reversing.",
                        severity=FormAlertSeverity.INFO,
                        timestamp=timestamp,
                    )
                )

        elif self.current_phase == MovementPhase.BOTTOM:
            self.min_knee_angle_in_rep = min(self.min_knee_angle_in_rep, knee_angle)
            dwell = timestamp - (self.bottom_entry_time or timestamp)

            # Rule: Excessive bottom dwell alert
            if dwell > self.config.max_bottom_dwell:
                self.active_alerts.append(
                    FormAlert(
                        code="BOTTOM_STUCK",
                        message=f"Extended pause at bottom ({dwell:.1f}s). Initiate ascent safely.",
                        severity=FormAlertSeverity.ALERT,
                        timestamp=timestamp,
                    )
                )

            # Rule: Transition to ASCENT requires knee beginning extension
            # AND having met the minimum sensory dwell time (prevent jitter bounce)
            if knee_angle > self.config.bottom_target_angle + 5.0 and dwell >= self.config.min_bottom_dwell:
                self.current_phase = MovementPhase.ASCENT
                self.last_rep_bottom_dwell = dwell
                self.last_phase_change_time = timestamp

        elif self.current_phase == MovementPhase.ASCENT:
            # Rule: Transition to LOCKOUT when knees return to standing angle
            if knee_angle >= self.config.standing_knee_angle:
                self.current_phase = MovementPhase.LOCKOUT
                self.last_phase_change_time = timestamp
                duration = timestamp - (self.rep_start_time or timestamp)
                self.last_rep_duration = duration
                self.last_rep_symmetry = symmetry_score

                # Quality filter: Must satisfy minimum duration to reject rapid sensor spikes
                if duration >= self.config.min_rep_duration:
                    self.repetition_count += 1
                    self.valid_reps += 1
                else:
                    self.active_alerts.append(
                        FormAlert(
                            code="ERRATIC_TEMPO",
                            message="Repetition rejected: duration too brief (sensor noise).",
                            severity=FormAlertSeverity.INFO,
                            timestamp=timestamp,
                        )
                    )

        elif self.current_phase == MovementPhase.LOCKOUT:
            # Reset state back to IDLE ready for next rep
            if knee_angle >= self.config.standing_knee_angle - 5.0:
                self.current_phase = MovementPhase.IDLE
                self.last_phase_change_time = timestamp

        return self.current_phase, self.active_alerts

    def reset(self):
        """Reset all counters and state."""
        self.current_phase = MovementPhase.IDLE
        self.repetition_count = 0
        self.valid_reps = 0
        self.rep_start_time = None
        self.bottom_entry_time = None
        self.min_knee_angle_in_rep = 180.0
        self.last_rep_bottom_dwell = 0.0
        self.last_rep_duration = 0.0
        self.active_alerts = []
        self.oscillator.reset()
