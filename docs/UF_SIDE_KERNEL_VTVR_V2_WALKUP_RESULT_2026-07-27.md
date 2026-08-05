# Isolated VTVR Side Kernel V2 — Corrected Walk-Up Result

Date: 2026-07-27

Status: non-canonical sensory-physics result. The canonical kernel and live
hearing path were not modified or evaluated by this walk-up.

## Correction

The first version of this report incorrectly treated auditory recurrence as
the learning unit. That is signal classification, not Guala's architecture.

Guala learns a THING as a bounded causal mosaic of lived experience. Sound,
sight, touch, smell, taste, body state, action, place, participants, and
consequence may all participate. A recurring sound can become a word only as
one reciprocal route into that wider mosaic. It cannot become meaning through
audio-only grouping.

No corpus directory name, transcript, tutor label, chi address, waveform
receipt, or auditory similarity relation may become mosaic identity.

## Rung 1 — synthetic joint VTVR contracts

Passed:

- deterministic replay;
- complete joint-field custody;
- exact common-positive-gain invariance;
- retained interaural delay;
- rejection of a distinct waveform.

Evidence: `tests/test_isolated_vtvr_side_kernel_v2.py`

## Rung 2 — physical binaural tones

Passed:

- exact authenticated replay;
- threefold common gain changed raw custody while the complete L1 structural
  field remained exactly equal;
- moving the source across the head changed the path from left/right delays
  `10/14` samples to `14/10` samples and changed the retained ear relation;
- a distinct physical tone produced a distinct VTVR field.

The result was differentiated rather than receipt-only:

- 526 causal frames were retained;
- source-location reversal changed 483 vector frames and 508 relation frames;
- tone change changed 464 vector frames, 419 volume frames, and 432 relation
  frames.

Evidence:
`tests/test_isolated_vtvr_side_kernel_physical_walkup.py`

## Rung 3 — physical speech custody

The exact replay sub-rung passed. The same authenticated recording, physically
rendered and transduced twice, produced the same physical-capture receipt and
the same complete VTVR structural receipt.

Two different speakers saying the same corpus word produced different fields:

- all 100 L1 vector frames differed;
- 99 of 100 L1 volume frames differed;
- all 100 L1 relation frames differed;
- 6,336 of 6,400 values differed in each of `D_k`, `M_k`, `P_k`, and `B_k`;
- 2,702 of 6,400 `R_rev_k` values differed;
- all 201,600 `C_k` relation facts differed;
- `U_star_k` did not differ because both experiences had the same observation
  custody state.

This is valid evidence that the side kernel preserves naturally varying speech
detail. It is not a failed word-learning test. The recordings were not part of
bound multisensory lived mosaics, so asking them to produce a learned word was
architecturally invalid.

Evidence:
`tools/probe_vtvr_side_kernel_physical_speech_walkup.py`

## Exact conclusion

The isolated VTVR side kernel preserves a rich and physically responsive
bilateral sensory field in the tested tones and speech recordings.

The next valid walk-up is not audio-only recurrence. It is one embodied THING
re-encountered through varied, bounded causal mosaics. The test must determine
whether familiarity expands across those experiences and whether the auditory
component becomes a reciprocal access route into the mosaic without becoming
its identity.
