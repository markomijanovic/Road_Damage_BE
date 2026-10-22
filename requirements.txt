"""Local hackathon API; video jobs run in-process and are not durable."""
from pathlib import Path
from typing import List
from uuid import uuid4
import logging
import os
import shutil

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from . import crud, models, schemas
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)
app = FastAPI(title="Pothole Detection API")
app.add_middleware(CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(","),
    allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
model_collection = {
    "pothole_detection": "pothole-detection-i00zy/2",
    "road_damage_detection": "road-damages-detection-mi2na/1",
    "road_damage": "road-damage-ww8ex/1", "custom": "hakaton-dataset-f8j4s/1"}
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
MAX_VIDEO_BYTES = 100 * 1024 * 1024
MAX_METADATA_BYTES = 2 * 1024 * 1024
logger = logging.getLogger(__name__)


def get_db():
    with SessionLocal() as db:
        yield db


@app.post("/potholes/", response_model=schemas.Pothole)
def api_create_pothole(pothole: schemas.PotholeCreate, db: Session = Depends(get_db)):
    return crud.create_pothole(db, pothole)


@app.get("/potholes/", response_model=List[schemas.Pothole])
def api_get_potholes(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000), db: Session = Depends(get_db)):
    return crud.get_potholes(db, skip=skip, limit=limit)


@app.get("/")
def read_root():
    return {"status": "Pothole API is running!"}


def save_upload(upload: UploadFile, destination: Path, maximum: int):
    total = 0
    with destination.open("wb") as target:
        while chunk := upload.file.read(1024 * 1024):
            total += len(chunk)
            if total > maximum:
                raise HTTPException(413, "Upload exceeds the size limit")
            target.write(chunk)
    if not total:
        raise HTTPException(400, "Empty upload")


@app.post("/upload-video/", status_code=202)
def api_upload_video(background_tasks: BackgroundTasks, model: str = Form(...),
                     video_file: UploadFile = File(...), metadata: UploadFile = File(...)):
    if model not in model_collection:
        raise HTTPException(422, "Unknown detection model")
    job_id = str(uuid4())
    directory = UPLOAD_DIR / job_id
    directory.mkdir(parents=True)
    video_path, metadata_path = directory / "video.mp4", directory / "metadata.json"
    try:
        save_upload(video_file, video_path, MAX_VIDEO_BYTES)
        save_upload(metadata, metadata_path, MAX_METADATA_BYTES)
        from .metadata import read_positions
        read_positions(metadata_path)
    except Exception:
        shutil.rmtree(directory, ignore_errors=True)
        raise
    finally:
        video_file.file.close()
        metadata.file.close()
    background_tasks.add_task(process_video_analysis, video_path, job_id, model, metadata_path)
    return {"message": "Video accepted for background processing", "job_id": job_id}


def process_video_analysis(video_path, job_id, model, metadata_file_path):
    try:
        # Keep the API and its tests usable without loading an inference model.
        from .video_processor import VideoProcessor
        with SessionLocal() as db:
            processor = VideoProcessor(model_id=model_collection[model])
            processor.record_processed_video(str(video_path), db, job_id, metadata_file_path)
    except Exception:
        logger.exception("Video job %s failed", job_id)
    finally:
        shutil.rmtree(Path(video_path).parent, ignore_errors=True)
