from dataclasses import dataclass
import numpy as np


# MediaPipe Pose Landmark Indices (BlazePose 33-keypoint topology)
class PoseLandmark:
    NOSE = 0
    LEFT_EYE_INNER = 1
    LEFT_EYE = 2
    LEFT_EYE_OUTER = 3
    RIGHT_EYE_INNER = 4
    RIGHT_EYE = 5
    RIGHT_EYE_OUTER = 6
    LEFT_EAR = 7
    RIGHT_EAR = 8
    MOUTH_LEFT = 9
    MOUTH_RIGHT = 10
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_PINKY = 17
    RIGHT_PINKY = 18
    LEFT_INDEX = 19
    RIGHT_INDEX = 20
    LEFT_THUMB = 21
    RIGHT_THUMB = 22
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    LEFT_HEEL = 29
    RIGHT_HEEL = 30
    LEFT_FOOT_INDEX = 31
    RIGHT_FOOT_INDEX = 32


@dataclass
class PoseResult:
    """Encapsulates extracted pose landmarks for a single frame."""
    landmarks: np.ndarray | None  # Shape (33, 4): x, y, z, visibility
    world_landmarks: np.ndarray | None  # Shape (33, 3): metric world coordinates in meters
    is_detected: bool
    confidence: float
    timestamp: float


class PoseTracker:
    """MediaPipe Pose Tracker with privacy-first in-memory processing.
    
    Frames are processed ephemerally in RAM and never stored to disk or network.
    """

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

    def process_frame(self, rgb_frame: np.ndarray, timestamp: float = 0.0) -> PoseResult:
        """Process an RGB frame and return extracted landmarks.
        
        Zero disk writes: the frame is processed directly from memory.
        """
        if rgb_frame is None or rgb_frame.size == 0:
            return PoseResult(
                landmarks=None,
                world_landmarks=None,
                is_detected=False,
                confidence=0.0,
                timestamp=timestamp,
            )

        # Ensure array is contiguous for MediaPipe C++ kernel
        if not rgb_frame.flags.c_contiguous:
            rgb_frame = np.ascontiguousarray(rgb_frame)

        results = self.pose.process(rgb_frame)

        if not results.pose_landmarks:
            return PoseResult(
                landmarks=None,
                world_landmarks=None,
                is_detected=False,
                confidence=0.0,
                timestamp=timestamp,
            )

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

        # Mean visibility of key body joints
        key_joints = [
            PoseLandmark.LEFT_HIP, PoseLandmark.RIGHT_HIP,
            PoseLandmark.LEFT_KNEE, PoseLandmark.RIGHT_KNEE,
            PoseLandmark.LEFT_ANKLE, PoseLandmark.RIGHT_ANKLE,
        ]
        mean_conf = float(np.mean(landmarks_data[key_joints, 3]))

        return PoseResult(
            landmarks=landmarks_data,
            world_landmarks=world_data,
            is_detected=True,
            confidence=mean_conf,
            timestamp=timestamp,
        )

    def close(self):
        """Release underlying MediaPipe graph resources."""
        if hasattr(self, "pose") and self.pose:
            self.pose.close()
