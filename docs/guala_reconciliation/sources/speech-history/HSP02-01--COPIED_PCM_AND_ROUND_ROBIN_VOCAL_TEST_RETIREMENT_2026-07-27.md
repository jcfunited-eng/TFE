# Copied-PCM and Round-Robin Vocal Test Retirement

Date: 2026-07-27

## Decision

The following whole test files were retired:

- `tests/test_real_recorded_thing_speaking_acceptance.py`
- `tests/test_engine_lived_thing_vocal_cycle.py`

They did not prove that Guala learned a vocal form through embodied causal
experience.

## Why the recorded-pressure test was invalid

The test loaded a tutor recording and admitted those exact PCM bytes as a
`SelfVocalPCMMotorOwner` exemplar.  Its decisive assertion was that a later
self emission reproduced the tutor PCM byte-for-byte.

That is copied playback, not growth of a self articulatory act.  It bypasses
the required larynx/tract learning problem and makes stored external pressure
the motor authority.

## Why the engine-cycle test was invalid

The engine test exercised `_attempt_lived_thing_vocal_learning`, whose current
path advances `claim_next_babble_program()` in sorted round-robin order for
each external vocal occurrence.  It then binds whichever unrelated program
the cursor selected after recurrent auditory structures happen to fire.

The external experience does not causally determine which self articulation
is retained.  Swapping tutor forms while preserving occurrence order would
select the same motor programs.  Therefore the test cannot distinguish
learning from cursor scheduling.

## Preserved requirements

Replacement acceptance must prove all of the following:

1. An external articulatory act is one physical cause of visible mouth motion
   and binaural room pressure.
2. The observation is continuous across authenticated physical quiescence,
   actuation, and return to quiescence.
3. Guala's candidate articulation is her own generated larynx/tract act; tutor
   PCM is never admitted as a self motor exemplar.
4. Only a later applied physical consequence for that exact candidate
   occurrence may close the THING-to-articulation relation.
5. Swapping which candidate receives the consequence swaps the learned
   relation after cold restore.
6. A later physical THING cue causes fresh synthesis and self hearing.
7. Every observed sensory tuple retains explicit `D_k`, `M_k`, `R_rev_k`,
   `U_star_k`, `C_k`, `P_k`, and `B_k`.
8. Unknown, unclosed, stale, ambiguous, or tampered evidence remains silent.
9. Raw tutor or self PCM is not retained as learned identity.

Until that replacement proof passes and is wired to the live engine, Guala
must not be described as having learned a recorded word or spoken it from
learned experience.
