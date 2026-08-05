# Guala D3 organism-runtime residency law

Date: 2026-08-03

Status: superseded historical allocator audit. Its logical-plan findings remain
falsification evidence, but `GUALA_NATIVE_RESIDENT_ORGANISM_RUNTIME_LAW_2026-08-04.md`
and the current `GLORUN01 -> GLMFAB06 -> (GLJNFT03 + GLCOG003)` implementation
govern the candidate. This document is not current mount or deployment authority.

## Architecture honesty gate

1. **Requested architecture:** one owner-free native organism runtime that
   restores and seals only the current `GLORUN01 -> GLMFAB04 -> GLJNFT03`
   chain, preserves exact field and identity continuity, and refuses work that
   exceeds physically admitted resources.
2. **Current code reality:** the test-only runtime retains one canonical
   envelope allocation, borrows its fabric and joint slices, derives an exact
   receipt-bound logical inspection plan before decoding, and streams canonical
   comparison instead of creating a second complete joint encoding.
3. **Conflict:** yes for production mounting. The logical quantities are
   separated and derived, but decoded state, exact rational work, validation
   collections, and canonical integer emission still use the general allocator.
4. **Mechanisms not extended:** historical restore, migration fallback, genesis
   fallback, owners, locks, databases, Python callbacks, reduced DSF, altered
   L0-L4, duplicate outer/fabric/joint bodies, or caller-invented working
   allowances.
5. **Single exact next item:** replace the remaining variable general-allocator
   paths with preflight-sized arenas or equally exact bounded allocation
   surfaces, then bind the admitted runtime peak to the finite observed cgroup
   ceiling.
6. **Field evaluation:** validation reconstructs the complete explicit DSF
   field through unchanged L0-L4; it does not flatten or score the field.
7. **Declared loss:** none in field or current custody. Allocator-exact
   production residency remains unproved and is not claimed.

## Typed logical inspection plan

Current GLJNFT03 preflight walks the borrowed bytes before decoded-state
construction and binds the resulting plan to both byte length and SHA-256
receipt. The plan distinguishes:

- `borrowed_joint_bytes`: a slice inside the envelope, not new residency;
- `retained_decoded_container_bytes`: logical backing for decoded typed
  containers;
- `retained_decoded_payload_bytes`: owned String and byte payload bodies;
- `retained_decoded_limb_bytes`: retained BigInt limb bodies;
- `largest_field_rebuild_logical_bytes`: the largest one-field exact L0-L4
  reconstruction phase;
- `validation_logical_scratch_bytes`: cardinality-derived validation scratch;
- `canonical_streaming_scratch_bytes`: the largest one-integer canonical
  emission body; and
- `additional_logical_arena_bytes`: retained decoded logical bytes plus the
  maximum overlapping phase.

The current formula is:

```text
D = decoded containers + owned payloads + retained limbs
A = D + max(largest field rebuild + validation scratch,
            canonical streaming scratch)
logical runtime peak = max(construction live,
                           retained envelope capacity + A)
```

The borrowed GLMFAB04 and GLJNFT03 slices alias the retained envelope allocation.
They add zero bytes to `A`. The runtime has no
`admitted_joint_inspection_bytes` input and cannot accept a caller-selected
inspection allowance.

## One-allocation outer continuity

The GLMFAB04 constructor accepts only a caller-owned vector whose existing
capacity can hold the complete GLORUN01 envelope. Insufficient headroom is
refused before mutation. Restore of an already-owned GLORUN01 vector moves that
allocation directly into the runtime. Seal consumes the runtime and moves the
same allocation into its result. Actual vector capacity, including unused
slack, is charged.

Ordinary restore accepts exactly:

```text
GLORUN01 version 1
  -> GLMFAB04 version 4
    -> GLJNFT03 version 3
```

GLMFAB02/03 and GLJNFT01/02 remain migration inputs only and are refused by
ordinary restore. Empty, truncated, trailing, noncanonical-identity, and invalid
inputs cannot create genesis.

## Why the runtime remains unmounted

The plan is an exact logical decomposition, not an allocator peak certificate.
The current implementation still has variable allocation behavior not
controlled by the plan:

1. Rust `Vec` and `String` capacity may exceed logical length.
2. `BigInt` and `BigRational` normalization and arithmetic create private
   temporary limbs.
3. `BTreeSet` and `BTreeMap` validation use private node allocations.
4. Exact L0-L4 reconstruction creates nested vector, Arc, rational, relation,
   and authority-hash intermediates.
5. Streaming canonical comparison removes the second full joint Vec, but
   `to_signed_bytes_be` still creates one variable integer Vec at a time.
6. Allocator metadata and any growth overlap are outside the logical plan.

`LogicalArenaStatus::GeneralAllocatorRequired` states that condition directly.
There is no Boolean, multiplier, or fake “complete allocator proof.” Production
mounting is prohibited until the remaining allocations consume derived bounded
surfaces. A production admission must also use the finite cgroup facts observed
by `native/guala_core/src/organism/platform_observer.rs`; a storage ceiling is
not a compute ceiling.

## Executable evidence and authority paths

- Runtime and logical admission:
  `native/guala_core/src/organism_runtime.rs`
- Current preflight, typed plan, physical validation, and streaming canonical
  comparison: `native/guala_core/src/mounted_joint_fractal.rs`
- Unchanged full-field L0-L4 authority:
  `native/guala_core/src/joint_field_l0_l4.rs`
- Native cgroup observation and finite-ceiling admission facts:
  `native/guala_core/src/organism/platform_observer.rs`
- Current custody architecture:
  `docs/GUALA_NEURON_ARCHITECTURE_TRUTH_GATE_2026-08-02.md`
- Full-field and resource law:
  `docs/GUALA_NATIVE_JOINT_FIELD_L0_L4_V1.md`
- Detailed inspection audit:
  `docs/GUALA_D3_CURRENT_JOINT_INSPECTION_RESIDENCY_AUDIT_2026-08-03.md`

The executable tests prove exact logical-boundary admission and one-byte-below
refusal, receipt-bound plan substitution refusal, adversarial count refusal,
borrowed-joint non-duplication, actual-capacity charging, pointer-identical
restore/seal, 10,000 stable restore/seal cycles, 100,000 stable preflights,
current-only schema refusal, invalid-input non-genesis, and zero Python
callbacks.
