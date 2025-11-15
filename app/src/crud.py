from sqlalchemy.orm import Session
from . import models, schemas


# Funkcija za citanje svih rupa

def get_potholes(db: Session):
    return db.query(models.Pothole).all()

# Funkcija za Kreiranje nove rupe
def create_pothole(db: Session, pothole: schemas.PotholeCreate):
    #Kreiramo SQLAlchemy model objekat od Pydantic podataka
    db_pothole = models.Pothole(
        class_name=pothole.class_name,
        latitude=pothole.latitude,
        longitude=pothole.longitude,
        confidence=pothole.confidence
    )

    db.add(db_pothole) # Dodaj u sesiju
    db.commit() # Sacuvaj u bazu
    db.refresh(db_pothole) # Osvezi objekata da dobije ID iz baze
    return db_pothole


