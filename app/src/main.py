from typing import Union, List
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uuid
from uuid import UUID
import os


from app.src.video_processor import VideoProcessor
from . import crud, models, schemas 
from .database import SessionLocal, engine
#from .video_processor import *



# OVA LINIJA KREIRA TABELE U 'pothole.db' FAJLU ako ne postoje
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Pothole Detection API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


model_collection = {
    "pothole_detection" : "pothole-detection-i00zy/2",
    "road_damage_detection" : "road-damages-detection-mi2na/1",
    "road_damage" : "road-damage-ww8ex/1"
}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Endpoint za Kreiranje nove rupe
@app.post("/potholes/", response_model=schemas.Pothole)
def api_create_pothole(pothole: schemas.PotholeCreate, db: Session = Depends(get_db)):
    return crud.create_pothole(db=db, pothole=pothole)


# Endpoint za citanje svih rupa
@app.get("/potholes/", response_model=List[schemas.Pothole])
def api_get_potholes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    potholes = crud.get_potholes(db)
    return potholes

@app.get("/")
def read_root():
    return {"status": "Pothole API is running!"}



# --- Novi endpoint za UPLOAD ---
@app.post("/upload-video/")
def api_upload_video(background_tasks: BackgroundTasks, model: str = Form(...), video_file: UploadFile = File(...), metadata: UploadFile = File(...)):
    job_id = uuid.uuid4()
    upload_dir = "../uploads"
    
    # Kreiraj folder ako ne postoji
    os.makedirs(upload_dir, exist_ok=True)
    
    temp_file_path = f"{upload_dir}/{job_id}_{video_file.filename}"
    metadata_file_path = f"{upload_dir}/{job_id}_{metadata.filename}"

    with open(temp_file_path, "wb") as f:
        f.write(video_file.file.read())

    with open(metadata_file_path, "wb") as f:
        f.write(metadata.file.read())

    background_tasks.add_task(
        process_video_analysis, 
        temp_file_path, 
        job_id, 
        model,
        metadata_file_path,
        
    )

    return {"message": "Video primljen, obrada počinje u pozadini."}




# --- Ovo je tvoj spori, teški posao ---
def process_video_analysis(video_path: str, job_id: UUID, model: str, metadata_file_path: str):
    print(f"POZADINSKI POSAO: Počinjem obradu {video_path}")

    db = SessionLocal()
    processor = VideoProcessor(model_id=model_collection[model])

    processor.record_processed_video(video_path, db, job_id, metadata_file_path)
    
    print("Obrada završena.")
    
    # 5. Očisti fajl (opciono)
    # os.remove(video_path)