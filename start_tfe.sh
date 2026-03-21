#!/usr/bin/env bash
set -euo pipefail

# Production-safe Streamlit startup for AWS environments.
python -m streamlit run app.py \
  --server.address 0.0.0.0 \
  --server.port "${PORT:-8501}" \
  --server.headless true
