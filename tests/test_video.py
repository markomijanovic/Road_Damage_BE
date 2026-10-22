"""Exercise real video IO with inference replaced by a deterministic identity step."""
import importlib
import json
import sys
import types
import cv2
import numpy as np
import pytest


def test_streams_video_with_short_metadata(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, 'inference', types.SimpleNamespace(get_model=lambda **kw: None))
    monkeypatch.setitem(sys.modules, 'supervision', types.SimpleNamespace(ByteTrack=lambda: None))
    sys.modules.pop('app.src.video_processor', None)
    module = importlib.import_module('app.src.video_processor')
    source = str(tmp_path / 'input.mp4')
    writer = cv2.VideoWriter(source, cv2.VideoWriter_fourcc(*'mp4v'), 60, (32, 32))
    assert writer.isOpened()
    for _ in range(5):
        writer.write(np.zeros((32, 32, 3), dtype=np.uint8))
    writer.release()
    metadata = tmp_path / 'metadata.json'
    metadata.write_text(json.dumps({'dynamicMetadata': [{'latitude': 44, 'longitude': 20}]}))
    processor = module.VideoProcessor.__new__(module.VideoProcessor)
    processor.output_dir = str(tmp_path / 'output')
    seen = []
    def frame_step(frame, tracker, detected, position):
        seen.append(position)
        return frame
    processor.process_frame = frame_step
    output = processor.record_processed_video(source, None, 'job', metadata)
    cap = cv2.VideoCapture(output)
    try:
        assert cap.get(cv2.CAP_PROP_FRAME_COUNT) == 5
        assert cap.get(cv2.CAP_PROP_FPS) == pytest.approx(60)
        assert seen == [(44, 20)] * 5
    finally:
        cap.release()
