FROM python:3.11-slim

# Prevent Python from writing .pyc files and force unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# -------------------------------------------------------------------------
# Install system dependencies needed for DFIR parsing and libraries
# -------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    unzip \
    libxml2-dev \
    libxslt1-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# -------------------------------------------------------------------------
# Install Python dependencies (done first for caching optimization)
# -------------------------------------------------------------------------
COPY api/requirements.txt /app/requirements.txt

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# -------------------------------------------------------------------------
# Copy API application code
# -------------------------------------------------------------------------
COPY api /app/api
COPY static /app/static

# Ensure artifact directory exists
RUN mkdir -p /data/artifacts

# -------------------------------------------------------------------------
# Expose FastAPI port and run the server
# -------------------------------------------------------------------------
EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
