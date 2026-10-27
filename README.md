# Road Damage Detection Backend

I built this backend as part of a road-damage and pothole-detection prototype for the automotive computer vision hackathon, where our team placed second. The goal was to turn video detections and GPS metadata into structured, geolocated road-damage records that the client application could consume.

## Road video demos

All four videos are shown side by side below. Click a preview to open its full video, or [watch all four synchronized in one MP4](demo/overview/all-four.mp4).

| Input + model | Confidence 0.10 / 0.30 | Confidence 0.10 / 0.50 | IoU 0.30 / 0.70 |
| --- | --- | --- | --- |
| [![Input and model](demo/overview/original.gif)](demo/road-demo.mp4) | [![Confidence 0.10 vs 0.30](demo/overview/confidence30.gif)](demo/parameters/confidence-10-vs-30.mp4) | [![Confidence 0.10 vs 0.50](demo/overview/confidence50.gif)](demo/parameters/confidence-10-vs-50.mp4) | [![IoU 0.30 vs 0.70](demo/overview/iou.gif)](demo/parameters/iou-30-vs-70.mp4) |

The first video compares the input with actual model predictions and ByteTrack IDs. The other videos compare parameter settings on the same road footage. All clips last 15 seconds at 30 FPS. Animated previews show seconds 2–8 at 8 FPS; the combined MP4 synchronizes all four complete videos in one row, retaining their panel labels. Open it at full size to read the labels.

The original team model is **YOLOv8n `hakaton-dataset-f8j4s/1`**. These are qualitative examples, with possible false positives and missed detections, rather than an accuracy benchmark.

[Demo details](demo/README.md) · [Parameter settings, counts and reproduction instructions](demo/parameters/README.md)

## My contribution

I worked as the backend engineer on the prototype. My contribution included:

- Designing backend APIs for creating and retrieving detected road damage.
- Building the data flow for video and GPS metadata uploads.
- Connecting detection results with latitude, longitude, class, and confidence data.
- Persisting detections with FastAPI, SQLAlchemy, and SQLite.
- Integrating the processing pipeline with the client-facing application flow.
- Helping the team turn the individual components into a working hackathon demo.

## Collaboration

I developed the project together with **Jovan Živanović** ([@Zivanovix](https://github.com/Zivanovix)). We collaborated on the end-to-end prototype, integration, and hackathon delivery.

This repository is a fork of [Jovan's original repository](https://github.com/Zivanovix/Road_Damage_BE), so the original project history and attribution remain visible.

## What the prototype does

- Accepts video and GPS metadata uploads for background processing.
- Runs configurable Roboflow detection models and tracks detections with ByteTrack.
- Associates detections with their geographic position and confidence.
- Stores pothole records through SQLAlchemy.
- Exposes FastAPI endpoints for the client application.
- Produces annotated output videos for review.

## Tech stack

Python, FastAPI, SQLAlchemy, SQLite, OpenCV, Roboflow Inference, Supervision, ByteTrack, and Pydantic.

## Running locally

Python 3.12 is used in CI. Create a virtual environment, then:

```bash
pip install -r requirements.txt
uvicorn app.src.main:app --reload
```

The CRUD API and `/docs` work without an inference model. For video processing:

```bash
pip install -r requirements-video.txt
export ROBOFLOW_API_KEY=your_key
uvicorn app.src.main:app --reload
```

The optional inference dependencies use version ranges and are not a locked environment. The hosted backend has been exercised end to end on the road clip linked above; local model execution still needs validation on the target machine.

`POST /upload-video/` accepts multipart `model`, `video_file`, and `metadata`. Supported model aliases are defined in `model_collection` in `app/src/main.py`. Metadata must have this shape:

```json
{"dynamicMetadata": [{"latitude": 44.0, "longitude": 20.0}]}
```

GPS samples are assumed to arrive at 30 samples per second; shorter metadata retains the last known position. This assumption needs timestamp-based alignment for a production pipeline.

Uploads are streamed to generated filenames, limited to 100 MiB for video and 2 MiB for metadata, and removed after processing. A successful request returns HTTP 202 with a `job_id` for log correlation. Annotated videos are streamed to `app/output_videos/` at source FPS instead of accumulating all frames in RAM. Output videos currently require manual retention/cleanup.

`GET /potholes/` supports validated `skip` and `limit` pagination. Set `CORS_ORIGINS` to a comma-separated list of frontend origins; defaults are localhost ports 3000 and 5173. Set `UPLOAD_DIR` to change temporary storage.

## Automated checks

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

The API regression tests cover pagination, ORM serialization, unknown models, invalid metadata, empty/oversized uploads, generated filenames, background-failure cleanup, and short GPS streams. A video IO regression also checks frame count, source FPS, and short metadata using deterministic mocked inference. Tests do not download models or call Roboflow. GitHub Actions runs the same command on Python 3.12.

## Scope and remaining work

This remains an unauthenticated local hackathon prototype. Jobs run in-process: there is no durable queue, job-status endpoint, admission control, or restart recovery. A job ID is a correlation identifier, not a guarantee of successful processing. Real inference and codec compatibility have not been validated by the API tests. Further work includes end-to-end fixtures, durable job state, authentication, atomic batch persistence, and timestamp-based GPS alignment.

## Hosted video inference

When local inference dependencies are unavailable, the same video pipeline can use the Roboflow hosted API:

```bash
pip install -r requirements-hosted.txt
export ROBOFLOW_API_KEY=your_key
export ROBOFLOW_INFERENCE_BACKEND=hosted
uvicorn app.src.main:app --reload
```

Upload the video and GPS metadata through `/docs` → `POST /upload-video/`, choosing `custom`. The API sends each frame to Roboflow; tracking, annotations, video output, GPS association, and database persistence run locally. Hosted requests consume the workspace's inference credits. The default backend remains local. Keep API keys in environment variables and out of Git.
