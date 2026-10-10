"""PERFORMX Engine: Algorithmic core for filtering, kinematics, and sensorimotor intelligence.

Translates Drosophila melanogaster neurobiology into testable software:
1. Walknet Rule Gating: State machine ensuring mechanical depth and dwell conditions.
2. Central Pattern Generator (CPG): Kuramoto coupled phase-amplitude oscillator.
3. Chordotonal Proprioceptive Reflexes: Low-latency form cues for trunk lean and asymmetry.
4. One Euro Filter: Adaptive low-pass filter dynamically attenuating high-frequency jitter.
"""

from dataclasses import dataclass
import math
import numpy as np

from performx.core import (
    FormAlertSeverity,
    MovementPhase,
    SquatConfig,
)
from performx.contracts import FormAlertData, RepetitionSummary


class OneEuroFilter:
    """1€ Filter: Adaptive Low-Pass Filter for real-time jitter reduction.
    
    Inspired by MediaPipe's OneEuroFilter (mediapipe/util/filtering/one_euro_filter.cc)
    and Casiez et al., CHI 2012.
    """

    def __init__(self, freq: float = 30.0, min_cutoff: float = 1.0, beta: float = 0.007, d_cutoff: float = 1.0):
        if freq <= 0.0 or not math.isfinite(freq):
            raise ValueError(f"freq must be finite > 0, got {freq}")
        if min_cutoff <= 0.0 or not math.isfinite(min_cutoff):
            raise ValueError(f"min_cutoff must be finite > 0, got {min_cutoff}")
        if beta < 0.0 or not math.isfinite(beta):
            raise ValueError(f"beta must be finite >= 0, got {beta}")
        if d_cutoff <= 0.0 or not math.isfinite(d_cutoff):
            raise ValueError(f"d_cutoff must be finite > 0, got {d_cutoff}")

        self.freq = float(freq)
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)

        self._x_prev: np.ndarray | None = None
        self._dx_prev: np.ndarray | None = None
        self._t_prev: float | None = None

    def _alpha(self, cutoff: np.ndarray | float, dt: float) -> np.ndarray | float:
        tau = 1.0 / (2.0 * np.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def filter(self, x: np.ndarray | float, timestamp: float | None = None) -> np.ndarray | float:
        x_val = np.asarray(x, dtype=np.float64)

        if not np.all(np.isfinite(x_val)):
            # If incoming value is NaN/Inf, preserve prior estimate if available
            return self._x_prev if self._x_prev is not None else x_val

        if self._x_prev is None:
            self._x_prev = x_val.copy()
            self._dx_prev = np.zeros_like(x_val)
            self._t_prev = timestamp
            return x

        if timestamp is not None and self._t_prev is not None:
            dt = timestamp - self._t_prev
            if dt <= 1e-6 or not math.isfinite(dt):
                dt = 1.0 / self.freq
        else:
            dt = 1.0 / self.freq

        self._t_prev = timestamp

        # Derivative smoothing
        dx = (x_val - self._x_prev) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        dx_hat = a_d * dx + (1.0 - a_d) * self._dx_prev
        self._dx_prev = dx_hat

        # Adaptive cutoff based on instantaneous velocity
        cutoff = self.min_cutoff + self.beta * np.abs(dx_hat)
        a = self._alpha(cutoff, dt)

        # Output estimate
        x_hat = a * x_val + (1.0 - a) * self._x_prev
        self._x_prev = x_hat

        if np.isscalar(x):
            return float(x_hat)
        return x_hat

    def reset(self):
        self._x_prev = None
        self._dx_prev = None
        self._t_prev = None


# ---------------------------------------------------------
# Vectorized Kinematic Geometry
# ---------------------------------------------------------

def compute_angle_2d(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Calculate planar angle ABC (degrees) with vertex at b."""
    ba = np.asarray(a[:2], dtype=np.float64) - np.asarray(b[:2], dtype=np.float64)
    bc = np.asarray(c[:2], dtype=np.float64) - np.asarray(b[:2], dtype=np.float64)

    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)

    if norm_ba < 1e-7 or norm_bc < 1e-7:
        return 0.0

    cosine = np.dot(ba, bc) / (norm_ba * norm_bc)
    cosine = np.clip(cosine, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosine)))


def compute_angle_3d(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Calculate 3D angle ABC (degrees) with vertex at b."""
    ba = np.asarray(a[:3], dtype=np.float64) - np.asarray(b[:3], dtype=np.float64)
    bc = np.asarray(c[:3], dtype=np.float64) - np.asarray(b[:3], dtype=np.float64)

    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)

    if norm_ba < 1e-7 or norm_bc < 1e-7:
        return 0.0

    cosine = np.dot(ba, bc) / (norm_ba * norm_bc)
    cosine = np.clip(cosine, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosine)))


def compute_torso_inclination(shoulder: np.ndarray, hip: np.ndarray) -> float:
    """Compute torso inclination relative to vertical (degrees). 0 = upright."""
    dx = shoulder[0] - hip[0]
    dy = hip[1] - shoulder[1]
    angle_rad = np.arctan2(abs(dx), max(dy, 1e-6))
    return float(np.degrees(angle_rad))


def compute_bilateral_symmetry(left_val: float, right_val: float) -> float:
    """Calculate bilateral symmetry in [0.0, 1.0], 1.0 is exact symmetry."""
    diff = abs(left_val - right_val)
    denom = max(abs(left_val), abs(right_val), 1.0)
    score = 1.0 - (diff / denom)
    return float(np.clip(score, 0.0, 1.0))


def compute_knee_lateral_shift(hip: np.ndarray, knee: np.ndarray, ankle: np.ndarray) -> float:
    """Measure knee lateral displacement normalized by leg segment length."""
    hip_pt = np.asarray(hip[:2], dtype=np.float64)
    knee_pt = np.asarray(knee[:2], dtype=np.float64)
    ankle_pt = np.asarray(ankle[:2], dtype=np.float64)

    axis = ankle_pt - hip_pt
    leg_len = np.linalg.norm(axis)
    if leg_len < 1e-6:
        return 0.0

    return float(np.cross(axis, knee_pt - hip_pt) / leg_len)


def compute_segment_length_2d(p1: np.ndarray, p2: np.ndarray) -> float:
    """Calculate Euclidean distance between two 2D points in normalized image space."""
    return float(np.linalg.norm(np.asarray(p1[:2], dtype=np.float64) - np.asarray(p2[:2], dtype=np.float64)))


# ---------------------------------------------------------
# Drosophila CPG Phase Oscillator
# ---------------------------------------------------------

class PhaseOscillator:
    """Coupled Phase Oscillator for rhythmic movement tracking.
    
    Inspired by Drosophila CPG (Central Pattern Generator) networks in FlyGym.
    Tracks an internal cyclical phase theta in [0, 2*pi).
    """

    def __init__(self, target_frequency_hz: float = 0.35):
        self.freq = target_frequency_hz
        self.phase: float = 0.0
        self.last_timestamp: float | None = None

    def update(self, observed_depth_ratio: float, dt: float):
        omega = 2.0 * np.pi * self.freq
        target_phase = observed_depth_ratio * np.pi if self.phase < np.pi else (2.0 - observed_depth_ratio) * np.pi
        coupling_strength = 1.8
        phase_diff = np.sin(target_phase - self.phase)
        
        d_theta = omega + coupling_strength * phase_diff
        self.phase = float((self.phase + d_theta * dt) % (2.0 * np.pi))

    def reset(self):
        self.phase = 0.0
        self.last_timestamp = None


# ---------------------------------------------------------
# Sensorimotor Decision Engine
# ---------------------------------------------------------

class SensorimotorEngine:
    """Fruit-fly inspired Sensorimotor Decision Engine for human movement.
    
    Core Principles translated from Drosophila neurobiology:
    1. Sensorimotor Feedback Loop: Real-time proprioceptive cues for joint alignment.
    2. Walknet State Gating: Rigid state progression preventing false counts.
    3. Coupled CPG Rhythm: Tracks movement cadence and identifies hesitation or rush.
    4. Adaptive Refractory Filtering: Temporal dwell checks prevent false rep triggers.
    """

    def __init__(self, config: SquatConfig | None = None):
        self.config = config or SquatConfig()
        self.current_phase = MovementPhase.IDLE
        self.oscillator = PhaseOscillator()

        self.repetition_count = 0
        self.valid_reps = 0
        self.rep_start_time: float | None = None
        self.bottom_entry_time: float | None = None
        self.last_phase_change_time: float = 0.0

        self.min_knee_angle_in_rep: float = 180.0
        self.last_rep_bottom_dwell: float = 0.0
        self.last_rep_duration: float = 0.0
        self.last_rep_symmetry: float = 1.0
        self.latest_rep_summary: RepetitionSummary | None = None
        self.completed_summaries: list[RepetitionSummary] = []
        self.incomplete_attempts_count: int = 0
        self.aborted_attempts_count: int = 0
        self._ascent_entry_time: float | None = None
        self._rep_symmetries: list[float] = []
        self._rep_confidences: list[float] = []
        self._last_frame_time: float | None = None
        self._last_valid_time: float | None = None

        self.active_alerts: list[FormAlertData] = []

    def evaluate_frame(
        self,
        knee_angle: float,
        hip_angle: float,
        torso_lean: float,
        symmetry_score: float,
        timestamp: float,
        confidence: float,
    ) -> tuple[MovementPhase, list[FormAlertData]]:
        self.active_alerts = []

        # 0. Confidence gate (chordotonal signal loss check)
        if confidence < self.config.min_visibility_conf:
            self.active_alerts.append(
                FormAlertData(
                    code="LOW_CONFIDENCE",
                    message="Landmark tracking degraded. Ensure full body is visible.",
                    severity=FormAlertSeverity.INFO,
                    timestamp=timestamp,
                    metric_value=confidence,
                )
            )
            # If tracking is lost during an active rep for extended duration (>1.5s), abort safely to IDLE
            if self._last_valid_time is not None:
                dropout_duration = timestamp - self._last_valid_time
                if dropout_duration > 1.5:
                    if self.current_phase in (MovementPhase.DESCENT, MovementPhase.BOTTOM, MovementPhase.ASCENT):
                        self.current_phase = MovementPhase.IDLE
                        self.rep_start_time = None
                        self.bottom_entry_time = None
                        self.min_knee_angle_in_rep = 180.0
                        self.last_phase_change_time = timestamp
                        self._was_occlusion_aborted = True
                        self.aborted_attempts_count += 1
                    
                    if getattr(self, "_was_occlusion_aborted", False):
                        self.active_alerts.append(
                            FormAlertData(
                                code="OCCLUSION_ABORT",
                                message="Movement tracking lost for >1.5s during repetition; rep safely aborted.",
                                severity=FormAlertSeverity.WARNING,
                                timestamp=timestamp,
                                metric_value=dropout_duration,
                            )
                        )
            return self.current_phase, self.active_alerts

        # Valid frame received - calculate dt and update last_valid_time
        if self._last_valid_time is None or self._last_frame_time is None:
            dt = 0.033
        else:
            dt = timestamp - self._last_frame_time
            if dt <= 1e-6 or not math.isfinite(dt):
                dt = 0.033
            else:
                dt = min(dt, 0.5)  # Cap large frame drops to 500ms

        self._last_frame_time = timestamp
        self._last_valid_time = timestamp
        self._was_occlusion_aborted = False

        # Initialize phase timing if first frame
        if self.last_phase_change_time == 0.0:
            self.last_phase_change_time = timestamp

        # Update coupled CPG oscillator with frame dt
        depth_span = max(self.config.standing_knee_angle - self.config.bottom_target_angle, 10.0)
        norm_depth = float(np.clip((self.config.standing_knee_angle - knee_angle) / depth_span, 0.0, 1.0))
        self.oscillator.update(norm_depth, dt)

        # 1. Proprioceptive Feedback Loops (Reflex Alerts)
        if torso_lean > self.config.max_torso_lean_deg:
            self.active_alerts.append(
                FormAlertData(
                    code="TORSO_LEAN",
                    message=f"Excessive forward torso lean ({torso_lean:.1f}° > {self.config.max_torso_lean_deg}°). Keep chest proud.",
                    severity=FormAlertSeverity.WARNING,
                    timestamp=timestamp,
                    metric_value=torso_lean,
                )
            )

        if symmetry_score < self.config.min_symmetry_score:
            self.active_alerts.append(
                FormAlertData(
                    code="ASYMMETRY",
                    message=f"Bilateral asymmetry detected ({symmetry_score:.0%}). Balance weight evenly.",
                    severity=FormAlertSeverity.WARNING,
                    timestamp=timestamp,
                    metric_value=symmetry_score,
                )
            )

        # Record symmetry and confidence samples during active movement
        if self.current_phase in (MovementPhase.DESCENT, MovementPhase.BOTTOM, MovementPhase.ASCENT):
            self._rep_symmetries.append(symmetry_score)
            self._rep_confidences.append(confidence)

        # 2. Walknet State Gating Rules
        if self.current_phase == MovementPhase.IDLE:
            if knee_angle < self.config.descent_trigger_angle:
                self.current_phase = MovementPhase.DESCENT
                self.rep_start_time = timestamp
                self.min_knee_angle_in_rep = knee_angle
                self.last_phase_change_time = timestamp
                self._rep_symmetries = [symmetry_score]
                self._rep_confidences = [confidence]

        elif self.current_phase == MovementPhase.SETUP:
            if knee_angle < self.config.descent_trigger_angle:
                self.current_phase = MovementPhase.DESCENT
                self.rep_start_time = timestamp
                self.min_knee_angle_in_rep = knee_angle
                self.last_phase_change_time = timestamp
                self._rep_symmetries = [symmetry_score]
                self._rep_confidences = [confidence]

        elif self.current_phase == MovementPhase.DESCENT:
            self.min_knee_angle_in_rep = min(self.min_knee_angle_in_rep, knee_angle)

            if knee_angle <= self.config.bottom_target_angle:
                self.current_phase = MovementPhase.BOTTOM
                self.bottom_entry_time = timestamp
                self.last_phase_change_time = timestamp
            elif knee_angle > self.config.descent_trigger_angle + 5.0:
                self.current_phase = MovementPhase.IDLE
                self.incomplete_attempts_count += 1
                self._rep_symmetries.clear()
                self._rep_confidences.clear()
                self.active_alerts.append(
                    FormAlertData(
                        code="INCOMPLETE_DEPTH",
                        message="Squat did not reach target depth before reversing.",
                        severity=FormAlertSeverity.INFO,
                        timestamp=timestamp,
                        metric_value=knee_angle,
                    )
                )

        elif self.current_phase == MovementPhase.BOTTOM:
            self.min_knee_angle_in_rep = min(self.min_knee_angle_in_rep, knee_angle)
            dwell = timestamp - (self.bottom_entry_time or timestamp)

            if dwell > self.config.max_bottom_dwell:
                self.active_alerts.append(
                    FormAlertData(
                        code="BOTTOM_STUCK",
                        message=f"Extended pause at bottom ({dwell:.1f}s). Initiate ascent safely.",
                        severity=FormAlertSeverity.ALERT,
                        timestamp=timestamp,
                        metric_value=dwell,
                    )
                )

            # Rule: Transition to ASCENT requires knee extension AND meeting min dwell
            if knee_angle > self.config.bottom_target_angle + 5.0 and dwell >= self.config.min_bottom_dwell:
                self.current_phase = MovementPhase.ASCENT
                self.last_rep_bottom_dwell = dwell
                self.last_phase_change_time = timestamp
                self._ascent_entry_time = timestamp

        elif self.current_phase == MovementPhase.ASCENT:
            if knee_angle >= self.config.standing_knee_angle:
                self.current_phase = MovementPhase.LOCKOUT
                self.last_phase_change_time = timestamp
                duration = timestamp - (self.rep_start_time or timestamp)
                self.last_rep_duration = duration
                self.last_rep_symmetry = symmetry_score

                # Calculate sub-phase intervals
                t_start = self.rep_start_time or timestamp
                t_bottom = self.bottom_entry_time or t_start
                t_ascent = self._ascent_entry_time or t_bottom
                descent_dur = max(0.0, t_bottom - t_start)
                bottom_dwell = max(0.0, t_ascent - t_bottom)
                ascent_dur = max(0.0, timestamp - t_ascent)
                mean_sym = float(np.mean(self._rep_symmetries)) if self._rep_symmetries else symmetry_score
                mean_conf = float(np.mean(self._rep_confidences)) if self._rep_confidences else confidence

                # Reject sensor spikes with min rep duration
                if duration >= self.config.min_rep_duration:
                    self.repetition_count += 1
                    self.valid_reps += 1
                    self.latest_rep_summary = RepetitionSummary(
                        rep_number=self.repetition_count,
                        duration_seconds=duration,
                        descent_duration=descent_dur,
                        bottom_dwell=bottom_dwell,
                        ascent_duration=ascent_dur,
                        min_knee_angle=self.min_knee_angle_in_rep,
                        mean_symmetry=mean_sym,
                        mean_confidence=mean_conf,
                        is_valid=True,
                        explanation=f"Repetition {self.repetition_count} accepted: full sequence completed in {duration:.2f}s (min knee {self.min_knee_angle_in_rep:.1f}°).",
                        completion_timestamp=float(timestamp),
                    )
                    self.completed_summaries.append(self.latest_rep_summary)
                else:
                    self.latest_rep_summary = RepetitionSummary(
                        rep_number=self.repetition_count + 1,
                        duration_seconds=duration,
                        descent_duration=descent_dur,
                        bottom_dwell=bottom_dwell,
                        ascent_duration=ascent_dur,
                        min_knee_angle=self.min_knee_angle_in_rep,
                        mean_symmetry=mean_sym,
                        mean_confidence=mean_conf,
                        is_valid=False,
                        explanation="Repetition rejected: duration too brief (sensor noise or erratic tempo).",
                        completion_timestamp=float(timestamp),
                    )
                    self.completed_summaries.append(self.latest_rep_summary)
                    self.active_alerts.append(
                        FormAlertData(
                            code="ERRATIC_TEMPO",
                            message="Repetition rejected: duration too brief (sensor noise).",
                            severity=FormAlertSeverity.INFO,
                            timestamp=timestamp,
                            metric_value=duration,
                        )
                    )
                self._rep_symmetries.clear()
                self._rep_confidences.clear()

        elif self.current_phase == MovementPhase.LOCKOUT:
            if knee_angle >= self.config.standing_knee_angle - 5.0:
                self.current_phase = MovementPhase.IDLE
                self.last_phase_change_time = timestamp

        return self.current_phase, self.active_alerts

    def reset(self):
        self.current_phase = MovementPhase.IDLE
        self.repetition_count = 0
        self.valid_reps = 0
        self.rep_start_time = None
        self.bottom_entry_time = None
        self.min_knee_angle_in_rep = 180.0
        self.last_rep_bottom_dwell = 0.0
        self.last_rep_duration = 0.0
        self.latest_rep_summary = None
        self.completed_summaries.clear()
        self.incomplete_attempts_count = 0
        self.aborted_attempts_count = 0
        self._ascent_entry_time = None
        self._rep_symmetries.clear()
        self._rep_confidences.clear()
        self._last_frame_time = None
        self._last_valid_time = None
        self.active_alerts = []
        self.oscillator.reset()
