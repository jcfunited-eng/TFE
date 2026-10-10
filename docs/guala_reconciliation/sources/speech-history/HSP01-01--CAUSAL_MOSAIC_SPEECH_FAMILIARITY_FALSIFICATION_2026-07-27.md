# Causal mosaic speech-familiarity falsification — 2026-07-27

## Decision

Do not implement a new auditory-familiarity authority from the tested
relations. The required exact causal structural relation is not present.

## What was tested

The verified mini Speech Commands corpus supplied source-disjoint speakers.
Completed experiences were causally grouped so that several speakers of one
command represented one lived grounding and different commands represented
distinct groundings. Held-out speakers were excluded from growth. Command and
speaker metadata classified completed results only; neither entered PCM,
L0–L4, recurrent neurons, temporal neurons, or query relations.

All explicit `D_k/M_k/R_rev_k/U_star_k/C_k/P_k/B_k` fields and all 32
pressure/phase component paths remained available. L0–L4 was unchanged.

## Result

- Exact full-field relations: 64 speakers, 224 within-command pairs, 1,792
  cross-command pairs, and 24 held-out queries. All five declared exact
  relations produced 0 within-command locks and 0/24 held-out passes.
- Repeated causal full-field recurrence: all four declared relations produced
  0/24 held-out passes. Recurrent structure grew, but it did not form a
  selective speaker-independent grounding.
- Current recurrent and temporal neurons: 18 source-disjoint speakers across
  three causal groundings grew 735 motif neurons and three temporal
  assemblies. Held-out result was 0/3; one query incorrectly resolved another
  grounding.

The authenticated compact record is
`docs/CAUSAL_MOSAIC_SPEECH_FAMILIARITY_FALSIFICATION_2026-07-27.json`.

## Precise information gap

The causal mosaic can truthfully retain that several lived occurrences belong
to the same physical THING. It does not thereby create an auditory relation
between different speakers.

The current production auditory route admits a re-hearing only when the
complete ordered sound-root tuple is exactly equal to a retained tuple.
Source-disjoint speakers saying the same command do not satisfy that equality.
The current recurrent and temporal neurons also do not supply a selective
exact relation: broadly recurring structure is shared among different
groundings, while grounding-specific structure does not lock for held-out
speakers.

Therefore an unheard occurrence contains no exact authority that can choose
the causally correct THING. A union, intersection count, score, threshold,
label, topology key, or reduced quotient would invent the missing relation.
No such fallback was implemented.

## Production truth

This result does not falsify deterministic learning or causal mosaics. It
falsifies promotion of the currently tested auditory roots and current
recurrent/temporal neurons into speaker-independent THING familiarity.
Contextual physical re-encounter of an already known THING remains valid;
auditory-only familiarity across a new speaker remains unresolved.
