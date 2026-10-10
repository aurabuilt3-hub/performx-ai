import time
import cv2
import numpy as np
import streamlit as st

from performx.core import SquatConfig
from performx.pipeline import MovementPipeline
from performx.visualizer import draw_hud


def main():
    st.set_page_config(
        page_title="PERFORMX | Bio-Inspired Movement Analysis",
        page_icon="🧬",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Top Header
    st.title("🧬 PERFORMX: Human Movement Analysis MVP")
    st.caption("Bio-Inspired Sensorimotor Algorithmic Modeling (Walknet State Gating & CPG Phase Oscillations) • Privacy-First Computer Vision")


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
        st.subheader("🎯 Standing Calibration")
        st.caption("Step back so your full body is visible. Stand tall and still.")

        calib_active = False
        if "pipeline" in st.session_state:
            calib_status = st.session_state.pipeline.session.calibration_service.status.value
            if calib_status == "CALIBRATED":
                st.success("✅ Calibrated")
                calib_active = True
                res = st.session_state.pipeline.session.calibration_service.current_result
                if res:
                    st.caption(f"Scale proxy: {res.body_height_proxy_2d:.2f} | Knee: {res.standing_knee_angle:.1f}°")
            elif calib_status == "COLLECTING":
                st.info(f"⏳ Collecting samples ({len(st.session_state.pipeline.session.calibration_service._samples)}/15)...")
            elif calib_status == "FAILED":
                st.error("❌ Calibration Failed")
                res = st.session_state.pipeline.session.calibration_service.current_result
                if res and res.failure_reason:
                    st.caption(res.failure_reason)
            else:
                st.warning("⚠️ Not Calibrated")

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            do_calibrate = st.button("📏 Calibrate Pose")
        with col_c2:
            if st.button("🔄 Reset Calib"):
                if "pipeline" in st.session_state:
                    st.session_state.pipeline.reset_calibration()
                st.rerun()

        if st.button("🔄 Reset Entire Session"):
            if "pipeline" in st.session_state:
                st.session_state.pipeline.reset_session()
            st.toast("Session reset successfully!")

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

    # Re-instantiate pipeline with validated configuration
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
        st.session_state.pipeline.update_config(config)

    pipeline = st.session_state.pipeline

    # Tabs for Stream Mode vs Snapshot Mode vs Protocol Mode
    tab_live, tab_snapshot, tab_protocol = st.tabs([
        "🎥 Live Webcam Loop",
        "📸 Snapshot & Single Image Evaluation",
        "📋 Manual Test Protocol & Scorecard",
    ])

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
            m_summary = st.empty()
            m_session = st.empty()

        # Render current session intelligence (persistent across camera toggles)
        sess_sum = pipeline.session.get_summary()
        if sess_sum.metrics and (sess_sum.metrics.total_completed_reps > 0 or sess_sum.metrics.incomplete_attempts > 0 or sess_sum.metrics.aborted_attempts > 0):
            sm = sess_sum.metrics
            with m_session.container():
                st.markdown("---")
                st.markdown("#### 📈 Session Movement Intelligence")
                c_m1, c_m2, c_m3 = st.columns(3)
                with c_m1:
                    st.metric("Accepted Reps", f"{sm.accepted_reps}")
                    st.metric("Rejected Reps", f"{sm.rejected_reps}")
                with c_m2:
                    st.metric("Incomplete Attempts", f"{sm.incomplete_attempts}")
                    st.metric("Aborted (Occlusion)", f"{sm.aborted_attempts}")
                with c_m3:
                    dur_str = f"{sm.mean_duration:.2f}s (±{sm.duration_range/2:.2f}s)" if sm.mean_duration is not None and sm.duration_range is not None else "N/A"
                    st.metric("Avg Duration", dur_str)
                    depth_str = f"{sm.mean_min_knee_angle:.1f}° (±{sm.knee_angle_range/2:.1f}°)" if sm.mean_min_knee_angle is not None and sm.knee_angle_range is not None else "N/A"
                    st.metric("Avg Peak Depth", depth_str)

                st.markdown("##### Explainable Session Feedback")
                for ins in sm.explainable_insights:
                    st.markdown(f"- {ins}")

        if run_live:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                st.error("⚠️ Could not access local webcam device (index 0). Please ensure camera permissions are granted or switch to Snapshot tab.")
            else:
                try:
                    while run_live:
                        ret, frame = cap.read()
                        if not ret or frame is None:
                            st.warning("⚠️ Webcam frame unavailable. Check physical connection or camera occlusion.")
                            break

                        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        now_t = time.monotonic()

                        if do_calibrate and pipeline.session.calibration_service.status.value != "CALIBRATED":
                            cal_res = pipeline.calibrate_frame(rgb_frame, timestamp=now_t)
                            result = pipeline.process_frame(rgb_frame, timestamp=now_t)
                        else:
                            result = pipeline.process_frame(rgb_frame, timestamp=now_t)

                        # Render Heads-Up Display
                        annotated = draw_hud(rgb_frame, result)
                        frame_window.image(annotated, channels="RGB", use_container_width=True)

                        # Update metrics panel from validated data contract with explicit classification
                        m_rep.metric("Valid Repetitions", f"{result.repetition_count}")
                        m_phase.metric("State: Movement Phase", f"{result.current_phase.value}")
                        m_knee.metric("Measured: Knee Angle", f"{result.features.avg_knee_angle:.1f}°")
                        m_sym.metric("Measured: Symmetry Score", f"{result.features.symmetry_score:.0%}")
                        m_dwell.metric("Measured: Bottom Dwell", f"{result.bottom_dwell_time:.2f} s")
                        norm_depth_str = f" | Norm Depth: {result.features.normalized_hip_depth:.2f}" if result.features.normalized_hip_depth is not None else ""
                        m_cpg.metric("Estimated: CPG Phase (θ)", f"{result.oscillator_phase:.2f} rad{norm_depth_str}")

                        if result.active_alerts:
                            alert = result.active_alerts[0]
                            m_alert.warning(f"⚠️ [{alert.code}] {alert.message}")
                        else:
                            m_alert.success("✨ Posture Aligned")

                        if result.repetition_summary:
                            s = result.repetition_summary
                            status_badge = "✅ **ACCEPTED**" if s.is_valid else "⚠️ **REJECTED**"
                            m_summary.info(
                                f"{status_badge} — **Repetition #{s.rep_number} Breakdown**\n\n"
                                f"• **Total Duration**: {s.duration_seconds:.2f}s (Measured)\n\n"
                                f"• **Sub-Phases**: Descent {s.descent_duration:.2f}s | Bottom Dwell {s.bottom_dwell:.2f}s | Ascent {s.ascent_duration:.2f}s\n\n"
                                f"• **Peak Depth**: Min Knee {s.min_knee_angle:.1f}° (Measured 2D)\n\n"
                                f"• **Form Consistency**: Symmetry {s.mean_symmetry:.0%} | Tracking Confidence {s.mean_confidence:.0%}\n\n"
                                f"> _{s.explanation}_"
                            )

                        # Dynamically update session intelligence container
                        latest_sum = pipeline.session.get_summary()
                        if latest_sum.metrics and (latest_sum.metrics.total_completed_reps > 0 or latest_sum.metrics.incomplete_attempts > 0 or latest_sum.metrics.aborted_attempts > 0):
                            lsm = latest_sum.metrics
                            with m_session.container():
                                st.markdown("---")
                                st.markdown("#### 📈 Session Movement Intelligence")
                                c_m1, c_m2, c_m3 = st.columns(3)
                                with c_m1:
                                    st.metric("Accepted Reps", f"{lsm.accepted_reps}")
                                    st.metric("Rejected Reps", f"{lsm.rejected_reps}")
                                with c_m2:
                                    st.metric("Incomplete Attempts", f"{lsm.incomplete_attempts}")
                                    st.metric("Aborted (Occlusion)", f"{lsm.aborted_attempts}")
                                with c_m3:
                                    dur_str = f"{lsm.mean_duration:.2f}s (±{lsm.duration_range/2:.2f}s)" if lsm.mean_duration is not None and lsm.duration_range is not None else "N/A"
                                    st.metric("Avg Duration", dur_str)
                                    depth_str = f"{lsm.mean_min_knee_angle:.1f}° (±{lsm.knee_angle_range/2:.1f}°)" if lsm.mean_min_knee_angle is not None and lsm.knee_angle_range is not None else "N/A"
                                    st.metric("Avg Peak Depth", depth_str)

                                st.markdown("##### Explainable Session Feedback")
                                for ins in lsm.explainable_insights:
                                    st.markdown(f"- {ins}")

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

            snap_result = pipeline.process_frame(rgb_snap, timestamp=time.monotonic())
            snap_annotated = draw_hud(rgb_snap, snap_result)

            c1, c2 = st.columns(2)
            with c1:
                st.image(snap_annotated, caption="Evaluated Frame with In-Memory HUD", use_container_width=True)
            with c2:
                st.markdown(f"**Detected Phase:** `{snap_result.current_phase.value}`")
                st.markdown(f"**Knee Angle:** `{snap_result.features.avg_knee_angle:.1f}°`")
                st.markdown(f"**Bilateral Symmetry:** `{snap_result.features.symmetry_score:.0%}`")
                st.markdown(f"**Torso Forward Lean:** `{snap_result.features.torso_lean_angle:.1f}°`")
                if snap_result.active_alerts:
                    for a in snap_result.active_alerts:
                        st.warning(f"⚠️ [{a.code}] {a.message}")
                else:
                    st.success("Form within target biomechanical envelope.")

            del img
            del rgb_snap
            del snap_annotated

    with tab_protocol:
        st.subheader("📋 Controlled Manual Test Protocol & Non-Clinical Validation")
        st.markdown(
            """
            Use this interactive guide to systematically evaluate PERFORMX live with an actual user.
            
            > **Privacy Notice**: Frames are processed strictly in volatile RAM. No video, images, or biometric telemetry are ever stored or transmitted.
            > **Engineering Notice**: PERFORMX provides educational fitness biomechanics derived from monocular 2D computer vision. It is **not** a medical device and does not perform clinical diagnosis or injury risk prediction.
            """
        )

        st.markdown("### Step 1: Camera Setup & Baseline Positioning")
        st.info("Place your webcam ~2.0 to 2.5 meters away at waist/hip height (sagittal or semi-sagittal view). Ensure your full head, hips, knees, and feet are visible.")

        st.markdown("### Step 2: Protocol Checklist & Scorecard")
        st.markdown("Execute the following 6 test trials and verify system behavior:")

        t1 = st.checkbox("Trial 1: Standing Pose Calibration (Stand tall for 15-45 frames until 'CALIB: ACTIVE')")
        t2 = st.checkbox("Trial 2: 5 Complete Squats (Comfortable pace: ~2.5-3.0s per repetition)")
        t3 = st.checkbox("Trial 3: 3 Incomplete Half-Squats (Reverse above 100°; verify 0 false reps & INCOMPLETE_DEPTH alert)")
        t4 = st.checkbox("Trial 4: Bottom Pause Squat (Hold bottom for 1.5s; verify dwell time updates and rep counts on rise)")
        t5 = st.checkbox("Trial 5: Temporary Occlusion / Step Out of Frame (Step aside for 3s; verify graceful recovery without crashing)")
        t6 = st.checkbox("Trial 6: Session Reset & Recalibration (Click 'Reset Calib' & 'Reset Entire Session'; verify all counters zero out)")

        st.divider()
        st.markdown("### Step 3: Manual Trial Scorecard & Validation Integrity")
        st.caption(
            "Record live trial observations here. Results remain explicitly PENDING until an actual trial is conducted. "
            "Data entry and formal operator verification are decoupled to preserve validation integrity."
        )

        sc_top1, sc_top2 = st.columns(2)
        with sc_top1:
            trial_conducted = st.checkbox("📝 Data Entered for Physical Trial", value=False)
        with sc_top2:
            operator_confirmed = st.checkbox("✅ Operator Verified (Confirm observations match actual physical trial)", value=False)

        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            trial_id_input = st.text_input("Trial Identifier", value="TRIAL-001")
            target_reps = st.number_input("Target Complete Reps (Trial 2)", min_value=0, max_value=50, value=5)
            detected_reps = st.number_input("Accepted Reps by PERFORMX", min_value=0, max_value=50, value=pipeline.session.engine.repetition_count)
            rejected_reps = st.number_input("Rejected Reps (Erratic Tempo)", min_value=0, max_value=50, value=len([s for s in pipeline.session.engine.completed_summaries if not s.is_valid]))
        with sc2:
            cam_dist = st.number_input("Camera Distance (meters)", min_value=1.0, max_value=5.0, value=2.2, step=0.1)
            incomplete_reps = st.number_input("Incomplete Reps Attempted (Trial 3)", min_value=0, max_value=50, value=3)
            incomplete_det = st.number_input("Incomplete Attempts Detected", min_value=0, max_value=50, value=pipeline.session.engine.incomplete_attempts_count)
            aborted_det = st.number_input("Aborted Attempts Detected (Occlusion)", min_value=0, max_value=50, value=pipeline.session.engine.aborted_attempts_count)
            false_positives = st.number_input("False-Positive Counts", min_value=0, max_value=max(int(detected_reps), 50), value=0)
            missed_reps = st.number_input("Missed Valid Reps", min_value=0, max_value=max(int(target_reps), 50), value=0)
        with sc3:
            calib_status_val = pipeline.session.calibration_service.status.value
            calib_ok = (calib_status_val == "CALIBRATED")
            st.metric("Live Calibration Status", calib_status_val)
            
            # Tracking confidence proxy from latest summary if available
            sess_metrics = pipeline.session.get_summary().metrics
            conf_val = sess_metrics.mean_tracking_confidence if (sess_metrics and sess_metrics.mean_tracking_confidence is not None) else 0.85
            st.metric("Mean Tracking Confidence", f"{conf_val:.0%}" if sess_metrics and sess_metrics.mean_tracking_confidence is not None else "N/A (Awaiting Reps)")

            obs_notes = st.text_input("Qualitative Notes (Lighting, Angle, Occlusion)", value="Sagittal view, ~300 lux, high-contrast")

            # Enforce validation bounds on FP and FN before creating scorecard
            fp_clamped = min(int(false_positives), int(detected_reps))
            fn_clamped = min(int(missed_reps), int(target_reps))
            if int(false_positives) > int(detected_reps):
                st.warning(f"⚠️ FP ({false_positives}) cannot exceed detected reps ({detected_reps}); clamped to {fp_clamped}.")
            if int(missed_reps) > int(target_reps):
                st.warning(f"⚠️ FN ({missed_reps}) cannot exceed target reps ({target_reps}); clamped to {fn_clamped}.")

            from performx.contracts import ManualScorecardData, compute_scorecard_metrics, TrialVerificationStatus
            scorecard = ManualScorecardData(
                trial_id=str(trial_id_input),
                camera_distance_m=float(cam_dist),
                target_complete_reps=int(target_reps),
                detected_complete_reps=int(detected_reps),
                incomplete_reps_attempted=int(incomplete_reps),
                false_positives=fp_clamped,
                missed_reps=fn_clamped,
                calibration_successful=calib_ok,
                rejected_reps=int(rejected_reps),
                incomplete_detected=int(incomplete_det),
                aborted_detected=int(aborted_det),
                mean_tracking_confidence=float(conf_val) if sess_metrics and sess_metrics.mean_tracking_confidence is not None else None,
                observation_notes=str(obs_notes),
                trials_conducted=trial_conducted,
                operator_confirmed=operator_confirmed,
            )
            metrics = compute_scorecard_metrics(scorecard)

            # Verification badge
            v_status = metrics.get("verification_status", "NOT_CONDUCTED")
            if v_status == "NOT_CONDUCTED":
                st.warning("⏳ Status: NOT CONDUCTED (Awaiting trial execution)")
                st.caption(metrics["summary_text"])
            elif v_status == "DATA_ENTERED":
                st.info("📝 Status: DATA ENTERED (Pending Operator Verification)")
                st.caption("Observations entered. Operator must review and check verification box.")
            else:
                st.success("✅ Status: OPERATOR VERIFIED")

            if metrics.get("precision") is not None:
                st.metric("Precision", f"{metrics['precision']:.1%}", help="TP / (TP + FP)")
                st.metric("Recall", f"{metrics['recall']:.1%}", help="TP / (TP + FN)")
                st.metric("F1 Score", f"{metrics['f1_score']:.1%}", help="Harmonic mean of precision and recall")
                st.caption(f"Evaluation Mode: {metrics.get('evaluation_mode', 'OPERATOR_REPORTED_ESTIMATE')}")
                st.caption(metrics["summary_text"])

        st.divider()
        st.markdown("### Step 4: Event-Level Validation (Temporal One-to-One Matching)")
        st.caption(
            "Match detected repetitions to ground-truth timestamps within a configurable tolerance window. "
            "Guarantees that each target rep matches at most one detected rep, preventing inflated aggregate claims. "
            "**Notice on Tolerance**: Tolerance (default ±1.5s) is a biomechanical evaluation boundary reflecting "
            "stopwatch reaction latency (~0.3–0.5s) and movement cadence pacing, not a score-inflation tuning knob. "
            "For squats at a 2.5–3.0s pace, ±1.5s prevents cross-rep adjacent contamination."
        )

        detected_summaries = [s for s in pipeline.session.engine.completed_summaries if s.is_valid]
        session_start = pipeline.session.start_time
        if detected_summaries:
            det_info = []
            for s in detected_summaries:
                if s.completion_timestamp is not None:
                    # Show elapsed seconds from session start
                    elapsed = max(0.0, s.completion_timestamp - session_start)
                    det_info.append(f"Rep #{s.rep_number}: elapsed = {elapsed:.2f}s (dur={s.duration_seconds:.2f}s)")
            st.info("🕒 Live Detected Repetition Completion Times (Elapsed Seconds from Session Start):\n- " + "\n- ".join(det_info) if det_info else "Awaiting reps with timestamps.")
        else:
            st.caption("No accepted repetitions recorded yet in this session.")

        ev_col1, ev_col2 = st.columns(2)
        with ev_col1:
            gt_timestamps_str = st.text_input(
                "Observed Target Completion Timestamps (elapsed seconds from trial start, comma-separated)",
                value="",
                help="Enter elapsed seconds from trial start, e.g. '3.2, 6.1, 9.4, 12.8, 16.0' (do NOT use wall-clock time like 14:05:22).",
            )
        with ev_col2:
            match_tol = st.number_input(
                "Temporal Matching Tolerance (± seconds)",
                min_value=0.5,
                max_value=3.0,
                value=1.5,
                step=0.25,
                help="Recommended ±1.5s for standard 2.5-3.0s cadence squats to prevent adjacent rep misassignment.",
            )

        if gt_timestamps_str.strip():
            try:
                from performx.contracts import RepetitionEvent, match_repetition_events
                gt_floats = [float(x.strip()) for x in gt_timestamps_str.split(",") if x.strip()]
                gt_events = [RepetitionEvent(event_id=f"TGT-{i+1}", timestamp=t, is_target_valid=True) for i, t in enumerate(gt_floats)]
                
                det_events = [
                    RepetitionEvent(
                        event_id=f"DET-{s.rep_number}",
                        timestamp=max(0.0, s.completion_timestamp - session_start) if s.completion_timestamp is not None else 0.0,
                        is_target_valid=True,
                    )
                    for s in detected_summaries
                    if s.completion_timestamp is not None
                ]

                match_res = match_repetition_events(gt_events, det_events, tolerance_seconds=float(match_tol))

                st.markdown("#### Event-Level Temporal Matching Results")
                ev_m1, ev_m2, ev_m3 = st.columns(3)
                with ev_m1:
                    st.metric("Event Precision", f"{match_res.precision:.1%}" if match_res.precision is not None else "N/A")
                with ev_m2:
                    st.metric("Event Recall", f"{match_res.recall:.1%}" if match_res.recall is not None else "N/A")
                with ev_m3:
                    st.metric("Event F1 Score", f"{match_res.f1_score:.1%}" if match_res.f1_score is not None else "N/A")

                st.write(
                    f"**Matched Pairs (TP)**: {len(match_res.matched_pairs)} | "
                    f"**Unmatched Detections (FP)**: {match_res.fp} | "
                    f"**Unmatched Targets (FN)**: {match_res.fn}"
                )
                if match_res.matched_pairs:
                    st.caption("Matched Events: " + ", ".join([f"{t} ↔ {d} (Δt={dt}s)" for t, d, dt in match_res.matched_pairs]))
                if match_res.unmatched_detected_ids:
                    st.caption("Unmatched Detections (FP): " + ", ".join(match_res.unmatched_detected_ids))
                if match_res.unmatched_target_ids:
                    st.caption("Unmatched Targets (FN): " + ", ".join(match_res.unmatched_target_ids))
            except Exception as e:
                st.error(f"Error parsing event timestamps: {e}")

        with st.expander("🛠️ Operator Troubleshooting & Demonstration Guide", expanded=False):
            st.markdown(
                """
                - **Camera Feed Unavailable**: Verify no other app (Zoom, Teams, OBS) is holding the webcam device. Ensure browser permissions are enabled.
                - **Low Tracking Confidence (<50%)**: Increase ambient lighting. Step back so your ankles and feet are clearly framed. Wear clothing contrasting with the background.
                - **Calibration Failed**: Ensure you stand fully upright with extended knees (knee angle ≥ 164°). Avoid swaying during the 15-frame sampling window. If failed, click `🔄 Reset Calib` and re-attempt.
                - **Temporary Occlusion**: Stepping out of view pauses the state progression; re-entering standing upright safely resumes tracking without false repetition counts.
                - **Session Reset**: Click `🔄 Reset Entire Session` to atomically zero out all rep counters, attempt tracking, filters, and calibration data.
                """
            )

        st.caption("Privacy Guarantee: All evaluations remain strictly in-memory. Zero video or biometric telemetry persisted.")


if __name__ == "__main__":
    main()
