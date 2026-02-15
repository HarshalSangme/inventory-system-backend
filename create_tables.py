# create_tables.py
"""
Standalone script to create all tables in the production database.
Make sure your DATABASE_URL environment variable is set to your PostgreSQL connection string before running this script.
Usage:
    python create_tables.py
"""

import os
from app.database import engine
from app import models

if __name__ == "__main__":
    print("Creating all tables in the database...")
    models.Base.metadata.create_all(bind=engine)
    print("All tables created successfully.")
