# Auditory Dynamic Sensory-Neuron Missing Law — 2026-07-27

## Architecture honesty

- Requested architecture: a new stateful sensory neuron driven anew by
  actual W1 cochlear pressure/phase trajectories and every explicit
  D/M/R/U/C/P/B field. Receptive bandwidth and time constants must come only
  from existing cochlear/filter physics or certified interval uncertainty.
  Repeated physically custodied THING episodes may grow and fission
  deterministic couplings; canonical L6 alone governs release.
- Current code reality: the provider supplies sixteen fourth-order complex
  gammatone filters, ERB widths, exact 16 kHz recurrence, and 10 ms
  observation cadence. It does not supply a finite auditory-category
  acceptance bandwidth, a finite memory cutoff, or a physical law mapping
  speaker-varying acoustic trajectories into one articulatory event.
- Conflict: yes. Implementing the requested neuron now requires at least one
  boundary not derived by the mounted physics.
- Mechanisms not extended: LoomNeuron, ChiAtlas, MapInject, Gaussian
  injection, heuristic commit thresholds and delays, incomplete STDP,
  static relation quotients, event IDs, scores, nearest matching, word
  labels, waveform matching, and ML.
- Single item: determine whether every dynamic-neuron constant is physically
  derivable before implementation.
- Full-field evaluation: the proposed input remains the complete explicit
  D/M/R/U/C/P/B trajectories. No compatibility vector was evaluated.
- Reduced approximation: none was implemented.

## What the mounted physics derives

For cochlear channel \(i\), the provider defines

\[
r_i=\exp\left(
  -2\pi(1.019)\operatorname{ERB}(f_i)/16000
\right).
\]

Therefore it derives the exact recurrence form, one-pole decay rate, channel
centre, ERB coordinate, fourth-order cascade, and the 160-sample observation
cadence. Across the sixteen channels, the one-pole time constants are about
4.685 ms down to 0.187 ms. The corresponding one-hop retentions are about
0.1183 down to \(6.35\times10^{-24}\).

These are filter dynamics, not recognition boundaries.

## Why no receptive cutoff follows

The complex one-pole magnitude at any finite frequency offset is

\[
\left|
\frac{1-r_i}
     {1-r_i e^{j\Delta\omega}}
\right|.
\]

Because \(0<r_i<1\), the numerator is positive and the denominator is finite.
The fourth-order magnitude is therefore strictly positive at every finite
frequency. ERB names the width of an equivalent rectangular filter; it is
not a hard support boundary.

Consequently, the mounted filter physics cannot decide that one neighboring
channel drives a learned neuron while another does not. A hard ERB edge,
response fraction, top-k choice, or overlap cutoff would be a new developer
threshold.

## Why no finite temporal cutoff follows

The fourth-order impulse response contains a positive polynomial factor times
\(r_i^n\). Since \(0<r_i<1\), it decays but remains mathematically nonzero for
every finite \(n\). The physics therefore supplies a decay law, not a finite
memory horizon.

Using floating-point underflow, a selected number of time constants, an
amplitude fraction, or an episode-length truncation as neuronal forgetting
would introduce a numerical or developer boundary. A typed causal episode
may bound storage, but it does not prove that later acoustic influence is
physically zero.

## Why certified intervals do not supply speaker tolerance

The current certified resonance balls enclose arithmetic evaluation error at
a mounted precision. Their width is computational uncertainty, not
microphone, room, vocal-tract, dialect, or speaker variability. Overlap of
those balls cannot lawfully become an acoustic-category tolerance.

The W1 D/M/R/U/C/P/B values are retained as exact Fractions after their
authenticated conversion. They do not carry a calibrated physical
measurement-error interval that could become a receptive width.

## Missing physical authority

A lawful dynamic category neuron still needs one of:

1. a physically measured uncertainty/calibration interval for each receptor
   and full-field trajectory;
2. a causal articulatory source observation that relates external acoustic
   variation to the same vocal gesture;
3. an explicitly approved learned tolerance or basin law.

The current room microphone supplies none of these. The already proven
source-filter non-identifiability means the acoustic mixture alone cannot
recover a unique vocal-tract cause.

## Decision

Stop before implementing the neuron. Every available decay coefficient is
derived, but the category receptive width and finite coupling/forgetting
boundary are not. Inventing either would violate the no-threshold,
substrate-true contract.

This is not a claim that human-like hearing is impossible. It is the exact
missing authority in the current substrate. The recommended next item is to
add or approve a calibrated physical uncertainty law, or to make external
speech causally co-observed with an articulatory/visual source whose
continuity supplies the equivalence.
