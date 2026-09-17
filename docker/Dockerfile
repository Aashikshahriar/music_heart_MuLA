FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends git ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Torch first, from the CUDA 12.1 wheel index (matches heartlib's torch>=2.4,<2.11 range).
RUN pip install --no-cache-dir torch==2.5.1 torchaudio==2.5.1 torchvision==0.20.1 \
    --extra-index-url https://download.pytorch.org/whl/cu121

COPY heartlib /app/heartlib
RUN pip install --no-cache-dir -e /app/heartlib

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY frontend /app/frontend
COPY assets /app/assets
COPY scripts /app/scripts

WORKDIR /app/backend
ENV PYTHONPATH=/app/backend

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
