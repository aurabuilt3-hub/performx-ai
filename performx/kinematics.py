"""Backward-compatibility shim for performx.kinematics."""

from performx.engine import (
    compute_angle_2d,
    compute_angle_3d,
    compute_torso_inclination,
    compute_bilateral_symmetry,
    compute_knee_lateral_shift,
)

__all__ = [
    "compute_angle_2d",
    "compute_angle_3d",
    "compute_torso_inclination",
    "compute_bilateral_symmetry",
    "compute_knee_lateral_shift",
]
