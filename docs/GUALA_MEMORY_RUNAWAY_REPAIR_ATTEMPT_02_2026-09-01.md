# Guala memory-runaway repair attempt 02 — 2026-09-01

Status: `SOURCE_IMPLEMENTED_FOCUSED_CAUSAL_PROOF_PASSED_COPIED_BODY_PROOF_PENDING`

## Immutable boundary

- Repair base: `aac0b9858031c6874b68853434e6b1110ddc2442`.
- Production remains contained at zero running tasks while this attempt is
  reviewed and proven on a copied production body.
- L0-L4, the seven joint DSF fields, native neuron physics, persisted organism
  state, learned sensory state, world state, and speech mechanisms are not
  changed.
- `_active_cross_intake_causal_motor_traces` remains a process-local,
  read-only observer. It never enters organism custody or selects an action.

## Repair-attempt history carried forward

1. Changed-versus-prior retention was rejected. Exact causal paths lawfully
   extend each native interval, so change alone is not a lifetime law.
2. Commit `6fc079e1` was rejected. It counted Python intake calls rather than
   native organism intervals, made results depend on transport batching,
   introduced nontransactional birth/ordinal globals, and permitted an expired
   historical key to be born again.
3. The first version of this attempt used a three-interval completion limit.
   An existing causal regression correctly failed: three retained predecessor
   frontiers may complete into the current fourth interval. The implementation
   was corrected before commit or copied-body proof.

None of these rejected mechanisms may be revived as a fallback.

## Exact causal impact

The unbounded resident keeper is the Python observation dictionary
`_active_cross_intake_causal_motor_traces`. Its path advance law already drops
a trace on the first interval that supplies no exact endpoint continuation.
The runaway case instead supplies a real continuation every interval. Because
the observer carried the origin and its whole accumulated path without a
physical-age boundary, approximately one new generation of origin histories
was retained per lived beat. Accepted vocal/self-hearing activity multiplied
that existing defect.

The native organism keeps `older_active_electrical_frontier`,
`preceding_active_electrical_frontier`, and `active_electrical_frontier`, then
settles the current interval. That gives one exact law:

- an origin may be evaluated for completion while its first causal transfer
  remains in the three retained predecessor frontiers plus the current
  interval;
- an incomplete origin may cross an intake only while the next native interval
  can still witness that same window;
- age is `current_organism_tick - origin_organism_tick`, independent of how
  Python groups native intervals into requests;
- once expired, the exact origin tick remains old, so the identical historical
  key cannot resurrect.

The implementation applies the completion horizon inside every exact native
interval, including intervals nested in one aggregate intake. Cross-intake
retention applies the stricter carry horizon after the final native interval.
It adds no timer, cap, birth table, intake ordinal, persistent field, restart
behavior, or cognition authority.

## Source proof so far

- Focused causal files: `23 passed`.
- Broader directly referencing set on the candidate: `45 passed, 13 failed`.
- The same broader command on untouched `aac0b985`: `43 passed, 13 failed`.
- All 13 failure names are identical and are inherited stale fixture/API
  failures outside this change. The candidate adds two passing falsifiers and
  no new failure.
- New falsifiers prove that an over-horizon completion is rejected identically
  when exact native intervals are split across transport intakes or batched in
  one intake, and that an expired exact key cannot be reintroduced.
- Existing regression evidence proves that a completion using all three
  retained predecessor frontiers and the current interval remains lawful.

## Remaining acceptance gate

This is not yet a production repair. Freeze and fingerprint the source, build
one exact artifact, then use the newest authenticated copied production body
to prove bounded trace cardinality and resident memory over repeated long
windows, four-interval custody, newest-CURRENT cold restore, another ordinary
post-restore interval, unchanged identity/body/world/neurons/formations/full
DSF delivery, and no positive resident drift capable of refilling the task.
Only that proof can authorize a controlled production restore.
