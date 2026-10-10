"""PERFORMX Manual Scorecard & Calibration Invalidation Regression Tests.

Validates:
1. compute_scorecard_metrics returns status='PENDING' when trials_conducted=False.
2. Accurate calculation of precision, recall, and trial accuracy on real numbers.
3. Proper handling of zero division and edge-case inputs (no reps performed).
4. Rejection of negative numbers in ManualScorecardData.
5. Invalidation of dependent scale metrics when calibration is reset or recalibration fails.
"""

import pytest

from performx.calibration import StandingCalibrationService
from performx.core import CalibrationStatus
from performx.contracts import (
    ManualScorecardData,
    RepetitionEvent,
    compute_scorecard_metrics,
    match_repetition_events,
)
from performx.services import MovementAnalysisSession
from tests.test_calibration import make_calib_landmarks


def test_scorecard_metrics_pending_when_not_conducted():
    scorecard = ManualScorecardData(
        target_complete_reps=5,
        detected_complete_reps=5,
        incomplete_reps_attempted=3,
        false_positives=0,
        missed_reps=0,
        calibration_successful=True,
        trials_conducted=False,  # Still pending
    )
    metrics = compute_scorecard_metrics(scorecard)
    assert metrics["status"] == "PENDING"
    assert metrics["accuracy"] is None
    assert metrics["precision"] is None
    assert metrics["recall"] is None
    assert "pending" in metrics["summary_text"].lower()


def test_scorecard_metrics_completed_trial_perfect_score():
    scorecard = ManualScorecardData(
        target_complete_reps=5,
        detected_complete_reps=5,
        incomplete_reps_attempted=3,
        false_positives=0,
        missed_reps=0,
        calibration_successful=True,
        trials_conducted=True,
    )
    metrics = compute_scorecard_metrics(scorecard)
    assert metrics["status"] == "COMPLETED"
    assert metrics["accuracy"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0


def test_scorecard_metrics_with_errors():
    # 5 targets, detected 5, but 1 was a false positive (half-rep counted) and 1 target was missed
    scorecard = ManualScorecardData(
        target_complete_reps=5,
        detected_complete_reps=5,
        incomplete_reps_attempted=3,
        false_positives=1,
        missed_reps=1,
        calibration_successful=True,
        trials_conducted=True,
    )
    metrics = compute_scorecard_metrics(scorecard)
    assert metrics["status"] == "COMPLETED"
    # True positives = 5 - 1 = 4.
    # Precision = 4 / (4 + 1) = 0.8
    assert pytest.approx(metrics["precision"], abs=1e-3) == 0.8
    # Recall = 4 / 5 = 0.8
    assert pytest.approx(metrics["recall"], abs=1e-3) == 0.8
    # Accuracy = 1.0 - ((1 + 1) / (5 + 3)) = 1.0 - 2/8 = 0.75
    assert pytest.approx(metrics["accuracy"], abs=1e-3) == 0.75


def test_scorecard_rejects_negative_counts():
    with pytest.raises(ValueError):
        ManualScorecardData(
            target_complete_reps=-1,
            detected_complete_reps=5,
            incomplete_reps_attempted=0,
            false_positives=0,
            missed_reps=0,
            calibration_successful=True,
            trials_conducted=True,
        )


def test_recalibration_failure_invalidates_scale_metrics():
    """Verify that if an already calibrated session fails recalibration, scale metrics become unavailable."""
    session = MovementAnalysisSession()

    # Step 1: Calibrate successfully
    for _ in range(15):
        session.calibration_service.add_frame_sample(make_calib_landmarks())
    assert session.calibration_service.status == CalibrationStatus.CALIBRATED

    # Step 2: Attempt recalibration with invalid non-standing pose (e.g. knee flexed 120 deg)
    res = session.calibration_service.add_frame_sample(make_calib_landmarks(knee_angle_deg=120.0))
    assert session.calibration_service.status == CalibrationStatus.FAILED

    # Step 3: Process frame through session -> normalized_hip_depth should be None because calib is invalid
    res_move = session.process_landmarks(make_calib_landmarks(), timestamp=1.0)
    assert res_move.calibration.status == CalibrationStatus.FAILED
    assert res_move.features.normalized_hip_depth is None


def test_scorecard_full_worksheet_breakdown():
    """Verify scorecard accurately captures rejected, incomplete, aborted attempts, F1 score, and notes."""
    scorecard = ManualScorecardData(
        trial_id="TRIAL-EXP-01",
        camera_distance_m=2.4,
        target_complete_reps=5,
        detected_complete_reps=5,
        incomplete_reps_attempted=3,
        false_positives=0,
        missed_reps=0,
        calibration_successful=True,
        rejected_reps=1,
        incomplete_detected=3,
        aborted_detected=1,
        mean_tracking_confidence=0.88,
        observation_notes="Controlled sagittal view under 300 lux lighting.",
        trials_conducted=True,
    )
    metrics = compute_scorecard_metrics(scorecard)
    assert metrics["status"] == "COMPLETED"
    assert metrics["trial_id"] == "TRIAL-EXP-01"
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1_score"] == 1.0
    assert metrics["rejected_reps"] == 1
    assert metrics["incomplete_detected"] == 3
    assert metrics["aborted_detected"] == 1
    assert metrics["confidence"] == 0.88
    assert "Controlled sagittal view" in metrics["notes"]


def test_scorecard_f1_score_with_mixed_errors():
    """Verify precision, recall, and F1 calculations with non-zero errors."""
    scorecard = ManualScorecardData(
        target_complete_reps=10,
        detected_complete_reps=9,
        incomplete_reps_attempted=0,
        false_positives=1,  # TP = min(10, 9-1) = 8
        missed_reps=2,      # FN = 2
        calibration_successful=True,
        trials_conducted=True,
    )
    metrics = compute_scorecard_metrics(scorecard)
    # TP = 8, FP = 1 -> Precision = 8 / 9 = ~0.8888
    # TP = 8, FN = 2 -> Recall = 8 / 10 = 0.8
    # F1 = 2 * (8/9) * 0.8 / (8/9 + 0.8) = 1.4222 / 1.6888 = ~0.8421
    assert pytest.approx(metrics["precision"], abs=1e-3) == 8.0 / 9.0
    assert pytest.approx(metrics["recall"], abs=1e-3) == 0.8
    assert pytest.approx(metrics["f1_score"], abs=1e-3) == (2.0 * (8.0/9.0) * 0.8) / (8.0/9.0 + 0.8)


def test_scorecard_rejects_invalid_camera_distance():
    """Verify non-positive camera distance raises ValueError."""
    with pytest.raises(ValueError):
        ManualScorecardData(
            target_complete_reps=5,
            detected_complete_reps=5,
            incomplete_reps_attempted=0,
            false_positives=0,
            missed_reps=0,
            calibration_successful=True,
            camera_distance_m=-1.0,  # Invalid negative distance
        )


def test_scorecard_rejects_invalid_tracking_confidence():
    """Verify confidence out of [0.0, 1.0] raises ValueError."""
    with pytest.raises(ValueError):
        ManualScorecardData(
            target_complete_reps=5,
            detected_complete_reps=5,
            incomplete_reps_attempted=0,
            false_positives=0,
            missed_reps=0,
            calibration_successful=True,
            mean_tracking_confidence=1.25,  # Invalid > 1.0
        )


def test_scorecard_rejects_fp_exceeding_detected_reps():
    """Verify ValueError when false_positives > detected_complete_reps."""
    with pytest.raises(ValueError, match="false_positives .* cannot exceed detected_complete_reps"):
        ManualScorecardData(
            target_complete_reps=5,
            detected_complete_reps=3,
            incomplete_reps_attempted=0,
            false_positives=4,  # Impossible: detected 3 but claims 4 FP
            missed_reps=0,
            calibration_successful=True,
            trials_conducted=True,
        )


def test_scorecard_rejects_fn_exceeding_target_reps():
    """Verify ValueError when missed_reps > target_complete_reps."""
    with pytest.raises(ValueError, match="missed_reps .* cannot exceed target_complete_reps"):
        ManualScorecardData(
            target_complete_reps=5,
            detected_complete_reps=5,
            incomplete_reps_attempted=0,
            false_positives=0,
            missed_reps=6,  # Impossible: target was 5 but claims 6 FN
            calibration_successful=True,
            trials_conducted=True,
        )


def test_scorecard_zero_targets_and_zero_detections():
    """Verify zero targets and zero detections yields NOT_CONDUCTED / PENDING with None metrics."""
    scorecard = ManualScorecardData(
        target_complete_reps=0,
        detected_complete_reps=0,
        incomplete_reps_attempted=0,
        false_positives=0,
        missed_reps=0,
        calibration_successful=True,
        trials_conducted=True,  # Conducted flag checked, but zero trial activity
    )
    metrics = compute_scorecard_metrics(scorecard)
    assert metrics["status"] == "PENDING"
    assert metrics["verification_status"] == "NOT_CONDUCTED"
    assert metrics["is_verified"] is False
    assert metrics["precision"] is None
    assert metrics["recall"] is None
    assert metrics["f1_score"] is None


def test_scorecard_fp_with_zero_targets():
    """Verify detector hallucinating reps when target was 0 yields 0 Precision, 1.0 Recall, 0 F1."""
    scorecard = ManualScorecardData(
        target_complete_reps=0,
        detected_complete_reps=2,
        incomplete_reps_attempted=0,
        false_positives=2,  # Both detections were false alarms
        missed_reps=0,
        calibration_successful=True,
        trials_conducted=True,
        operator_confirmed=True,
    )
    metrics = compute_scorecard_metrics(scorecard)
    assert metrics["verification_status"] == "OPERATOR_VERIFIED"
    assert metrics["is_verified"] is True
    assert metrics["tp"] == 0
    assert metrics["fp"] == 2
    assert metrics["fn"] == 0
    assert metrics["precision"] == 0.0
    assert metrics["recall"] == 1.0  # target=0, missed=0
    assert metrics["f1_score"] == 0.0


def test_scorecard_missed_reps_with_zero_detections():
    """Verify complete miss (target 5, detected 0, missed 5) yields 0 Precision, 0 Recall, 0 F1."""
    scorecard = ManualScorecardData(
        target_complete_reps=5,
        detected_complete_reps=0,
        incomplete_reps_attempted=0,
        false_positives=0,
        missed_reps=5,
        calibration_successful=True,
        trials_conducted=True,
        operator_confirmed=True,
    )
    metrics = compute_scorecard_metrics(scorecard)
    assert metrics["tp"] == 0
    assert metrics["fp"] == 0
    assert metrics["fn"] == 5
    assert metrics["precision"] == 0.0
    assert metrics["recall"] == 0.0
    assert metrics["f1_score"] == 0.0


def test_scorecard_three_state_verification_lifecycle():
    """Verify distinct states: NOT_CONDUCTED, DATA_ENTERED, and OPERATOR_VERIFIED."""
    # State 1: NOT_CONDUCTED (trials_conducted=False)
    sc_not_conducted = ManualScorecardData(
        target_complete_reps=5,
        detected_complete_reps=5,
        incomplete_reps_attempted=0,
        false_positives=0,
        missed_reps=0,
        calibration_successful=True,
        trials_conducted=False,
        operator_confirmed=False,
    )
    m1 = compute_scorecard_metrics(sc_not_conducted)
    assert m1["verification_status"] == "NOT_CONDUCTED"
    assert m1["is_verified"] is False
    assert m1["precision"] is None

    # State 2: DATA_ENTERED (trials_conducted=True, operator_confirmed=False)
    sc_data_entered = ManualScorecardData(
        target_complete_reps=5,
        detected_complete_reps=5,
        incomplete_reps_attempted=0,
        false_positives=0,
        missed_reps=0,
        calibration_successful=True,
        trials_conducted=True,
        operator_confirmed=False,
    )
    m2 = compute_scorecard_metrics(sc_data_entered)
    assert m2["verification_status"] == "DATA_ENTERED"
    assert m2["is_verified"] is False
    assert m2["precision"] == 1.0

    # State 3: OPERATOR_VERIFIED (trials_conducted=True, operator_confirmed=True)
    sc_verified = ManualScorecardData(
        target_complete_reps=5,
        detected_complete_reps=5,
        incomplete_reps_attempted=0,
        false_positives=0,
        missed_reps=0,
        calibration_successful=True,
        trials_conducted=True,
        operator_confirmed=True,
    )
    m3 = compute_scorecard_metrics(sc_verified)
    assert m3["verification_status"] == "OPERATOR_VERIFIED"
    assert m3["is_verified"] is True
    assert m3["precision"] == 1.0


def test_scorecard_inconsistent_event_count_detection():
    """Verify that discordant event counts (TP + FN != target) flag a consistency warning."""
    # Target 5, detected 5, FP = 0 -> TP = 5. But operator entered missed_reps = 1 (TP + FN = 6 != 5)
    scorecard = ManualScorecardData(
        target_complete_reps=5,
        detected_complete_reps=5,
        incomplete_reps_attempted=0,
        false_positives=0,
        missed_reps=1,
        calibration_successful=True,
        trials_conducted=True,
        operator_confirmed=True,
    )
    metrics = compute_scorecard_metrics(scorecard)
    assert metrics["is_consistent"] is False
    assert metrics["consistency_warning"] is not None
    assert "discrepancy" in metrics["consistency_warning"].lower()


def test_scorecard_metrics_bounded_and_finite():
    """Verify precision, recall, and F1 are strictly within [0.0, 1.0] and finite."""
    for fp, fn, det, tgt in [(0, 0, 5, 5), (5, 0, 5, 5), (0, 5, 0, 5), (2, 2, 4, 4)]:
        sc = ManualScorecardData(
            target_complete_reps=tgt,
            detected_complete_reps=det,
            incomplete_reps_attempted=0,
            false_positives=fp,
            missed_reps=fn,
            calibration_successful=True,
            trials_conducted=True,
            operator_confirmed=True,
        )
        m = compute_scorecard_metrics(sc)
        for key in ["precision", "recall", "f1_score", "protocol_compliance_score"]:
            val = m[key]
            assert val is not None
            assert 0.0 <= val <= 1.0
            import math
            assert math.isfinite(val)


# =========================================================================
# Event-Level Temporal One-to-One Matching Regression Tests (Phase 19)
# =========================================================================

def test_event_matching_perfect_one_to_one():
    """Verify perfect 5-for-5 temporal match within tolerance yields 100% P, R, F1."""
    targets = [RepetitionEvent(event_id=f"TGT-{i}", timestamp=float(i * 3.0)) for i in range(1, 6)]
    # Detections within 0.2s of targets
    detections = [RepetitionEvent(event_id=f"DET-{i}", timestamp=float(i * 3.0 + 0.15)) for i in range(1, 6)]

    res = match_repetition_events(targets, detections, tolerance_seconds=1.5)
    assert res.tp == 5
    assert res.fp == 0
    assert res.fn == 0
    assert res.precision == 1.0
    assert res.recall == 1.0
    assert res.f1_score == 1.0
    assert len(res.matched_pairs) == 5
    assert len(res.unmatched_detected_ids) == 0
    assert len(res.unmatched_target_ids) == 0


def test_event_matching_extra_unmatched_detections_as_fp():
    """Verify extra detections outside of targets count as false positives."""
    targets = [RepetitionEvent(event_id="TGT-1", timestamp=3.0)]
    # Detector recorded 3 events: one true, two spurious noise spikes
    detections = [
        RepetitionEvent(event_id="DET-1", timestamp=3.1),
        RepetitionEvent(event_id="DET-2", timestamp=7.0),
        RepetitionEvent(event_id="DET-3", timestamp=11.0),
    ]

    res = match_repetition_events(targets, detections, tolerance_seconds=1.0)
    assert res.tp == 1
    assert res.fp == 2
    assert res.fn == 0
    assert pytest.approx(res.precision, abs=1e-3) == 1.0 / 3.0
    assert res.recall == 1.0
    assert pytest.approx(res.f1_score, abs=1e-3) == 2.0 * (1/3) * 1.0 / (1/3 + 1.0)
    assert res.unmatched_detected_ids == ["DET-2", "DET-3"]


def test_event_matching_missed_targets_as_fn():
    """Verify target events with no matching detection count as false negatives."""
    targets = [
        RepetitionEvent(event_id="TGT-1", timestamp=3.0),
        RepetitionEvent(event_id="TGT-2", timestamp=6.0),
        RepetitionEvent(event_id="TGT-3", timestamp=9.0),
    ]
    detections = [RepetitionEvent(event_id="DET-1", timestamp=3.1)]

    res = match_repetition_events(targets, detections, tolerance_seconds=1.0)
    assert res.tp == 1
    assert res.fp == 0
    assert res.fn == 2
    assert res.precision == 1.0
    assert pytest.approx(res.recall, abs=1e-3) == 1.0 / 3.0
    assert pytest.approx(res.f1_score, abs=1e-3) == 2.0 * 1.0 * (1/3) / (1.0 + 1/3)
    assert res.unmatched_target_ids == ["TGT-2", "TGT-3"]


def test_event_matching_duplicate_detections_near_single_target():
    """Verify multiple detections near one target event only match once; extra is FP."""
    targets = [RepetitionEvent(event_id="TGT-1", timestamp=5.0)]
    detections = [
        RepetitionEvent(event_id="DET-1", timestamp=4.9),
        RepetitionEvent(event_id="DET-2", timestamp=5.2),
    ]

    res = match_repetition_events(targets, detections, tolerance_seconds=1.0)
    assert res.tp == 1
    assert res.fp == 1
    assert res.fn == 0
    assert res.precision == 0.5
    assert res.recall == 1.0
    assert pytest.approx(res.f1_score, abs=1e-3) == (2 * 0.5 * 1.0) / 1.5
    assert len(res.matched_pairs) == 1
    assert res.matched_pairs[0][0] == "TGT-1"
    assert res.matched_pairs[0][1] == "DET-1"  # DET-1 had dt=0.1, DET-2 had dt=0.2


def test_event_matching_out_of_tolerance_timestamps():
    """Verify events separated beyond tolerance are not matched."""
    targets = [RepetitionEvent(event_id="TGT-1", timestamp=5.0)]
    detections = [RepetitionEvent(event_id="DET-1", timestamp=8.0)]  # 3s difference

    res = match_repetition_events(targets, detections, tolerance_seconds=2.0)
    assert res.tp == 0
    assert res.fp == 1
    assert res.fn == 1
    assert res.precision == 0.0
    assert res.recall == 0.0
    assert res.f1_score == 0.0
    assert len(res.matched_pairs) == 0


def test_event_matching_empty_trials_and_invalid_inputs():
    """Verify behavior on empty lists and invalid tolerance/timestamps."""
    res_empty = match_repetition_events([], [])
    assert res_empty.tp == 0
    assert res_empty.fp == 0
    assert res_empty.fn == 0
    assert res_empty.precision == 1.0
    assert res_empty.recall == 1.0
    assert res_empty.f1_score == 1.0

    with pytest.raises(ValueError):
        match_repetition_events([], [], tolerance_seconds=-1.0)

    with pytest.raises(ValueError):
        match_repetition_events([], [], tolerance_seconds=0.0)

    with pytest.raises(ValueError):
        RepetitionEvent(event_id="TGT-1", timestamp=-5.0)


def test_event_matching_greedy_counterexample_maximum_cardinality():
    """Verify maximum cardinality is achieved where naive greedy matching would match fewer pairs.
    
    Adversarial Counterexample:
    Target A at t=5.0, Target B at t=5.9 (tolerance = 1.0s).
    Detection X at t=5.1, Detection Y at t=4.5.
    
    Distances:
    - Target A (5.0) to Det X (5.1): dt = 0.1s
    - Target A (5.0) to Det Y (4.5): dt = 0.5s
    - Target B (5.9) to Det X (5.1): dt = 0.8s
    - Target B (5.9) to Det Y (4.5): dt = 1.4s (out of tolerance > 1.0s)
    
    Greedy decision:
    - Sorts all pairs by distance: (0.1: A-X), (0.5: A-Y), (0.8: B-X).
    - Greedily takes A-X (dt=0.1).
    - Now Target B cannot match X (already taken) and cannot match Y (out of tolerance).
    - Greedy yields ONLY 1 MATCH: A-X (cardinality 1).
    
    Optimal Maximum-Cardinality Matching:
    - Match A to Y (dt=0.5) and B to X (dt=0.8).
    - Yields 2 MATCHES (cardinality 2, TP=2, FP=0, FN=0).
    """
    targets = [
        RepetitionEvent(event_id="TGT-A", timestamp=5.0),
        RepetitionEvent(event_id="TGT-B", timestamp=5.9),
    ]
    detections = [
        RepetitionEvent(event_id="DET-X", timestamp=5.1),
        RepetitionEvent(event_id="DET-Y", timestamp=4.5),
    ]

    res = match_repetition_events(targets, detections, tolerance_seconds=1.0)
    # The optimal bipartite algorithm MUST find 2 matches, whereas naive greedy finds only 1
    assert res.tp == 2, f"Expected 2 matches (optimal), but got {res.tp} (suboptimal greedy failure)"
    assert res.fp == 0
    assert res.fn == 0
    assert res.precision == 1.0
    assert res.recall == 1.0
    assert res.f1_score == 1.0

    matched_dict = {t: d for t, d, _ in res.matched_pairs}
    assert matched_dict["TGT-A"] == "DET-Y"
    assert matched_dict["TGT-B"] == "DET-X"


def test_event_matching_deterministic_equal_distance_ties():
    """Verify deterministic tie-breaking when two detections are at identical temporal distances."""
    targets = [RepetitionEvent(event_id="TGT-1", timestamp=10.0)]
    detections = [
        RepetitionEvent(event_id="DET-A", timestamp=9.5),  # dt = 0.5
        RepetitionEvent(event_id="DET-B", timestamp=10.5), # dt = 0.5
    ]

    # Running repeatedly must yield identical results
    res1 = match_repetition_events(targets, detections, tolerance_seconds=1.0)
    res2 = match_repetition_events(targets, detections, tolerance_seconds=1.0)

    assert res1.tp == 1
    assert res2.tp == 1
    assert res1.matched_pairs == res2.matched_pairs
    assert res1.unmatched_detected_ids == res2.unmatched_detected_ids
    assert len(res1.unmatched_detected_ids) == 1


def test_event_matching_duplicate_event_ids_rejected():
    """Verify ValueError is raised if duplicate event_id strings are passed in either list."""
    # Duplicate target IDs
    with pytest.raises(ValueError, match="Duplicate event_id detected in ground_truth_events"):
        match_repetition_events(
            [RepetitionEvent(event_id="TGT-1", timestamp=3.0), RepetitionEvent(event_id="TGT-1", timestamp=6.0)],
            [RepetitionEvent(event_id="DET-1", timestamp=3.0)],
        )

    # Duplicate detection IDs
    with pytest.raises(ValueError, match="Duplicate event_id detected in detected_events"):
        match_repetition_events(
            [RepetitionEvent(event_id="TGT-1", timestamp=3.0)],
            [RepetitionEvent(event_id="DET-1", timestamp=3.0), RepetitionEvent(event_id="DET-1", timestamp=6.0)],
        )


def test_event_matching_adjacent_repetition_separation():
    """Verify that at 2.5s cadence, a tolerance of 1.5s cleanly prevents cross-matching adjacent reps."""
    # Target squat sequence at 2.5s intervals: t = 2.5s, 5.0s, 7.5s
    targets = [
        RepetitionEvent(event_id="TGT-1", timestamp=2.5),
        RepetitionEvent(event_id="TGT-2", timestamp=5.0),
        RepetitionEvent(event_id="TGT-3", timestamp=7.5),
    ]
    # Detections: Rep 1 detected on time (2.6s), Rep 2 missed, Rep 3 detected (7.6s)
    detections = [
        RepetitionEvent(event_id="DET-1", timestamp=2.6),
        RepetitionEvent(event_id="DET-3", timestamp=7.6),
    ]

    # With tolerance 1.5s:
    # TGT-2 (at 5.0s) cannot accidentally match DET-1 (dt=2.4s > 1.5s) or DET-3 (dt=2.6s > 1.5s).
    res = match_repetition_events(targets, detections, tolerance_seconds=1.5)
    assert res.tp == 2
    assert res.fp == 0
    assert res.fn == 1  # TGT-2 remains unmatched
    assert res.unmatched_target_ids == ["TGT-2"]
    assert pytest.approx(res.recall, abs=1e-3) == 2.0 / 3.0


def test_event_matching_invalid_scalar_attributes_rejected():
    """Verify non-finite and negative timestamps, empty event IDs, and non-finite tolerances raise ValueError."""
    import math

    with pytest.raises(ValueError):
        RepetitionEvent(event_id="", timestamp=1.0)  # Empty event ID

    with pytest.raises(ValueError):
        RepetitionEvent(event_id="T1", timestamp=float("nan"))  # NaN timestamp

    with pytest.raises(ValueError):
        RepetitionEvent(event_id="T1", timestamp=float("inf"))  # Inf timestamp

    with pytest.raises(ValueError):
        match_repetition_events(
            [RepetitionEvent(event_id="T1", timestamp=1.0)],
            [RepetitionEvent(event_id="D1", timestamp=1.0)],
            tolerance_seconds=float("nan"),
        )


def test_event_matching_metric_balance_invariants():
    """Verify fundamental invariant: TP + FP = len(detected), TP + FN = len(valid_targets)."""
    targets = [
        RepetitionEvent(event_id=f"TGT-{i}", timestamp=float(i * 2.5))
        for i in range(1, 6)
    ]
    # 3 detections: 2 matching, 1 extra outside tolerance
    detections = [
        RepetitionEvent(event_id="DET-1", timestamp=2.6),
        RepetitionEvent(event_id="DET-2", timestamp=5.1),
        RepetitionEvent(event_id="DET-X", timestamp=25.0),
    ]

    res = match_repetition_events(targets, detections, tolerance_seconds=1.5)
    assert res.tp + res.fp == len(detections)
    assert res.tp + res.fn == len(targets)
    assert len(res.matched_pairs) == res.tp
    assert len(res.unmatched_detected_ids) == res.fp
    assert len(res.unmatched_target_ids) == res.fn



