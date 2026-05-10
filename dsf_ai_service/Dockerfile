FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn python-multipart numpy pandas

# Copy only what the service needs (no TFE trading code)
COPY uf_core/ /app/uf_core/
COPY tools/derive_sppu_weights.py /app/tools/
COPY dsf_ai_service/ /app/dsf_ai_service/

ENV PYTHONPATH=/app

EXPOSE 8080

CMD ["uvicorn", "dsf_ai_service.app:app", "--host", "0.0.0.0", "--port", "8080"]
