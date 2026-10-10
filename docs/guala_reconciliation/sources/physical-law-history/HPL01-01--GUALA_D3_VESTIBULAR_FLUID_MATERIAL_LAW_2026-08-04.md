# Guala D3 vestibular fluid-material law

Date: 2026-08-04

Status: isolated native material-conservation candidate. It is not registered
in the production library, mounted in the organism, deployed, or evidence of
D3 completion, cognition, autonomy, or tutoring.

## Architecture honesty gate

1. **Requested architecture:** hair-cell transduction and biological
   restoration must be one local material circulation, not a recovery timer or
   supervisory reset.
2. **Current code reality:** hair-cell apical K+/Ca2+ movement, hair-cell
   basolateral K+ movement, bundle PMCA2 Ca2+/H+ exchange, dark-cell
   Na+/K+-ATPase, dark-cell NKCC1, and dark-cell apical K+ secretion settle
   atomically from one predecessor. PMCA electrogenic charge also reaches the
   membrane capacitor.
3. **Conflict:** yes until channel and transporter extents arise from derived
   local kinetics, pH/ATP regeneration is present, and the complete receptor
   reaches a synapse and neuronal boundary.
4. **Not extended:** owner, lock, database, scheduler, persistence recovery,
   generic reaction framework, target voltage/concentration, guessed rate,
   lookup table, arbitrary capacity, semantic fluid score, DSF-driven current,
   or fixed K+/Ca2+ percentage.
5. **Single next item:** derive a local Type II conductance-gating law with an
   explicit ratified numerical representation for its measured exponential.
6. **DSF evaluation:** none. Complete L0-L4 remains separate and unchanged.
7. **Declared loss:** this material transition is pre-DSF receptor physics; it
   is not a DSF projection, Krimelack state, neuronal fractal, or cognition.

## Fixed local material

One 336-byte state contains twenty-one unsigned counts:

```text
endolymph: K+, Ca2+, H+
hair cell: K+, Ca2+, ATP4-, H2O, ADP3-, HPO4(2-), H+
perilymph: K+, Na+, Cl-
dark cell: K+, Na+, Cl-, ATP4-, H2O, ADP3-, HPO4(2-), H+
```

These are material quantities, not owners or database rows. The state has no
history list and does not grow with age.

## Atomic reaction law

All event counts are signed extents. Positive extents use these directions:

```text
dark-cell Na+/K+-ATPase:
  dark: ATP4- + H2O + 3 Na+ + perilymph: 2 K+
  -> dark: ADP3- + HPO4(2-) + H+ + 2 K+ + perilymph: 3 Na+

dark-cell NKCC1:
  perilymph: 1 Na+ + 1 K+ + 2 Cl-
  -> dark:   1 Na+ + 1 K+ + 2 Cl-

dark-cell KCNQ1/KCNE1 path:
  dark: 1 K+ -> endolymph: 1 K+

hair-bundle PMCA2:
  hair: ATP4- + H2O + Ca2+ + endolymph: H+
  -> hair: ADP3- + HPO4(2-) + H+ + H+ + endolymph: Ca2+
```

The two hair-cell product protons have distinct physical origins: ATP
hydrolysis produces one and PMCA countertransports one from endolymph. PMCA
moves one net positive elementary charge outward per forward cycle; that
carrier count joins the conductive-path carriers at the membrane capacitor.

For hair apical K+ count `a_K`, hair apical Ca2+ count `a_Ca`, apical
elementary-carrier count `a_q`, hair basolateral K+ count `h_K`, dark-cell pump
cycles `p`, dark-cell cotransporter cycles `n`, dark-cell apical K+ count `d_K`,
and hair-bundle PMCA cycles `c`:

```text
a_K + 2*a_Ca = a_q

delta endolymph_K = a_K + d_K
delta hair_K      = -a_K - h_K
delta perilymph_K = h_K - 2*p - n
delta dark_K      = 2*p + n - d_K

delta endolymph_Ca = a_Ca + c
delta hair_Ca      = -a_Ca - c

delta perilymph_Na = 3*p - n
delta dark_Na      = -3*p + n
delta perilymph_Cl = -2*n
delta dark_Cl      = 2*n

delta dark_ATP4- = -p
delta dark_H2O   = -p
delta dark_ADP3- = p
delta dark_HPO4  = p
delta dark_H+    = p

delta endolymph_H+ = -c
delta hair_ATP4-   = -c
delta hair_H2O     = -c
delta hair_ADP3-   = c
delta hair_HPO4    = c
delta hair_H+      = 2*c

PMCA outward elementary carriers = c
membrane outward carriers = sum(conductive path carriers) + c
```

Every successor quantity is calculated from the same predecessor. A mismatch,
arithmetic overflow, or negative successor refuses the entire transition; no
partial material update is committed. Negative extents express exact reversal
for falsification and restart testing. They do not assert that the biological
transporters reverse under all physiological conditions.

## Conserved quantities

The executable proof preserves:

```text
total K across endolymph + hair cell + perilymph + dark cell
total Ca across endolymph + hair cell
total Na across perilymph + dark cell
total Cl across perilymph + dark cell
total adenylate molecules across hair and dark cells: ATP + ADP
total phosphoryl groups across hair and dark cells: 3*ATP + 2*ADP + HPO4
total represented electric charge
```

The ATP chemical equation declares the above-pH-7 species basis
`ATP4- + H2O -> ADP3- + HPO4(2-) + H+`. Actual cytosol contains a pH- and
Mg2+-dependent mixture. This candidate does not pretend to contain that
unimplemented speciation, ATP regeneration, or thermodynamic rate law.

## What the executable model proves

The reached example has simultaneous apical -74,898 and basolateral +74,898
conductive carriers in one millisecond. An accounting partition of -74,896 K+
and -1 Ca2+ is used only to falsify the equations; it is not mounted anatomy.
One PMCA cycle restores that Ca2+ and contributes +1 electrogenic carrier.
With 24,966 dark-cell pump cycles, 24,966 NKCC1 cycles, and 74,898 dark-cell
apical K+ events, the same atomic successor closes the K+ return path while
retaining every nonzero reaction extent.

The isolated target passes 71/71 tests. It proves quiescence, exact reversal,
species conservation, charge conservation, active-transport membrane coupling,
atomic depletion refusal, fixed 336-byte residency, byte-exact restart, and
100,000 transitions without age-dependent state growth. The rejected
source-retirement gate passes 2/2.

It does not prove reaction kinetics, K+/Ca2+ selectivity, Type II voltage
gating, proton removal, ATP regeneration, full fluid-brain support, synaptic
release, neuronal settlement, deployment, or cognition.

## Sources

- Nin et al., vestibular endolymph K+ maintenance and dark/transitional-cell
  transport, <https://pmc.ncbi.nlm.nih.gov/articles/PMC6633285/>.
- Wilms et al., shared K+-secretory molecular machinery,
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC5041087/>.
- Carmosino et al., physiological 3 Na+:2 K+:1 ATP Na+/K+-ATPase stoichiometry,
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC10480117/>.
- Chew et al., NKCC 1 Na+:1 K+:2 Cl- stoichiometry,
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC6856059/>.
- Yamoah et al., hair-bundle PMCA calcium extrusion,
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC6792544/>.
- Hill et al., vestibular hair-bundle PMCA2 and obligatory H+ countertransport,
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC6674470/>.
- IUBMB thermodynamic nomenclature, ATP hydrolysis chemical-species equation,
  <https://iubmb.qmul.ac.uk/thermod/th1t3.html>.
