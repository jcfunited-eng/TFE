# Guala D3 virtual-body yaw actuation law

Date: 2026-08-04

Status: isolated native body/motor mechanics candidate. It is not mounted world
authority, autonomous action, vestibular neuron, D3, release, or production.

## Architecture honesty gate

1. **Requested architecture:** Guala's body produces an exact physical motion
   that her vestibular organ can experience, without a sensory receptor
   inventing how the body moved.
2. **Current code reality:** the Python world applies a target wrapped heading
   at the end of a duration. It retains neither signed displacement nor the
   intervening path.
3. **Conflict:** yes. The current endpoint representation cannot causally drive
   a vestibular receptor.
4. **Not extended:** shortest-turn inference, instantaneous endpoint teleport,
   receptor-generated movement, random trajectory, central cognition command,
   owner, lock, database, DSF input, Krimelack input, or fluid-brain input.
5. **Single next item:** mount a signed yaw actuation in the native body/world
   successor so the physical path survives into vestibular settlement.
6. **DSF evaluation:** none; complete L0-L4 remains unchanged downstream.
7. **Declared loss:** a motor trajectory is body physics, not experience,
   memory, meaning, or a neuronal fractal.

## Exact motor law

A command supplies signed yaw displacement and exact duration. Signed
displacement preserves direction and any complete revolutions; wrapped heading
is only the body's cyclic orientation state.

The endpoint-constrained minimum-jerk polynomial is

```text
f(u) = 10u^3 - 15u^4 + 6u^5
```

Its coefficients follow from the endpoint position with zero endpoint velocity
and acceleration while minimizing integrated squared jerk. This is an explicit
algorithmic motor law, not a hidden smoothing coefficient or learned model.
The implementation evaluates the polynomial with checked integer arithmetic at
the world's existing one-millisecond mechanical lattice. Consecutive cumulative
positions form signed integer motion samples. Their sum is proved equal to the
complete commanded displacement before the successor is returned.

The body persists only wrapped yaw in `[0, 360000)` millidegrees. The transient
trajectory is a fixed-capacity 5,000-sample array, derived from the world's
existing maximum five-second material action. Neither resident nor transient
width grows with organism age.

## Separation from the vestibular organ

This mechanism creates body motion. The virtual canal only consumes the
resulting samples. The combined isolated proof is therefore:

```text
signed body actuation
  -> exact motor trajectory and wrapped body successor
  -> borrowed trajectory reaches vestibular canal
  -> canal returns signed cupular response
```

No DSF, Krimelack, neuron, fluid-brain quantity, mosaic, tutor, or semantic
label participates.

## Executable proof

`native/guala_core/src/virtual_body_yaw_motion.rs` proves:

- complete signed displacement conservation;
- correct cyclic heading across zero in either direction;
- samplewise opposing-motion symmetry;
- a direct body-trajectory-to-canal transition with no endpoint inference;
- fixed four-byte resident body state and fixed-capacity transient trajectory;
  and
- refusal of invalid heading, off-lattice/overlong duration, and invalid
  restart bytes.

This does not yet prove native world command mounting, actuator energy and
muscle mechanics, pitch/roll, linear acceleration, channel gating, membrane
current, neuronal settlement, autonomy, deployment, or production.

## Biological/algorithmic source

- Flash and Hogan, "The coordination of arm movements: an experimentally
  confirmed mathematical model," *Journal of Neuroscience* 5(7), 1985,
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC6565116/>.
