# Use Ubuntu 22.04 LTS as base
FROM ubuntu:22.04

# Prevent interactive prompts during package installs
ARG DEBIAN_FRONTEND=noninteractive

# Ensure Python output is sent straight to terminal (no buffering)
ENV PYTHONUNBUFFERED=1

# Install Python 3.10, pip, venv, and clean up apt caches
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential \
    python3.10 \
    python3.10-venv \
    python3-pip \
    python3-dev \
    && ln -sf /usr/bin/python3.10 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/*

# Set working directory inside the container
WORKDIR /app

# Copy and install Python dependencies (if you have a requirements.txt)
# COPY requirements.txt .
RUN pip install pylate ragatouille
# RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Default command—override as needed
CMD ["python", "main.py"]
