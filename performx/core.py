"""PERFORMX Core: Shared constants, configuration schemas, and domain exceptions."""

from dataclasses import dataclass, field
from enum import Enum
import math


class MovementPhase(str, Enum):
    """Behavioral movement states representing exercise progression."""
    IDLE = "IDLE"              # Standing still, preparing
    SETUP = "SETUP"            # Subject aligned, descent initiating
    DESCENT = "DESCENT"        # Eccentric lowering phase
    BOTTOM = "BOTTOM"          # Inflection zone / deepest dwell / hole
    ASCENT = "ASCENT"          # Concentric rising phase
    LOCKOUT = "LOCKOUT"        # Returned to top, rep completed


class FormAlertSeverity(str, Enum):
    """Severity tier for biomechanical form feedback."""
    INFO = "INFO"
    WARNING = "WARNING"
    ALERT = "ALERT"


class CalibrationStatus(str, Enum):
    """Standing-pose calibration state machine."""
    NOT_CALIBRATED = "NOT_CALIBRATED"
    COLLECTING = "COLLECTING"
    CALIBRATED = "CALIBRATED"
    FAILED = "FAILED"


class ErrorCode(str, Enum):
    """Structured error codes for backend and pipeline operations."""
    INVALID_FRAME = "INVALID_FRAME"
    NON_FINITE_INPUT = "NON_FINITE_INPUT"
    MALFORMED_LANDMARKS = "MALFORMED_LANDMARKS"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    CAMERA_FAILURE = "CAMERA_FAILURE"
    SESSION_INACTIVE = "SESSION_INACTIVE"
    PROCESSING_FAILURE = "PROCESSING_FAILURE"
    CALIBRATION_FAILED = "CALIBRATION_FAILED"
    SESSION_LIMIT_EXCEEDED = "SESSION_LIMIT_EXCEEDED"


class PerformxError(Exception):
    """Base exception for all PERFORMX domain errors."""
    def __init__(self, code: ErrorCode, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class InvalidInputError(PerformxError):
    """Raised when input frame, coordinates, or timestamps are invalid."""
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(ErrorCode.INVALID_FRAME, message, details)


class LandmarkValidationError(PerformxError):
    """Raised when pose landmarks contain non-finite numbers or invalid dimensions."""
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(ErrorCode.MALFORMED_LANDMARKS, message, details)


class CalibrationError(PerformxError):
    """Raised when standing-pose calibration fails stability or geometric validation."""
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(ErrorCode.CALIBRATION_FAILED, message, details)


@dataclass(frozen=True)
class SquatConfig:
    """Validated biomechanical configuration contract for squat movement.
    
    All numeric fields enforce bounds and finite checks upon instantiation.
    """
    standing_knee_angle: float = 155.0
    descent_trigger_angle: float = 145.0
    bottom_target_angle: float = 95.0
    deep_squat_angle: float = 75.0
    min_bottom_dwell: float = 0.20   # Seconds
    max_bottom_dwell: float = 4.00   # Seconds
    min_rep_duration: float = 1.00   # Seconds
    max_torso_lean_deg: float = 48.0 # Degrees
    min_symmetry_score: float = 0.78 # Normalized [0.0, 1.0]
    min_visibility_conf: float = 0.50 # Normalized [0.0, 1.0]

    def __post_init__(self):
        # Validate finite values
        for name, val in self.__dict__.items():
            if not isinstance(val, (int, float)) or not math.isfinite(val):
                raise ValueError(f"SquatConfig field '{name}' must be a finite number, got {val}")

        # Validate logic relationships
        if not (0.0 < self.bottom_target_angle < self.descent_trigger_angle < self.standing_knee_angle <= 180.0):
            raise ValueError(
                f"Invalid angular hierarchy: require 0 < bottom ({self.bottom_target_angle}) "
                f"< descent ({self.descent_trigger_angle}) < standing ({self.standing_knee_angle}) <= 180"
            )
        if self.min_bottom_dwell < 0.0 or self.max_bottom_dwell < self.min_bottom_dwell:
            raise ValueError("Require 0 <= min_bottom_dwell <= max_bottom_dwell")
        if not (0.0 <= self.min_symmetry_score <= 1.0):
            raise ValueError(f"min_symmetry_score must be in [0.0, 1.0], got {self.min_symmetry_score}")
        if not (0.0 <= self.min_visibility_conf <= 1.0):
            raise ValueError(f"min_visibility_conf must be in [0.0, 1.0], got {self.min_visibility_conf}")


# MediaPipe 33-landmark topological constants
class LandmarkIndex:
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
