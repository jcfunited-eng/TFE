# Lever 4 Architectural Source Mapping: Existing Experience Producers, Retained State, and Action Consumers

---

### 1. Ground Truth Accounting: Rejection of Candidate `7d1db1e43`

Following A1's formal architectural rejection (`collaborative_todo.md:19184–19212`), candidate `7d1db1e43` is explicitly rejected. It introduced synthetic shortcuts that contradicted core architectural constraints:
1. **Scalar Proxy**: Targets were selected by an authored scalar potential $\Phi = \text{Tension} \cdot V \cdot \frac{1}{1 + D/1000}$ with an arbitrary activation threshold ($0.12$), arbitrary clipping ($0.1\text{--}2.0$), and default valence ($0.5$), bypassing 7-field L0–L4 structural kernel evaluation.
2. **Supplied Action Priorities & Semantic Labels**: It stored hardcoded semantic string labels (`"hunger"`, `"contact"`) and selected actions from hardcoded priority lists (`["bite", "take", "grasp", "touch"]` and `["toward_food", "toward_person", "toward_thing", "toward_door", "step"]`).
3. **Forced Durations & Magic Timers**: It relied on arbitrary counters: 16-beat interruption expiration, 6-stall collapse counter, and 120-tick cooldown exclusion.
4. **Disconnected Experience Store**: It invented a new object-and-drive score table (`meanings[entity_id][drive]`) instead of connecting to Guala's actual episodic memory architecture (`moments`, `meanings[key]`, `acts`, `learned`).
5. **Synthetic Test Injection**: Tests manually injected `meanings['apple-near'] = {'hunger': 0.8}`, set `_pain = 0.85` and `interrupted = True` directly on state, and preloaded stall counters rather than demonstrating experience-grown behavior through the physical loop.

Per A1's directive, this candidate is not to be tuned or promoted. The implementation has been reverted in source to clean baseline (`83281f75d`), and the rejected test suite removed.

This document executes the required single next item: **an exact architectural source map of existing experience producers, retained state schemas, action consumers, and the precise missing connections in `dsf_ai_service/guala_functional_organism.py`.**

---

### 2. Exact Map of Existing Experience Architecture

The existing cognitive loop in `dsf_ai_service/guala_functional_organism.py` already possesses an authentic, grounded experience-retention pipeline consisting of four stages:

```
[Instantaneous Senses] 
         |
         v
1. EXPERIENCE PRODUCERS:
   - _measure() / _kernel()         --> Multi-modal streams & L0-L4 discrete sign gates
   - _form_moments()                --> Discrete moments on acoustic events, somatic shock, or phase shifts
   - _settle()                      --> Values last act by bodily need drops (intake, comfort, sound, burn, pain)
   - commit()                       --> Records physical intake / pain into moments[last_moment]["acts"]
   - _dream_moment() / _dream()     --> Sleep consolidation of salient/recurrent moments & acts
         |
         v
2. RETAINED STATE (self._state):
   - moments                        --> Day store of episodic moments (key = hash(event|held|figure))
   - meanings                       --> Consolidated cross-day episodic meanings
   - acts                           --> Day store of structure keys, tries, net values, and successor transitions
   - learned                        --> Consolidated cross-day situation-keyed action values
   - conserved_objects              --> Spatial object permanence register (position, room, sight, confidence)
         |
         v
3. ACTION CONSUMERS (_choose):
   - evaluate_anticipatory_consequence() --> Vetoes (<-0.35) or promotes (>0.35) acts matching meanings
   - Predictive Foresight                --> One-step successor evaluation: mean_imm + 0.5 * max(next_means)
   - Structural Boredom                  --> Evacuates saturated basins toward negative space (doors)
   - Structural Uncertainty (U*_k > 0)   --> Directs least-tried exploratory selection
         |
         v
4. MOTOR ACTUATION & WORLD FEEDBACK
```

#### A. Existing Experience Producers

1. **Somatic Measurement & Kernel Invariants (`_measure`, `_kernel`)**:
   - Location: `guala_functional_organism.py:1452–1590`
   - Inputs: `Sensed` streams (active: focal sight, wide luminance, ear hops; passive: odour concentration, taste residue, skin contact fraction, touch warmth, interoceptive deficit and sleep pressure).
   - Operation: Computes 64-beat window across `STREAMS`. Calls UF L0–L4 structural kernel (`compute_sev_series`, `segment_gates`, `interpret_gates`, `compute_resonance`, `compute_directional_signal`, `compute_dsf`).
   - Output: 7-atom signature string (e.g. `B+ S- M0 R0 U+ C+ P-`), gate count, and discrete regime key.

2. **Moment Formation (`_form_moments`)**:
   - Location: `guala_functional_organism.py:2082–2161`
   - Trigger: Closed sound event, somatic shock/pain (`compute_somatic_salience > 0`), or visual/held figure phase shift.
   - Key Law: Deterministic invariant hash:
     $$\text{key} = \text{sha256}(f"{event}|{held}|{figure}")[:16]$$
   - State Produced:
     ```python
     moments[key] = {
         "count": int,
         "tick": int,
         "held": str,        # "texture/warmth" in eighths
         "figure": str,      # sight figure key from figure_of_disc
         "room": str,        # room region ID
         "context": list,    # [hunger, taste, skin_contact] in eighths
         "next": dict,       # {successor_key: transition_count}
         "acts": dict,       # {act: [tries, net_valence]}
         "fed": int,         # intake occurrences
         "source": str,      # "heard" | "own" | "visual"
         "salience": float,  # Gamma_salience from internal somatic deltas
     }
     ```

3. **Bodily Need Settlement (`_settle`, `commit`)**:
   - Location: `guala_functional_organism.py:2225–2297` and `commit()` lines `2440–2530`
   - Operands:
     * Intake value: $\text{deficit} \cdot (\text{intake} > 0)$
     * Novel structure value: $(1 - \text{deficit}) \cdot (1 - \text{sleep\_ratio}) \cdot \text{novel}$
     * Sound value: $(1 - \text{sleep\_ratio}) \cdot \text{sound\_now}$
     * Contact comfort: $\text{skin\_now} \cdot \text{warmth} + \text{contact\_ratio} \cdot (\text{skin\_now} > 0)$
     * Metabolic burn: $-\text{burn} / \text{CAPACITY}$
     * Cutaneous pain: $-\text{pain}$
   - Update: Credits $\text{acts}[key][act]$ and records successor transitions `successors[act][key_now] += 1`.
   - In `commit()`: If intake occurs during a moment's follow window, updates `moments[last_moment]["acts"]["bite"] = [tries, net_val]` and increments `fed`.

4. **Episodic Consolidation (`_dream_moment`, `_dream`)**:
   - Location: `guala_functional_organism.py:2298–2370`
   - Law (The Pool Shock Principle): High-salience moments ($\text{salience} \ge 0.65$) consolidate on a single trial ($\text{count} \ge 1$); low-salience background events require recurrence ($\text{count} \ge 2$).
   - State Produced: Merges `moments` into `self._state["meanings"][key]`, combining counts, acts, successor moments, and feedings.

#### B. Existing Retained State

1. `self._state["moments"]`: Immediate episodic buffer of waking experiences (capacity 8192).
2. `self._state["meanings"]`: Long-term consolidated semantic/episodic memory (capacity 4096).
3. `self._state["acts"]`: Day record of structural choices and successor distributions (capacity 4096).
4. `self._state["learned"]`: Consolidated situation memory (capacity 2048).
5. `self._state["conserved_objects"]`: Spatial object permanence register (capacity 64), tracking coordinates, radius, room, food status, and visual verification.

#### C. Existing Action Route (`_choose`)

In `guala_functional_organism.py:2456–2600`:
1. **Anticipatory Trajectory Reactivation (`evaluate_anticipatory_consequence`)**:
   - Compares candidate actions against `self._state["meanings"]` matching the current `sight_figure`, acoustic event, and room.
   - If mean valence $< -0.35$: action is vetoed (anticipates pain/shock).
   - If mean valence $> 0.35$ (or `bite` with `fed > 0`): action is promoted.
2. **Predictive Foresight**:
   - Evaluates recorded successor transitions in `acts[key]["successors"][a]`:
     $$\text{Score}(a) = \text{mean\_immediate}(a) + 0.5 \cdot \max(\text{next\_means})$$
3. **Structural Exploration**:
   - Governed by $U^*_k > 0$ (structural uncertainty) or every 8th visit: selects least-tried act.

---

### 3. The Missing Connections (The Causal Disconnect)

Why does the existing architecture fail to sustain an experience-grown pursuit across 2–10 seconds (8–40 beats)?

The disconnect is not a lack of memory. It stems from four specific architectural gaps between spatial permanence, episodic consolidation, and candidate affordance scoring:

```
[conserved_objects]                [meanings]
 (Spatial Permanence:              (Episodic Memory:
  Where objects are in world)       What figures mean)
         \                              /
          \                            /
           X <--- GAP 1: NO BINDING --X
                  Between conserved spatial objects
                  and episodic figure meanings
                       |
                       v
                 [_choose()]
                       |
           X <--- GAP 2: HORIZON BOUNDARY
                  Foresight evaluates only 1 step (0.25s),
                  not multi-beat trajectories (2-10s)
                       |
                       v
           X <--- GAP 3: ATTRIBUTION LEAK
                  Intake credits moment, but does not verify
                  which spatial object produced the intake
```

#### Gap 1: Disconnection Between Spatial Object Permanence and Episodic Meanings
- **Source Reality**: `conserved_objects` tracks object identity and spatial 3D coordinates ($x, y, z$). `meanings` keys episodes by visual figure hashes ($60 \times 45^\circ$ focal luminance disc), acoustic events, and held tactile state.
- **The Failure**: When Guala is hungry, she has episodic memories in `meanings` that biting a circular red figure pays with nutrition. She also has `apple` in `conserved_objects`. But there is **zero functional link** in source connecting the spatial entity in `conserved_objects` to the visual figure in `meanings`.
- **Consequence**: `evaluate_anticipatory_consequence` evaluates only what is *currently under Guala's retinal gaze* (`sight_figure`). If Guala turns her head or strides, `sight_figure` shifts to `"none"`, and the anticipatory promotion vanishes instantly on the very next beat. She cannot pursue what is not actively in her focal cone.

#### Gap 2: Foresight Horizon Boundary (1 Step vs Multi-Beat Trajectory)
- **Source Reality**: `_score(a)` in `_choose` evaluates:
  $$\text{Score}(a) = \text{mean\_immediate}(a) + 0.5 \cdot \max_{s \in \text{successors}(a)} V(s)$$
- **The Failure**: This is strictly one-step predictive foresight ($250\,\text{ms}$). If an apple is 1500 mm away, it requires 5 strides. Stepping forward does not yield immediate nutrition on step 1. At step 1, `mean_immediate("toward_food")` is 0 (or slight negative metabolic burn). The 1-step successor does not reach the feeding moment.
- **Consequence**: Without an active potential field or multi-step successor rollout that bridges the 5-stride gap, `_choose` falls back to least-tried exploratory selection or gets trapped in rotational deadlocks.

#### Gap 3: Physical Consequence Attribution
- **Source Reality**: In `_settle()` and `commit()`, when `intake > 0` occurs, nutrition is credited to `state["reserve_micrograms"]` and `moments[last_moment]["acts"]["bite"]`.
- **The Failure**: The credit attaches to whatever moment closed in the last 16 beats, but does not verify that the physical object bitten was the object that motivated the trajectory. If Guala starts toward a ball and is fed bread, the credit would attach to the ball's moment.
- **Consequence**: Causal consequence attribution leaks across objects.

#### Gap 4: Phase Space Reset on Reflex Preemption
- **Source Reality**: When a high-temperature contact occurs, the reflex in `decide()` returns `decision("release", ...)` and sets `state["pending_act"] = None`.
- **The Failure**: Because `_choose` has no continuous attractor basin or retained goal vector across beats, the entire action distribution resets to baseline exploration on the next beat. There is no structural momentum to resume the prior activity once the reflex clears.

---

### 4. Roadmap to a Valid, Un-Mocked Empirical Milestone

To demonstrate an experience-grown pursuit that satisfies A1's milestone without shortcuts:

1. **Step 1: Formalize the Physical Binding Law (Object Permanence $\leftrightarrow$ Episodic Meaning)**:
   - Define the deterministic, un-flattened structural projection between `conserved_objects` and episodic `meanings` based on verified sensorimotor history (not an authored dictionary of string names).
2. **Step 2: Connect Trajectory Reactivation to Multi-Beat Action Biasing**:
   - Extend anticipatory consequence evaluation from instantaneous retinal figures to conserved entities that match stored meanings, providing continuous potential gradients along the approach vector without hardcoded action lists.
3. **Step 3: Grounded Un-Mocked Experimental Proof**:
   - Run the ordinary loop with two identical organisms:
     * **Organism A (Naive)**: Has no prior feeding experience in `meanings`.
     * **Organism B (Experienced)**: Has encountered food, ingested nutrition, slept, and naturally consolidated the experience via `_form_moments` and `_dream_moment`.
   - Place both in the identical room encounter with food at a distance.
   - Prove that Organism B exhibits sustained approach and pursuit toward the food affordance, survives a real physical distraction (e.g. acoustic startle orienting reflex), and resumes approach, while Organism A does not.
   - Change real consequence (e.g. food is depleted) and demonstrate natural redirection without hardcoded timeouts or forced counters.
