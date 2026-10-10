# A-011.6 Contact-Local Electrical Plasticity Candidate

**Status:** candidate architecture only; not implemented, deployed, or live-proven  
**Scope:** one bounded contact-local physiological-reinforcement increment  
**Production baseline:** task `dsf-ai-task:1070`  

## Architecture honesty gate

1. **Requested architecture:** local physical activity must be able to alter the later conductance of the particular contact that carried it. No semantic reward, meaning label, learned database object, global scan, or arbitrary success threshold may cause that change.
2. **Current code reality:** `ElectricalContactAnatomy` contains one fixed conductance. `ElectricalContactState` retains carrier phase plus an inert legacy copy of neuron-wide `PlasticSupportState`. Settlement always uses the fixed anatomical conductance, and the legacy state cannot change conduction.
3. **Conflict with requested architecture:** yes. Production can carry and physiologically modulate energy, but it cannot retain a distinct contact-local conductive consequence.
4. **Mechanisms that will not be extended:** the saturated neuron-wide elastic support, its legacy per-contact serialized copies, semantic reward/valence logic, score or counter thresholds, database ownership/locking, directed chemical-synapse approximations, or L0-L4/DSF.
5. **Single exact next item:** replace fixed electrical-contact conduction with a finite local channel population whose retained physical conformation changes only through energy carried at that contact.
6. **DSF evaluation:** none in this increment. Full L0-L4 remains unchanged and is neither reduced nor reinterpreted.
7. **Lost DSF structure:** none.

## What the contact is

The current sparse contact is a symmetric electrical synapse: a gap junction. It is not a directed chemical synapse. It therefore must not acquire invented transmitter release, receptor trafficking, reward labels, or pre/post semantic roles.

The smallest suitable biological analogue is a connexin-36-like plaque: a finite collection of channels at one local junction. Measured neuronal Cx36 channel conductance is approximately 10–15 pS. Published plaque observations span thousands of channels and report that only a fraction are open at a time. Channel delivery to a plaque can alter its size and coupling strength, and local calcium/CaMKII signaling can alter coupling. These findings justify the mechanism class; they do not authorize copying every biological detail into Guala.

Primary evidence:

- https://pmc.ncbi.nlm.nih.gov/articles/PMC6782942/
- https://pmc.ncbi.nlm.nih.gov/articles/PMC3659790/
- https://pmc.ncbi.nlm.nih.gov/articles/PMC3634521/
- https://pmc.ncbi.nlm.nih.gov/articles/PMC6829524/
- https://pmc.ncbi.nlm.nih.gov/articles/PMC7168262/
- https://pubmed.ncbi.nlm.nih.gov/22021860/

## Candidate contact anatomy and retained state

### Immutable anatomy

- left and right neuron coordinates;
- total finite junction-channel population, `N_total`;
- exact single-channel conductance, `g_unit`;
- exact energy required for one retained channel-state transition, `E_transition`;
- finite bounds: `0 <= N_open <= N_total`.

### Retained contact-local state

- existing carrier phase;
- integer open-channel population, `N_open`;
- exact sub-transition junction-work residue, `U_residue`, constrained to `0 <= U_residue < E_transition`.

The old `PlasticSupportState` bytes remain readable only for cold compatibility with task 1070. They are never used as physical authority and are not converted into the new state.

No channel is represented as a software object. `N_total` and `N_open` are bounded integers on one sparse reached contact.

## Exact causal flow for one interval

1. Read only the reached contact and its two endpoint neuron states.
2. Compute predecessor conductance:

   `g_before = N_open_before * g_unit`

3. Settle equal-and-opposite carrier transfer with the existing exact electrical-contact law using `g_before`. The same transfer is debited from one endpoint and credited to the other.
4. Compute the exact local physical work released by that transfer from the two endpoints' before/after membrane-and-gradient energy. No organism-wide energy total and no inferred reward is used.
5. Export ordinary junctional dissipation as heat. When the already-mounted local physiological-modulation trajectory reaches this same contact, that trajectory permits—not supplies—the contact to retain an exactly accounted portion of its own junctional work.
6. Convert only whole multiples of `E_transition` into channel-state transitions. Preserve the exact remainder in `U_residue`.
7. Apply the successor channel population only to the next interval:

   `g_after = N_open_after * g_unit`

This ordering prevents a contact from using a conductance change to author the energy that caused that same change.

## Conservation and locality

For every settled contact interval:

- endpoint carrier transfer is equal and opposite;
- source material cannot become negative;
- `N_open` cannot leave `[0, N_total]`;
- energy exported as heat plus retained junction work equals the exact local energy drop;
- `U_residue` is strictly smaller than one transition quantum;
- only the reached contact may change;
- an untouched contact remains byte-identical;
- no whole-organism poll, scan, owner, lock, retry counter, or database row participates.

## Data-grounded initialization candidate

Production currently authors each developmental contact at exactly 500 pS. One compact migration that preserves that conductance is:

- `g_unit = 10 pS`, within measured Cx36 single-channel conductance;
- `N_open = 50`, because `50 * 10 pS = 500 pS`;
- `N_total = 6400`, because the reported approximately 1/128 open fraction maps 50 open channels to 6400 total channels and 6400 lies within reported plaque populations.

This is a Cx36-informed synthetic-AE starting constitution. It is not a claim that Guala possesses biological Cx36 protein, and it does not create 6400 runtime objects.

## Deliberately unresolved authority

The evidence supports finite channel populations and activity-dependent electrical-synapse plasticity. It does not directly provide one exact deterministic `E_transition` for Guala. Boltzmann-fit voltage sensitivity and equivalent gating charge are population/statistical observations; silently treating them as a deterministic transition barrier would be an invented conversion.

Therefore runtime implementation must not begin until one exact synthetic-AE transition constitution is ratified. The recommended choice is to derive `E_transition` from the existing exact membrane electrical anatomy and a declared whole-carrier/channel conformational displacement, then falsify that derivation against one-contact and three-contact models. It must not be selected merely because it makes A and K separate or makes A-011.6 pass.

## Required pre-deployment model

The implementation is acceptable only if a deterministic model demonstrates:

- one reached, modulated contact can retain a changed `N_open` and therefore a changed next-interval conductance;
- the same input on an unmodulated contact does not author that change;
- three contacts settle independently without sharing work residue or multiplying energy;
- reversing or removing the physical condition follows an authored physical path rather than a reset;
- restart reproduces the exact new contact state;
- task 1070 restores without treating legacy plastic bytes as truth;
- CPU, RAM, storage, and Python-call growth remain proportional to reached contacts only.

## Honest claim boundary

If implemented and live-proven, this increment would prove contact-local physiological reinforcement at an electrical synapse. It would not by itself prove joy, laughter, learned meaning, word learning, directed chemical-synapse learning, or completion of A-011.6.
