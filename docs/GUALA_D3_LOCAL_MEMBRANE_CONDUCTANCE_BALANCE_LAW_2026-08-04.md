# Guala D3 local membrane conductance-balance law

Date: 2026-08-04

Status: isolated native physical-law candidate. It is not registered in the
production library, mounted in the organism, deployed, or evidence of D3
completion, cognition, autonomy, or tutoring.

## Architecture honesty gate

1. **Requested architecture:** reached sensory conductance and electrogenic
   transport must alter membrane charge through local physics while preserving
   real material circulation.
2. **Current code reality:** each conductive path settles current and carriers
   separately; reached active-transport carriers join only at the membrane
   capacitor; and the material paths atomically update one shared 21-material
   vestibular state.
3. **Conflict:** yes until Type II gating, physiological K+/Ca2+ partition,
   pH/ATP recovery, synapse, neuron boundary, organism residency, and production
   cutover are complete.
4. **Not extended:** persistence recovery, owner/lock/database machinery,
   semantic fluid scores, guessed percentages or rates, interpolated gates,
   target-voltage controllers, arbitrary clamps, or DSF-driven current.
5. **Single next item:** derive the local Type II channel-gating law without
   inventing a numerical approximation.
6. **DSF evaluation:** none. L0-L4 remains downstream, complete, and unchanged.
7. **Declared loss:** membrane/material state is receptor physics, not a
   reduced DSF field, Krimelack state, neuronal fractal, or meaning.

## Exact electrical relation

For each reached conductive path `i` and the reached signed electrogenic
transport count `n_active`:

```text
I_i = g_i * (V_predecessor - E_i)
(n_i, phase_i_next) = elementary_carriers(I_i, delta_t, phase_i)
n_conductive = sum(n_i)
n_membrane = n_conductive + n_active
Q_successor = Q_predecessor - n_membrane * e
V_successor = Q_successor / C_membrane
```

Conductance is nonnegative. Zero conductance is a physically closed path.
Current is zero when membrane potential equals that path's reversal potential.
Opposed paths settle an equilibrium from conductances and reversal potentials;
the code does not store a desired resting voltage.

Each conductive path retains its own bounded carrier phase. Equal apical inward
and basolateral outward currents may leave conductive charge unchanged while
ions cross both paths. Active transport is not flattened into a conductive
current or given a fabricated conductance; its already-reached integer carrier
count joins at charge conservation.

The conductance-only entry point supplies exact zero active transport. The
coupled entry point requires the explicit reached count. It derives no pump
rate, timer, or desired membrane state.

## Exact local material relation

One shared state contains K+, Ca2+, Na+, Cl-, ATP4-, water, ADP3-, hydrogen
phosphate, and protons across endolymph, hair cell, perilymph, and dark cell.
Hair-cell conductance events settle with PMCA2 Ca2+/H+ exchange, dark-cell
3 Na+:2 K+:1 ATP Na+/K+-ATPase, 1 Na+:1 K+:2 Cl- NKCC1, and dark-cell apical K+
secretion.

Every quantity uses exact bounded integer/rational arithmetic. Electrical
phase is unresolved continuous ensemble current, not a fractional electron.
Compile-time path count is mounted anatomy, not an arbitrary runtime cap. The
material state is fixed at 336 bytes, allocates nothing per transition, and
does not grow with age.

## Biological boundary

Vestibular Type II hair cells express distinct basolateral delayed and transient
outward K+ currents, inward rectifiers, Ca2+ current, and in some preparations
Ca2+-activated K+ current. Expression depends on species, developmental age,
and crista region. Those currents remain distinct where evidence supports them.

The chick E19-E21 zone-2/3 Type II study reports voltage-dependent I_K(V)
activation with a fitted half-activation potential of -24 mV and slope of
12.3 mV, plus time-dependent activation and inactivation. A Boltzmann fit
contains a real exponential. It is not silently replaced with a lookup table,
linear interpolation, or unbounded floating approximation. Executable gating
remains unavailable until numerical precision and error authority are
explicitly ratified.

PMCA2 calcium extrusion and its electrogenic carrier are present as exact
reaction extents, not kinetics. ATP regeneration, proton/Mg2+ speciation,
proton removal, Na+/Cl- return, and the gate kinetics remain outside the
current boundary and are not presented as complete metabolism.

## Executable falsification

The isolated target proves:

- simultaneous -12 pA and +12 pA paths each transfer carriers while their
  conductive sum is exactly zero;
- one PMCA cycle adds exactly one outward carrier to that membrane successor;
- restorative conductive direction on both sides of equilibrium;
- exact quiescence for closed or reversal-matched paths;
- refusal of negative conductance;
- atomic hair-cell and dark-cell material circulation from one predecessor;
- conservation of K, Ca, Na, Cl, adenylate, phosphoryl groups, and represented
  electric charge;
- reversal, depletion refusal, and byte-exact restart; and
- 100,000 transitions without age-dependent state growth or erased flux.

The complete isolated candidate target passes 68/68 tests after retirement of
the selected linear hair-cell gate. The rejected D3
source-retirement gate passes 2/2. Strict whole-library Clippy with warnings
denied is not green: it stops on 34 unrelated existing warnings/lints; none
reported this candidate module, but that is not represented as a clean
whole-library lint result.

## Sources

- Ohmori, chick vestibular hair-cell mechanotransduction,
  <https://pubmed.ncbi.nlm.nih.gov/3656183/>.
- Masetto et al., chick semicircular-canal hair-cell membrane development,
  <https://pubmed.ncbi.nlm.nih.gov/10805673/>.
- Masetto et al., chick vestibular Type I/II capacitance and currents,
  <https://pubmed.ncbi.nlm.nih.gov/12702715/>.
- Nin et al., vestibular endolymph K+ maintenance and recycling,
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC6633285/>.
- Yamoah et al., hair-bundle PMCA calcium extrusion,
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC6792544/>.
- Hill et al., PMCA2 Ca2+/H+ exchange in vestibular hair bundles,
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC6674470/>.
- Carmosino et al., Na+/K+-ATPase stoichiometry,
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC10480117/>.
- Chew et al., NKCC1 stoichiometry,
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC6856059/>.
- IUBMB thermodynamic nomenclature for ATP hydrolysis,
  <https://iubmb.qmul.ac.uk/thermod/th1t3.html>.
