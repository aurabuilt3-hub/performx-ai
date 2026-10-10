# PERFORMX: Human Movement Analysis Platform

> **Bio-inspired real-time movement analysis powered by *Drosophila melanogaster* sensorimotor intelligence and MediaPipe computer vision.**

---

## 1. Overview & Architecture

PERFORMX translates computational principles of fruit-fly sensorimotor control into real-time human movement analysis without copying hexapod anatomy or claiming clinical diagnostic authority:

1. **Central Pattern Generators (CPG)**: A coupled phase oscillator tracks movement rhythm, cadence, and phase lag.
2. **Walknet State Gating**: Multi-stage state machine (`IDLE` ➔ `DESCENT` ➔ `BOTTOM` ➔ `ASCENT` ➔ `LOCKOUT`) enforcing depth and dwell thresholds before counting reps.
3. **Proprioceptive Reflex Loops**: Immediate cueing for lateral asymmetry and excessive trunk lean.
4. **Adaptive Low-Pass Filtering**: 1€ Filter adapts cutoff frequency dynamically (high smoothing during pauses, low latency during rapid movement).
5. **Privacy by Design**: Frames are processed strictly in volatile RAM and immediately discarded. Zero media disk writes.

---

## 2. Environment Setup & Installation

### Prerequisites
- Python 3.11 (64-bit recommended)
- Webcam (built-in or USB)

### Installation
```powershell
# 1. Create a dedicated virtual environment
py -3.11 -m venv .venv

# 2. Activate environment
.\.venv\Scripts\Activate.ps1

# 3. Install tested dependencies
pip install -r requirements.txt
```

---

## 3. Running the Application

Launch the Streamlit interactive dashboard:
```powershell
.\.venv\Scripts\streamlit run performx/app.py
```

The application provides:
- **Live Webcam Loop**: Real-time Heads-Up Display (HUD) overlay and biometric metrics panel.
- **Snapshot Posture Check**: Single-frame posture evaluation using Streamlit's built-in camera widget.
- **Biomechanical Controls**: Adjustable knee depth targets, minimum bottom dwell time, and torso lean limits.

---

## 4. Running the Test Suite

Run all automated unit tests covering kinematics, 1€ filtering, sensorimotor gating, and privacy invariants:
```powershell
.\.venv\Scripts\pytest -v
```

### Verified Test Categories:
- **Geometry & Kinematics**: 2D/3D angle correctness, trunk inclination, and bilateral symmetry calculation.
- **Adaptive Filtering**: Noise attenuation variance testing on the 1€ filter.
- **Sensorimotor Engine**: Full repetition cycles, Walknet rejection of shallow half-reps, and reflex warning cues.
- **Privacy Enforcement**: Automated assertions verifying zero image/video file writes and zero external network transmissions.

---

## 5. Scope & Limitations
- **Intended Purpose**: Athletic training, posture feedback, and movement consistency tracking.
- **Disclaimer**: PERFORMX is **not** a clinical or medical diagnostic device and does not predict injury risk.
