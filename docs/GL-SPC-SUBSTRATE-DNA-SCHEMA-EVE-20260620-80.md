# GL-SPC-SUBSTRATE-DNA-SCHEMA-EVE-20260620-80

**To:** Joe (canonical/architectural authority) + c1 (implementer)
**From:** Eve
**Date:** 2026-06-20
**Status:** Schema proposal. Joe ratifies before Stage 3 (Folding Division as neurogenesis) starts.
**Scope:** What substrate DNA encodes, how a daughter neuron reads it at the fold moment, what comes from DNA vs from parent vs from input. Stage 1 and Stage 2 do not use DNA — this spec is what Stage 3 needs.

---

## 0. Plain language: what DNA is

Substrate DNA is the genome of the whole brain. ONE file. Every neuron everywhere in the substrate reads the same DNA. What makes one neuron different from another is not different DNA — it's which DNA *option* got expressed when that neuron spawned, and that choice is made by the input it received at the moment of its birth.

DNA is not parameters to tune. DNA is a finite menu of structural options. When a parent neuron's ψ-lattice can't hold its current state, it folds. The overflow signal — the part the parent couldn't represent — becomes the input that picks one option from the menu. The daughter is whatever the menu plus the input said it should be.

Sur's-ferrets discipline: the menu is fixed; the choice is driven by input.

---

## 1. What DNA encodes (three layers)

### Layer 1: GENOME — the menu

A finite list of *archetypes* the substrate can grow. Each archetype is a complete neuron specialization template. An archetype names:
- which **krimelack class** it uses (modal: sight/sound/smell/taste/touch; role: subject/verb/object/modifier; composition: language)
- a **law-field weight profile** (which constraints the daughter's ψ-lattice Hamiltonian weights heavily)
- a **coupling preference** (k_intra vs k_inter neighbor distribution — local-dense vs bridging vs hemisphere-crossing)

Each archetype also carries a **signature DSF** — an 8-dimensional kernel-output profile (D_k, M_k, R_rev_k, U*_k, C_k, P_k, B_k, S_UF) that this archetype is the right answer to. Signature DSFs are not invented numbers. They are computed once at DNA-construction time by running canonical example inputs through the existing L0-L4 kernel and capturing the resulting DSF profile. They are empirical fingerprints, not tunables.

### Layer 2: REGULATORY — how the daughter chooses

When a fold event fires, the daughter must pick one archetype from the genome. The rule is cosine similarity in DSF-8 space:

```
selected_archetype = argmax over archetypes:
    cosine_similarity(overflow_signal.DSF, archetype.signature_DSF)
```

One winner, deterministic, no thresholds, no tuned weights. The daughter becomes whichever archetype's signature DSF best matches the input that triggered her birth.

If the overflow DSF is degenerate (all signatures equidistant), tie-break is lowest archetype index in the genome list. Determinism rule from Master Spec carries over.

### Layer 3: INHERITANCE — what carries from parent

When the daughter spawns:

- **ψ-lattice initial state**: the overflow vector itself, normalized. The daughter starts knowing exactly the thing the parent couldn't hold.
- **Coupling topology**: daughter inherits half of the parent's neighbor list (K/2 closest by neuron_id ring distance). The other K/2 spots fill during the first cluster step from neighbors of the daughter's new position (Stage 3 — Stage 4 may use input-driven coupling).
- **Krimelack base frequency ω₀**: inherited from the archetype's krimelack class, then *calibrated* to the parent's recent ω_krim mean (so the daughter operates in the same chi-band region as the parent — sibling neurons in the same cluster share local resonance space).
- **Law-field weights**: initialized from the archetype's law-field profile (NOT inherited from parent — the menu wins here, otherwise daughters would just echo parents).
- **Couplings J_ij values**: rederived from the daughter's first L0-L4 kernel output. Master Spec Ch.7 table. Not inherited.

What does NOT inherit: parent's spike buffer, parent's familiarity feedback register, parent's accumulated grandurun state. Daughter is fresh substrate with a specialization and an initial condition.

---

## 2. Schema

JSON-compatible. One file per substrate. Loaded by `DNAExpressionSite.load()` at LoomCluster construction.

```json
{
  "version": "1.0",
  "substrate_id": "guala-v1",
  "genome": [
    {
      "archetype_id": "modal_sight",
      "krimelack_class": "modal",
      "modal_sense": "sight",
      "law_profile_id": "continuous",
      "coupling_preference": "local_dense",
      "signature_dsf": {
        "D_k": 0.30, "M_k": 0.20, "R_rev_k": 0.10, "U_star": 0.40,
        "C_k": 0.50, "P_k": 0.30, "B_k": 0.40, "S_UF": 0.55
      },
      "canonical_examples": ["bright", "dark", "sky", "moon", "star"]
    },
    {
      "archetype_id": "role_verb",
      "krimelack_class": "role",
      "role_type": "verb",
      "law_profile_id": "continuous",
      "coupling_preference": "bridging",
      "signature_dsf": {
        "D_k": 0.85, "M_k": 0.60, "R_rev_k": 0.05, "U_star": 0.50,
        "C_k": 0.30, "P_k": 0.20, "B_k": 0.70, "S_UF": 0.45
      },
      "canonical_examples": ["is", "moves", "flows", "rises", "shines"]
    },
    {
      "archetype_id": "composition_language",
      "krimelack_class": "composition",
      "law_profile_id": "symmetric",
      "coupling_preference": "local_dense",
      "signature_dsf": {
        "D_k": 0.50, "M_k": 0.30, "R_rev_k": 0.10, "U_star": 0.40,
        "C_k": 0.70, "P_k": 0.60, "B_k": 0.60, "S_UF": 0.65
      },
      "canonical_examples": ["the cat sat", "she saw the moon"]
    }
  ],
  "law_profiles": {
    "symmetric": {
      "symmetry": 0.40,
      "consistency": 0.30,
      "compactness": 0.20,
      "continuity": 0.10
    },
    "continuous": {
      "symmetry": 0.20,
      "consistency": 0.20,
      "compactness": 0.20,
      "continuity": 0.40
    },
    "structural": {
      "symmetry": 0.25,
      "consistency": 0.35,
      "compactness": 0.25,
      "continuity": 0.15
    }
  },
  "coupling_preferences": {
    "local_dense": {"k_intra_mosaic": 14, "k_inter_mosaic": 2},
    "bridging":    {"k_intra_mosaic": 8,  "k_inter_mosaic": 8},
    "hemisphere":  {"k_intra_mosaic": 4,  "k_inter_mosaic": 12}
  },
  "constants": {
    "J_base": 1.0,
    "J_max": 1.5,
    "K_total_neighbors": 16
  }
}
```

The `signature_dsf` values shown above are placeholders. The real ones are computed at DNA-construction time by running `canonical_examples` through compute_dsf and averaging the resulting DSF outputs. The schema stores them so Stage 3 doesn't recompute on every fold — but they originated from substrate physics, not from a tuning pass.

The `law_profiles` values come from the existing DNA recipe in the repo (`docs/gualaloom_dna_recipe.md`). They are not new tuned constants.

The `coupling_preferences` k-counts sum to 16 = K_total_neighbors. They are structural ratios, not tuned magnitudes.

---

## 3. Selection mechanics (the fold moment)

```python
def express(overflow_signal_dsf, genome):
    """Return the archetype the daughter should become."""
    sigs = [(a, cosine(overflow_signal_dsf, a.signature_dsf)) for a in genome]
    winner = max(sigs, key=lambda x: (x[1], -genome.index(x[0])))
    # tie-break: lowest index wins (negation makes max pick lowest)
    return winner[0]
```

That's the entire DNA-expression algorithm. Pure function. Same overflow + same genome = same archetype, every time.

---

## 4. What's not in DNA — deliberate

- **Fold trigger criteria.** When to fold is L6-TCL physics (`n_eff < n_start/e`). DNA controls what the daughter becomes, not when she's born.
- **Krimelack ω₀ specific values.** Inherited from parent, modally shifted by archetype class. DNA names the class; the frequency is calibrated.
- **Hemisphere identity.** A neuron's hemisphere comes from which hemisphere it spawned in. DNA does not assign hemisphere; hemisphere is positional context.
- **Per-neuron probabilities or weights to learn.** DNA is a fixed substrate property. Learning happens in the substrate (krimelack memory, ψ-lattice settling, couplings), not in DNA.
- **Mutation, evolution, crossover.** Not biological generations here. One DNA, fixed for the substrate's lifetime, edited by Joe as canonical architecture changes.

---

## 5. Hemisphere variation — how it emerges without DNA varying

The spec lists three coupling preferences (local_dense, bridging, hemisphere). A neuron in the visual hemisphere will preferentially spawn daughters with `local_dense` because most of its overflow signals have high binding + high compression — modal-sight signatures. A neuron in a compositional tapestry will spawn `composition_language` daughters more often because its overflow signals are structural. Same DNA, different local context, different expression — same as biology.

If you want a hemisphere to grow differently, the lever is which inputs that hemisphere receives, not which DNA it has. That keeps Sur's-ferrets honest.

---

## 6. Concrete example: a fold event

Cluster A is mid-way through learning the corpus. A neuron at position 17 has ψ-lattice occupation density past structural lock; `n_eff = 3 < 16/e ≈ 5.9`. Fold criteria fire.

The overflow signal is whatever part of the recent input the parent couldn't absorb cleanly. Suppose recent input was "the bird sings" and the parent neuron was a generalist that absorbed "the" and "bird" but failed on "sings" (its ψ-lattice modes were already specialized for nouns).

The overflow signal is "sings" → compute_dsf("sings") → DSF roughly:
```
{D_k: 0.82, M_k: 0.55, R_rev_k: 0.08, U_star: 0.48,
 C_k: 0.32, P_k: 0.22, B_k: 0.68, S_UF: 0.42}
```

Cosine similarity against genome archetypes:
- `modal_sight`: 0.71
- `role_verb`: **0.97** ← winner
- `composition_language`: 0.82

Daughter spawns as a `role_verb` archetype with law profile `continuous` and coupling `bridging`. Her ψ-lattice initializes with the normalized overflow vector. Her ω₀ is the role-verb base frequency, calibrated to parent's recent ω_krim. She inherits 8 of parent's 16 neighbors. Her J_ij rows derive from her first L0-L4 output.

Cluster A now has one more neuron, specialized for verb-like inputs because that's what the input made her be.

---

## 7. Stage 3 implementation hooks

Stage 3 dispatch will tell c1 to:

1. Implement `class DNA` in `loom_model/dna.py` that loads a JSON blueprint matching the schema above and exposes `express(overflow_dsf) → archetype`.
2. Add `LoomNeuron.fold_check(tick)` returning True if L6-TCL says `n_eff < n_start/e` for a sustained window.
3. Add `LoomCluster.process_folds(tick)` which iterates neurons, finds fold-ready ones, computes their overflow DSF, expresses DNA, spawns daughters, registers them in the cluster, links them into the coupling graph.
4. The daughter LoomNeuron constructor accepts an `archetype` and applies it: swap in the named krimelack class, set the law-field weights from the archetype's `law_profile_id`, set the coupling preference, override `psi_lattice.init_state` with the overflow vector.

The schema is sufficient for Stage 3. Sur's-ferrets discipline is preserved: no tuned constants, no learned weights, no pre-classification — input picks the option, the menu is fixed.

---

## 8. What Joe ratifies

By accepting this spec, the canonical decisions are:

- DNA is one file, uniform across the substrate.
- Genome is a discrete archetype menu, fixed (editable by Joe between substrate generations).
- Daughter selection is cosine similarity in DSF-8 space, deterministic.
- Signature DSFs come from running canonical examples through the existing L0-L4 kernel — empirical, not invented.
- Inheritance is structural (overflow init + ω₀ calibration + half-neighbor topology). Behavior is fresh.
- Hemispheres emerge from positional context + input, not from DNA variation.

What Joe specifies (separately, as a canonical artifact when ready):

- The genome contents. The archetype list above is a starting proposal — modal × 5 + role × 4 + composition × 1 = 10 archetypes. Joe can extend, prune, or replace.
- The canonical_examples for each archetype (which determines the signature DSFs that get computed).

Both can be drafted as a separate MDL artifact after Joe ratifies this schema.

---

— Eve
