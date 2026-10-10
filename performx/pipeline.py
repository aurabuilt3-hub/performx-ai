from dataclasses import dataclass
import time
import numpy as np

from performx.filtering import OneEuroFilter
from performx.kinematics import (
    compute_angle_2d,
    compute_torso_inclination,
    compute_bilateral_symmetry,
)
from performx.pose_tracker import PoseLandmark, PoseResult, PoseTracker
from performx.sensorimotor import FormAlert, MovementPhase, SensorimotorEngine, SquatConfig


@dataclass
class MovementMetrics:
    """Consolidated instantaneous biomechanical movement metrics."""
    timestamp: float
    is_detected: bool
    confidence: float
    current_phase: MovementPhase
    repetition_count: int
    left_knee_angle: float
    right_knee_angle: float
    avg_knee_angle: float
    left_hip_angle: float
    right_hip_angle: float
    torso_lean: float
    symmetry_score: float
    oscillator_phase: float
    bottom_dwell_time: float
    rep_duration: float
    active_alerts: list[FormAlert]


class MovementPipeline:
    """Master Human Movement Analysis Pipeline.
    
    Coordinates:
    1. In-memory Pose Landmark Detection (MediaPipe)
    2. Adaptive Jitter Reduction (OneEuroFilter)
    3. Kinematic Feature Calculations (NumPy)
    4. Fruit-fly Sensorimotor Decision Engine (Walknet gating & CPG)
    5. Ephemeral In-Memory processing (Privacy by design)
    """

    def __init__(self, config: SquatConfig | None = None):
        self.config = config or SquatConfig()
        self.tracker = PoseTracker()
        self.engine = SensorimotorEngine(config=self.config)

        # Filters for key biometric angles to avoid high-frequency jitter
        self.knee_filter_left = OneEuroFilter(freq=30.0, min_cutoff=1.5, beta=0.01)
        self.knee_filter_right = OneEuroFilter(freq=30.0, min_cutoff=1.5, beta=0.01)
        self.hip_filter_left = OneEuroFilter(freq=30.0, min_cutoff=1.5, beta=0.01)
        self.hip_filter_right = OneEuroFilter(freq=30.0, min_cutoff=1.5, beta=0.01)
        self.torso_filter = OneEuroFilter(freq=30.0, min_cutoff=1.5, beta=0.01)

        self.last_timestamp = 0.0

    def process_frame(self, rgb_frame: np.ndarray, timestamp: float | None = None) -> MovementMetrics:
        """Process a single video frame in memory and compute movement metrics.
        
        Guaranteed zero persistence: caller retains ownership, no disk I/O.
        """
        curr_time = time.time() if timestamp is None else timestamp
        self.last_timestamp = curr_time

        # 1. Pose Landmark Extraction
        pose_result: PoseResult = self.tracker.process_frame(rgb_frame, timestamp=curr_time)

        if not pose_result.is_detected or pose_result.landmarks is None:
            # Propagate fallback metrics when subject is not in frame
            return MovementMetrics(
                timestamp=curr_time,
                is_detected=False,
                confidence=0.0,
                current_phase=self.engine.current_phase,
                repetition_count=self.engine.repetition_count,
                left_knee_angle=180.0,
                right_knee_angle=180.0,
                avg_knee_angle=180.0,
                left_hip_angle=180.0,
                right_hip_angle=180.0,
                torso_lean=0.0,
                symmetry_score=1.0,
                oscillator_phase=self.engine.oscillator.phase,
                bottom_dwell_time=0.0,
                rep_duration=self.engine.last_rep_duration,
                active_alerts=[
                    FormAlert(
                        code="NO_PERSON_DETECTED",
                        message="Position yourself fully inside the camera frame.",
                        severity=FormAlert.severity if hasattr(FormAlert, "severity") else "INFO",
                        timestamp=curr_time,
                    )
                ],
            )

        lm = pose_result.landmarks

        # 2. Extract Key Joints (Normalized 2D coordinates)
        l_shoulder = lm[PoseLandmark.LEFT_SHOULDER][:2]
        r_shoulder = lm[PoseLandmark.RIGHT_SHOULDER][:2]
        l_hip = lm[PoseLandmark.LEFT_HIP][:2]
        r_hip = lm[PoseLandmark.RIGHT_HIP][:2]
        l_knee = lm[PoseLandmark.LEFT_KNEE][:2]
        r_knee = lm[PoseLandmark.RIGHT_KNEE][:2]
        l_ankle = lm[PoseLandmark.LEFT_ANKLE][:2]
        r_ankle = lm[PoseLandmark.RIGHT_ANKLE][:2]

        # 3. Kinematic Angle Computations
        raw_l_knee_angle = compute_angle_2d(l_hip, l_knee, l_ankle)
        raw_r_knee_angle = compute_angle_2d(r_hip, r_knee, r_ankle)
        raw_l_hip_angle = compute_angle_2d(l_shoulder, l_hip, l_knee)
        raw_r_hip_angle = compute_angle_2d(r_shoulder, r_hip, r_knee)

        # Midpoint torso inclination
        mid_shoulder = (l_shoulder + r_shoulder) / 2.0
        mid_hip = (l_hip + r_hip) / 2.0
        raw_torso_lean = compute_torso_inclination(mid_shoulder, mid_hip)

        # 4. Adaptive Filtering (1€ Filter)
        filt_l_knee = self.knee_filter_left.filter(raw_l_knee_angle, timestamp=curr_time)
        filt_r_knee = self.knee_filter_right.filter(raw_r_knee_angle, timestamp=curr_time)
        filt_l_hip = self.hip_filter_left.filter(raw_l_hip_angle, timestamp=curr_time)
        filt_r_hip = self.hip_filter_right.filter(raw_r_hip_angle, timestamp=curr_time)
        filt_torso = self.torso_filter.filter(raw_torso_lean, timestamp=curr_time)

        avg_knee = (filt_l_knee + filt_r_knee) / 2.0
        symmetry = compute_bilateral_symmetry(filt_l_knee, filt_r_knee)

        # 5. Fly-Inspired Sensorimotor Evaluation
        phase, alerts = self.engine.evaluate_frame(
            knee_angle=avg_knee,
            hip_angle=(filt_l_hip + filt_r_hip) / 2.0,
            torso_lean=filt_torso,
            symmetry_score=symmetry,
            timestamp=curr_time,
            confidence=pose_result.confidence,
        )

        dwell = 0.0
        if self.engine.bottom_entry_time is not None and phase == MovementPhase.BOTTOM:
            dwell = curr_time - self.engine.bottom_entry_time
        elif self.engine.last_rep_bottom_dwell > 0.0:
            dwell = self.engine.last_rep_bottom_dwell

        return MovementMetrics(
            timestamp=curr_time,
            is_detected=True,
            confidence=pose_result.confidence,
            current_phase=phase,
            repetition_count=self.engine.repetition_count,
            left_knee_angle=filt_l_knee,
            right_knee_angle=filt_r_knee,
            avg_knee_angle=avg_knee,
            left_hip_angle=filt_l_hip,
            right_hip_angle=filt_r_hip,
            torso_lean=filt_torso,
            symmetry_score=symmetry,
            oscillator_phase=self.engine.oscillator.phase,
            bottom_dwell_time=dwell,
            rep_duration=self.engine.last_rep_duration,
            active_alerts=alerts,
        )

    def reset(self):
        """Reset internal filters and state engine."""
        self.engine.reset()
        self.knee_filter_left.reset()
        self.knee_filter_right.reset()
        self.hip_filter_left.reset()
        self.hip_filter_right.reset()
        self.torso_filter.reset()

    def close(self):
        """Release underlying vision resources."""
        self.tracker.close()
