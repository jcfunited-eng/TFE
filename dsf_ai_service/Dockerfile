FROM public.ecr.aws/docker/library/python:3.11-slim

# GL-CMD-HOTFIX-BUNDLE-95 item 4: build identity. Source arrives via
# `git archive HEAD` (no .git dir), so the SHA must be passed in.
ARG GIT_SHA=unknown
ARG BUILD_TS=unknown
LABEL org.opencontainers.image.revision="${GIT_SHA}" \
      com.gualaloom.build_ts="${BUILD_TS}"
RUN printf 'git_sha=%s built=%s\n' "${GIT_SHA}" "${BUILD_TS}" > /BUILD_INFO
# GL-CMD-GROWTH-LIVE-EVE-20260705-202 G1: the ARG above was only ever
# baked into a LABEL and a file nothing at runtime reads -- exposed as
# a real env var so /status can report what SHA is actually running,
# ending "what's deployed" arguments permanently.
ENV GIT_SHA=${GIT_SHA}
ENV BUILD_TS=${BUILD_TS}

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg espeak-ng && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir fastapi uvicorn python-multipart numpy pandas cryptography Pillow pillow-heif PyMuPDF boto3 onnxruntime websockets faster-whisper

# Copy only what the service needs (no TFE trading code)
COPY uf_core/ /app/uf_core/
COPY ses_core/ /app/ses_core/
COPY tools/derive_sppu_weights.py tools/wave_constants.py tools/wave_spillover.py /app/tools/
COPY tools/sensory_curriculum_orchestrator.py tools/curriculum_seed.json /app/tools/
COPY dsf_ai_service/ /app/dsf_ai_service/
COPY dsf_ai_service/corpus/ /app/corpus/
COPY dsf_ai_service/models/ /app/models/
# YOLO model for visual scene recognition (tracked in git for build reproducibility)
COPY yolov8n.onnx /app/yolov8n.onnx

# Pre-download whisper-tiny model at build time so it's available at runtime
# without needing internet access. Baked into the image (~150MB).
RUN python3 -c "from faster_whisper import WhisperModel; WhisperModel('tiny', device='cpu', compute_type='int8'); print('whisper-tiny baked')" 2>&1 || echo "whisper pre-download failed (non-fatal)"

# GualaLoom state dir (persists via ECS volume or recreates on deploy)
RUN mkdir -p /app/state/dreams

ENV PYTHONPATH=/app

# GL-CMD-PRODUCTION-FLAG-FLIP-EVE-20260618-19
# Emission pipeline: dynamics + inhibition + cross-modal + biological noise
ENV EMISSION_DYNAMICS=1
ENV LATERAL_INHIBITION_ENABLED=1
# GL-CMD-BRAIN-FULL-DEPLOY-175 / GL-NOTE-VOICE-WIRING-RULING W3: flipped
# 1->0 this deploy. RICH_SENSORY_INPUT routes _emit_dynamics through
# _rich_sensory_candidates, whose Source A (gualaloom_v5_engine.py
# _rich_sensory_candidates, ~line 2950) queries self.atlas.entries
# directly, keyed on the CALLER's input words -- a second, independent
# non-brain candidate source the ruling's "one mind, one mouth" did not
# intend to leave standing. Observed live, this deploy: a real converse
# turn produced n_candidates=199 (vs an expected <=3 from the brain's
# tapestry.compose()), with rich_sensory=true in the logged event --
# confirmed the atlas-lookup path was dominating her actual reply, not
# the brain. Turning this off restores the plain _grandurun_select_
# candidates(deep_candidates=brain-sourced) path W2 specifies. Not
# deleted -- re-enable only after Source A itself is redesigned to run
# on brain output instead of bypassing it.
# GL-CMD-ENABLE-COGNITION-EVE-20260705-211 RCA / Joe decision 2026-07-06:
# introducing commit 140cfd8 self-tagged [C2 FAIL] -- measured, reproducibly,
# a small perturbation to the emission Hamiltonian that suppresses 1 of 15
# section commits from reaching entropic_flip (i.e. makes settling on one
# winning word ~7% less likely). The commit's own message said "STOP: do
# not tune, bring back to Eve for decision" -- that decision was never
# closed out and this stayed baked ON regardless. The oscillation design
# itself (slow, candidate-subspace-aligned, novelty-modulated) is sound and
# not being rejected on merit -- but sentence-completion is ALREADY failing
# most turns (arcs_fallback dominating over real commits) even without this
# extra headwind, so adding "more variety" before "can finish a sentence at
# all" is the wrong order of operations. Off until the underlying commit
# rate is healthy; revisit then, not deleted.
ENV RICH_SENSORY_INPUT=0
ENV EMISSION_STRUCTURED_NOISE=0
# GL-CMD-EMISSION-COST-SAMPLE-87: dynamics window 40→80 (rider condition MET, cost CLEAN)
ENV EMISSION_DYNAMICS_TICKS=80

# GL-CMD-COGNITION-BUNDLE-EVE-20260619-23
# Hemisphere cognition gates — all OFF by default, Eve+Joe flip after report
ENV HEMI_PR_ENABLED=1
ENV HEMI_EP_ENABLED=1
ENV HEMI_SC_ENABLED=1
ENV HEMI_GP_ENABLED=1

EXPOSE 8080

CMD ["uvicorn", "dsf_ai_service.app:app", "--host", "0.0.0.0", "--port", "8080"]
