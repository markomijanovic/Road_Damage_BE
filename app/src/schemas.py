from pydantic import BaseModel
import datetime

# Osnovni model sa poljima koja primamo od klijenta
class PotholeCreate(BaseModel):
    class_name: str
    latitude: float
    longitude: float
    confidence: float

# Model koji vraćamo klijentu (ima 'id' i 'detected_at' koje baza generiše)
class Pothole(PotholeCreate):
    id: int
    detected_at: datetime.datetime

    class Config:
        orm_mode = True # Ovo omogućava Pydantic-u da čita podatke iz SQLAlchemy objekata