# W1 Auditory Source–Filter Mapping Audit — 2026-07-27

## Architecture honesty gate

- Requested architecture: deterministic physical separation of vocal
  excitation, vocal-tract spectral envelope, and temporal articulation,
  mounted through unchanged full-field L0–L4.
- Current code reality: the provider retains 16 ERB-band 10 ms RMS envelopes,
  cumulative carrier phase, phase advance, and absolute ERB coordinates.
  L0–L4 acts independently on each pressure/phase port.
- Conflict: yes. No glottal excitation, harmonic lattice, source-normalized
  transfer envelope, or formant relation is retained.
- Mechanisms not extended: cepstral/LPC fitting, peak or top-k selection,
  strongest-bin routing, thresholded periodicity, scores, ML, interpolation,
  and canonical L0–L4.
- Single item: determine whether the required physical quantities map
  directly and uniquely to the retained fields.
- Field evaluation: all explicit D/M/R/U/C/P/B trajectories were included in
  the mapping. They describe the source–filter mixture; none independently
  observes either factor.

## Mapping

| Required quantity | Current field | Result |
|---|---|---|
| Native pressure waveform | Available only during transduction | Not retained |
| Independent glottal event train | None | Missing |
| Source fundamental/harmonic lattice | None | Missing |
| Band response magnitude | 16-channel 10 ms RMS | Retained mixture/product |
| Band response phase motion | Cumulative phase and phase advance | Retained mixture/sum |
| Source-independent tract transfer | None | Not identifiable |
| Absolute formant relations | ERB coordinates only | Coordinates present; operator and normalized envelope absent |
| Temporal articulation | 10 ms full L0–L4 trajectories | Mixture trajectory present |

## Exact non-identifiability

For observed magnitudes `Y_i = E_i H_i`, every nonzero exact `q_i` produces:

`Y_i = (E_i q_i)(H_i / q_i)`.

For observed phase `φ_i = φ_E,i + φ_H,i`, every exact `q_i` produces:

`φ_i = (φ_E,i + q_i) + (φ_H,i - q_i)`.

The audit includes two distinct rational factorizations with exactly equal
products and phase sums. Therefore the current cochlear/L4 field cannot
select one source–filter decomposition without adding an external physical
authority or an unapproved model assumption.

## Smallest missing authority

The direct missing observation is one causally independent vocal-excitation
field paired with the acoustic response. For self-produced speech, truthful
laryngeal/vocal motor embodiment could supply it. Room audio alone does not
uniquely expose that source.

No separator was implemented, because the mapping is not direct.

## Authorities

- Audit:
  `/tmp/w1_auditory_source_filter_mapping_audit.json`
- Audit authority:
  `b13b317badd730ad2d96c09b5947e92cfdcbb05c1686d0031aceb77bf2f11118`
- Audit tool SHA-256:
  `382e53b3063ac1422fd64d1cb51ef2733e69db56b27db62626ef7ac0b3ddb6fa`
- Focused verification: 26 tests passed.
