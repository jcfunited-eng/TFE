# Fractal-Gate Completion — Declared Choices (NON-CANONICAL)

2026-07-29. The recovered framework (docs/recovered_lineage/) leaves
specific holes. Each is completed here with a DECLARED choice — stated
before any run, physics- or lineage-grounded, no outcome-fitting.
Implementation: tools/fractal_gate_engine.py.

## Holes and completions

**H1 — Phase of a vertex (needed by the mosaic/Kuramoto layer).**
Not defined in the source. Completed: delay-embedded phase-portrait
angle over the kernel's structural share,

    φ_i(t) = atan2( Δx̂_i(t), Δx̂_i(t−1) )

Parameter-free, scale-invariant, computed from the retained field only.

**H2 — Field order parameter.** Completed per Kuramoto:

    Z(t) = (1/n)·Σ_i e^{iφ_i(t)};  Ω(t) = |Z(t)|;  Θ_M(t) = arg Z(t)

Ω is field coherence (the meadow state); vertex dissonance
d_i(t) = 1 − cos(φ_i(t) − Θ_M(t)).

**H3 — The R axis (relevance/attention).** Absent from every current
input. Completed lineage-true (notebook's "flashing" = attention
bursts; mapping docs name volume/sentiment): per vertex,

    r_i(t) = dollar_volume_i(t) / median_{20 bars}(dollar_volume_i)

a unitless attention-burst ratio. First time the kernel's input side
gains the fourth original axis.

**H4 — Free parameters of the gate simulation.** Pinned,
deterministic (SHA-256-seeded), declared: d=8 state dims; one gate per
vertex; clusters of 10 (alphabetical thirds); W_i random orthogonal
scaled to spectral radius 0.9; P equal-budget 4×8; A_ij = α/k with
α=0.1, conservative (zero row sums); β=1; η=0.05; θ_i init from seed;
Δt=1 sim step per bar.

**H5 — ψ_C (fractal signature), defined by gesture in the source.**
Completed executably: ψ_C(t) = Ω_C(t)·e^{iΘ_C(t)} where Ω_C is the
source's own cluster coherence and Θ_C = atan2 of the first two
components of the cluster-mean state.

## Application protocol (declared before running)

Fit-free tests on the real field (cohort A, closed bars only):

  T1 RELAXATION — does field coherence mean-revert (attractor
     behavior)? corr(Ω(t), Ω(t+k)−Ω(t)) for k ∈ {1,5,20}.
     Kuramoto prediction: negative.
  T2 REALIGNMENT — do top-tercile dissonant vertices reduce their
     dissonance over the next 5/20 bars more than bottom-tercile?
     Source's own law (dθ/dt = −η·sin) predicts yes.
  T3 MEADOW LINKAGE — forward 20/60-bar universe mean return and WR by
     Ω tercile. All bands reported; no threshold exists to tune.
  T4 VERTEX LINKAGE — forward 20/60-bar returns by dissonance tercile.
     All bands reported. (The restoring-flow question, done as
     dynamics, not band-mining.)

Then the lineage simulation (gates→clusters→mosaic→motivation) driven
by the completed four-axis input, reporting whether the interpretive
layer's coherence Ω_M tracks the field's Ω — an emergence check,
exploratory, report-only.

Everything reports raw. Nothing here is a trading rule until it
survives its own predictions AND forward data.
