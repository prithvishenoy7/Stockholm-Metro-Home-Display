# ============================================================================
# Multi-stage Dockerfile for Train Departure API
# ============================================================================
# DOCKER CONCEPT: This file defines HOW to build a container image
# Think of it as a recipe: each instruction is a step
# The result is an IMAGE that can be run as a CONTAINER

# ============================================================================
# Stage 1: Base Image Selection
# ============================================================================
# CONCEPT: We start from a base image - someone else's pre-built environment
# python:3.11-slim is official Python image, "slim" = smaller size (security benefit)
FROM python:3.11-slim

# METADATA: Labels help organize and document images
# CONCEPT: Like tags or properties on the image
LABEL maintainer="prithvishenoy7@gmail.com"
LABEL description="Train departure API for ESP32 LED display"
LABEL version="1.0.0"

# ============================================================================
# Stage 2: System Setup
# ============================================================================

# SECURITY: Don't run as root user inside container
# CONCEPT: Principle of least privilege - run with minimal permissions needed
# Create a non-root user called "appuser"
RUN groupadd -r appuser && useradd -r -g appuser appuser

# DOCKER CONCEPT: Set working directory inside container
# All subsequent commands run from this directory
WORKDIR /app

# ============================================================================
# Stage 3: Dependency Installation
# ============================================================================

# DOCKER OPTIMIZATION: Copy requirements first, before code
# WHY? Docker caches layers. If code changes but dependencies don't,
# Docker reuses the cached dependency layer = faster builds!
COPY requirements.txt .

# Install Python dependencies
# --no-cache-dir: Don't store pip cache (smaller image size)
# CONCEPT: Every RUN command creates a new layer in the image
RUN pip install --no-cache-dir -r requirements.txt

# ============================================================================
# Stage 4: Application Code
# ============================================================================

# Copy application code into container
# CONCEPT: This copies from your local machine INTO the image
COPY app.py .

# SECURITY: Change ownership of files to non-root user
RUN chown -R appuser:appuser /app

# SECURITY: Switch to non-root user for running the application
# Everything after this runs as "appuser", not root
USER appuser

# ============================================================================
# Stage 5: Container Configuration
# ============================================================================

# NETWORKING: Expose port 5000 (Flask default)
# CONCEPT: This is documentation - tells users which port the app uses
# NOTE: This doesn't actually publish the port, just documents it
EXPOSE 5000

# DOCKER CONCEPT: Environment variables with default values
# These can be overridden when running the container
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

# HEALTH CHECK: Docker can automatically test if container is healthy
# CONCEPT: Every 30s, Docker runs this command. If it fails, container is "unhealthy"
# USEFUL: Orchestrators like Kubernetes can restart unhealthy containers
# NOTE: This checks port 5000 INSIDE the container, not the host port (5001)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health')"

# ============================================================================
# Stage 6: Startup Command
# ============================================================================

# DOCKER CONCEPT: CMD defines what runs when container starts
# This is the "entrypoint" - the main process
# When this process stops, the container stops
CMD ["python", "app.py"]

# ============================================================================
# DOCKERFILE BEST PRACTICES USED HERE:
# ============================================================================
# ✅ Use official base images (python:3.11-slim)
# ✅ Run as non-root user (security)
# ✅ Copy dependencies before code (build optimization)
# ✅ Use .dockerignore to exclude unnecessary files
# ✅ Include health checks
# ✅ Use EXPOSE to document ports
# ✅ Keep images small (slim base, --no-cache-dir)
# ✅ Add labels for documentation
# ============================================================================