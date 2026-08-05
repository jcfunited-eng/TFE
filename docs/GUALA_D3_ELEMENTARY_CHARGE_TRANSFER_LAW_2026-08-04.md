# Guala D3 elementary-charge transfer law

Date: 2026-08-04

Status: isolated native current-to-carrier candidate. It is not a membrane,
ion inventory, fluid manager, neuron, D3 completion, deployment, or production.

## Architecture honesty gate

1. **Requested architecture:** reached receptor current causes discrete local
   charge transfer through physical units, not a sign label or code trigger.
2. **Current code reality:** the isolated yaw/canal/hair-cell path now produces
   exact macroscopic current; production still reports physical transduction
   unavailable.
3. **Conflict:** yes until transferred carriers update conserved local ion
   inventories and membrane charge, and that state reaches the resident neuron.
4. **Not extended:** normalized signal, integer-rounded channel expectation,
   stored polarity, threshold firing, DSF-to-current, winding-to-ion, owner,
   lock, database, scheduler, Python callback, or semantic meaning.
5. **Single next item:** apply emitted signed carriers to paired local ion pools
   and membrane charge with explicit capacitance and restorative transport.
6. **DSF evaluation:** none; complete explicit L0-L4 remains separate and
   unchanged.
7. **Declared loss:** carrier transfer is not DSF, Krimelack, a neuronal
   fractal, or cognition.

## Physical and algorithmic law

The SI defines elementary charge exactly:

```text
e = 1.602176634e-19 C
  = 801088317 / 5000000000000 fC
```

For outward-positive current `I` in picoamperes and reached duration `dt` in
microseconds:

```text
Q_fC = I_pA * dt_us / 1000
ideal_carriers = Q_fC / e_fC
accumulated = predecessor_phase + ideal_carriers
emitted_carriers = trunc_toward_zero(accumulated)
successor_phase = accumulated - emitted_carriers
```

`successor_phase` is always a proper signed fraction with magnitude below one.
It is a deterministic sigma-delta phase for converting a measured continuous
ensemble current into discrete carrier events. It is not claimed to be a
fractional electron or ion. No charge is discarded: emitted whole carriers
plus retained phase equal the exact integrated ideal current.

The interval is reached causal time supplied by body/sensory mechanics. There
is no polling clock. The existing physical action boundary limits one call to
at most five seconds. Persistent phase is one signed 128-bit numerator and one
unsigned 128-bit denominator regardless of organism age.

## Executable proof

The isolated native tests prove:

- exact conversion of `-12 pA` over `1 ms` to `-74,898` emitted elementary
  charges plus its exact conserved residual phase;
- exact quiescence at zero current;
- samplewise symmetry for opposing currents;
- direct use of the reached measured hair-cell current;
- exact aggregate conservation through 100,000 recurrent intervals with fixed
  residency; and
- refusal of absent/overlong reached time or an invalid predecessor phase.

The complete isolated D3 physics target passes 54/54 tests, and the rejected
direct-winding source retirement gate passes 2/2. These are local proofs only.

## Unresolved biological boundary

The emitted count does not yet identify K+, Ca2+, or another carrier and does
not yet debit an endolymph pool, credit cytosol, change membrane charge, drive
restorative basolateral transport, or consume metabolic support. Those belong
to the next local ion/membrane/fluid transition. The fluid brain may condition
and replenish those local quantities; it may not fabricate the sensory event
or its meaning.

## Sources

- BIPM, *SI Brochure*, exact elementary charge definition,
  <https://www.bipm.org/en/publications/si-brochure>.
- Ohmori, chick vestibular mechanotransduction conductance and current,
  <https://pubmed.ncbi.nlm.nih.gov/2582113/>.
