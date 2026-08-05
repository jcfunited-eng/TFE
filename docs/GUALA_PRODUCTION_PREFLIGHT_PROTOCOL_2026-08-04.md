# Guala production preflight protocol

Date: 2026-08-04

Status: canonical read-only admission gate before discarded-state rehearsal and
production cutover. It is not a deployment controller and cannot deploy.

## Purpose

`tools/preflight_guala_production.py` turns the recurring deployment checks
into one repeatable, fail-closed operation. It validates the exact reviewed
Guala source, native release closure, immutable candidate, live predecessor,
and intended cutover command shapes before any production mutation occurs.

The preflight does not create an organism owner, lock, seal, database, fallback
brain, migration brain, or deployment generation. It does not evaluate DSF or
alter neuron/runtime physics. Transaction-duration exclusion inside a future
binary persistence adapter is outside this preflight and receives no cognitive
authority from it.

## Required invocation

Run from any directory, but name the exact Guala root, reviewed commit,
registered candidate task definition, and immutable candidate image digest:

```text
python3 tools/preflight_guala_production.py \
  --root /exact/guala/worktree \
  --expected-commit <40-lowercase-hex-commit> \
  --candidate-task-definition <exact-dsf-ai-task-arn> \
  --candidate-image-digest sha256:<64-lowercase-hex>
```

Success emits one canonical JSON receipt with status
`ready_for_discarded_state_rehearsal_not_deployed`. That statement means only
that the immutable candidate is admitted to the next isolated rehearsal. It is
not a deployment or functionality claim.

Any failure emits `PREFLIGHT BLOCKED` and exits nonzero. Correct that exact
failure before proceeding. Never bypass or weaken a failed check to obtain a
cutover.

## Exact gates

The preflight checks, in order:

1. The supplied directory is the exact Git root, `HEAD` equals the reviewed
   commit, the tree is clean, and `git diff --check` passes.
2. The release manifest includes the native organism runtime, resident Python
   boundary, raw binary store, resource admission, Docker inputs, and release
   controllers.
3. The manifest cannot ship the rejected Python physical runtime, owner-scoped
   persistence, Python native-core fallback, legacy cold/live generation
   stores, or separate ECS seal transport.
4. The deployment controller names `tfe-web-cluster` and
   `dsf-ai-service-lb`, never `tfe-web-service-lb`, and contains no automatic
   old-image rollback, owner-lock requirement, sealed-state requirement,
   generation-store requirement, or quiesce/seal ceremony.
5. The complete native test suite builds and passes with the locked Cargo
   dependency graph in the worktree and again from the packaged archive. The
   second build detects native source files omitted from the manifest.
6. The deterministic packager creates and re-verifies a temporary release
   context and archive from the exact clean commit. The staged archive is
   inspected again for every required native serving file.
7. ECS resolves exactly one active, settled Guala service, one completed
   deployment, one running healthy task, one `dsf-ai` container, and the
   `dsf-ai-task` family. A similarly named TFE service is rejected.
8. The candidate task definition is active, distinct from the live task, uses
   exactly one essential `dsf-ai` container, and pins its image as
   `repository@sha256:digest`, not a mutable tag.
9. Candidate commit and digest environment match the reviewed artifact. Legacy
   owner, lock, seal, generation-store, restore-switch, Python field-worker,
   and database environment variables are rejected. Positive CPU and RAM
   envelopes are mandatory.
10. ECR resolves exactly that immutable digest and its physical byte size.
11. Authenticated live readiness matches the ECS task definition and image,
    exposes one native resident state identity and tick, and reports zero
    Python cognition callbacks.
12. The exact `dsf-ai-site` bucket and `E17JT9XGBFU493` CloudFront
    distribution resolve read-only. UI publication remains a separate action.
13. The rehearsal and fail-closed cutover commands are emitted as unexecuted
    data. The cutover explicitly uses `rollback=false`; an older incompatible
    image is never an automatic rollback brain.
14. ECS is read again. Any task, image, service, or deployment drift during the
    preflight invalidates the receipt.

## Non-mutation proof

The program has an internal allowlist containing only these AWS reads:

- ECS describe/list operations;
- ECR image description;
- Secrets Manager secret read for authenticated readiness;
- S3 bucket-location and CloudFront distribution reads.

Any unreviewed or mutating AWS operation is rejected before the AWS CLI can be
started. The only writes are disposable local Cargo artifacts and a temporary
release archive, both outside production. The emitted `update-service` and
candidate-rehearsal commands are evidence of their exact shape; the preflight
never executes them.

## Required local integration gate before candidate packaging

The AWS preflight assumes that the reviewed native source and the Python wheel
used by local integration tests are the same build. Before committing a
candidate, run this exact local sequence:

1. Run the full native Rust library suite from `native/guala_core`.
2. Build one release wheel from that same source and install that exact wheel
   into the verification environment.
3. Instantiate a native resident organism and prove that its runtime schema
   exactly equals the Python boundary's required schema. A stale installed
   wheel is a release blocker, even when the source suite is green.
4. Run native genesis, raw `CURRENT` publication, cold restore, candidate
   rehearsal, serving, and UI contract tests together. A DSF delivery,
   delivery receipt, sign tuple, or historical perspective must never satisfy
   a cognitive trace, fractal, mosaic, recall, or learning assertion.
5. Run both HTML interfaces against
   `guala.native.public_observation.v1` in a real browser. Prove zero page
   errors, one monotonic integer generation, conditional ETag reads, hidden-tab
   suspension, and fail-closed media cleanup.
6. Run `git diff --check` and the exact release-packaging suite after the last
   serving, manifest, or deployment-controller edit.

Do not repair a failed gate by restoring owner-era storage, the excluded Python
organism, legacy v5 observation fields, browser-generated articulation, or
false cognition counters. Replace an obsolete assertion with a current
architecture proof only when the old assertion positively demands a retired
mechanism.

## Current expected blocking evidence

The 2026-08-04 worktree is actively dirty and therefore cannot pass the first
release gate. The reviewed manifest and controller now select the native HTTP
boundary, raw `CURRENT` persistence, one-shot authenticated predecessor
migration, one discarded-state rehearsal, one cold-restore proof, and one
fail-closed cutover. Their local contract and packaging tests are green, but
that is not a production claim. The definitive neuron is still test-only and
the mounted joint-field ingress still conflicts with the proposed canonical UF
v1.4 joint lift. A successful preflight is expected only after that architecture
is ratified and implemented, the whole release closure is reviewed and
committed, and the candidate image/task definition are immutable.

## Required next operation after success

Run the emitted discarded-state candidate rehearsal from the exact predecessor
named in the receipt. Re-read production after that rehearsal. Only a matching
rehearsal proof and unchanged predecessor may authorize the emitted cutover
command. The cutover itself remains the responsibility of the reviewed
deployment controller and requires separate live verification.

