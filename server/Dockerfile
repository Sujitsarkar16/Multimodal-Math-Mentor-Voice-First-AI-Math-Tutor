# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create directory for SQLite database (even if ephemeral)
RUN mkdir -p app/data

# Expose the port that the app runs on
EXPOSE 8000

# Command to run the application
# Using shell form to allow PORT environment variable expansion (Railway uses dynamic ports)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
