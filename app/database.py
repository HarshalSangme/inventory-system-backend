from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Production: Use DATABASE_URL from environment (Supabase PostgreSQL)
# Development: Fall back to SQLite
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Production PostgreSQL (Supabase)
    # Handle both postgres:// and postgresql:// schemes
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # Log connection info (masked password)
    try:
        masked = DATABASE_URL.split("@")
        if len(masked) > 1:
            logger.info(f"Connecting to PostgreSQL: ***@{masked[-1]}")
        else:
            logger.info("Connecting to PostgreSQL (DATABASE_URL set)")
    except Exception:
        logger.info("Connecting to PostgreSQL (DATABASE_URL set)")
    
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Verify connections before using
        pool_size=5,         # Conservative pool size for Supabase free tier
        max_overflow=10,     # Max connections beyond pool_size
        pool_recycle=1800,   # Recycle connections every 30 min
        pool_timeout=30,     # Wait up to 30s for a connection
        echo=False,          # Set to True for SQL debugging
    )
else:
    # Development SQLite
    logger.info("No DATABASE_URL found, using local SQLite database")
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

