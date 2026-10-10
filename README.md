# PERFORMX: Human Movement Analysis Platform

> **Bio-inspired real-time movement analysis powered by *Drosophila melanogaster* sensorimotor intelligence and MediaPipe computer vision.**

---

## 1. Modular Backend Architecture

PERFORMX is structured into clear, decoupled module boundaries:

```
performx/
  ├── core.py         # Validated configuration (SquatConfig), shared domain enums, error hierarchy
  ├── contracts.py    # Strict typed data contracts: PoseLandmarksData, MovementResult, CalibrationResult
  ├── engine.py       # Algorithmic core: OneEuroFilter, vectorized kinematics, CPG oscillator, Walknet gating
  ├── calibration.py  # Standing pose calibration: windowed posture validation & robust body scale proxy
  ├── services.py     # Isolated services: PoseEstimationService & session-scoped MovementAnalysisSession
  ├── pipeline.py     # Master orchestrator connecting vision and movement analysis
  ├── visualizer.py   # In-memory Heads-Up Display (HUD) rendering with calibration badge
  ├── api.py          # Clean typed in-process BackendService API
  ├── http_api.py     # Production FastAPI REST API for frontend client integration
  └── app.py          # Streamlit presentation dashboard with calibration controls
```

### Module Responsibilities
- **`core`**: Contains typed enums (`MovementPhase`, `FormAlertSeverity`, `CalibrationStatus`, `ErrorCode`), domain exceptions (`PerformxError`, `CalibrationError`), and validated frozen configs (`SquatConfig`).
- **`contracts`**: Defines immutability-enforced, finite-checked data models (`PoseLandmarksData`, `MovementFeatures`, `MovementResult`, `CalibrationResult`, `SessionSummary`). Enforces that raw frames and video buffers are **never** returned or serialized.
- **`calibration`**: Collects a rolling temporal window (15–45 frames) of upright standing landmarks, verifies knee extension ($\geq 164^\circ$) and stability ($\sigma \leq 0.04$), and calculates robust median limb lengths (femur, tibia, torso, height proxy) without retaining video or images.
- **`engine`**: Pure computational logic for adaptive filtering (1€ filter), 2D/3D joint angles, bilateral symmetry, Kuramoto CPG coupled phase oscillator, and Walknet state transitions.
- **`services`**:
  - `PoseEstimationService`: Wraps MediaPipe Pose execution with landmark validation.
  - `MovementAnalysisSession`: Maintains independent filter instances, rep counters, dwell timers, and metrics per active session, preventing cross-session state leakage.
- **`api`**: In-process backend interface providing session lifecycle management, health checks, and capability introspection without network serialization overhead.
- **`http_api`**: Production FastAPI REST service exposing session lifecycle, standing calibration, and privacy-preserving browser landmark ingestion. See [docs/API_INTEGRATION.md](docs/API_INTEGRATION.md).
- **`app`**: Streamlit presentation layer. Consumes validated `MovementResult` contracts and avoids duplicate biomechanics calculations.

---

## 2. In-Process Service & Production HTTP API Architecture

PERFORMX supports two complementary operational modes:
1. **In-Process Service (`performx/api.py`)**:
   - Powering the local Streamlit dashboard (`performx/app.py`).
   - Frames remain strictly in-memory within the local Python process for maximal throughput and zero network overhead.
   - Run locally: `streamlit run performx/app.py`
2. **Production HTTP REST API (`performx/http_api.py`)**:
   - High-performance FastAPI server providing REST endpoints for external frontend clients (React, Next.js, mobile apps).
   - **Privacy-first landmark ingestion**: Frontends running client-side MediaPipe send pre-extracted $(x, y, z)$ coordinates, guaranteeing zero camera video leaves the user's browser.
   - **Server fallback**: Supports RAM-only multipart image processing with a strict 5MB limit and immediate garbage collection.
   - **Production ASGI Startup**: `python -m performx.http_api` or `uvicorn performx.http_api:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1`
   - **Health Probes**: `GET /healthz`, `GET /health`, `GET /`
   - Complete guides: [docs/API_INTEGRATION.md](docs/API_INTEGRATION.md) and [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).


---

## 3. Privacy & Security Architecture

- **Ephemeral Processing**: Webcam frames reside strictly in volatile RAM (`numpy.ndarray`).
- **Zero Media Persistence**: Media frames are never written to disk or logged.
- **Network Isolation**: Outbound network connections are prevented; processing runs 100% locally.
- **Hardware Lifecycle**: Camera capture handles are reliably released upon session termination.
- **Privacy Test Limitations**: While tests verify zero disk writes and loopback socket constraints, automated unit tests cannot guarantee physical RAM anti-forensics (e.g., standard OS page file memory retention). PERFORMX minimizes this surface by zero-copy array operations and immediate reference release.

---

## 4. Environment Setup & Installation

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

## 5. Running the Application & Tests

### Run Automated Unit & Security Tests:
```powershell
.\.venv\Scripts\pytest -v
```

### Launch the Streamlit Dashboard:
```powershell
.\.venv\Scripts\streamlit run performx/app.py
```

### Launch the Production HTTP REST API:
```powershell
.\.venv\Scripts\uvicorn performx.http_api:app --host 0.0.0.0 --port 8000 --reload
# Interactive API documentation will be available at http://localhost:8000/docs
```

---

## 6. Demonstration Workflow & Controlled Manual Protocol

To execute a complete, reproducible operator demonstration:

1. **Camera Framing**:
   - Place webcam 2.0–2.5 meters away at waist/hip height (sagittal or semi-sagittal view).
   - Ensure full body framing: head, hips, knees, and ankles visible under good lighting.
2. **Start Camera Loop**:
   - Toggle `Activate Live Camera Feed` in the Streamlit dashboard.
   - Verify the heads-up display (HUD) renders in real time without lag.
3. **Standing Calibration**:
   - Stand tall and still with fully extended knees (knee angle $\ge 164^\circ$).
   - Click `📏 Calibrate Pose` in the sidebar and hold for 15–45 frames until `CALIB: ACTIVE` appears.
4. **Controlled Movement Sets**:
   - **Trial 1 (Valid Squats)**: Perform 5 complete repetitions at a controlled pace (~2.5–3.0s per rep).
   - **Trial 2 (Incomplete Half-Squats)**: Perform 3 shallow squats reversing above 100°. Verify `INCOMPLETE_DEPTH` alert and 0 false rep counts.
   - **Trial 3 (Bottom Pause Squat)**: Hold the bottom position for 1.5s. Verify bottom dwell accumulator updates live.
   - **Trial 4 (Transient Occlusion)**: Step out of view for 3s. Verify graceful occlusion handling without crashes or false reps.
5. **Review Session Movement Intelligence**:
   - Examine the `Session Movement Intelligence` metrics panel: check accepted vs rejected counts, duration variability, dwell shifts, depth ranges, and explainable feedback.
6. **Session Reset & Cleanup**:
   - Click `🔄 Reset Entire Session` to atomically zero out all counters and buffers.
   - Toggle camera feed off to safely release the hardware device.

### Operator Troubleshooting
- **Webcam unavailable**: Verify other applications (Zoom, Teams, OBS) are closed.
- **Low Confidence (<50%)**: Increase room illumination; step back so ankles and feet are framed.
- **Calibration Failed**: Avoid swaying during the 15-frame window. If failed, click `🔄 Reset Calib` and re-attempt.

---

## 7. Detection Performance Formulations & Validation Integrity (Phase 18 & 19)

### Confusion-Matrix Semantics for Continuous Movement
In continuous repetition counting, an "event" is a completed repetition cycle:
- **Valid Target Repetitions**: Physical movements executed by the human subject according to protocol standards (e.g. 5 full squats with knee angle $\le 95^\circ$).
- **Detected Accepted Repetitions**: Repetitions detected and accepted by PERFORMX satisfying all Walknet transition gates.
- **False Positives ($FP$)**: Detected accepted counts that do *not* correspond to a genuine completed target repetition (e.g. noise spikes, jitter, or shallow reversals wrongly accepted). Validated bound: $0 \le FP \le \text{Detected}$.
- **False Negatives ($FN$) / Missed Repetitions**: Valid target repetitions completed by the human subject that the detector failed to count. Validated bound: $0 \le FN \le \text{Target}$.
- **True Positives ($TP$)**: Genuine target repetitions correctly counted by PERFORMX:
  $$TP = \min(\text{Target}, \max(0, \text{Detected} - FP))$$
- **Event Consistency**: In a closed, controlled trial, $\text{Target} = TP + FN$. If $TP + FN \ne \text{Target}$, the scorecard flags an event count discrepancy warning.
- **Absence of True Negatives ($TN$) & Conventional Accuracy**: In continuous stream analysis, $TN$ (identifying moments when the user is *not* squatting) cannot be defined without arbitrary time-bin discretization. Standard accuracy $((TP + TN) / \text{Total})$ is ill-defined in repetition counting. PERFORMX therefore omits conventional accuracy and evaluates performance using:
  - **Precision**: $\text{Precision} = \frac{TP}{TP + FP} = \frac{TP}{\text{Detected}}$ (defaults to $1.0$ if $FP = 0$ and $\text{Target} = 0$, else $0.0$).
  - **Recall**: $\text{Recall} = \frac{TP}{\text{Target}}$ (defaults to $1.0$ if $FN = 0$ and $\text{Target} = 0$, else $0.0$).
  - **F1 Score**: Harmonic mean of precision and recall:
    $$F_1 = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}} \quad (\text{if Precision} + \text{Recall} = 0 \implies 0.0)$$
  - **Protocol Compliance Score (Opportunity Proxy)**: Evaluates total decision opportunities (valid targets + intentional incomplete attempts):
    $$\text{Score} = \max\left(0.0, 1.0 - \frac{FP + FN}{\max(\text{Target} + \text{Incomplete Attempted}, 1)}\right)$$

### Event-Level Temporal Bipartite Matching (Phase 20 & 21)
To prevent unsupported claims where aggregate numbers align by coincidence without individual detections matching actual movements, PERFORMX implements a deterministic, maximum-cardinality minimum-cost bipartite event-matching protocol (`match_repetition_events`):
1. **Mathematical Optimality**:
   - **Maximum Cardinality First**: Guarantees finding the maximum possible number of valid repetition pairings, eliminating greedy-choice suboptimality (e.g. where an early close match blocks an adjacent match, reducing total detected count).
   - **Minimum Total Temporal Error**: Among all maximum-cardinality matchings, selects the matching that minimizes $\sum |\Delta t|$.
   - **Deterministic Tie-Breaking**: Lexicographical tie-breaking over sorted pairs guarantees deterministic, reproducible matching outcomes.
   - **Empirical Scalability (Phase 21 Benchmark)**:
     * $N = 5$: 0.07 ms
     * $N = 10$: 0.12 ms
     * $N = 50$: 0.27 ms
     * $N = 100$: 0.85 ms
     * $N = 500$: 17.52 ms
     * Auxiliary Space: $O(N)$
   - **Live Frame Processing Latency (Phase 21 Measured on Host CPU)**:
     * Synthetic black frames ($640 \times 480$): Median = 11.11 ms, 95th Percentile = 12.36 ms (~80–90 FPS capacity).
     * Live hardware webcam frames ($640 \times 480$): Median = 15.53 ms, 95th Percentile = 16.68 ms (~60–64 FPS capacity).
2. **Tolerance Window ($\tau = \pm 1.5\text{s}$)**:
   - Evaluates $|t_{\text{target}} - t_{\text{detected}}| \le \tau$.
   - **Biomechanical Cadence Rationale**: At a standard 2.5–3.0s squat cadence, a $\pm 1.5\text{s}$ window accommodates human stopwatch reaction latency (~0.3–0.5s) while preventing cross-rep contamination with adjacent repetitions ($\Delta t_{\text{rep}} \ge 2.5\text{s} > 1.5\text{s}$).
   - **Evaluation Parameter Integrity**: Tolerance is strictly an evaluation boundary parameter, not an accuracy tuning knob.
3. **Event-Level TP, FP, FN**:
   - $TP$: Matched valid target events.
   - $FP$: Unmatched detections (or spurious noise detections).
   - $FN$: Unmatched valid target events.
   - Invariant: $TP + FP = \text{len}(\text{detected})$, $TP + FN = \text{len}(\text{valid targets})$.
4. **Privacy-Preserving**: Only scalar elapsed timestamps (monotonic seconds from trial start) are processed in memory. Zero raw video, imagery, or face telemetry is captured or stored.

### 3-State Physical Trial Verification Lifecycle
To preserve evaluation integrity, trial states are explicitly decoupled:
1. **`NOT_CONDUCTED`**: Initial state where no physical trials have occurred or all counts are zero. Precision, recall, and F1 are strictly `None`.
2. **`DATA_ENTERED`**: Manual observation data has been inputted into the scorecard, but awaiting formal operator verification sign-off.
3. **`OPERATOR_VERIFIED`**: Operator has physically overseen the trial, verified that observed counts are mathematically consistent with recorded video events, and signed off.

Use this structured worksheet during live operator testing:

| Field | Description / Operator Record |
| :--- | :--- |
| **Operator / Subject** | Controlled Human Subject (Healthy adult) |
| **Camera View & Setup** | Monocular webcam, sagittal/semi-sagittal view, 2.2m distance, waist height |
| **Lighting & Environment** | ~300 lux indoor lighting, high-contrast clothing, plain backdrop |
| **Trial 1: Calibration** | Target: 15–45 frames upright standing ($\ge 164^\circ$) $\to$ `CALIBRATED` (`CALIB: ACTIVE`) |
| **Trial 2: Standard Squats** | Target: 5 full squats (~2.5–3.0s pace). Record detected accepted reps and timestamps. |
| **Trial 3: Incomplete Half-Squats** | Target: 3 shallow squats (reverse $>100^\circ$). Record detected incomplete attempts (target 0 false reps). |
| **Trial 4: Bottom Pause Squat** | Target: 1 pause squat (1.5s hold). Record dwell timing and rep count. |
| **Trial 5: Transient Occlusion** | Target: Step out of view for 3s. Record `OCCLUSION_ABORT` and graceful recovery. |
| **Trial 6: Session Reset** | Target: Click `🔄 Reset Entire Session`. Record all counters zeroing out. |
| **Ground-Truth Observations** | Enter target reps, accepted reps, rejected reps, false positives, missed reps, and timestamps |
| **Verification Lifecycle** | `NOT_CONDUCTED` $\to$ `DATA_ENTERED` $\to$ `OPERATOR_VERIFIED` |

---

## 8. Scope & Operating System Limitations
- **Non-Clinical Athletic Scope**: PERFORMX is an educational fitness movement analysis tool. It is **not** a clinical diagnostic medical device and does not predict injury risk or diagnose pathological fatigue.
- **Monocular 2D Geometry**: Joint angles and body scale proxies are derived from monocular 2D planar projections. Extreme overhead, low-angle, or diagonal perspectives reduce joint depth accuracy.
- **Operating-System Memory Boundary**: Frames are processed strictly in volatile RAM (`np.ndarray`) with immediate memory dereferencing (`del frame`). However, application-level Python execution cannot override host operating-system pagefile swapping, hibernate memory images, or OS crash-dump behaviors.
- **Verification Integrity**: Automated unit tests prove mathematical, algorithmic, and state-machine correctness. Real-human trial results remain explicitly marked **`PENDING`** or **`NOT_CONDUCTED`** until a physical subject executes the protocol.

