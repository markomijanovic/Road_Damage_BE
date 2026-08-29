# Road Damage Detection Backend

I built this backend as part of a road-damage and pothole-detection prototype for the Rivian & Volkswagen Group Hackathon, where our team placed second. The goal was to turn video detections and GPS metadata into structured, geolocated road-damage records that the client application could consume.

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

1. Create and activate a Python virtual environment.
2. Install the required Python packages.
3. Set the `ROBOFLOW_API_KEY` environment variable.
4. Start the API:

```bash
uvicorn app.src.main:app --reload
```

The interactive API documentation is available at `/docs` while the service is running.

## Project status

This repository contains the hackathon prototype. Before production use, I would add complete dependency pinning, automated tests, upload validation, job-status tracking, cleanup of generated artifacts, and stricter CORS configuration.
