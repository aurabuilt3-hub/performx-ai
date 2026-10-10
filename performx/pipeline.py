"""PERFORMX Pipeline: Orchestrates the end-to-end human movement processing lifecycle.

Pipeline stages:
1. Frame validation & ingest (in-memory)
2. Pose landmark estimation (MediaPipe)
3. Landmark sanity & confidence check
4. Session-scoped temporal filtering (One Euro Filter)
5. Kinematic feature extraction (NumPy)
6. Sensorimotor engine evaluation (CPG & Walknet rules)
7. Production of validated MovementResult
8. Zero disk/network persistence
"""

import time
import numpy as np

from performx.core import (
    ErrorCode,
    InvalidInputError,
    PerformxError,
    SquatConfig,
)
from performx.contracts import (
    CalibrationResult,
    MovementFeatures,
    MovementResult,
    PoseLandmarksData,
    SessionSummary,
)
from performx.services import (
    MovementAnalysisSession,
    PoseEstimationService,
)


class MovementPipeline:
    """Master pipeline orchestrator connecting pose estimation with movement analysis."""

    def __init__(self, config: SquatConfig | None = None, pose_service: PoseEstimationService | None = None):
        self.config = config or SquatConfig()
        self.pose_service = pose_service or PoseEstimationService()
        self.session = MovementAnalysisSession(config=self.config)

    def process_frame(self, rgb_frame: np.ndarray, timestamp: float | None = None) -> MovementResult:
        """Process an RGB frame through the end-to-end pipeline.
        
        Guarantees zero persistence: frame is processed strictly from RAM.
        """
        curr_time = time.monotonic() if timestamp is None else float(timestamp)

        if rgb_frame is None or not isinstance(rgb_frame, np.ndarray) or rgb_frame.size == 0:
            self.session.error_count += 1
            return self._build_undetected_result(curr_time)

        try:
            landmarks_data = self.pose_service.extract_landmarks(rgb_frame, timestamp=curr_time)
            result = self.session.process_landmarks(landmarks_data, timestamp=curr_time)
            return result
        except PerformxError:
            self.session.error_count += 1
            return self._build_undetected_result(curr_time)
        except Exception:
            self.session.error_count += 1
            return self._build_undetected_result(curr_time)

    def _build_undetected_result(self, timestamp: float) -> MovementResult:
        return self.session.process_landmarks(None, timestamp=timestamp)

    def calibrate_frame(self, rgb_frame: np.ndarray, timestamp: float | None = None) -> CalibrationResult:
        """Process an RGB frame for standing-pose calibration without persisting the image."""
        curr_time = time.monotonic() if timestamp is None else float(timestamp)
        if rgb_frame is None or not isinstance(rgb_frame, np.ndarray) or rgb_frame.size == 0:
            return self.session.calibration_service.add_frame_sample(None)

        landmarks_data = self.pose_service.extract_landmarks(rgb_frame, timestamp=curr_time)
        return self.session.calibration_service.add_frame_sample(landmarks_data)

    def reset_calibration(self):
        """Reset standing-pose calibration state."""
        self.session.calibration_service.reset()

    def update_config(self, config: SquatConfig):
        """Update biomechanical configuration cleanly across pipeline and session."""
        self.config = config
        self.session.update_config(config)

    def get_session_summary(self) -> SessionSummary:
        return self.session.get_summary()

    def reset_session(self):
        self.session.reset()

    def close(self):
        self.pose_service.close()
