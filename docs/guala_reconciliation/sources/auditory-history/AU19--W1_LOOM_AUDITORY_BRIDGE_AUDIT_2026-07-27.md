# W1 Loom auditory bridge audit — 2026-07-27

## Mandatory architecture honesty gate

1. **Requested architecture:** authenticated full binaural pressure, phase,
   causal time, and explicit D/M/R/U/C/P/B trajectories must enter real
   sensory neurons and participate in later causal THING learning.
2. **Current code reality before this work:** `process_sound_frame` retained
   the structured field in settlement custody but deliberately set
   `_last_sound_signal = None`. The organism queue accepted only one
   `input_signal`, optional chi, and no ear/topology/field arguments. The
   alternate wave-summary route reduced a sense to aggregate amplitude and
   top-three chi cells. The production Loom brain also constructed H1/H6 with
   `LanguageKrimelack`, despite the committed topology declaring them
   auditory.
3. **Conflict:** yes.
4. **Mechanisms not extended:** wave-summary/top-three projection,
   `LoomNeuron.step`, chi familiarity, match scores, 16-dimensional
   `_map_inject`, psi commit, transcript identity, and static peak-cell
   identity.
5. **Single implemented item:** authenticated W1 binaural settlement to real
   Loom auditory-Krimelack intake.
6. **Field evaluation:** complete explicit field.
7. **Reduced structure lost:** none at intake. Every ear, channel,
   pressure/phase component, causal frame, and D/M/R/U/C/P/B coordinate is
   delivered independently.

## Exact loss proof

`tools/probe_w1_loom_neuron_adapter_loss.py` proves:

- the live mono sound entry retains 32 channel/component records with topology
  and causal time;
- `process_sound_frame` does not call the organism sensory queue;
- the queue has no ear, topology, or explicit DSF arguments;
- the legacy raw route mutates oscillator/DSF/psi state only through a
  one-dimensional input and invokes chi `match_score`;
- `resonant_spectral` encoding does not advance neuron dynamics;
- default H1/H6 neurons have `LanguageKrimelack`;
- the wave summary defaults to top three and discards complex phase, ear,
  topology, and explicit fields.

Authenticated report:

- file: `/tmp/w1_loom_neuron_adapter_loss_v2.json`
- file SHA-256:
  `84d17ed6d530c2936b3171d4c5900a5bd188c0eb7af658e14fecb7b191c550b4`
- authority SHA-256:
  `a1c3db678bdf97db7fd03240b4eb6d04902aa62cfa2802f6b8f8809218938475`

## Implemented bridge

`dsf_ai_service/substrate/w1_loom_auditory_bridge.py` accepts only a verified
`W1BinauralReceptorSettlement`.

For one occurrence it delivers:

- 2 ears × 16 cochlear channels ×
  (2 components × 7 DSF fields + 4 physical pressure/phase lanes)
  = **576 independent sensory trajectories**;
- 16 channels × 5 exact interaural relations
  = **80 bilateral trajectories** for pressure, relevance, cumulative phase,
  phase advance, and source time.

H1 and H6 are initial routing banks, not learned ear identities. Both banks
receive the same bilateral relation lanes so downstream mosaics can become
bilateral.

Each target is an actual Loom neuron and the intake mutates that neuron's
existing `krimelack_bank["auditory"]`. Each lane retains a bounded latest
response and source authority. No raw-history list grows.

The existing binary64 oscillator remains an observational response. In
parallel, every lane advances exact phase and winding using exact Fractions,
the exact causal duration, and rationalized existing oscillator constants.
Later resonance is prohibited from treating the float response as authority.

The bridge is wired into `Guala._attempt_lived_thing_vocal_learning` before
the older peak-motif experiment. Restore rebinds the bridge to the restored
live brain.

## Verification

- `tests/test_w1_loom_auditory_bridge.py`: 5 passed.
- `tests/test_w1_loom_neuron_adapter_loss.py`: 4 passed.
- `tests/test_engine_lived_thing_vocal_cycle.py`: 2 passed, including full
  engine save/restore.

The bridge tests prove all 576 deliveries, all 80 bilateral relations, no
legacy step/wave-summary path, no-input/no-learning storage stability,
duplicate occurrence refusal, and exact production structural-graph cold
restore.

## Honest remaining boundary

This fixes the upstream sensory-neuron intake defect. It does **not** prove
held-out word recognition or arbitrary-room source separation. The next
required item is a bounded exact bilateral co-resonance and causal THING-growth
law over these neuronal lanes. It must remain score-free and must not fall
back to chi, psi, transcript labels, or static peak cells as identity.
