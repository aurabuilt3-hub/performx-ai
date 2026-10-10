import pytest
import numpy as np

from performx.filtering import OneEuroFilter
from performx.kinematics import (
    compute_angle_2d,
    compute_angle_3d,
    compute_torso_inclination,
    compute_bilateral_symmetry,
    compute_knee_lateral_shift,
)


def test_angle_2d_orthogonal():
    # 90-degree right angle at (0, 0)
    a = np.array([0.0, 1.0])
    b = np.array([0.0, 0.0])
    c = np.array([1.0, 0.0])
    angle = compute_angle_2d(a, b, c)
    assert pytest.approx(angle, abs=1e-3) == 90.0


def test_angle_2d_straight_line():
    # 180-degree straight line
    a = np.array([0.0, 1.0])
    b = np.array([0.0, 0.0])
    c = np.array([0.0, -1.0])
    angle = compute_angle_2d(a, b, c)
    assert pytest.approx(angle, abs=1e-3) == 180.0


def test_angle_2d_collinear_folded():
    # 0-degree completely folded
    a = np.array([0.0, 1.0])
    b = np.array([0.0, 0.0])
    c = np.array([0.0, 1.0])
    angle = compute_angle_2d(a, b, c)
    assert pytest.approx(angle, abs=1e-3) == 0.0


def test_angle_3d_known_geometry():
    # 3D right angle
    a = np.array([0.0, 1.0, 0.0])
    b = np.array([0.0, 0.0, 0.0])
    c = np.array([0.0, 0.0, 1.0])
    angle = compute_angle_3d(a, b, c)
    assert pytest.approx(angle, abs=1e-3) == 90.0


def test_torso_inclination_vertical():
    # Completely upright torso (shoulder above hip)
    shoulder = np.array([0.5, 0.2])
    hip = np.array([0.5, 0.6])
    lean = compute_torso_inclination(shoulder, hip)
    assert pytest.approx(lean, abs=1e-3) == 0.0


def test_torso_inclination_45_degrees():
    shoulder = np.array([0.8, 0.3])
    hip = np.array([0.5, 0.6])
    lean = compute_torso_inclination(shoulder, hip)
    assert pytest.approx(lean, abs=1.0) == 45.0


def test_bilateral_symmetry_calculation():
    # Identical values = 100% symmetry
    assert compute_bilateral_symmetry(90.0, 90.0) == 1.0
    
    # Asymmetry
    sym = compute_bilateral_symmetry(90.0, 80.0)
    assert 0.88 <= sym <= 0.90
    
    # Zero symmetry clamped
    assert compute_bilateral_symmetry(100.0, 0.0) == 0.0


def test_one_euro_filter_jitter_attenuation():
    filter_ = OneEuroFilter(freq=30.0, min_cutoff=1.0, beta=0.005)
    
    # Generate noisy signal around 100.0
    np.random.seed(42)
    noise = np.random.normal(0, 2.0, 100)
    signal = 100.0 + noise
    
    filtered_values = []
    for i, val in enumerate(signal):
        filt = filter_.filter(val, timestamp=i * (1.0 / 30.0))
        filtered_values.append(filt)
        
    filtered_arr = np.array(filtered_values[20:])  # Skip warm up
    raw_arr = signal[20:]
    
    # Filtered signal variance should be significantly less than raw noise variance
    assert np.var(filtered_arr) < np.var(raw_arr) * 0.35
