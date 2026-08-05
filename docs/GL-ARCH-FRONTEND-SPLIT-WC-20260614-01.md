# GL-ARCH-FRONTEND-SPLIT-WC-20260614-01

Splits the substrate (_guala) into its own OS process. Frontend (FastAPI, page, ALB health) stays as a thin proxy. Communication via Unix socket on a shared task-local volume.

## Why

Pileon-v3 (5 min real load) showed /ready p95=2.5s, /v7/state p95=3.9s, /quiet p50=4.3s. One process serves ALB health, page polling, sensory decode, and substrate. Worker threads serialize on GIL. Phase 2 fixed event-loop blocking but cannot fix GIL contention. The one-task model is the wall.

## Target

Two containers in one ECS task. Shared task-local volume /shared/.

Frontend: gualaloom.html + /api/v1/gualaloom + /v7/* + /admin/* + /ready. Owns ALB health. /ready returns 200 if frontend process is alive — does not depend on substrate. Substrate calls forward over Unix socket. Sensory uploads write payload to /shared/sensory_in/, notify substrate, return 200 immediately.

Substrate: holds _guala. Listens on /shared/substrate.sock. Single-threaded request loop. Heartbeats to /shared/substrate.alive every 5s. All admin mutations fsync before returning.

## Socket protocol

JSON-over-newline.
Request: {"id": "<uuid>", "op": "<name>", "args": {...}}
Response: {"id": "<uuid>", "ok": true, "result": {...}} or {"id": "<uuid>", "ok": false, "error": "..."}

Ops: status, v7_state, v7_converse, v7_quiet, v7_feedback, v7_save, gualaloom_post, amnesty, force_dream, backup, repause, unpause, atlas_snapshot, sensory_notify, job_status.

## Sensory ingest (Phase 3, not this phase)

Frontend writes payload to /shared/sensory_in/<uuid>.<ext>, sends sensory_notify, returns 200. Substrate worker consumes at its own rate. If files accumulate past threshold, oldest dropped. /sight_frame and /sound_frame become trivial in this architecture.

## Admin endpoints as transactions (Phase 4, not this phase)

amnesty, force_dream, backup, repause, unpause: substrate completes mutation, fsyncs, then returns. No race against SIGTERM. unpause becomes a real bridge tool. force_dream returns artifact when it actually fires.

## Health and deploy

/ready decoupled from substrate. Substrate can be slow, restarting, dreaming — ALB doesn't care. Deploys: substrate drains in-flight, fsyncs, exits. Frontend drains, exits. New task starts both. Page sees "thinking" not "crashed."

## What stays unchanged

v7_engine.py, gualaloom_v5_engine.py, atlas, krimelack, decay, dream consolidation. Not changing how she thinks. Changing the container she lives in.

gualaloom.html unchanged. Same endpoints. Same shapes.

## Phases

**Phase 1 (THIS):** substrate_runner.py + substrate_client.py + SUBSTRATE_MODE env var (embedded default, remote opt-in) + frontend handler routing. Local verification only. NO production deploy.

Phase 2: Dockerfile per container, ECS task def with two containers, production deploy with pileon-v4 verification.

Phase 3: sensory ingest as queue-then-notify; /sight_frame and /sound_frame.

Phase 4: admin transactions; /admin/unpause; fixed force_dream artifact return.

## Phase 1 acceptance (local only)

- substrate launches via python -m dsf_ai_service.substrate_runner
- frontend launches via uvicorn dsf_ai_service.app:app
- SUBSTRATE_MODE=remote routes substrate ops over socket
- /ready probe 100 in a row at 100ms intervals: every one 200 under 50ms, even while substrate is doing V7Session construction
- /ready returns 200 even when substrate socket is down
- /v7/state on fresh session_id returns correct data via socket
- /api/v1/gualaloom /status works end-to-end via socket
- SUBSTRATE_MODE=embedded (default) continues to work — production unaffected

## Constraints

- No kernel logic changes. v7_engine.py and gualaloom_v5_engine.py untouched.
- Embedded mode must still work — default unchanged for prod.
- Unix socket only. JSON over newline. No gRPC, no protobuf.
- All admin endpoint behavior preserved exactly. Frontend dispatches; substrate executes same code.
- No production deploy in Phase 1.
