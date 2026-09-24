# Lever 4 Specification: Deterministic Pursuit Mechanisms
## Domain Proving Ground: Guala Cognitive Substrate

---

### 1. Architectural Authority and Physical Context

Guala's cognitive substrate is the proving ground for Deterministic Structural Field AI (DSF-AI). As defined in canonical architecture (`AGENTS.md` and `GEMINI.md`), cognition emerges from deterministic basin physics—not probabilistic machine learning, heuristic smoothing, or artificial goal scripts.

A1's empirical **Pursuit Milestone** establishes the acceptance criterion for sustained activity:
> *"Demonstrate one experience-grown pursuit that survives a distraction, resumes when appropriate, and stops or changes when its real consequence changes—without a supplied action list, semantic intent label, or forced duration."*

This specification maps the **Five Pursuit Mechanisms** directly into the canonical single-clock ($\Delta t = 250\,\text{ms}$) loop of [`dsf_ai_service/guala_functional_organism.py`](../dsf_ai_service/guala_functional_organism.py).

---

### 2. Physical Invariants and Boundary Conditions

1. **Single Canonical Clock ($\Delta t = 250\,\text{ms}$)**:
   Multi-beat persistence (2–10 seconds) does not require separate clock loops or multi-threaded temporal nesting. It is governed strictly by state retention within `self._state` across consecutive discrete beats.
2. **Zero Semantic Intent Enums / Scripted Action Stacks**:
   Programmer-supplied goal enums (`IntentCategory.HUNGER_FORAGE`, etc.) and canned motor plans are forbidden. The test harness [`dsf_ai_service/guala_hierarchical_stack.py`](../dsf_ai_service/guala_hierarchical_stack.py) remains strictly quarantined as test-only.
3. **Conserved Physical Grounding**:
   Every pursuit binds to a concrete physical object present in `conserved_objects` (spatial permanence) and is energized by real somatic drive tensions (deficit, contact pressure, nociceptive gradients).
4. **Consequence Authority**:
   A pursuit is reinforced, redirected, or collapsed exclusively by verified physical interactions (intake, touch contact fraction, motor refusal, physical collision, or displacement stalls).

---

### 3. Detailed Mechanism Specifications

```
+-----------------------------------------------------------------------------------+
|                            CANONICAL BEAT (250 ms)                                |
|                                                                                   |
|  [Sensory Streams] ---> [L0-L4 Structural Kernel] ---> [Somatic Drives & Deficits]|
|                                                                 |                 |
|                                                                 v                 |
|  [Fast Reflex Interrupts] (Thermal/Contact/Acoustic)   [Attractor Matching]       |
|            |                                                    |                 |
|            v                                                    v                 |
|   {Preempt / Suspend} <---------------------------- {Active Pursuit Basin}        |
|            |                                                    |                 |
|            v                                                    v                 |
|     (Reflex Act)                                         (Biased Motor Act)       |
|            |                                                    |                 |
|            +-----------------------+----------------------------+                 |
|                                    |                                              |
|                                    v                                              |
|                      [Physical World Actuation]                                   |
|                                    |                                              |
|                                    v                                              |
|                       [Verified Physical Outcome]                                 |
|                   (Intake / Collision / Refusal / Move)                           |
|                                    |                                              |
|                                    v                                              |
|                      [Consequence Feedback & Credit]                              |
|                    {Reinforce / Adapt / Collapse Pursuit}                         |
+-----------------------------------------------------------------------------------+
```

#### Mechanism 1: Retained State Representation (`active_pursuit`)

The organism maintains an explicit structural pursuit field in `self._state["active_pursuit"]`:

```python
{
    "target_entity_id": str,          # Physical object ID tracked in conserved_objects
    "drive": str,                     # Somatic tension: "hunger", "contact", "exploration"
    "initiation_tick": int,           # Monotonic organism tick at basin formation
    "accumulated_beats": int,         # Monotonic count of beats active
    "interrupted": bool,              # True if suspended by fast reflex preemption
    "interruption_reason": str | None,# Fast reflex cause ("thermal_nociception", "contact_shock")
    "interruption_beats": int,        # Count of consecutive beats spent in interrupted state
    "consecutive_stalls": int,        # Consecutive beats with zero displacement / refusal
    "last_distance_mm": float,        # Euclidean distance to target at prior beat
    "prior_valence": float,           # Historical valence retrieved from episodic memory
}
```

- Initialized to `None` in `genesis()`.
- Fully serialized within `encoded()` and restored in `decoded()`, ensuring persistence across checkpoint cycles and service restarts.

#### Mechanism 2: Update Law (Deterministic Attractor Formation)

Pursuit formation is an emergent state transition when internal somatic drive tension couples with spatial memory:
1. When internal tension exceeds resting thresholds:
   - Hunger: $\text{deficit} > 0.05$
   - Contact Affection: $\text{contact\_pressure} > 0.15$
   - Exploration: $\text{boredom} > 0.30$
2. For each entity $e \in \text{conserved\_objects}$:
   Retrieve episodic valence $V(e) = \text{meanings}[e][\text{drive}]$.
   Calculate spatial distance $D(e) = \|\vec{x}_{\text{guala}} - \vec{x}_e\|$.
   Compute the deterministic attractor potential:
   $$\Phi(e) = \text{Tension}(\text{drive}) \cdot \max(0.1, V(e)) \cdot \frac{1}{1 + \frac{D(e)}{1000.0}}$$
3. If no pursuit is active (or previous pursuit collapsed) and $\max_e \Phi(e) \ge \Phi_{\text{threshold}}$:
   Bind `active_pursuit` to the maximal attractor entity $e^*$.

#### Mechanism 3: Dynamic Action Influence (Biasing Canonical Selection)

Rather than executing a canned script of steps, `active_pursuit` injects continuous potential gradients into candidate motor affordance scoring:
1. In `_choose()` and affordance generation:
   - If `active_pursuit` is active and `not interrupted`:
     * Compute vector $\vec{v} = \vec{x}_{\text{target}} - \vec{x}_{\text{guala}}$ and distance $D = \|\vec{v}\|$.
     * If $D > \text{reach\_distance}$ ($400\,\text{mm}$):
       Affordances that reduce distance (`toward_thing`, `step`, `turn_toward`) receive structural affinity bias proportional to $\Phi(e^*)$.
     * If $D \le \text{reach\_distance}$:
       Affordances that manipulate the entity (`reach_hand`, `grasp`, `bite`, `touch`) receive dominant execution priority.
2. Obstacle and portal geometry are respected naturally: if direct line-of-sight is blocked, environmental affordances (`toward_door`) retain normal spatial routing without programmatic override.

#### Mechanism 4: Prompt Interruption & Appropriate Resumption

1. **Fast Reflex Preemption**:
   In `decide()`, high-frequency nociceptive or shock signals bypass pursuit evaluation:
   - Thermal hazard: $T_{\text{skin}} \ge 340.0\,\text{K}$
   - Cutaneous shock: $P_{\text{contact}} \ge 0.95$
   - Acoustic blast: $A_{\text{spl}} \ge 0.90$
   When reflex triggers:
   - Reflex act is dispatched immediately (`release_grasp`, `step_back`, `startle_freeze`).
   - `active_pursuit["interrupted"] = True`
   - `active_pursuit["interruption_reason"] = "nociception"`
   - The pursuit basin is preserved, not destroyed.
2. **Appropriate Resumption Invariants**:
   When reflex conditions subside:
   - Check 1: Is `target_entity_id` still in `conserved_objects`? (Target permanence)
   - Check 2: Is somatic tension still unresolved? (Drive permanence)
   - Check 3: Is `interruption_beats` $\le 16$ beats ($4.0\,\text{seconds}$)? (Temporal retention boundary)
   If ALL pass:
   - Clear `interrupted = False`.
   - Pursuit **resumes** immediately on the very next beat.
   If ANY fail:
   - Pursuit collapses cleanly (`active_pursuit = None`).

#### Mechanism 5: Consequence-Driven Termination & Adaptation

In `commit()`, real physical receipts govern pursuit closure and episodic memory update:
1. **Physical Satisfaction (Success)**:
   - Intake occurs: `intake_micrograms > 0`
   - Contact achieved: `contact_fraction > 0.3`
   - Outcome:
     * Credit episodic memory: $\text{meanings}[e][\text{drive}] \leftarrow \text{meanings}[e][\text{drive}] + 0.2$
     * Somatic deficit drops.
     * Terminate pursuit cleanly: `active_pursuit = None`.
2. **Physical Impossibility / Reality Feedback (Stall & Refusal)**:
   - If motor act produced an explicit physics refusal (`refusal is not None`) OR
   - Distance change $\Delta D = |D_t - D_{t-1}| \le 10\,\text{mm}$ while attempting approach:
     `active_pursuit["consecutive_stalls"] += 1`.
   - When `consecutive_stalls >= 6` ($1.5\,\text{seconds}$ of zero progress):
     * Target is recognized as physically obstructed or unreachable.
     * Update episodic memory: $\text{meanings}[e][\text{drive}] \leftarrow \max(0.0, \text{meanings}[e][\text{drive}] - 0.3)$.
     * Register entity in temporary `unreachable` registry.
     * Terminate pursuit: `active_pursuit = None`.
     * The organism falls back to alternative environmental affordances without looping.

---

### 4. Verification and Empirical Milestones

The automated verification suite [`tests/test_experience_grown_pursuit.py`](../tests/test_experience_grown_pursuit.py) executes six empirical proofs:
1. **Experience-Grown Formation**: Organism forms pursuit of food when hungry based on prior episodic valence, without supplied action list.
2. **Multi-Beat Persistence**: Pursues target across 20 consecutive beats ($5.0\,\text{s}$) on single 250ms clock.
3. **Interruption & Resumption**: Thermal nociceptive shock interrupts approach; upon cooling, organism resumes pursuit of the same target.
4. **Target Disappearance Abandonment**: When target is removed during distraction, organism does not pursue empty coordinates; pursuit collapses.
5. **Consequence Satisfaction**: Ingestion decreases deficit, reinforces episodic memory, and terminates pursuit.
6. **Physical Stall Collapse**: Persistent obstacle causing 6 consecutive stalls collapses pursuit and updates valence, preventing infinite loops.
