FROM public.ecr.aws/docker/library/python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg espeak-ng && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir fastapi uvicorn python-multipart numpy pandas cryptography Pillow pillow-heif PyMuPDF boto3

# Copy only what the service needs (no TFE trading code)
COPY uf_core/ /app/uf_core/
COPY ses_core/ /app/ses_core/
COPY tools/derive_sppu_weights.py /app/tools/
COPY dsf_ai_service/ /app/dsf_ai_service/
COPY dsf_ai_service/corpus/ /app/corpus/

# GualaLoom state dir (persists via ECS volume or recreates on deploy)
RUN mkdir -p /app/state/dreams

ENV PYTHONPATH=/app

EXPOSE 8080

CMD ["uvicorn", "dsf_ai_service.app:app", "--host", "0.0.0.0", "--port", "8080"]
