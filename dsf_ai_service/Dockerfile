FROM public.ecr.aws/docker/library/python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg espeak-ng && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir fastapi uvicorn python-multipart numpy pandas cryptography Pillow pillow-heif PyMuPDF boto3 onnxruntime websockets faster-whisper

# Copy only what the service needs (no TFE trading code)
COPY uf_core/ /app/uf_core/
COPY ses_core/ /app/ses_core/
COPY tools/derive_sppu_weights.py /app/tools/
COPY dsf_ai_service/ /app/dsf_ai_service/
COPY dsf_ai_service/corpus/ /app/corpus/
COPY dsf_ai_service/models/ /app/models/

# GualaLoom state dir (persists via ECS volume or recreates on deploy)
RUN mkdir -p /app/state/dreams

ENV PYTHONPATH=/app

# GL-CMD-PRODUCTION-FLAG-FLIP-EVE-20260618-19
# Emission pipeline: dynamics + inhibition + cross-modal + biological noise
ENV EMISSION_DYNAMICS=1
ENV LATERAL_INHIBITION_ENABLED=1
ENV RICH_SENSORY_INPUT=1
ENV EMISSION_STRUCTURED_NOISE=1

EXPOSE 8080

CMD ["uvicorn", "dsf_ai_service.app:app", "--host", "0.0.0.0", "--port", "8080"]
