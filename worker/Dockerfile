FROM python:3.11-slim

# Python environment optimizations
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# -----------------------------------------------------------
# Install system dependencies
# (matching API environment so both containers behave the same)
# -----------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    unzip \
    libxml2-dev \
    libxslt1-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------
# Install Python dependencies first
# -----------------------------------------------------------
COPY worker/requirements.txt /app/requirements.txt

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# -----------------------------------------------------------
# Copy Worker Code
# -----------------------------------------------------------
COPY worker /app/worker

# Make sure data path exists (mounted by docker-compose)
RUN mkdir -p /data

# -----------------------------------------------------------
# Start the worker
# -----------------------------------------------------------
CMD ["sleep", "infinity"]
