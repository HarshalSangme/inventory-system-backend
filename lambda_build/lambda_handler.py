"""
AWS Lambda handler for FastAPI application.
This wraps the FastAPI app for serverless execution on AWS Lambda.
"""

import sys
import os
from pathlib import Path

# Add app directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.main import app
from mangum import Mangum

# Wrap FastAPI app with Mangum for Lambda
handler = Mangum(app, lifespan="off")
