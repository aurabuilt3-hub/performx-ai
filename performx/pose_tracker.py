"""Backward-compatibility shim for performx.pose_tracker."""

from performx.core import LandmarkIndex as PoseLandmark
from performx.services import PoseEstimationService as PoseTracker
from performx.contracts import PoseLandmarksData

__all__ = ["PoseLandmark", "PoseTracker", "PoseLandmarksData"]
