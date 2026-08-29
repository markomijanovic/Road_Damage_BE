# Road Damage Detection Backend

Backend service for a road-damage and pothole-detection prototype developed for the Rivian & Volkswagen Group Hackathon, where our team placed second.

## Collaboration

This project was developed jointly by **Marko Mijanović** ([@markomijanovic](https://github.com/markomijanovic)) and **Jovan Živanović** ([@Zivanovix](https://github.com/Zivanovix)). This repository is a fork of [Jovan's original repository](https://github.com/Zivanovix/Road_Damage_BE), preserving the original project history and attribution.

## What it does

- Exposes FastAPI endpoints for creating and retrieving detected road damage.
- Accepts video and GPS metadata uploads for background processing.
- Runs configurable Roboflow detection models and tracks detections with ByteTrack.
- Associates detections with latitude, longitude, class, and confidence data.
- Stores pothole records in SQLite through SQLAlchemy.
- Produces annotated output videos for review.

## Tech stack

Python, FastAPI, SQLAlchemy, SQLite, OpenCV, Roboflow Inference, Supervision, ByteTrack and Pydantic.

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

This repository contains the hackathon prototype. Before production use, dependency pinning, automated tests, upload validation, job-status tracking and stricter CORS configuration should be added.
