# Guala D3 rejection: selected linear vestibular hair-cell gate

Date: 2026-08-04

Status: rejected architecture. This document is a correction record, not an
executable law, release authority, deployment claim, or production authority.

## Architecture honesty gate

1. **Requested architecture:** exact local sensory physics derived from
   conserved quantities, measured biological mechanisms, or exact algorithmic
   functions that preserve those mechanisms.
2. **Current code reality:** the rejected candidate selected 600 nm as full
   mechanotransduction activation, derived a linear slope from that selection,
   and clamped the resulting fraction to zero and one.
3. **Conflict:** yes. The selected endpoint and derived slope were not measured
   finite-state channel kinetics and therefore introduced an arbitrary rule.
4. **Mechanisms not extended:** the selected endpoint, linear gate, clamps,
   fractional channel occupancy as literal anatomy, stochastic draws,
   interpolated tables, fitted fallback curves, or DSF-derived channel gating.
5. **Single exact next item:** determine an exact finite Type II vestibular
   hair-cell conformational transition law from a named biological preparation,
   or leave the gate explicitly unavailable.
6. **DSF evaluation:** none. This correction neither evaluates nor reduces the
   complete DSF field, and L0-L4 remains unchanged.
7. **Declared loss:** the isolated candidate no longer claims body-to-channel
   transduction. Exact body mechanics, canal mechanics, elementary charge,
   membrane capacitance, conductive balance, and conserved vestibular material
   remain separate candidates; their existence does not fill this missing law.

## Why the candidate was rejected

The source preparation reports a macroscopic current-displacement relationship,
an estimated channel population, and approximate operating behavior. It does
not determine that every finite channel is open at exactly 600 nm or provide a
complete exact transition law for each channel's reached conformational state.

A Boltzmann fit or ensemble open fraction is a population expectation. It does
not specify which integer number of channels changed state in this particular
deterministic organism transition. Multiplying a finite channel count by that
fraction can produce a non-integer expected population; retaining it without
rounding does not turn it into conserved physical channel state.

The rejected code therefore proved only the internally consistent consequences
of a selected curve. It did not prove the biological gate. Its source file,
dependent integration test, and former apparent-authority document are retired
and protected by the rejected-source test.

## Admissible replacement boundary

An admissible replacement must name its preparation and represent finite
channel conformational populations as integer state. Every reached transition
must follow an explicit physical or biochemical event law with units, preserve
population and material conservation, remain quiescent without a reached
cause, and reproduce exactly across restart. If the measured evidence cannot
determine that transition, the correct state is `unavailable`, not a selected
coefficient, threshold, probability draw, or compatibility rule.

## Sources examined

- Ohmori, “Gating properties of the mechano-electrical transducer channel in
  the dissociated vestibular hair cell of the chick,” *Journal of Physiology*
  387, 1987, <https://pubmed.ncbi.nlm.nih.gov/3656183/>.
- Masetto et al., “Membrane properties of chick semicircular canal hair cells
  in situ during embryonic development,” *Journal of Neurophysiology* 83(5),
  2000, <https://pubmed.ncbi.nlm.nih.gov/10805673/>.
