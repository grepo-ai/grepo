# Use Ubuntu 22.04 LTS as base
FROM ubuntu:22.04

# Prevent interactive prompts during package installs
ARG DEBIAN_FRONTEND=noninteractive

# Ensure Python output is sent straight to terminal (no buffering)
ENV PYTHONUNBUFFERED=1

# Install Python 3.10, pip, venv, and clean up apt caches
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    build-essential \
    python3.10 \
    python3.10-venv \
    python3-pip \
    python3-dev \
    && ln -sf /usr/bin/python3.10 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/*

# Download the latest installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh

# Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"


# Set working directory inside the container
WORKDIR /app

# RUN uv venv grepo-main-env
# RUN . .venv/bin/activate

# Copy the rest of your application code
COPY . .

# Install dependencies in venv
RUN pip install pylate ragatouille

RUN pip install -r requirements.txt

# Default command—override as needed
CMD ["uvicorn", "src.server.api:app", "--host", "0.0.0.0", "--port", "8000"]
