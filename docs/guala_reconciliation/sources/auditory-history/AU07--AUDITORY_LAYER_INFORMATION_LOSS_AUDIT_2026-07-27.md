# Auditory information-loss localization — 2026-07-27

## Architecture honesty gate

1. **Requested architecture:** real two-ear W1 propagation, exact
   interaural time/phase/level topology, both ears kept separate through the
   unchanged L0–L4 kernel, and mirrored bilateral assemblies in which each
   side receives both ears.
2. **Current code reality:** the isolated audit now implements that physical
   path. Production hearing remains unchanged. The earlier coupled candidate
   remains a duplicated-mono control and is not physical binaural evidence.
3. **Conflict with requested architecture:** no conflict in the isolated
   audit; production still does not contain this complete path.
4. **Mechanisms not extended:** the duplicated-mono candidate, metadata-only
   interaural comparisons, the dormant receipt-only 16-channel graph, legacy
   compatibility vectors, scalar scores, ML, and production L0–L5.
5. **Single exact next item:** retain the current kernel and require a new
   label-blind relation to demonstrate selective held-out recurrence before
   considering any hearing-scoped implementation.
6. **Full field or reduced approximation:** raw, receptor, trace, brainstem,
   and L4 witnesses are complete. Each recurrence relation is an explicitly
   reduced exact quotient over those complete witnesses.
7. **Exact structure lost by the quotients:** the whole-trajectory quotient
   loses one positive scale per numeric partition, absolute magnitude,
   cross-partition magnitude, and cross-duration alignment. The local
   structural alphabet loses magnitude, multiplicity, long-range order,
   cross-partition simultaneity, and categorical duration.

## Result

No layer-loss boundary was established.

Neither declared exact quotient demonstrates selective same-command
recurrence at raw PCM. Therefore there is no established raw recurrence that
can be shown to disappear at the cochlear receptor, L0, L1, L2, L3, or L4.
No held-out query passes at any audited layer, including physical brainstem
and physical stereo L4.

The cochlear provider is openly information-reducing: it maps 16,000 PCM
samples to 100 observations over 16 bands and states that the waveform is not
losslessly preserved. That proves a dimensional reduction exists. It does
not prove that this reduction caused word recurrence to fail, because the
required selective recurrence was absent at raw PCM under both declared
relations.

Consequently:

- no L0–L4 change is justified;
- no new L5 operator is promoted;
- there is no evidence-backed minimal deterministic hearing change to
  specify yet.

## Exact recurrence census

Every count below is computed after the complete 64×64 relation matrix exists.
Command labels classify finished relations only.

| Layer | Exact whole-trajectory within / cross locks | Local structural within / cross locks | Held-out pass |
|---|---:|---:|---:|
| Raw PCM | 0 / 0 | 224 / 1,792 | 0 / 24 |
| Cochlear receptor | 0 / 0 | 157 / 1,290 | 0 / 24 |
| L0 | 0 / 0 | 217 / 1,736 | 0 / 24 |
| L1 | 0 / 0 | 0 / 0 | 0 / 24 |
| L2 | 0 / 0 | 0 / 0 | 0 / 24 |
| L3 | 0 / 0 | 0 / 0 | 0 / 24 |
| L4 | 0 / 0 | 1 / 8 | 0 / 24 |
| Physical brainstem | 0 / 0 | 210 / 1,682 | 0 / 24 |
| Physical stereo L4 | 0 / 0 | 0 / 8 | 0 / 24 |

The local raw relation is universal rather than selective. The exact
whole-trajectory relation is empty between different speakers. The two
opposite exact failure modes remain non-selective at every later surface.

## Physical stereo findings

- Ear positions: `(0, +100, 0)` mm and `(0, -100, 0)` mm.
- Source positions: `(200, +100, 0)` mm and `(200, -100, 0)` mm.
- Transfer paths: source A is left 10/right 14 samples; source B is left
  14/right 10 samples. All four attenuations are exactly `1/1`.
- Eight corpus source pairs were superposed at the two distinct positions.
  The exact binaural solver recovered both scaled emitters byte-for-byte in
  all eight checks.
- Each single-source experience mounted 32 left-ear and 32 right-ear ports
  through unchanged L0–L4.
- The brainstem retained per-band exact path-delay, envelope-level,
  cumulative-phase, and phase-advance differences.
- The left assembly received `[left ear, right ear]`; the right assembly
  received `[right ear, left ear]`. There are no weights and neither ear is
  assigned to only one side.
- The 14-sample propagation tail is below the 160-sample cochlear observation
  interval and is explicitly reported as unsettled, not padded or cropped.

This controlled chamber does not model pinna transfer, head shadow,
diffraction, reflections, reverberation, or sensor noise. Those are catalogued
missing physics, not silently approximated.

## Authority and reproducibility

- Full report:
  `/tmp/guala_auditory_layer_information_loss_v1.json`
- Full report authority:
  `fa944f83daf07c26778e31072c77f8e5d626036d686e6070585bda671e7f1ec0`
- Full report file SHA-256:
  `d4e23bf0d6797f2793171cdd3f0ec7ad73cd32f0c36e287ff2cbeee4d8243c80`
- Full report size: 61,767,274 bytes
- Corpus authority:
  `49650f2341b26d886b46b3f4fb8fed59e30300b17550f1ee4a768b3106cf93a0`
- Source-disjoint speakers: 64
- Focused contract: 6 tests passed

The compact authenticated record is
`docs/AUDITORY_LAYER_INFORMATION_LOSS_REPORT_2026-07-27.json`.
