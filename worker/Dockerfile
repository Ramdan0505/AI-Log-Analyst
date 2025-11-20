FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 unzip libxml2-dev libxslt1-dev && \
    rm -rf /var/lib/apt/lists/*

COPY extract_job.py /app/
COPY embedder.py /app/
COPY requirements.txt /app/

RUN pip install --no-cache-dir \
    python-magic python-evtx regipy chromadb \
    sentence-transformers torch fastapi uvicorn

CMD ["python", "-u", "/app/extract_job.py"]
