# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY app ./app
COPY populate_data.py .
COPY create_admin.py .

# Create database directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Set environment variables
ENV DATABASE_URL=sqlite:////app/data/inventory.db
ENV PYTHONUNBUFFERED=1

# Initialize database and run app
CMD python create_admin.py && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
