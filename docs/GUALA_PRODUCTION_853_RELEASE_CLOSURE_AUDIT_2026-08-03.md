# Guala production 853 release-closure audit

Date: 2026-08-03

Status: read-only production and source audit. No file, deployment, task,
organism state, or secret was changed by the audit.

## Architecture honesty gate

1. **Requested architecture:** one bounded native organism authority with one
   continuous causal thought/action loop. Python is limited to HTTP, media
   transport, health, and persistence adapters. Cognitive sub-owners, owner
   leases, fixed Python worker farms, chatbot databases, ML, scripted meaning,
   and flattened DSF are prohibited.
2. **Current code reality:** production task 853 runs one Python Uvicorn parent,
   one Python multiprocessing resource tracker, and four spawned Python exact-
   field workers. A large Python `Guala` object graph remains the runtime
   coordinator. Rust contains exact kernels, the D2 materialized-fabric
   transition, and structural codecs, but no resident organism loop.
3. **Conflict:** yes.
4. **Mechanisms not extended:** the Python `Guala` owner graph, retired restore
   bodies, `substrate/native_core.py` monkeypatch/fallback, the four-worker
   exact-field executor, separate cognitive owners/registries, and owner-status
   readiness. Short transaction locks used solely to publish authenticated
   immutable persistence are a different infrastructure concern.
5. **Single exact next item:** implement a native `OrganismRuntime` that cold-
   restores the existing D2 fabric bytes without alteration, exclusively owns
   the successor state, and exposes bounded restore, ingest, step, observe, and
   seal operations.
6. **Full field or reduced approximation:** the live field path retains
   explicit `D_k`, `M_k`, `R_rev_k`, `U_star_k`, `C_k`, `P_k`, and `B_k`.
7. **Field loss:** no seven-coordinate loss was found. The defect is split
   Python orchestration and process ownership, not scalar DSF flattening.

## Live task proof

The audited production target is:

- ECS task definition `dsf-ai-task:853`;
- source commit `8cd0a4ba896cb4e298794d3e00533fe8f409b56a`;
- image digest
  `sha256:58affa41111829945b2ce34daa194a399aa69fcdb79a0480fd9f0ef32df15f74`;
- service desired/running/pending count `1/1/0`;
- one Uvicorn command without multiple Uvicorn workers; and
- one healthy load-balancer target.

Direct process observation found six Python interpreters inside that one ECS
task:

1. PID 1 Uvicorn;
2. one multiprocessing resource tracker; and
3. four `spawn_main` field workers.

CloudWatch independently reported `exact native field executor ready: 4 fixed
workers`. Boot also reported `autonomous_experience=unavailable`. Current code
sets the autonomous experience driver to `None`; its start method returns
`legacy_python_autonomy_retired`. The mounted play helper is not an unattended
organism loop.

The task environment still contains `GUALA_OWNER_LOCK_PATH`, but neither the
deployed commit nor the current worktree consumes it. It is vestigial
configuration rather than a live owner lease and must be removed at cutover.

## Shipped and reachable closure

The production manifest contains 146 runtime Python modules. Static import
closure from `app.py` reaches 136; ten are packaged only for other entry points
or package roots. The current worktree manifest is smaller at 133 modules, 123
reachable from `app.py`, with the same ten packaged-only files. The smaller
current closure is not yet live.

Production boot imports fourteen legacy modules through
`substrate/native_core.install()`. That installer monkeypatches Krimelack,
cochlear, visual, DSF, map-injection, and Psi-settlement surfaces and includes a
pure-Python fallback. The current manifest removes those fourteen files, but
does not yet forbid their exact paths, so anti-resurrection is incomplete.

The production application closure defines 62 classes whose names end in
`Owner`, `Registry`, `Authority`, `Coordinator`, `Store`, `Manager`, or
`Executor`, and contains 74 thread/process synchronization or process-
construction sites. These counts are an audit inventory, not a claim that all
62 classes own cognition. The four-worker executor is the one process
constructor and creates the observed four children.

Boot-created cognitive and coordination surfaces span auditory streams and
motifs, causal experience, embodiment, body state, action teaching,
deliberation, play, prediction, visual continuity, encounter continuity, and
multiple evidence authorities. Many retired methods also remain compiled in
the approximately fourteen-thousand-line Python physical runtime core behind
unconditional failures. They are not executing cognition today, but they are
shipped resurrection bodies.

Necessary background infrastructure currently includes the checkpoint
coroutine, bounded input-ring thread, local persistence consumer, and S3
consumer. These transport or persist bytes; none is autonomous cognition.

## Database finding

No SQLite, SQLAlchemy, PostgreSQL, Redis, or MongoDB import was found in the
deployed or current manifest closure. No database container, endpoint,
environment variable, or task-role permission was found. S3 is object
persistence. The historical corpora, models, pickle, and dataset paths are
excluded by manifest rules.

There is therefore no active chatbot SQL database to delete. The remaining
risk is the shipped Python owner graph, monkeypatch/fallback path, and dead
legacy bodies.

## Native classification

The deployed Rust library does not contain or compile the current local
`neuron_electrical_physics.rs` reference module. In the dirty worktree that
module is declared in `lib.rs`, so a complete local Cargo build compiles it,
but it has only crate-private symbols, no PyO3 registration, and no call site.
It is compiled-only local reference code. Its arbitrary-precision rational
state is not live and must not become persistent production biology.

The deployed native library still exposes historical functions used through
the production monkeypatch installer. The current library removes those
exports and exposes the joint-source, joint-kernel, materialized-fabric, and
organism-structure boundaries, but it still has no state-owning resident
runtime.

## D2 preservation boundary

The migration must preserve byte-identically:

- the authenticated `CURRENT` generation and deployment seal;
- organism identity and tick/state revision;
- the `guala_core.json` contract
  `guala.native_exact_organism_state.v2`;
- nested `native_materialized_fabric.state_base64` bytes;
- its exact byte count and SHA-256;
- the materialized-fabric reference; and
- every retained joint-field and neuronal-fractal authority.

The current destination generation persists only this native fabric. Retired
per-owner state is not part of the preservation boundary and must never become
a fallback migration source.

## Ordered retirement

1. Read and hash the exact live `CURRENT` generation and native D2 fabric using
   read-only custody. Establish those bytes as the only migration input.
2. Implement and falsify one native `OrganismRuntime` with bounded restore,
   ingest, step, observe, seal, and unattended wake behavior. It must consume
   the same joint source and preserve every explicit field.
3. Switch only application boot and organism endpoints to one native handle.
   Retain the working HTTP/static, health, generation-persistence, EFS/S3, and
   transaction-duration exclusion adapters.
4. After cold-restore and equal-transition proof, delete the Python `Guala`
   cognition imports, native-core installer/fallback, four-worker executor,
   dead restore bodies, and owner-status readiness. Remove
   `GUALA_OWNER_LOCK_PATH`. Add exact forbidden paths and symbol checks so the
   removed closure cannot re-enter a release.
5. Rehearse the complete release from the authenticated production predecessor
   before cutover. Cut over once, then perform live process, state, field,
   continuity, health, persistence, and resource verification.

## Acceptance

The retirement is complete only when production proves:

- exactly one ECS task;
- one Python HTTP/media adapter and one native organism loop;
- no Python multiprocessing resource tracker or field worker;
- unchanged D2 identity, tick lineage, fabric bytes, and full-field authority
  through the migration boundary;
- background organism generations advance from physical wake causes without a
  request or operator;
- HTTP, health, EFS generation publication, and S3 persistence remain working;
- no packaged Python cognitive owner/registry constructor remains;
- removed legacy paths are forbidden by the release manifest; and
- CPU, RAM, durable bytes, Python-call count, and native-call count remain
  bounded and truthfully observed.

This audit proves the production conflict and the preservation/retirement
boundary. It does not prove a native runtime, autonomy, D3 recall, learning,
tutoring, or corrected live interfaces.
