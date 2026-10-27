"""Compare real hosted predictions with the application's annotation/tracking code.

Run from the repository root with ROBOFLOW_API_KEY set. Cache contains real API
responses; confidence variants filter the same post-NMS predictions. Each IoU
value is queried separately. Every variant uses an independent ByteTrack instance.
"""
import argparse
import concurrent.futures
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

import cv2
import numpy as np
import supervision as sv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.src.hosted_inference import HostedModel
from app.src.video_processor import VideoProcessor

MODEL = "hakaton-dataset-f8j4s/1"
VARIANTS = {
    "conf10": (0.10, 0.50), "conf30": (0.30, 0.50),
    "conf50": (0.50, 0.50), "iou30": (0.10, 0.30),
    "iou70": (0.10, 0.70),
}
PAIRS = [
    ("confidence-10-vs-30", "conf10", "conf30", "CONFIDENCE 0.10 vs 0.30 | IoU 0.50"),
    ("confidence-10-vs-50", "conf10", "conf50", "CONFIDENCE 0.10 vs 0.50 | IoU 0.50"),
    ("iou-30-vs-70", "iou30", "iou70", "IoU 0.30 vs 0.70 | CONFIDENCE 0.10"),
]


class CachedPredictions:
    def __init__(self, responses, confidence):
        self.responses = iter(responses)
        self.confidence = confidence
        self.predictions = 0

    def infer(self, frame, **kwargs):
        response = dict(next(self.responses))
        response["predictions"] = [p for p in response["predictions"] if p["confidence"] >= self.confidence]
        self.predictions += len(response["predictions"])
        return [response]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("demo/parameters"))
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(args.video.read_bytes()).hexdigest()
    cap = cv2.VideoCapture(str(args.video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        ok, encoded = cv2.imencode(".jpg", frame)
        if not ok:
            raise RuntimeError("Cannot encode source frame")
        frames.append(encoded.tobytes())
    cap.release()
    if not frames or fps <= 0:
        raise ValueError("Invalid input video")
    cache_root = args.cache / digest
    cache_root.mkdir(parents=True, exist_ok=True)
    local = threading.local()

    def fetch(task):
        index, iou = task
        path = cache_root / f"iou{iou:.2f}-frame{index:05d}.json"
        if not path.exists():
            if not hasattr(local, "model"):
                local.model = HostedModel(MODEL, os.environ["ROBOFLOW_API_KEY"])
            frame = cv2.imdecode(np.frombuffer(frames[index], dtype=np.uint8), cv2.IMREAD_COLOR)
            response = local.model.infer(frame, confidence=0.10, iou_threshold=iou)[0]
            path.write_text(json.dumps(response))
        return index, iou, json.loads(path.read_text())

    tasks = [(i, iou) for iou in [0.30, 0.50, 0.70] for i in range(len(frames))]
    responses = {iou: [None] * len(frames) for iou in [0.30, 0.50, 0.70]}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(fetch, task) for task in tasks]
        for completed, future in enumerate(concurrent.futures.as_completed(futures), 1):
            index, iou, result = future.result()
            responses[iou][index] = result
            if completed % 90 == 0:
                print(f"API/cache responses: {completed}/{len(tasks)}", flush=True)

    processors, trackers, detected = {}, {}, {}
    for name, (confidence, iou) in VARIANTS.items():
        # Replay verified API responses through the actual app's process_frame.
        processor = VideoProcessor.__new__(VideoProcessor)
        processor.confidence, processor.iou_threshold = confidence, iou
        processor.model = CachedPredictions(responses[iou], confidence)
        processors[name] = processor
        trackers[name] = sv.ByteTrack(frame_rate=round(fps))
        detected[name] = {}
    writers = {}
    for name, *_ in PAIRS:
        path = cache_root / f"{name}-intermediate.mp4"
        writers[name] = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (1440, 640))
        if not writers[name].isOpened():
            raise RuntimeError("Cannot create comparison video")
    try:
        for index, encoded in enumerate(frames):
            frame = cv2.imdecode(np.frombuffer(encoded, dtype=np.uint8), cv2.IMREAD_COLOR)
            annotated = {name: processor.process_frame(frame, trackers[name], detected[name], (0, 0))
                         for name, processor in processors.items()}
            for name, left, right, title in PAIRS:
                canvas = np.full((640, 1440, 3), (22, 17, 13), dtype=np.uint8)
                cv2.putText(canvas, title, (24, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (235, 240, 245), 2, cv2.LINE_AA)
                for x, variant in [(24, left), (728, right)]:
                    confidence, iou = VARIANTS[variant]
                    label = f"CONF {confidence:.2f} | IoU {iou:.2f} | ByteTrack"
                    cv2.putText(canvas, label, (x, 78), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (140, 225, 130), 1, cv2.LINE_AA)
                    canvas[94:582, x:x + 688] = cv2.resize(annotated[variant], (688, 488))
                cv2.putText(canvas, f"YOLOv8n | {MODEL} | SAME FRAME {index + 1}/{len(frames)} | {fps:g} FPS",
                            (24, 614), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (170, 180, 190), 1, cv2.LINE_AA)
                writers[name].write(canvas)
                if index == 150:
                    cv2.imwrite(str(args.output / f"{name}.jpg"), canvas)
    finally:
        for writer in writers.values():
            writer.release()
    for name, *_ in PAIRS:
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(cache_root / f"{name}-intermediate.mp4"),
                        "-c:v", "libx264", "-preset", "fast", "-crf", "22", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                        str(args.output / f"{name}.mp4")], check=True)
    summary = {"model": MODEL, "input_sha256": digest, "frames": len(frames), "fps": fps,
               "duration_seconds": len(frames) / fps, "inference": "Actual hosted API responses, separately queried for each IoU. Confidence filters replay the same post-NMS responses through VideoProcessor.process_frame.",
               "supervision_version": sv.__version__, "opencv_version": cv2.__version__,
               "tracking": "Independent default Supervision ByteTrack per variant. Tracker IDs are not matched across panels. No database or GPS persistence in this parameter comparison.",
               "variants": {}}
    for name, (confidence, iou) in VARIANTS.items():
        summary["variants"][name] = {"confidence": confidence, "iou_threshold": iou,
            "raw_prediction_instances": processors[name].model.predictions,
            "unique_tracker_ids": len(detected[name]),
            "final_track_classes": dict(Counter(d["class_name"] for d in detected[name].values()))}
    (args.output / "results.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
