import sys
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add current directory to path so we can import app
sys.path.append(os.getcwd())

try:
    from app.database import engine
    from app import models
except ImportError as e:
    logger.error(f"Error importing app modules: {e}")
    logger.error("Make sure you are running this script from the 'inventory-system-backend' directory.")
    sys.exit(1)

def init_db():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.warning("DATABASE_URL environment variable is not set. Using default/local database.")
    else:
        # Mask password for logging
        safe_url = db_url.split("@")[-1] if "@" in db_url else "..."
        logger.info(f"Connecting to database at: ...@{safe_url}")

    logger.info("Creating tables...")
    try:
        models.Base.metadata.create_all(bind=engine)
        logger.info("Tables created successfully.")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_db()
