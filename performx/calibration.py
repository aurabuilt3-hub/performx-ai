"""PERFORMX Calibration Service: Robust standing-pose calibration and body-scale estimation.

Collects a temporal window of valid standing-pose landmarks:
- Enforces strict visibility, upright posture, and anatomical plausibility.
- Uses robust statistics (median and interquartile range / std) across multiple frames.
- Stores derived scale measurements (femur, tibia, torso, body-height proxy) only.
- Never persists video frames or image data to disk or network.
"""

from collections import deque
import numpy as np

from performx.core import (
    CalibrationError,
    CalibrationStatus,
    LandmarkIndex,
    SquatConfig,
)
from performx.contracts import (
    CalibrationResult,
    PoseLandmarksData,
)
from performx.engine import (
    compute_angle_2d,
    compute_segment_length_2d,
    compute_torso_inclination,
)


class StandingCalibrationService:
    """Manages windowed standing-pose calibration without frame retention."""

    def __init__(
        self,
        min_samples: int = 15,
        max_samples: int = 45,
        min_confidence: float = 0.65,
        max_knee_flexion_deg: float = 16.0,  # Knee must be >= (180 - 16) = 164 deg
        max_standing_lean_deg: float = 18.0, # Must be reasonably upright
        max_jitter_std: float = 0.04,        # Max normalized coordinate std dev
    ):
        self.min_samples = min_samples
        self.max_samples = max_samples
        self.min_confidence = min_confidence
        self.max_knee_flexion_deg = max_knee_flexion_deg
        self.max_standing_lean_deg = max_standing_lean_deg
        self.max_jitter_std = max_jitter_std

        self._samples: deque[dict] = deque(maxlen=max_samples)
        self._current_result: CalibrationResult | None = None
        self._status = CalibrationStatus.NOT_CALIBRATED

    @property
    def status(self) -> CalibrationStatus:
        return self._status

    @property
    def current_result(self) -> CalibrationResult | None:
        return self._current_result

    def reset(self):
        """Reset calibration samples and result."""
        self._samples.clear()
        self._current_result = None
        self._status = CalibrationStatus.NOT_CALIBRATED

    def add_frame_sample(self, landmarks_data: PoseLandmarksData | None) -> CalibrationResult:
        """Evaluate a frame for standing-pose calibration."""
        if landmarks_data is None:
            return self._record_failure("Landmarks not detected in frame.")

        if landmarks_data.mean_confidence < self.min_confidence:
            return self._record_failure(
                f"Landmark confidence ({landmarks_data.mean_confidence:.2f}) below threshold ({self.min_confidence:.2f})."
            )

        lm = landmarks_data.coords

        # Extract joints
        l_shoulder = lm[LandmarkIndex.LEFT_SHOULDER][:2]
        r_shoulder = lm[LandmarkIndex.RIGHT_SHOULDER][:2]
        l_hip = lm[LandmarkIndex.LEFT_HIP][:2]
        r_hip = lm[LandmarkIndex.RIGHT_HIP][:2]
        l_knee = lm[LandmarkIndex.LEFT_KNEE][:2]
        r_knee = lm[LandmarkIndex.RIGHT_KNEE][:2]
        l_ankle = lm[LandmarkIndex.LEFT_ANKLE][:2]
        r_ankle = lm[LandmarkIndex.RIGHT_ANKLE][:2]

        # 1. Geometric posture validity
        l_knee_angle = compute_angle_2d(l_hip, l_knee, l_ankle)
        r_knee_angle = compute_angle_2d(r_hip, r_knee, r_ankle)
        avg_knee = (l_knee_angle + r_knee_angle) / 2.0

        if avg_knee < (180.0 - self.max_knee_flexion_deg):
            return self._record_failure(
                f"Subject not fully standing upright (knee angle {avg_knee:.1f}° < {180.0 - self.max_knee_flexion_deg:.1f}°)."
            )

        mid_shoulder = (l_shoulder + r_shoulder) / 2.0
        mid_hip = (l_hip + r_hip) / 2.0
        torso_lean = compute_torso_inclination(mid_shoulder, mid_hip)

        if torso_lean > self.max_standing_lean_deg:
            return self._record_failure(
                f"Torso lean ({torso_lean:.1f}°) exceeds standing limit ({self.max_standing_lean_deg:.1f}°)."
            )

        # 2. Segment length measurements (2D image space)
        femur_l = compute_segment_length_2d(l_hip, l_knee)
        femur_r = compute_segment_length_2d(r_hip, r_knee)
        tibia_l = compute_segment_length_2d(l_knee, l_ankle)
        tibia_r = compute_segment_length_2d(r_knee, r_ankle)
        torso = compute_segment_length_2d(mid_shoulder, mid_hip)
        femur = (femur_l + femur_r) / 2.0
        tibia = (tibia_l + tibia_r) / 2.0

        # Body height proxy: vertical distance from shoulder to ankle
        mid_ankle = (l_ankle + r_ankle) / 2.0
        body_height_proxy = float(abs(mid_ankle[1] - mid_shoulder[1]))

        if body_height_proxy < 0.15 or femur < 0.05 or tibia < 0.05:
            return self._record_failure("Estimated limb segments are too small; step closer or align camera.")

        # Record valid sample in rolling window
        self._samples.append({
            "avg_knee": avg_knee,
            "torso_lean": torso_lean,
            "femur": femur,
            "tibia": tibia,
            "torso": torso,
            "body_height_proxy": body_height_proxy,
            "mid_hip_y": float(mid_hip[1]),
            "confidence": landmarks_data.mean_confidence,
        })

        if len(self._samples) < self.min_samples:
            self._status = CalibrationStatus.COLLECTING
            self._current_result = CalibrationResult(
                status=self._status,
                confidence=landmarks_data.mean_confidence,
                standing_knee_angle=avg_knee,
                standing_torso_lean=torso_lean,
                femur_length_2d=femur,
                tibia_length_2d=tibia,
                torso_length_2d=torso,
                body_height_proxy_2d=body_height_proxy,
                sample_count=len(self._samples),
                failure_reason=None,
            )
            return self._current_result

        # 3. Check stability across window (std dev check)
        hip_y_vals = [s["mid_hip_y"] for s in self._samples]
        std_hip_y = float(np.std(hip_y_vals))
        if std_hip_y > self.max_jitter_std:
            self._samples.popleft()  # Discard oldest sample if unstable
            return self._record_failure("Movement instability detected during standing window. Stand still.")

        # 4. Compute robust median estimates
        med_knee = float(np.median([s["avg_knee"] for s in self._samples]))
        med_lean = float(np.median([s["torso_lean"] for s in self._samples]))
        med_femur = float(np.median([s["femur"] for s in self._samples]))
        med_tibia = float(np.median([s["tibia"] for s in self._samples]))
        med_torso = float(np.median([s["torso"] for s in self._samples]))
        med_height = float(np.median([s["body_height_proxy"] for s in self._samples]))
        med_conf = float(np.median([s["confidence"] for s in self._samples]))

        self._status = CalibrationStatus.CALIBRATED
        self._current_result = CalibrationResult(
            status=self._status,
            confidence=med_conf,
            standing_knee_angle=med_knee,
            standing_torso_lean=med_lean,
            femur_length_2d=med_femur,
            tibia_length_2d=med_tibia,
            torso_length_2d=med_torso,
            body_height_proxy_2d=med_height,
            sample_count=len(self._samples),
            failure_reason=None,
        )
        return self._current_result

    def _record_failure(self, reason: str) -> CalibrationResult:
        # Invalidate status
        self._status = CalibrationStatus.FAILED

        self._current_result = CalibrationResult(
            status=self._status,
            confidence=0.0,
            standing_knee_angle=180.0,
            standing_torso_lean=0.0,
            femur_length_2d=0.0,
            tibia_length_2d=0.0,
            torso_length_2d=0.0,
            body_height_proxy_2d=0.0,
            sample_count=len(self._samples),
            failure_reason=reason,
        )
        return self._current_result
