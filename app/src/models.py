from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from .database import Base



class Pothole(Base):
    __tablename__ = "potholes" #Ime tabele u bazi

    # Kolone
    id = Column(Integer, primary_key=True, index=True)
    class_name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)

    # Automatski dodaje vreme kada je rupa prijavljena
    detected_at = Column(DateTime(timezone=True), server_default=func.now())

    #frame_image_path = Column(String, nullable=True)