# Guala D3 virtual vestibular canal law

Date: 2026-08-04

Status: isolated native sensory-organ mechanics candidate. It is not mounted
body motor physics, receptor channel, membrane, neuron, D3, release, or
production authority.

## Architecture honesty gate

1. **Requested architecture:** actual virtual-body motion causes biologically
   grounded local sensory-organ mechanics and ultimately neuronal experience.
2. **Current code reality:** the production world stores exact yaw endpoints
   and action duration but not the signed trajectory between them; its internal
   body path misclassifies global XYZ as proprioception and marks vestibular
   state unavailable.
3. **Conflict:** yes. Endpoints cannot recover direction, revolutions,
   velocity, or acceleration.
4. **Not extended:** shortest-turn guessing, receptor-owned motion generation,
   DSF-trit drive, winding-as-current, normalized signal,
   fluid-brain-as-sensor, Python hot physics, owner, lock, database, score,
   threshold, or semantic label.
5. **Single next item:** join reached local hair-cell current to exact membrane
   charge using explicit local ion/reversal state and time.
6. **DSF evaluation:** none here; complete explicit L0-L4 remains separate and
   unchanged.
7. **Declared loss:** cupular displacement is neither DSF, Krimelack, a
   neuronal fractal, nor cognition.

## The causal layers remain separate

```text
body/motor physics
  exact signed motion trajectory
    -> vestibular sensory-organ physics
       endolymph response -> cupula/hair-bundle displacement
         -> neuronal electrical physics
            channel conductance -> ionic current -> membrane charge
              -> substrate cognition
                 full DSF -> MathLoom/Krimelack -> neuronal fractal
```

The canal consumes body motion; it never plans or generates it. Cognitive
development does not choose receptor output. Semicircular-canal endolymph is a
body sensory-organ fluid, not Guala's fluid brain. The fluid brain may later
provide local ionic, metabolic, recovery, and modulatory conditions but cannot
create motion, assign meaning, or become a mosaic member.

## Biological and physical correspondence

Semicircular canals use relative endolymph/canal-wall motion to displace the
cupula and hair bundles. Their response has fast and slow mechanical components.
The isolated candidate represents those as two local relaxation states driven
by each exact signed wall-motion sample. Their difference is the cupular
velocity-equivalent response: it rises during rotation, adapts during sustained
motion, and reverses after stopping.

The input is a bounded borrowed sequence of signed millidegrees for successive
one-millisecond world-mechanical intervals. One millidegree per millisecond is
exactly one degree per second. The trajectory must come from body mechanics;
the canal refuses an absent or overlong trajectory and has no endpoint-only
constructor.

Initial isolated reference anatomy uses explicit values:

- a 1 ms mechanical tick, fixed by the embodiment world's existing minimum
  physical action interval;
- a 6 ms fast time constant;
- a 13.2 s slow time constant; and
- a 25 nm/(degree/second) cupular gain selected from the cited biological
  model's measurement scale.

These are selected-from-biological-reference anatomy, not inferred from DSF or
adjusted to obtain a test result. Before mounting, the chosen species/age,
preparation, measurement uncertainty, and virtual anatomy must be ratified as
one physical genesis.

## Exact bounded algorithm

The body admits a one-millidegree spatial lattice and a one-millisecond time
lattice. Therefore the canal stores filtered velocity in millidegrees/second.
This is not a chosen sensory threshold: it is the finest velocity state derived
from the already-admitted body units. The earlier whole-degree/second state was
incorrect because it erased a real 1.2-degree motion's slow endolymph lag.

For each reached body step, each canal state settles:

```text
wall_velocity = signed_step_millidegrees * 1000 millidegrees/second
numerator = wall_velocity - local_velocity + retained_remainder
delta = trunc_toward_zero(numerator / (tau_ticks + 1))
local_velocity_next = local_velocity + delta
remainder_next = numerator - delta * (tau_ticks + 1)
```

The signed remainder conserves sub-quantum influence without an age-growing
rational denominator. Its magnitude remains below its fixed anatomy-bound
denominator. Cupular displacement converts the relative filtered velocity back
through the exact 1000 millidegrees/degree unit relation before applying gain.

Persistent state is four signed 64-bit integers regardless of organism age.
Work is proportional only to reached body-motion samples, never a poll of the
organism, and is bounded by the existing five-second action boundary: at most
5,000 local native updates.

## Current executable proof

The isolated candidate proves:

- exact quiescence at rest;
- conservation of complete supplied positive or negative signed motion;
- opposing-motion symmetry;
- an opposing physical response after rotation stops;
- reached-tick transduction of a 1.2-degree movement without erasing slow lag;
- byte-exact restart preserving the next physical transition;
- fixed 32-byte resident state through 100,000 recurrent transitions; and
- refusal of absent/overlong trajectories and invalid restart state.

This does not prove ion inventories, reversal potential, membrane charge,
neuronal D1, Krimelack dynamics, mosaic formation, fluid-brain transport,
embodiment command migration, resident mounting, deployment, or production.

## Sources

- Rabbitt and Damiano, "A hydroelastic model of macromechanics in the
  endolymphatic vestibular canal," *Journal of Fluid Mechanics* 238, 1992,
  <https://doi.org/10.1017/S0022112092001745>.
- Selva, Oman, and Stone, "Mechanical properties and motion of the cupula of
  the human semicircular canal," *Journal of Vestibular Research* 19, 2009.
- Rabbitt, "Semicircular canal biomechanics in health and disease," *Journal
  of Neurophysiology* 121, 2019,
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC6520623/>.
