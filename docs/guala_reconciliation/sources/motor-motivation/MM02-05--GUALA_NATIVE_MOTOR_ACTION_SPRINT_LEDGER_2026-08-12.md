# Guala Native Motor Action Sprint Ledger — 2026-08-12

## Requested architecture

One bounded native causal path from already-mounted layer-12 motor-neuron
physics to exact virtual-body motion and vestibular sensory return. No Python
choice logic, semantic intent, timer-authored activity, dense/global scan,
owner, queue, lock, database object, persisted command, or new cognitive
meaning is introduced.

## Change-impact ledger

- Exact input: predecessor/successor open-channel populations produced by one
  reached complete-neuron interval.
- Function/file path:
  `complete_neuron::settle_extended_interval_with_contact` derives only the
  positive population delta; `reached_neuron_cohort::settle_reached_cohort_interval`
  carries only sparse nonzero deltas; `resident_cognitive_formation::settle_internal_contact_interval`
  admits only source-independent layer-12 cells; `organism_runtime` projects
  those transient events across the native boundary; `_perform_admitted_intake_locked`
  consumes them once.
- State transformation: the neuron state changes under existing physics. The
  event itself changes no retained organism state. Its opposed motor topology
  settles on the existing one-millidegree/one-millisecond yaw lattice; the
  resulting vestibular trajectory returns through the existing native body
  path.
- Expected output: no recruitment means no changed behavior or added
  per-neuron allocation. Recruitment means one prepared world yaw, one native
  vestibular consequence, one organism publication, and one world
  persistence.
- Production acceptance: a live unattended interval must report
  `native_causal_action_observed`, the world heading must change by the exact
  signed recruitment sum, vestibular ticks must equal the one-tick trajectory,
  cold restore must preserve the resulting body, Python cognition callbacks
  must remain zero, and idle CPU/RAM/state-byte growth must not increase.
- Observed evidence before release: 417 native library tests pass; the
  transient opening test proves opening emits once and closing emits zero; the
  opposed-yaw test proves `+7 -2 +1 = +6` millidegrees on one tick; the focused
  production-world test proves preparation is invisible until commit and then
  changes heading without translating position.

## Failed hypotheses retained

- A dense zero-filled event vector was rejected during review because it
  allocates in proportion to every reached neuron. The implementation now
  carries only sparse nonzero `(resident index, opened channels)` entries.
- The historical unattended-time test is not release evidence: it depends on
  the deleted `UNATTENDED_CADENCE_ENV` control. That control is not restored.
- A fresh default embodiment-world fixture currently declares 66 objects under
  a hard maximum of 64. The motor proof uses one lawful object; the unrelated
  fixture defect is not hidden as a motor failure and is not expanded into
  this sprint.

## Delivery truth

This ledger is local implementation evidence only. The sprint is not delivered
until the production acceptance path above passes against the live organism.
