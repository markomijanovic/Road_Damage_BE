from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker


DATABASE_URL = "sqlite:///./pothole.db"

#sql alchemy engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# 3. Kreiramo SessionLocal klasu koja će se koristiti za svaku konekciju

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#4. Osnovna klasa koju ce nasi modeli nasledjivati

Base = declarative_base()
