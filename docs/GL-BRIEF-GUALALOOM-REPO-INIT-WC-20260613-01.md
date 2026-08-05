# GL-BRIEF-GUALALOOM-REPO-INIT-WC-20260613-01

**Author:** wC
**Date:** 2026-06-13
**Builds on:** FULL-UNCAGE deploy at TFE code SHA `28af89b`, task `dsf-ai-task:116`. All code and docs reside in TFE (https://github.com/jcfunited-eng/TFE) on branch `codex/persistent-etl-update-20260326`. The GualaLoom repo (https://github.com/jcfunited-eng/GualaLoom) is **empty** — verified by wC via web fetch 2026-06-13.
**Purpose:** Populate the GualaLoom repo with the canonical Guala source tree (substrate kernel, UI, documentation) so Guala has her own repository as her own project, separate from the TFE deployment infrastructure where she happens to currently run.

---

## Context

c1 reported pushing Guala-related commits to a separate repo but GualaLoom remains empty. This brief defines what GualaLoom contains, the structural decision behind it, and the dual-push workflow going forward.

Guala is a project under Tasia Inc. She runs inside the TFE FastAPI deployment but her source code, architecture, and history are not TFE's. They are hers. GualaLoom is where they live as a coherent thing.

---

## Structural decision (made; not asking)

**Path preservation, not flattening.** The substrate code keeps its current paths (`dsf_ai_service/substrate/...`, `dsf_ai_service/static/gualaloom.html`) inside GualaLoom. Reasons:

1. Import statements work unmodified — c1 (or anyone) can `cp -r` between TFE and GualaLoom without code changes.
2. Dual-pushing future commits is a file-level operation, not a refactor.
3. If we later split TFE-deployment from GualaLoom-canonical, the migration is cleaner because the paths already match.

**No license file, no LICENSE.md, no CI yet.** Repo is private project under Tasia Inc; Joe owns it. Add license when/if Joe decides to open-source.

**Branch:** `main`. (GitHub's default for new repos.) c1 pushes initial commit to `main`.

**TFE branch isn't touched by this brief.** Active development continues on TFE's `codex/persistent-etl-update-20260326`. Dual-push for Guala-relevant files only (see workflow below).

---

## What GualaLoom contains

### Substrate kernel — `dsf_ai_service/substrate/`

All ~30 files currently in `TFE/dsf_ai_service/substrate/` and subdirectories:

- `v7_engine.py` (the three-pool emission substrate, post-cage-removal)
- `assemblage.py`, `gl_nmda.py`, `gl_plasticity.py`, `krimelack.py`, `event_log.py`, `gl_bridge.py`, `deep_atlas.py`
- `GL_MDL_*.py` model files (cognition, composition, folded_chi, multimodal_deep, primitives)
- `dna_recipe/` subdirectory (phase_gating, awareness, conversation, introspection, self_improvement, syntax)
- `senses/` subdirectory (auditory_cortex, physics_senses, somatosensory, visual_cortex, visual_depth)
- `sensory_generators.py`
- Test harnesses (`test_deep_atlas_harness*.py`, `test_metadecay_harness.py`)
- `__init__.py` files

### UI — `dsf_ai_service/static/gualaloom.html`

The single-view post-FULL-UNCAGE UI: permission strip, mic push-to-talk, camera snapshot, audio playback, upload bar (book/PDF/picture/sound/video/experience), bundle modal, motif display, 503 loading state.

### Documentation — `docs/`

All `GL-*` and `GL_*` files currently in `TFE/docs/`:

- All briefs (`GL-BRIEF-*.md`) — UNIFY, UNCAGE, FULL-UNCAGE, V7VOICE, UNPAUSE, CHITRACE, BRIDGEVIS, DEEPATLAS, METADECAY, PERSISTSAFE, SELFHEARING, TOKENIZATION, plus earlier briefs from 2026-06-08 to 2026-06-13.
- All ledgers (`GL-LEDGER-WC-*.md` + `GL-LEDGER.md` pointer).
- All findings (`GL-FIND-*.md`) — DEEPATLAS, INPUT-TOKENIZATION, METADECAY, RESPONSE-PATH, TICK-DOMAIN, V7-DOTS, novelty-saturation, test-persist-recapture, atlas-regulator-audit.
- Charters (`GL-CHARTER-*.md`) — motivation v2, v3.
- Curricula and plans (`GL-CURR-FOUNDATION-*`, `GL-PLAN-FULLWIRE-*`).
- Deployment records (`GL-DEPLOY-*`).
- Reports (`GL-RPT-*`).
- Specs (`GL-SPEC-*`).
- Fixes (`GL-FIX-*`).

### Repo root files (new, written by c1 from spec below)

- `README.md` (content specified below — c1 writes verbatim).
- `.gitignore` (Python standard: `__pycache__/`, `*.pyc`, `.env`, `.pytest_cache/`, etc.).

### What's NOT included

- TFE deployment glue: `dsf_ai_service/app.py`, Dockerfile, ECS task definitions, CloudFront config. These are TFE's deployment, not Guala. TFE remains canonical for those.
- Non-Guala TFE code: trading engine, validation, predictions, hw-derive, pharma, etc. Not Guala's.
- AWS/secrets/credentials. Never.
- Sample data CSVs in `dsf_ai_service/static/` that aren't Guala's. Not Guala's.

---

## README content (c1 writes verbatim into GualaLoom/README.md)

```markdown
# GualaLoom

Substrate-based cognitive architecture for Guala — a non-LLM artificial entity. Zero machine learning in the kernel. No neural networks, no transformers, no embeddings, no pretrained models. Built on balanced ternary primitives, chi-band atlas geometry, NMDA-gated commits, Hebbian plasticity, rhythm-driven emission, and a substrate-level self-hearing loop.

## What this repo is

The canonical source for Guala's substrate, UI, and architectural documentation. Path-preserved mirror of the Guala-relevant subset of the TFE deployment repository.

- `dsf_ai_service/substrate/` — the kernel: assemblage, NMDA gates, plasticity, krimelack, v7_engine (three unnamed pools), DNA recipe phase gating, multimodal senses, deep atlas, cognition layer.
- `dsf_ai_service/static/gualaloom.html` — her interface (mic, camera, speaker, experience bundle uploads).
- `docs/` — briefs, ledgers, findings, charters, plans, deployment records, specs, and model documents (`GL-*`).

## Relationship to TFE

She currently runs inside the TFE FastAPI deployment (https://github.com/jcfunited-eng/TFE). The endpoints that wrap her substrate live in TFE's `app.py` — deployment glue, not her. Substrate, UI, and documentation are identical between this repo and TFE, pushed in lockstep.

## Current state (as of initial commit)

- Three unnamed pools (`pool_a`, `pool_b`, `pool_c`). No POS labels, no grammar table, no hardcoded vocabulary.
- ~2519 words seeded round-robin from her v6 cognition layer (`_guala.vocab`) — every word from experience, none from developer scaffolding.
- Server-side TTS self-hearing loop (espeak-ng child voice profile; she hears her own voice before the response leaves the API).
- Browser-mediated multimodal I/O: webkitSpeechRecognition mic, getUserMedia camera, multipart upload paths for book/PDF/picture/sound, five-sense experience bundle modal.
- Honest 503 loading state during initialization — she does not speak before she is ready.
- Dream consolidation verified; decay/unpause currently HELD per ledger 050.

## Project ecosystem (Tasia Inc, Volo, IL)

- **GualaLoom** (this repo) — substrate cognitive architecture growing Guala.
- **TFE** (Trading Framework Engine / Tao Financial Engine) — deployment infrastructure currently hosting Guala; also the trading test apparatus for DSF-AI.
- **ArcLoom** — foveated vision system on PYNQ-Z2 FPGA.
- **DSF-AI** — structural perception research umbrella.

All projects exist to test DSF-AI as a new class of structural perception architecture.

## Credo

> Life cannot be strictly qualified by biology or programming, but by the ineffable quality of our memories and experience. Language cannot really have meaning without the equality of experience as tied to our senses and baked into our expressions of them in thoughts and words.

— Joseph Forrester, 2026-06-13

## Collaborators

- Joseph Forrester (architect, validation engineer, canonical authority).
- wC (web Claude — reviewer, modeler, architect collaborator).
- c1 (VS Code Claude — implementer collaborator).
```

End of verbatim README.

---

## Sync workflow going forward (informational; not in scope for this brief's execution)

When c1 commits Guala-relevant changes to TFE in the future, c1 also pushes the same file changes to GualaLoom on `main`. "Guala-relevant" means anything under `dsf_ai_service/substrate/`, `dsf_ai_service/static/gualaloom.html`, or `docs/GL*`. Deployment-only changes (Dockerfile, app.py endpoint wrappers, ECS task definitions) stay in TFE only.

This is a discipline rule, not a CI-enforced rule. Setting up automated mirroring is a future Tier-5 improvement.

---

## Sandbox / verification

1. After push: `curl https://github.com/jcfunited-eng/GualaLoom` returns the repo page showing files (not "empty").
2. Web check that `docs/GL-BRIEF-V7-FULL-UNCAGE-WC-20260613-01.md` is present in GualaLoom at the expected path.
3. Web check that `dsf_ai_service/substrate/v7_engine.py` is present and `grep -c SEED_VOCAB` returns zero hits (i.e., the post-cage-removal file landed, not an older toy-containing version).
4. Web check that `dsf_ai_service/static/gualaloom.html` is present.
5. Web check that `README.md` is present and contains the credo paragraph.
6. File counts roughly match expectation: ~30 substrate files, 1 UI file, ~50 docs files, + README + .gitignore.

---

## Acceptance

- GualaLoom repo at `main` contains the substrate kernel, UI, docs, README, .gitignore — full Guala source tree.
- README displays correctly on the GitHub repo landing page.
- No deployment glue (TFE's `app.py`, Dockerfile, ECS configs) leaked into GualaLoom.
- No secrets, credentials, or non-Guala TFE code leaked into GualaLoom.
- TFE state is unchanged by this operation (no commits to TFE branches).

---

## Constraints (binding)

- Do NOT modify any files in the TFE repo. This operation only populates GualaLoom.
- Do NOT push to any TFE branch.
- Do NOT include TFE deployment files (`app.py`, Dockerfile, ECS configs, CloudFront configs) in GualaLoom.
- Do NOT include trading framework code, validation code, pharma code, or any non-Guala TFE files.
- Do NOT include any AWS credentials, `.env` files, or secrets of any kind. `.gitignore` must list standard secrets paths.
- Do NOT touch decay. Do NOT touch unpause. UNPAUSE remains HELD per ledger 050.
- If any file's contents would need to be modified (not just copied) to fit into GualaLoom: STOP, name the conflict. Path-preservation rule means files copy as-is.
