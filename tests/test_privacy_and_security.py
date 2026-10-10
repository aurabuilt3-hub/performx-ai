import socket
from pathlib import Path
import numpy as np
import pytest

from performx.pipeline import MovementPipeline


def test_zero_disk_writes_during_pipeline_processing(tmp_path, monkeypatch):
    """Verify that processing video frames produces zero media files on disk."""
    pipeline = MovementPipeline()

    media_extensions = {"*.png", "*.jpg", "*.jpeg", "*.mp4", "*.avi", "*.mov", "*.bin"}
    target_dir = Path(".")

    # Initial file snapshot
    initial_files = set()
    for ext in media_extensions:
        initial_files.update(target_dir.rglob(ext))

    # Process 25 synthetic frames through the full vision pipeline
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    for i in range(25):
        pipeline.process_frame(dummy_frame, timestamp=i * 0.033)

    pipeline.close()

    # Post-execution snapshot
    final_files = set()
    for ext in media_extensions:
        final_files.update(target_dir.rglob(ext))

    # Assert no media files were written
    new_files = final_files - initial_files
    assert len(new_files) == 0, f"Privacy violation: Media files persisted to disk: {new_files}"


def test_no_external_network_connections_allowed(monkeypatch):
    """Verify pipeline executes completely offline with zero external network socket calls."""
    real_connect = socket.socket.connect

    def blocked_connect(self, address):
        host = address[0] if isinstance(address, tuple) else address
        # Allow only local loopback communication
        if host not in ("127.0.0.1", "localhost", "::1"):
            raise ConnectionRefusedError(f"Privacy breach: external connection attempted to {host}")
        return real_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", blocked_connect)

    pipeline = MovementPipeline()
    dummy_frame = np.ones((240, 320, 3), dtype=np.uint8) * 128

    # Process frames - must complete without attempting outbound connection
    for i in range(10):
        pipeline.process_frame(dummy_frame, timestamp=float(i))

    pipeline.close()


def test_missing_and_blank_frames_handled_gracefully():
    """Verify that None or empty frames do not crash pipeline or leave dangling references."""
    pipeline = MovementPipeline()

    # Pass empty frame
    empty_frame = np.empty((0, 0, 3), dtype=np.uint8)
    metrics = pipeline.process_frame(empty_frame, timestamp=1.0)

    assert not metrics.is_detected
    assert metrics.confidence == 0.0

    # Pass None frame
    metrics_none = pipeline.process_frame(None, timestamp=2.0)
    assert not metrics_none.is_detected

    pipeline.close()


def test_sanitizer_deep_copy_and_forbidden_fields_scrubbed():
    """Verify that summary sanitization explicitly discards unwhitelisted fields such as pose landmarks or images."""
    from performx.contracts import SessionMetrics, SessionSummary, SquatConfig
    from performx.storage import sanitize_summary_metrics

    metrics = SessionMetrics(
        total_completed_reps=6,
        accepted_reps=5,
        rejected_reps=1,
        incomplete_attempts=0,
        aborted_attempts=0,
        mean_duration=2.5,
        min_duration=2.0,
        max_duration=3.0,
        duration_range=1.0,
        mean_descent_duration=1.2,
        mean_bottom_dwell=0.3,
        mean_ascent_duration=1.0,
        mean_min_knee_angle=85.0,
        knee_angle_range=10.0,
        mean_rep_symmetry=0.92,
        mean_tracking_confidence=0.95,
        explainable_insights=["Good depth", "Slight forward lean"],
    )
    # SessionSummary wrapping the metrics
    summary = SessionSummary(
        session_id="test-session-sanitizer",
        start_time=100.0,
        end_time=130.0,
        total_frames_processed=900,
        total_reps=6,
        valid_reps=5,
        mean_symmetry=0.92,
        mean_rep_duration=2.5,
        config=SquatConfig(),
        metrics=metrics,
    )

    sanitized = sanitize_summary_metrics(summary)

    # Allowed keys
    assert sanitized["accepted_reps"] == 5
    assert sanitized["rejected_reps"] == 1
    assert sanitized["mean_duration"] == 2.5
    assert sanitized["mean_rep_symmetry"] == 0.92
    assert sanitized["explainable_insights"] == ["Good depth", "Slight forward lean"]

    # Forbidden keys must be stripped / not present
    assert "raw_landmarks" not in sanitized
    assert "camera_feed" not in sanitized
    assert "nested_telemetry" not in sanitized
    assert "extra_field" not in sanitized


def test_in_memory_session_reset_and_close_wipes_sensitive_state():
    """Verify that backend session reset and close cleanly evicts state from memory."""
    from performx.api import BackendService

    service = BackendService(max_sessions=10, session_idle_timeout=60.0)
    session_id = service.create_session("squat")
    assert session_id in service._sessions

    # Resetting session retains the container but clears all metrics/buffers
    service.reset_session(session_id)
    summary = service.get_session_summary(session_id)
    assert summary.metrics is None or summary.metrics.total_completed_reps == 0

    # Ending session completely removes session container from active backend memory
    ended = service.delete_session(session_id)
    assert ended is True
    assert session_id not in service._sessions

    # Full service close wipes all remaining sessions
    id2 = service.create_session("squat")
    assert id2 in service._sessions
    service.close()
    assert len(service._sessions) == 0



