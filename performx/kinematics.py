import numpy as np


def compute_angle_2d(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Calculate the planar angle ABC (in degrees) with vertex at point b.
    
    Formula uses vector dot product and determinant / norm for numerical stability:
        BA = a - b
        BC = c - b
    Returns an angle in range [0, 180] degrees.
    """
    ba = np.asarray(a[:2], dtype=np.float64) - np.asarray(b[:2], dtype=np.float64)
    bc = np.asarray(c[:2], dtype=np.float64) - np.asarray(b[:2], dtype=np.float64)

    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)

    if norm_ba < 1e-7 or norm_bc < 1e-7:
        return 0.0

    cosine = np.dot(ba, bc) / (norm_ba * norm_bc)
    # Clip for floating point precision tolerance
    cosine = np.clip(cosine, -1.0, 1.0)
    angle_rad = np.arccos(cosine)
    return float(np.degrees(angle_rad))


def compute_angle_3d(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Calculate the 3D angle ABC (in degrees) with vertex at point b.
    
    Useful when 3D world landmarks (x, y, z) are available.
    Returns angle in [0, 180] degrees.
    """
    ba = np.asarray(a[:3], dtype=np.float64) - np.asarray(b[:3], dtype=np.float64)
    bc = np.asarray(c[:3], dtype=np.float64) - np.asarray(b[:3], dtype=np.float64)

    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)

    if norm_ba < 1e-7 or norm_bc < 1e-7:
        return 0.0

    cosine = np.dot(ba, bc) / (norm_ba * norm_bc)
    cosine = np.clip(cosine, -1.0, 1.0)
    angle_rad = np.arccos(cosine)
    return float(np.degrees(angle_rad))


def compute_torso_inclination(shoulder: np.ndarray, hip: np.ndarray) -> float:
    """Compute torso inclination relative to vertical (in degrees).
    
    0 deg = completely upright posture
    90 deg = horizontal forward lean
    """
    dx = shoulder[0] - hip[0]
    # In normalized image coordinates, y increases downward
    dy = hip[1] - shoulder[1]
    
    # Angle with vertical axis (0, 1)
    angle_rad = np.arctan2(abs(dx), max(dy, 1e-6))
    return float(np.degrees(angle_rad))


def compute_bilateral_symmetry(left_val: float, right_val: float) -> float:
    """Calculate symmetry index between left and right bilateral joints.
    
    Returns a score in [0.0, 1.0], where 1.0 is perfect bilateral symmetry.
    Score = 1.0 - (|left - right| / max(left, right, 1.0))
    """
    diff = abs(left_val - right_val)
    denom = max(abs(left_val), abs(right_val), 1.0)
    score = 1.0 - (diff / denom)
    return float(np.clip(score, 0.0, 1.0))


def compute_knee_lateral_shift(hip: np.ndarray, knee: np.ndarray, ankle: np.ndarray) -> float:
    """Measure knee lateral displacement (valgus/varus indicator) in 2D plane.
    
    Returns the horizontal offset of the knee relative to the hip-ankle axis.
    Normalized by leg length to be distance-invariant.
    """
    hip_pt = np.asarray(hip[:2], dtype=np.float64)
    knee_pt = np.asarray(knee[:2], dtype=np.float64)
    ankle_pt = np.asarray(ankle[:2], dtype=np.float64)

    # Reference axis from hip to ankle
    axis = ankle_pt - hip_pt
    leg_len = np.linalg.norm(axis)
    if leg_len < 1e-6:
        return 0.0

    # Orthogonal projection distance from knee to hip-ankle segment
    # 2D cross product gives signed distance * leg_len
    lateral_offset = np.cross(axis, knee_pt - hip_pt) / leg_len
    return float(lateral_offset)
