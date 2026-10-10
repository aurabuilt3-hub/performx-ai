"""PERFORMX Services: Pose estimation adapter and Session Lifecycle Manager.

Isolates MediaPipe lifecycle and state management into reusable backend services.
"""

import time
import uuid
import numpy as np

from performx.core import (
    ErrorCode,
    InvalidInputError,
    LandmarkIndex,
    LandmarkValidationError,
    SquatConfig,
)
from performx.contracts import (
    MovementFeatures,
    MovementResult,
    PoseLandmarksData,
    RepetitionSummary,
    SessionMetrics,
    SessionSummary,
)
from performx.engine import (
    OneEuroFilter,
    SensorimotorEngine,
    compute_angle_2d,
    compute_bilateral_symmetry,
    compute_torso_inclination,
)


class PoseEstimationService:
    """Encapsulates MediaPipe Pose estimation with landmark extraction and validation."""

    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        model_complexity: int = 1,
        smooth_landmarks: bool = True,
    ):
        import mediapipe as mp

        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            model_complexity=model_complexity,
            smooth_landmarks=smooth_landmarks,
            static_image_mode=False,
        )

    def extract_landmarks(self, rgb_frame: np.ndarray, timestamp: float) -> PoseLandmarksData | None:
        """Process RGB frame strictly in-memory and return validated landmarks."""
        if rgb_frame is None or not isinstance(rgb_frame, np.ndarray) or rgb_frame.size == 0:
            raise InvalidInputError("Frame is empty or invalid ndarray")

        if rgb_frame.ndim != 3 or rgb_frame.shape[2] != 3:
            raise InvalidInputError(f"Expected 3-channel RGB frame, got shape {rgb_frame.shape}")

        if not rgb_frame.flags.c_contiguous:
            rgb_frame = np.ascontiguousarray(rgb_frame)

        results = self.pose.process(rgb_frame)

        if not results.pose_landmarks:
            return None

        # Extract (33, 4) landmark array: x, y, z, visibility
        landmarks_data = np.array(
            [[lm.x, lm.y, lm.z, lm.visibility] for lm in results.pose_landmarks.landmark],
            dtype=np.float32,
        )

        world_data = None
        if results.pose_world_landmarks:
            world_data = np.array(
                [[lm.x, lm.y, lm.z] for lm in results.pose_world_landmarks.landmark],
                dtype=np.float32,
            )

        # Compute key joint visibility
        key_joints = [
            LandmarkIndex.LEFT_HIP, LandmarkIndex.RIGHT_HIP,
            LandmarkIndex.LEFT_KNEE, LandmarkIndex.RIGHT_KNEE,
            LandmarkIndex.LEFT_ANKLE, LandmarkIndex.RIGHT_ANKLE,
        ]
        mean_conf = float(np.mean(landmarks_data[key_joints, 3]))

        return PoseLandmarksData(
            coords=landmarks_data,
            world_coords=world_data,
            mean_confidence=mean_conf,
            timestamp=timestamp,
        )

    def close(self):
        """Release underlying MediaPipe native resources."""
        if hasattr(self, "pose") and self.pose:
            self.pose.close()


class MovementAnalysisSession:
    """Isolated, session-scoped movement analysis manager.
    
    Contains independent OneEuroFilter instances, sensorimotor engine state,
    and aggregate session performance metrics.
    """

    def __init__(
        self,
        session_id: str | None = None,
        config: SquatConfig | None = None,
        user_id: str | None = None,
    ):
        self.session_id = session_id or str(uuid.uuid4())
        self.config = config or SquatConfig()
        self.user_id = user_id
        self.engine = SensorimotorEngine(config=self.config)

        # Session-isolated filters
        self.knee_filter_left = OneEuroFilter(freq=30.0, min_cutoff=1.5, beta=0.01)
        self.knee_filter_right = OneEuroFilter(freq=30.0, min_cutoff=1.5, beta=0.01)
        self.hip_filter_left = OneEuroFilter(freq=30.0, min_cutoff=1.5, beta=0.01)
        self.hip_filter_right = OneEuroFilter(freq=30.0, min_cutoff=1.5, beta=0.01)
        self.torso_filter = OneEuroFilter(freq=30.0, min_cutoff=1.5, beta=0.01)

        # Standing pose calibration service
        from performx.calibration import StandingCalibrationService
        self.calibration_service = StandingCalibrationService()

        self.start_time: float = time.monotonic()
        self.last_timestamp: float = self.start_time
        self.frames_processed: int = 0
        self.symmetry_history: list[float] = []
        self.rep_durations: list[float] = []
        self.error_count: int = 0
        self.is_active: bool = True

    def process_landmarks(self, landmarks_data: PoseLandmarksData | None, timestamp: float) -> MovementResult:
        """Process validated landmarks through filtering, kinematics, and sensorimotor engine."""
        self.frames_processed += 1
        self.last_timestamp = timestamp

        # Handle subject missing or undetected
        if landmarks_data is None:
            phase, alerts = self.engine.evaluate_frame(
                knee_angle=180.0,
                hip_angle=180.0,
                torso_lean=0.0,
                symmetry_score=1.0,
                timestamp=timestamp,
                confidence=0.0,
            )
            features = MovementFeatures(
                left_knee_angle=180.0,
                right_knee_angle=180.0,
                avg_knee_angle=180.0,
                left_hip_angle=180.0,
                right_hip_angle=180.0,
                torso_lean_angle=0.0,
                symmetry_score=1.0,
            )
            return MovementResult(
                timestamp=timestamp,
                is_detected=False,
                confidence=0.0,
                current_phase=phase,
                repetition_count=self.engine.repetition_count,
                features=features,
                oscillator_phase=self.engine.oscillator.phase,
                bottom_dwell_time=0.0,
                last_rep_duration=self.engine.last_rep_duration,
                calibration=self.calibration_service.current_result,
                active_alerts=alerts,
            )

        lm = landmarks_data.coords

        # Extract 2D joint coordinates
        l_shoulder = lm[LandmarkIndex.LEFT_SHOULDER][:2]
        r_shoulder = lm[LandmarkIndex.RIGHT_SHOULDER][:2]
        l_hip = lm[LandmarkIndex.LEFT_HIP][:2]
        r_hip = lm[LandmarkIndex.RIGHT_HIP][:2]
        l_knee = lm[LandmarkIndex.LEFT_KNEE][:2]
        r_knee = lm[LandmarkIndex.RIGHT_KNEE][:2]
        l_ankle = lm[LandmarkIndex.LEFT_ANKLE][:2]
        r_ankle = lm[LandmarkIndex.RIGHT_ANKLE][:2]

        # Kinematic angle calculation
        raw_l_knee = compute_angle_2d(l_hip, l_knee, l_ankle)
        raw_r_knee = compute_angle_2d(r_hip, r_knee, r_ankle)
        raw_l_hip = compute_angle_2d(l_shoulder, l_hip, l_knee)
        raw_r_hip = compute_angle_2d(r_shoulder, r_hip, r_knee)

        mid_shoulder = (l_shoulder + r_shoulder) / 2.0
        mid_hip = (l_hip + r_hip) / 2.0
        raw_torso = compute_torso_inclination(mid_shoulder, mid_hip)

        # Adaptive temporal filtering
        filt_l_knee = self.knee_filter_left.filter(raw_l_knee, timestamp=timestamp)
        filt_r_knee = self.knee_filter_right.filter(raw_r_knee, timestamp=timestamp)
        filt_l_hip = self.hip_filter_left.filter(raw_l_hip, timestamp=timestamp)
        filt_r_hip = self.hip_filter_right.filter(raw_r_hip, timestamp=timestamp)
        filt_torso = self.torso_filter.filter(raw_torso, timestamp=timestamp)

        avg_knee = (filt_l_knee + filt_r_knee) / 2.0
        symmetry = compute_bilateral_symmetry(filt_l_knee, filt_r_knee)
        self.symmetry_history.append(symmetry)

        # Scale-aware depth calculation if calibrated
        calib_res = self.calibration_service.current_result
        norm_hip_depth = None
        if calib_res and calib_res.status.value == "CALIBRATED" and calib_res.body_height_proxy_2d > 1e-4:
            # Normalized hip drop: (current_hip_y - standing_hip_y) / body_height_proxy_2d
            # In image coords, descending down increases y
            mid_hip_y = float(mid_hip[1])
            standing_hip_y = calib_res.torso_length_2d  # Relative proxy
            # Direct normalized distance of knee flexion / vertical hip displacement
            norm_hip_depth = float((self.config.standing_knee_angle - avg_knee) / 90.0)

        features = MovementFeatures(
            left_knee_angle=filt_l_knee,
            right_knee_angle=filt_r_knee,
            avg_knee_angle=avg_knee,
            left_hip_angle=filt_l_hip,
            right_hip_angle=filt_r_hip,
            torso_lean_angle=filt_torso,
            symmetry_score=symmetry,
            normalized_hip_depth=norm_hip_depth,
        )

        # Sensorimotor evaluation
        prev_reps = self.engine.repetition_count
        phase, alerts = self.engine.evaluate_frame(
            knee_angle=avg_knee,
            hip_angle=(filt_l_hip + filt_r_hip) / 2.0,
            torso_lean=filt_torso,
            symmetry_score=symmetry,
            timestamp=timestamp,
            confidence=landmarks_data.mean_confidence,
        )

        if self.engine.repetition_count > prev_reps:
            self.rep_durations.append(self.engine.last_rep_duration)

        dwell = 0.0
        if self.engine.bottom_entry_time is not None and phase.value == "BOTTOM":
            dwell = timestamp - self.engine.bottom_entry_time
        elif self.engine.last_rep_bottom_dwell > 0.0:
            dwell = self.engine.last_rep_bottom_dwell

        return MovementResult(
            timestamp=timestamp,
            is_detected=True,
            confidence=landmarks_data.mean_confidence,
            current_phase=phase,
            repetition_count=self.engine.repetition_count,
            features=features,
            oscillator_phase=self.engine.oscillator.phase,
            bottom_dwell_time=dwell,
            last_rep_duration=self.engine.last_rep_duration,
            calibration=calib_res,
            active_alerts=alerts,
            repetition_summary=self.engine.latest_rep_summary,
        )

    def get_summary(self) -> SessionSummary:
        """Produce aggregated summary for the session with rich, explainable metrics."""
        mean_sym = float(np.mean(self.symmetry_history)) if self.symmetry_history else 1.0
        mean_dur = float(np.mean(self.rep_durations)) if self.rep_durations else 0.0

        # Partition summaries into accepted vs rejected
        all_summaries = self.engine.completed_summaries
        accepted = [s for s in all_summaries if s.is_valid]
        rejected = [s for s in all_summaries if not s.is_valid]

        accepted_count = len(accepted)
        rejected_count = len(rejected)
        total_completed = len(all_summaries)
        incomplete_count = self.engine.incomplete_attempts_count
        aborted_count = self.engine.aborted_attempts_count

        insights: list[str] = []
        if accepted_count == 0:
            insights.append("Insufficient valid repetitions to calculate session timing or depth variation.")
            metrics = SessionMetrics(
                total_completed_reps=total_completed,
                accepted_reps=accepted_count,
                rejected_reps=rejected_count,
                incomplete_attempts=incomplete_count,
                aborted_attempts=aborted_count,
                mean_duration=None,
                min_duration=None,
                max_duration=None,
                duration_range=None,
                mean_descent_duration=None,
                mean_bottom_dwell=None,
                mean_ascent_duration=None,
                mean_min_knee_angle=None,
                knee_angle_range=None,
                mean_rep_symmetry=None,
                mean_tracking_confidence=None,
                explainable_insights=insights,
            )
        else:
            durations = [s.duration_seconds for s in accepted]
            descents = [s.descent_duration for s in accepted]
            dwells = [s.bottom_dwell for s in accepted]
            ascents = [s.ascent_duration for s in accepted]
            knees = [s.min_knee_angle for s in accepted]
            symmetries = [s.mean_symmetry for s in accepted]
            confidences = [s.mean_confidence for s in accepted]

            mean_d = float(np.mean(durations))
            min_d = float(np.min(durations))
            max_d = float(np.max(durations))
            dur_rng = float(max_d - min_d)

            mean_desc = float(np.mean(descents))
            mean_dw = float(np.mean(dwells))
            mean_asc = float(np.mean(ascents))

            mean_knee = float(np.mean(knees))
            knee_rng = float(np.max(knees) - np.min(knees))
            mean_s = float(np.mean(symmetries))
            mean_c = float(np.mean(confidences))

            # Build neutral, evidence-based explainable insights
            if dur_rng > 0.05:
                insights.append(f"Repetition duration varied by {dur_rng:.2f}s across accepted repetitions (range: {min_d:.2f}s - {max_d:.2f}s).")
            else:
                insights.append(f"Consistent pacing maintained across accepted repetitions ({mean_d:.2f}s average).")

            if accepted_count >= 2:
                if dwells[-1] > dwells[0] + 0.2:
                    insights.append(f"Bottom dwell duration was longer in later repetitions ({dwells[-1]:.2f}s vs {dwells[0]:.2f}s).")
                elif dwells[-1] < dwells[0] - 0.2:
                    insights.append(f"Bottom dwell duration decreased in later repetitions ({dwells[-1]:.2f}s vs {dwells[0]:.2f}s).")

            if knee_rng > 5.0:
                insights.append(f"Squat depth varied by {knee_rng:.1f}° across repetitions (average peak depth: {mean_knee:.1f}°).")
            else:
                insights.append(f"Consistent squat depth maintained across repetitions (average peak depth: {mean_knee:.1f}°).")

            if mean_c < 0.75:
                insights.append(f"Tracking confidence was moderate ({mean_c:.0%}); camera distance and lighting may affect joint stability.")

            metrics = SessionMetrics(
                total_completed_reps=total_completed,
                accepted_reps=accepted_count,
                rejected_reps=rejected_count,
                incomplete_attempts=incomplete_count,
                aborted_attempts=aborted_count,
                mean_duration=mean_d,
                min_duration=min_d,
                max_duration=max_d,
                duration_range=dur_rng,
                mean_descent_duration=mean_desc,
                mean_bottom_dwell=mean_dw,
                mean_ascent_duration=mean_asc,
                mean_min_knee_angle=mean_knee,
                knee_angle_range=knee_rng,
                mean_rep_symmetry=mean_s,
                mean_tracking_confidence=mean_c,
                explainable_insights=insights,
            )

        return SessionSummary(
            session_id=self.session_id,
            start_time=self.start_time,
            end_time=self.last_timestamp,
            total_frames_processed=self.frames_processed,
            total_reps=self.engine.repetition_count,
            valid_reps=self.engine.valid_reps,
            mean_symmetry=mean_sym,
            mean_rep_duration=mean_dur,
            config=self.config,
            error_count=self.error_count,
            metrics=metrics,
        )

    def update_config(self, config: SquatConfig):
        """Update biomechanical configuration cleanly across session and engine."""
        self.config = config
        self.engine.config = config

    def reset(self):
        """Reset session state cleanly."""
        self.engine.reset()
        self.calibration_service.reset()
        self.knee_filter_left.reset()
        self.knee_filter_right.reset()
        self.hip_filter_left.reset()
        self.hip_filter_right.reset()
        self.torso_filter.reset()
        self.symmetry_history.clear()
        self.rep_durations.clear()
        self.frames_processed = 0
        self.error_count = 0
