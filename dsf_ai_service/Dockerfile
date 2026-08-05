# The build context is produced only by tools/package_guala_release.py from
# deploy/guala_release_manifest.json. It contains no repository-wide tree.
FROM public.ecr.aws/docker/library/python:3.11-slim AS native-builder
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl build-essential && rm -rf /var/lib/apt/lists/*
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
        | sh -s -- -y --profile minimal
ENV PATH="/root/.cargo/bin:${PATH}"
RUN pip install --no-cache-dir maturin
COPY native/guala_core/Cargo.toml \
     native/guala_core/Cargo.lock \
     native/guala_core/pyproject.toml \
     /build/guala_core/
COPY native/guala_core/src/ /build/guala_core/src/
COPY native/guala_core/tests/fixtures/ /build/guala_core/tests/fixtures/
COPY native/guala_core/tests/organism_codec.rs /build/guala_core/tests/organism_codec.rs
RUN cd /build/guala_core && cargo test --locked
RUN cd /build/guala_core && maturin build --release -o /build/dist

FROM public.ecr.aws/docker/library/python:3.11-slim

ARG GIT_SHA=unknown
ARG BUILD_TS=unknown
LABEL org.opencontainers.image.revision="${GIT_SHA}" \
      com.gualaloom.build_ts="${BUILD_TS}"
RUN printf 'git_sha=%s built=%s\n' "${GIT_SHA}" "${BUILD_TS}" > /BUILD_INFO
ENV GIT_SHA=${GIT_SHA}
ENV BUILD_TS=${BUILD_TS}

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    python-multipart \
    numpy \
    pandas \
    cryptography \
    Pillow \
    pillow-heif \
    PyMuPDF \
    boto3 \
    websockets \
    ijson==3.4.0.post0 \
    python-flint==0.9.0
COPY --from=native-builder /build/dist/*.whl /tmp/wheels/
RUN pip install --no-cache-dir /tmp/wheels/*.whl \
    && rm -rf /tmp/wheels

# `runtime/` is not a source-tree wildcard. Its exact file set and hashes are
# sealed in _release/release-receipt.json before CodeBuild starts.
COPY runtime/ /app/

RUN mkdir -p /app/state/dreams

ENV PYTHONPATH=/app
ENV LATERAL_INHIBITION_ENABLED=1

EXPOSE 8080

CMD ["uvicorn", "dsf_ai_service.native_production_app:app", "--host", "0.0.0.0", "--port", "8080"]
