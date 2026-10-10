# Guala D3 current joint-inspection residency audit

Date: 2026-08-03

Status: current-only typed logical plan and streaming canonical comparison;
general-allocator dependency remains; not production mount authority.

## Architecture honesty gate

1. **Requested architecture:** derive a typed logical inspection plan from the
   exact current GLJNFT03 body before decoding, remove caller-supplied inspection
   allowances, avoid charging borrowed aliases twice, and state allocator limits
   truthfully.
2. **Current code reality:** current-only preflight scans GLJNFT03 version 3,
   derives a receipt-bound plan, the runtime admits that plan, and canonical
   comparison streams against the borrowed input without a second full encoded
   joint Vec.
3. **Conflict:** yes for production mounting. Logical resources are derived and
   separated, but several variable allocations still use Rust's general
   allocator and therefore do not have an exact enforced peak.
4. **Mechanisms not extended:** migration parsing as ordinary restore,
   historical custody, fallback, genesis, owners, locks, databases, Python,
   altered L0-L4, reduced DSF, guessed coefficients, or fake allocator proof.
5. **Single exact next item:** move decoded containers/payloads/limbs,
   reconstruction intermediates, validation nodes, and canonical integer
   emission onto preflight-sized bounded allocation surfaces.
6. **Field evaluation:** physical validation reconstructs the complete explicit
   joint field through unchanged L0-L4.
7. **Declared loss:** none in field authority. General-allocator capacity and
   temporary overlap remain outside the present logical plan.

## Completed current-only preflight

`preflight_current_inspection` walks GLJNFT03 version 3 without constructing
the decoded State. It verifies exact magic, version, end position, fixed
boundaries, feasible counts, optional flags, structural trits, current
receptor-binding shape, and positive rational denominators.

It returns `CurrentInspectionPlan`, bound to the exact joint byte length and
SHA-256 receipt, with separate quantities for:

- borrowed joint bytes;
- retained decoded container backing;
- retained owned payload backing;
- retained BigInt limb backing;
- total retained decoded logical bytes;
- largest one-field exact rebuild;
- validation scratch;
- canonical streaming scratch; and
- additional logical arena bytes.

The additional logical arena excludes the borrowed joint because that slice
aliases the retained GLORUN01 allocation. Plan equality is re-derived and
checked immediately before inspection, so a plan from another body or a
modified plan is refused.

## Canonical comparison

Canonical state output is compared incrementally with the input body. This
removes the former second complete `encode_state` Vec and keeps the complete
canonicality check. Rational emission still uses one
`BigInt::to_signed_bytes_be` Vec at a time; its largest logical body is recorded
as canonical streaming scratch.

## Honest remaining allocation dependency

The plan does not claim allocator-exact residency. These live allocations
remain implementation-dependent:

1. `Vec` and `String` can have capacity beyond requested logical length.
2. Big integer/rational normalization, GCD, multiplication, division, and
   comparison can create private temporary limbs.
3. `BTreeSet` and `BTreeMap` validation nodes have private layouts and
   schedules.
4. L0-L4 reconstruction still creates nested vectors, Arc values, rationals,
   relation facts, and authority-hash intermediates.
5. The one-at-a-time canonical integer Vec has a known logical length but an
   allocator-controlled capacity.
6. Allocator metadata and growth overlap are not represented.

Accordingly the plan reports
`LogicalArenaStatus::GeneralAllocatorRequired`. That enum is a refusal reason,
not an allocator-proof flag. The native organism runtime remains test-only and
unmounted.

## Exact closure criterion

Mount eligibility requires all variable general allocations above to consume
preflight-derived bounded arenas or another allocation surface with exact
capacity and live-phase enforcement. The resulting peak must then be admitted
against freshly observed finite cgroup headroom. This is storage/execution
refactoring only; it cannot change L0-L4 equations, DSF fields, current custody,
or transition physics.

## Executable evidence and authority paths

- Current scanner, plan, inspector, and streaming comparator:
  `native/guala_core/src/mounted_joint_fractal.rs`
- Outer runtime plan admission:
  `native/guala_core/src/organism_runtime.rs`
- Full-field L0-L4:
  `native/guala_core/src/joint_field_l0_l4.rs`
- Cgroup observation:
  `native/guala_core/src/organism/platform_observer.rs`
- Governing runtime law:
  `docs/GUALA_D3_ORGANISM_RUNTIME_RESIDENCY_LAW_2026-08-03.md`

Tests cover exact logical boundary and one-byte-below refusal, exact-plan
substitution refusal, adversarial count refusal before decoded construction,
100,000 repeated stable preflights, current-only schema refusal, and canonical
noncanonical-rational detection.

