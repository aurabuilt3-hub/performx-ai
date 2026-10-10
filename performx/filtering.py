import numpy as np


class OneEuroFilter:
    """1€ Filter: Adaptive Low-Pass Filter for real-time jitter reduction.
    
    Inspired by MediaPipe's OneEuroFilter (mediapipe/util/filtering/one_euro_filter.cc)
    and Casiez et al., CHI 2012.
    
    At low speeds, a lower cutoff frequency eliminates jitter/noise.
    At high speeds, a higher cutoff frequency minimizes latency/lag.
    """

    def __init__(self, freq: float = 30.0, min_cutoff: float = 1.0, beta: float = 0.007, d_cutoff: float = 1.0):
        if freq <= 0.0:
            raise ValueError(f"freq must be > 0, got {freq}")
        if min_cutoff <= 0.0:
            raise ValueError(f"min_cutoff must be > 0, got {min_cutoff}")
        if beta < 0.0:
            raise ValueError(f"beta must be >= 0, got {beta}")
        if d_cutoff <= 0.0:
            raise ValueError(f"d_cutoff must be > 0, got {d_cutoff}")

        self.freq = float(freq)
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)

        self._x_prev: np.ndarray | None = None
        self._dx_prev: np.ndarray | None = None
        self._t_prev: float | None = None

    def _alpha(self, cutoff: np.ndarray | float, dt: float) -> np.ndarray | float:
        """Calculate exponential smoothing factor alpha = 1 / (1 + tau/dt)."""
        tau = 1.0 / (2.0 * np.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def filter(self, x: np.ndarray | float, timestamp: float | None = None) -> np.ndarray | float:
        """Filter value x given an optional timestamp (in seconds)."""
        x_val = np.asarray(x, dtype=np.float64)

        if self._x_prev is None:
            self._x_prev = x_val.copy()
            self._dx_prev = np.zeros_like(x_val)
            self._t_prev = timestamp
            return x

        # Calculate dynamic sampling rate / dt
        if timestamp is not None and self._t_prev is not None:
            dt = timestamp - self._t_prev
            if dt <= 1e-6:
                dt = 1.0 / self.freq
        else:
            dt = 1.0 / self.freq

        self._t_prev = timestamp

        # Derivative calculation and filtering
        dx = (x_val - self._x_prev) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        dx_hat = a_d * dx + (1.0 - a_d) * self._dx_prev
        self._dx_prev = dx_hat

        # Adaptive cutoff calculation based on speed
        cutoff = self.min_cutoff + self.beta * np.abs(dx_hat)
        a = self._alpha(cutoff, dt)

        # Filtered signal
        x_hat = a * x_val + (1.0 - a) * self._x_prev
        self._x_prev = x_hat

        if np.isscalar(x):
            return float(x_hat)
        return x_hat

    def reset(self):
        """Reset internal filter states."""
        self._x_prev = None
        self._dx_prev = None
        self._t_prev = None
