# Guala production 853 persisted-state reality

Date: 2026-08-03

Status: read-only live-production audit. No state, tick, task, service, or
deployment was changed.

## Architecture honesty gate

1. **Requested architecture:** one current native organism state that cold
   restores without an owner-scoped brain, compatibility fallback, or repeated
   legacy migration.
2. **Current code reality:** task 853 holds a current in-memory `GLMFAB04`
   projection, but active recovery still persists the prior `GLMFAB03` body
   inside a large legacy whole-organism JSON object.
3. **Conflict:** yes. Cold boot still depends on explicitly authorized
   v3-to-v4 migration rather than restoring a durably sealed current body.
4. **Mechanisms not extended:** ordinary v3 restore, legacy cognitive fields,
   owner-lock files, old whole-organism JSON cognition, or a second fallback
   path.
5. **Single next item:** rehearse one authenticated predecessor migration that
   writes a canonical current-only native runtime envelope, then prove the next
   cold boot rejects v3 and restores the same identity, tick, fields, neurons,
   and receipts.
6. **DSF evaluation:** the audit does not evaluate or reduce DSF. The migrated
   current body must retain its complete reconstructable joint-field authority.
7. **Field loss:** none is authorized. Only legacy classes and pseudo-mosaic
   fields already excluded from D2 authority may be discarded by the explicit
   one-way migration.

## Live evidence

The audited service was settled and healthy:

- ECS service `dsf-ai-service-lb`;
- task definition `dsf-ai-task:853`;
- desired/running/pending `1/1/0`;
- task health `HEALTHY`;
- identity `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`;
- active recovery generation
  `d44d203f-5d1e-4f9e-869c-795751fc7597`;
- active recovery tick `23,723,846`.

The authenticated readiness response reported an in-memory native fabric:

- schema `guala.owner_free.materialized_fabric.reference.v4`;
- state bytes `442,352`;
- SHA-256
  `2fd667d8446b7fadea2308dd368411080d80487ddbb1c770471f16a0d5add952`;
- two joint fields;
- 96 joint neurons;
- transition description `cold_restore_one_way_migration`.

A separate read-only load of the immutable active recovery generation found
the nested persistence record at:

```text
guala_core.json
  -> data
  -> organism_state
  -> native_materialized_fabric
  -> state_base64
```

Its exact persisted properties were:

- record schema `guala.native.materialized_fabric.persistence.v1`;
- decoded magic `GLMFAB03`;
- decoded bytes `4,148,843`;
- decoded SHA-256
  `b1f538e25d0bf59584266172ccb473b2b2db6ad7ddf1fc1f7ffa542bd2cc7e14`;
- outer saved tick `23,723,846`.

The persisted `organism_state` also retains dozens of legacy named cognition,
curriculum, owner-like control, and mechanism records. They are not the D2
native cognitive authority, but their continued presence makes the active
generation much larger and keeps their restore schema reachable.

The EFS scope still contains vestigial lock files including:

```text
/app/guala/.guala-owner.lock
/app/guala/sealed/.generation-store.lock
/app/guala/sealed/.deployment-transaction.lock
/app/guala/sealed-live-recovery/.generation-store.lock
```

File presence alone does not prove an active lifetime owner. It does prove the
old artifacts have not yet been removed from the persistent scope. They must be
retired only as part of the verified cutover that no longer opens them.

## Resource observation

A read-only migration attempt with 64 MiB of admitted native working memory
failed before producing a successor:

```text
persisted joint field requires 265201410 derived working bytes,
admitted 67108864
```

This is not an 82-million-call recurrence and did not change production. It is
evidence that current restore verification requires at least 265,201,410
derived working bytes for the retained field. The future runtime must either
admit that measured one-time restore cost inside the platform envelope or
replace the implementation with an exactly equivalent streaming verification.
It may not skip full-field verification or call the 442,352-byte output proof
that restore RAM is equally small.

## Required cutover proof

No D3 deployment may rely on ordinary v3 acceptance. The candidate must prove,
in order:

1. authenticate the exact immutable v3 predecessor, identity, and tick;
2. invoke the separately named one-way migration once;
3. prove the migrated current body's exact fields, neuron lineages, fractal
   receipts, counts, and expected current bytes;
4. place that current body inside the native runtime envelope without changing
   its bytes;
5. publish one successor generation atomically;
6. cold restart using current-only restore;
7. prove `GLMFAB03`, `GLJNFT01`, and `GLJNFT02` are rejected by ordinary restore;
8. prove the old JSON cognition fields and owner/lock paths are absent from the
   new release and persistent head; and
9. prove one task, one native runtime, unchanged identity/tick continuity, and
   bounded CPU, RAM, and durable bytes.

Until those checks pass, the truthful statement is: D2 is live in memory, but
its current representation is not yet the sole durably persisted cold-restore
authority.
