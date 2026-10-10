"""PERFORMX In-Process Service API & Capability Provider.

Provides a clean typed Python backend interface for sessions, capabilities,
and metrics analysis without HTTP serialization overhead or port exposure.
"""

import time
from typing import Any
import numpy as np

from performx.core import (
    ErrorCode,
    InvalidInputError,
    PerformxError,
    SquatConfig,
)
from performx.contracts import (
    CalibrationResult,
    ErrorResponse,
    MovementResult,
    PoseLandmarksData,
    SessionSummary,
)
from performx.services import (
    MovementAnalysisSession,
    PoseEstimationService,
)


class BackendService:
    """Master in-process backend service managing analysis sessions and engine status."""

    def __init__(self, max_sessions: int = 100, session_idle_timeout: float = 1800.0):
        self._pose_service = PoseEstimationService()
        self._sessions: dict[str, MovementAnalysisSession] = {}
        self._max_sessions = max_sessions
        self._session_idle_timeout = session_idle_timeout

    def _evict_stale_sessions(self):
        """Remove sessions that have been idle past the configured timeout to prevent memory leak."""
        now = time.monotonic()
        stale_ids = [
            sid for sid, sess in self._sessions.items()
            if (now - sess.last_timestamp) > self._session_idle_timeout
        ]
        for sid in stale_ids:
            sess = self._sessions.pop(sid, None)
            if sess:
                sess.is_active = False

    def get_health(self) -> dict[str, Any]:
        """Return engine operational status and backend health metrics."""
        self._evict_stale_sessions()
        return {
            "status": "healthy",
            "pose_engine": "mediapipe_blazepose",
            "active_sessions": len(self._sessions),
            "max_sessions": self._max_sessions,
            "privacy_mode": "local_in_memory",
            "disk_persistence": False,
        }

    def get_capabilities(self) -> dict[str, Any]:
        """Return supported exercises, biomechanical metrics, and default ranges."""
        return {
            "supported_exercises": ["squat"],
            "features": [
                "knee_flexion_extension",
                "hip_flexion_extension",
                "torso_inclination",
                "bilateral_symmetry",
                "cpg_phase_oscillation",
                "bottom_dwell_time",
                "walknet_state_gating",
                "standing_pose_calibration",
            ],
            "default_squat_envelope": {
                "standing_knee_angle_deg": 155.0,
                "target_bottom_depth_deg": 95.0,
                "min_dwell_seconds": 0.20,
                "max_torso_lean_deg": 48.0,
                "min_symmetry_score": 0.78,
            },
        }

    def create_session(
        self, config: SquatConfig | None = None, user_id: str | None = None
    ) -> str:
        """Create a new isolated movement analysis session with capacity enforcement."""
        self._evict_stale_sessions()
        if len(self._sessions) >= self._max_sessions:
            raise PerformxError(
                ErrorCode.SESSION_LIMIT_EXCEEDED,
                f"Maximum active session capacity ({self._max_sessions}) reached. Terminate inactive sessions.",
            )
        session = MovementAnalysisSession(config=config, user_id=user_id)
        self._sessions[session.session_id] = session
        return session.session_id

    def get_session(self, session_id: str) -> MovementAnalysisSession | None:
        """Retrieve an active session by its identifier."""
        return self._sessions.get(session_id)

    def process_frame(self, session_id: str, rgb_frame: np.ndarray, timestamp: float) -> MovementResult:
        """Process a frame within an isolated session."""
        if session_id not in self._sessions:
            raise PerformxError(
                ErrorCode.SESSION_INACTIVE,
                f"Session '{session_id}' not found or inactive",
            )

        session = self._sessions[session_id]
        landmarks_data = self._pose_service.extract_landmarks(rgb_frame, timestamp=timestamp)
        return session.process_landmarks(landmarks_data, timestamp=timestamp)

    def process_landmarks(
        self, session_id: str, landmarks_data: PoseLandmarksData | None, timestamp: float
    ) -> MovementResult:
        """Process pre-extracted pose landmarks directly within an isolated session."""
        if session_id not in self._sessions:
            raise PerformxError(
                ErrorCode.SESSION_INACTIVE,
                f"Session '{session_id}' not found or inactive",
            )
        session = self._sessions[session_id]
        return session.process_landmarks(landmarks_data, timestamp=timestamp)

    def calibrate_frame(self, session_id: str, rgb_frame: np.ndarray, timestamp: float) -> CalibrationResult:
        """Collect a standing pose calibration frame for an isolated session."""
        if session_id not in self._sessions:
            raise PerformxError(
                ErrorCode.SESSION_INACTIVE,
                f"Session '{session_id}' not found or inactive",
            )

        session = self._sessions[session_id]
        landmarks_data = self._pose_service.extract_landmarks(rgb_frame, timestamp=timestamp)
        return session.calibration_service.add_frame_sample(landmarks_data)

    def calibrate_landmarks(
        self, session_id: str, landmarks_data: PoseLandmarksData | None
    ) -> CalibrationResult:
        """Collect a standing pose calibration landmark sample for an isolated session."""
        if session_id not in self._sessions:
            raise PerformxError(
                ErrorCode.SESSION_INACTIVE,
                f"Session '{session_id}' not found or inactive",
            )
        session = self._sessions[session_id]
        return session.calibration_service.add_frame_sample(landmarks_data)

    def reset_calibration(self, session_id: str):
        """Reset calibration for an isolated session."""
        if session_id not in self._sessions:
            raise PerformxError(
                ErrorCode.SESSION_INACTIVE,
                f"Session '{session_id}' not found or inactive",
            )
        self._sessions[session_id].calibration_service.reset()

    def reset_session(self, session_id: str):
        """Reset movement counters and filters for an isolated session."""
        if session_id not in self._sessions:
            raise PerformxError(
                ErrorCode.SESSION_INACTIVE,
                f"Session '{session_id}' not found or inactive",
            )
        self._sessions[session_id].reset()

    def get_session_summary(self, session_id: str) -> SessionSummary:
        """Retrieve the current aggregated summary of an active session without terminating it."""
        if session_id not in self._sessions:
            raise PerformxError(
                ErrorCode.SESSION_INACTIVE,
                f"Session '{session_id}' not found or inactive",
            )
        return self._sessions[session_id].get_summary()

    def end_session(self, session_id: str) -> SessionSummary:
        """Terminate a session and retrieve its final performance summary."""
        if session_id not in self._sessions:
            raise PerformxError(
                ErrorCode.SESSION_INACTIVE,
                f"Session '{session_id}' not found or inactive",
            )

        session = self._sessions.pop(session_id)
        session.is_active = False
        return session.get_summary()

    def delete_session(self, session_id: str) -> bool:
        """Remove and terminate an active session if it exists."""
        if session_id in self._sessions:
            session = self._sessions.pop(session_id)
            session.is_active = False
            return True
        return False

    def close(self):
        """Release underlying vision resources."""
        self._pose_service.close()
        self._sessions.clear()
