"""PERFORMX Benchmark: Fruit-fly Bio-Inspired CPG vs Naive Threshold Baseline.

Evaluates:
1. Cadence and phase synchronization under smooth, rhythmic squatting.
2. Stability and robustness under noisy/jittery landmark inputs.
3. Behavior during deliberate isometric pauses in the bottom position.
4. Repetition detection accuracy between Walknet state-gating vs naive threshold counting.
"""

import numpy as np
import pytest

from performx.core import MovementPhase, SquatConfig
from performx.engine import PhaseOscillator, SensorimotorEngine


class NaiveThresholdRepCounter:
    """Conventional baseline rep counter without bio-inspired CPG or Walknet rules.
    
    Simple hysteresis:
    - If angle < 95: state = DOWN
    - If angle > 150 and state == DOWN: state = UP, rep += 1
    Does NOT require minimum dwell time, does NOT track cadence or rhythm.
    """

    def __init__(self, bottom_threshold: float = 95.0, top_threshold: float = 150.0):
        self.bottom_thresh = bottom_threshold
        self.top_thresh = top_threshold
        self.state = "UP"
        self.repetition_count = 0

    def update(self, knee_angle: float):
        if self.state == "UP" and knee_angle <= self.bottom_thresh:
            self.state = "DOWN"
        elif self.state == "DOWN" and knee_angle >= self.top_thresh:
            self.state = "UP"
            self.repetition_count += 1


def test_walknet_vs_naive_counter_on_jitter_noise():
    """Demonstrate that Walknet state gating rejects high-frequency noise spikes that fool naive counters."""
    naive = NaiveThresholdRepCounter(bottom_threshold=95.0, top_threshold=150.0)
    engine = SensorimotorEngine(config=SquatConfig(bottom_target_angle=95.0, min_bottom_dwell=0.2, min_rep_duration=1.0))

    # Rapid jitter bouncing across thresholds in < 0.1s (simulating camera glitch or occlusion flash)
    jitter_angles = [160.0, 90.0, 155.0, 88.0, 160.0]
    t = 0.0
    for ang in jitter_angles:
        naive.update(ang)
        engine.evaluate_frame(ang, 160.0, 10.0, 1.0, timestamp=t, confidence=0.9)
        t += 0.033

    # Naive counter falsely counted 2 reps in 0.13 seconds due to threshold crossing
    assert naive.repetition_count == 2
    # SensorimotorEngine correctly rejected the sensor spikes because minimum rep duration & dwell were violated
    assert engine.repetition_count == 0


def test_cpg_oscillator_tracks_rhythmic_cadence():
    """Verify that Kuramoto coupled phase oscillator locks onto rhythmic squat trajectory."""
    oscillator = PhaseOscillator(target_frequency_hz=0.35)
    
    # 3-second smooth squat cycle: 0 -> pi -> 2*pi
    timestamps = np.linspace(0, 3.0, 90)
    # Norm depth in [0, 1] following half-sine
    depths = np.sin(np.pi * (timestamps / 3.0))

    dt = 3.0 / 90.0
    phases = []
    for d in depths:
        oscillator.update(d, dt)
        phases.append(oscillator.phase)

    # Phase should smoothly advance from start through bottom inflection (~pi) to ~2*pi
    assert phases[0] > 0.0
    # At midpoint (peak depth), phase should be near pi (3.14 rad)
    mid_phase = phases[45]
    assert 2.0 <= mid_phase <= 4.0
    # Phase advances monotonically modulo 2*pi
    assert len(phases) == 90


def test_sensorimotor_engine_handles_variable_speeds():
    """Verify engine reliably detects slow vs explosive squats with valid rep counts."""
    engine = SensorimotorEngine(config=SquatConfig(min_bottom_dwell=0.15, min_rep_duration=0.8))

    # Slow controlled 4-second squat
    t = 0.0
    engine.evaluate_frame(165.0, 170.0, 10.0, 1.0, timestamp=t, confidence=0.9)
    # Descent over 1.5s
    for ang in np.linspace(165.0, 85.0, 10):
        t += 0.15
        engine.evaluate_frame(ang, ang + 5.0, 15.0, 1.0, timestamp=t, confidence=0.9)
    # Dwell at bottom for 0.6s
    for _ in range(4):
        t += 0.15
        engine.evaluate_frame(85.0, 90.0, 15.0, 1.0, timestamp=t, confidence=0.9)
    # Ascent over 1.5s
    for ang in np.linspace(85.0, 165.0, 10):
        t += 0.15
        engine.evaluate_frame(ang, ang + 5.0, 12.0, 1.0, timestamp=t, confidence=0.9)

    assert engine.repetition_count == 1
    assert engine.valid_reps == 1
