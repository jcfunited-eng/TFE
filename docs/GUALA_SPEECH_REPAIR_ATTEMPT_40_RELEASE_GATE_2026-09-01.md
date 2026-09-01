# Guala speech repair attempt 40 — inherited-test release gate

Production remained unchanged and healthy on task 1404 throughout this
attempt. The first standard release invocation built immutable image digest
`sha256:377dfe6964b7432369fd87e01fd944eed741e0d631817de157c4f42412119210`
from exact commit `5138983603a46b59d393d8c455a1bc92f70aa931` and registered candidate task
definition 1405. The preflight stopped before rehearsal, drain, or cutover.
The service stayed at exactly one completed task-1404 deployment.

## Cause

The preflight required an absolutely green full Rust suite even though the
same 16 tests have been recorded as inherited failures since untouched commit
`faff9e06`. Direct isolated builds reconfirmed the complete comparison:

- exact task-1404 source: `554 passed, 16 failed, 11 ignored`;
- copied-body-proven speech candidate: `556 passed, 16 failed, 11 ignored`;
- the 16 failure IDs are identical;
- the candidate adds two passing speech tests and no failing test.

Repairing unrelated historical tests during this speech release would violate
the standing repair-history rule and would expand the organism change after
its copied-body proof. Bypassing preflight or using the hot-deploy path would
remove stronger controls and is rejected.

## Exact control repair

The release now carries a machine-readable, commit-anchored roster of the 16
known failures. Preflight performs the full native suite in both the reviewed
source and freshly packaged source. It also lists the compiled tests first so
no baseline test can be deleted or renamed. It accepts zero failures or a
subset of the exact roster; any unlisted failure, compilation failure,
unparseable result, removed test, non-descendant candidate, or abnormal exit
fails closed.

This control changes deployment evidence only. It does not alter L0-L4, DSF,
neurons, cognition, persisted body bytes, speech physics, world physics, or
the copied-production-body proof in attempt 39.
