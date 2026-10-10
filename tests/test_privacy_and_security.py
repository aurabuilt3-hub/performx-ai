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
