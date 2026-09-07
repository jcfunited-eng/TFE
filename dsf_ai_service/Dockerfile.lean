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


FROM public.ecr.aws/docker/library/python:3.11-slim AS source-allowlist

WORKDIR /source
COPY dsf_ai_service/ /source/dsf_ai_service/
COPY guala_curriculum/cards/ /source/guala_curriculum/cards/
COPY uf_core/ /source/uf_core/
RUN mkdir /allowlisted \
    && while IFS= read -r path; do \
         test -n "$path" \
         && test -f "/source/$path" \
         && cp --parents "/source/$path" /allowlisted; \
       done < /source/dsf_ai_service/lean_runtime_manifest.txt \
    && test "$(find /allowlisted/source -type f | wc -l)" -eq 98


FROM public.ecr.aws/docker/library/python:3.11-slim AS runtime-base

ARG GIT_SHA=unknown
ARG BUILD_TS=unknown
LABEL org.opencontainers.image.revision="${GIT_SHA}" \
      com.gualaloom.build_ts="${BUILD_TS}" \
      com.gualaloom.runtime="lean-five-route"

RUN printf 'git_sha=%s built=%s runtime=lean-five-route\n' \
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
COPY --from=source-allowlist /allowlisted/source/ /app/
COPY dsf_ai_service/lean_runtime_manifest.txt /LEAN_RUNTIME_MANIFEST

RUN test ! -e /app/dsf_ai_service/app.py \
    && test ! -e /app/dsf_ai_service/native_production_app.py \
    && test "$(find /app/dsf_ai_service /app/uf_core -type f -name '*.py' | wc -l)" -eq 62 \
    && test "$(find /app/guala_curriculum/cards -type f -name '*.png' | wc -l)" -eq 36

EXPOSE 8080

CMD ["uvicorn", "dsf_ai_service.lean_production_app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--no-access-log"]


FROM runtime-base AS migration

COPY tools/migrate_guala_paired_v1_to_v2.py /app/tools/migrate_guala_paired_v1_to_v2.py
ENTRYPOINT ["python", "/app/tools/migrate_guala_paired_v1_to_v2.py"]
CMD []


FROM runtime-base AS runtime
