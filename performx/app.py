import time
import cv2
import numpy as np
import streamlit as st

from performx.pipeline import MovementPipeline
from performx.sensorimotor import SquatConfig
from performx.visualizer import draw_hud


def main():
    st.set_page_config(
        page_title="PERFORMX | Bio-Inspired Movement Analysis",
        page_icon="🧬",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom styling
    st.markdown(
        """
        <style>
        .metric-card {
            background-color: #1e293b;
            padding: 16px;
            border-radius: 10px;
            border: 1px solid #334155;
            margin-bottom: 12px;
        }
        .bio-badge {
            background-color: #0284c7;
            color: white;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.85rem;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Top Header
    st.title("🧬 PERFORMX: Human Movement Analysis MVP")
    st.caption("Fruit-Fly (*Drosophila*) Sensorimotor Intelligence • Real-Time Privacy-First CV Pipeline")

    # Sidebar: Configurable Biomechanical Parameters
    with st.sidebar:
        st.header("⚙️ Biomechanical Config")
        st.markdown("**Walknet State Gating & Reflex Limits**")

        standing_knee = st.slider("Standing Knee Angle (°)", 140.0, 180.0, 155.0, 5.0)
        bottom_target = st.slider("Target Bottom Depth (°)", 70.0, 120.0, 95.0, 5.0)
        min_dwell = st.slider("Min Bottom Dwell Pause (s)", 0.05, 1.0, 0.20, 0.05)
        max_torso_lean = st.slider("Max Forward Trunk Lean (°)", 20.0, 65.0, 48.0, 2.0)
        min_symmetry = st.slider("Min Bilateral Symmetry", 0.50, 0.95, 0.78, 0.02)

        st.divider()
        st.subheader("🛡️ Privacy Verification")
        st.success("✅ Zero Disk Storage Policy active")
        st.success("✅ In-memory volatile RAM processing only")
        st.info("ℹ️ Frames are instantly released after pose extraction.")

        st.divider()
        st.subheader("💡 Fruit-Fly Biological Mapping")
        st.markdown(
            """
            - **Walknet Rule Gating**: Prevents partial/shallow half-reps.
            - **Coupled Oscillator (CPG)**: Rhythmic cadence & tempo tracking.
            - **Chordotonal Reflex Loops**: Low-latency valgus & lean warning cues.
            """
        )

    # Re-instantiate pipeline with reactive configuration
    config = SquatConfig(
        standing_knee_angle=standing_knee,
        bottom_target_angle=bottom_target,
        min_bottom_dwell=min_dwell,
        max_torso_lean_deg=max_torso_lean,
        min_symmetry_score=min_symmetry,
    )

    if "pipeline" not in st.session_state:
        st.session_state.pipeline = MovementPipeline(config=config)
    else:
        st.session_state.pipeline.config = config
        st.session_state.pipeline.engine.config = config

    pipeline = st.session_state.pipeline

    # Tabs for Stream Mode vs Snapshot Mode
    tab_live, tab_snapshot = st.tabs(["🎥 Live Webcam Loop", "📸 Snapshot & Single Image Evaluation"])

    with tab_live:
        st.write("Start the camera loop to analyze movement in real time with the bio-inspired sensorimotor engine.")

        col_cam, col_metrics = st.columns([3, 2])

        with col_cam:
            run_live = st.toggle("Activate Live Camera Feed", value=False)
            frame_window = st.image([])

        with col_metrics:
            st.subheader("📊 Instantaneous Biometrics")
            m_rep = st.empty()
            m_phase = st.empty()
            m_knee = st.empty()
            m_sym = st.empty()
            m_dwell = st.empty()
            m_cpg = st.empty()
            m_alert = st.empty()

        if run_live:
            # VideoCapture session loop
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                st.error("Could not access local webcam device (index 0). Please check camera permissions or try snapshot mode.")
            else:
                try:
                    while run_live:
                        ret, frame = cap.read()
                        if not ret or frame is None:
                            st.warning("Webcam frame unavailable.")
                            break

                        # Process strictly in RAM
                        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        now_t = time.time()
                        metrics = pipeline.process_frame(rgb_frame, timestamp=now_t)

                        # Render Heads-Up Display
                        annotated = draw_hud(rgb_frame, metrics)
                        frame_window.image(annotated, channels="RGB", use_container_width=True)

                        # Update metrics panel
                        m_rep.metric("Valid Repetitions", f"{metrics.repetition_count}")
                        m_phase.metric("Movement Phase", f"{metrics.current_phase.value}")
                        m_knee.metric("Avg Knee Angle", f"{metrics.avg_knee_angle:.1f}°")
                        m_sym.metric("Bilateral Symmetry", f"{metrics.symmetry_score:.0%}")
                        m_dwell.metric("Bottom Dwell", f"{metrics.bottom_dwell_time:.2f} s")
                        m_cpg.metric("CPG Phase (θ)", f"{metrics.oscillator_phase:.2f} rad")

                        if metrics.active_alerts:
                            alert = metrics.active_alerts[0]
                            m_alert.warning(f"⚠️ {alert.message}")
                        else:
                            m_alert.success("✨ Posture Aligned")

                        # Immediate memory release
                        del frame
                        del rgb_frame
                        del annotated

                finally:
                    cap.release()
                    st.info("Webcam hardware stream safely released.")

    with tab_snapshot:
        st.subheader("Camera Snapshot Input")
        cam_photo = st.camera_input("Take a snapshot posture test")

        if cam_photo is not None:
            bytes_data = cam_photo.getvalue()
            np_arr = np.frombuffer(bytes_data, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            rgb_snap = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            snap_metrics = pipeline.process_frame(rgb_snap, timestamp=time.time())
            snap_annotated = draw_hud(rgb_snap, snap_metrics)

            c1, c2 = st.columns(2)
            with c1:
                st.image(snap_annotated, caption="Evaluated Frame with In-Memory HUD", use_container_width=True)
            with c2:
                st.markdown(f"**Detected Phase:** `{snap_metrics.current_phase.value}`")
                st.markdown(f"**Knee Angle:** `{snap_metrics.avg_knee_angle:.1f}°`")
                st.markdown(f"**Bilateral Symmetry:** `{snap_metrics.symmetry_score:.0%}`")
                st.markdown(f"**Torso Forward Lean:** `{snap_metrics.torso_lean:.1f}°`")
                if snap_metrics.active_alerts:
                    for a in snap_metrics.active_alerts:
                        st.warning(f"⚠️ [{a.code}] {a.message}")
                else:
                    st.success("Form within target biomechanical envelope.")

            del img
            del rgb_snap
            del snap_annotated


if __name__ == "__main__":
    main()
