from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Production: Use DATABASE_URL from environment (AWS RDS PostgreSQL)
# Development: Fall back to SQLite
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Production PostgreSQL
    # Handle both postgres:// and postgresql:// schemes
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Verify connections before using
        pool_size=10,        # Connection pool size
        max_overflow=20,     # Max connections beyond pool_size
        pool_recycle=3600    # Recycle connections after 1 hour
    )
else:
    # Development SQLite
    db_path = "./inventory.db"
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
