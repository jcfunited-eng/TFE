FROM public.ecr.aws/docker/library/python:3.11-slim AS native-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl \
    && rm -rf /var/lib/apt/lists/*
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
    | sh -s -- -y --profile minimal
ENV PATH="/root/.cargo/bin:${PATH}"
RUN pip install --no-cache-dir maturin
COPY native/guala_core/ /build/guala_core/
RUN cd /build/guala_core && maturin build --release -o /build/dist

FROM public.ecr.aws/docker/library/python:3.11-slim

ARG GIT_SHA=unknown
ARG BUILD_TS=unknown
LABEL org.opencontainers.image.revision="${GIT_SHA}" \
      com.gualaloom.build_ts="${BUILD_TS}" \
      com.gualaloom.runtime="lean-native"
RUN printf 'git_sha=%s built=%s runtime=lean-native\n' \
      "${GIT_SHA}" "${BUILD_TS}" > /BUILD_INFO
ENV GIT_SHA=${GIT_SHA} \
    BUILD_TS=${BUILD_TS} \
    PYTHONPATH=/app \
    GUALA_PAIRED_ROOT=/app/state/paired-current-gen2 \
    GUALA_MAX_WORLD_BYTES=16777216 \
    OPENBLAS_NUM_THREADS=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    RAYON_NUM_THREADS=4

WORKDIR /app
RUN pip install --no-cache-dir \
    fastapi \
    numpy \
    pandas \
    Pillow \
    python-flint==0.9.0 \
    uvicorn
COPY --from=native-builder /build/dist/*.whl /tmp/wheels/
RUN pip install --no-cache-dir /tmp/wheels/*.whl \
    && rm -rf /tmp/wheels

# The reviewed release packager places only the resolved lean import closure
# and exact optical surfaces under runtime/. No repository-wide source tree is
# available to this build.
COPY runtime/ /app/
COPY dsf_ai_service/lean_runtime_manifest.txt /LEAN_RUNTIME_MANIFEST

RUN test ! -e /app/dsf_ai_service/app.py \
    && test ! -e /app/dsf_ai_service/native_production_app.py \
    && test ! -e /app/dsf_ai_service/candidate_release_rehearsal.py \
    && test ! -e /app/dsf_ai_service/cold_restore_probe.py \
    && test "$(find /app/guala_curriculum/cards -type f -name '*.png' | wc -l)" -eq 36

EXPOSE 8080
CMD ["uvicorn", "dsf_ai_service.lean_production_app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--no-access-log"]
