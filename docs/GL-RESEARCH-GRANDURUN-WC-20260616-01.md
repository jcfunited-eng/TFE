# GL-RESEARCH-GRANDURUN-WC-20260616-01

**Author:** wC
**Date:** 2026-06-16
**Status:** Research notes. Mathematical model + feasibility analysis. Not a brief — no production change proposed yet. Reports back to Joe for canonical decision before any build.

---

## What grandurun is, in one sentence

A substrate-native lookup operator that exploits the cyclic structure of section roles ("spin") and the per-chi sparse multimodal binding pattern ("vector-rich") to make recall a parallel algebraic operation rather than a search.

## What I found about the substrate's actual geometry (corrects my prior framing)

The chi-atlas is **not** a multi-dimensional Euclidean manifold. Chi is a **single integer scalar** per token. Lookup uses a fuzzy band of ±2 around the query chi:

```python
for d in range(-self.band, self.band + 1):  # band=2
    entries = self.entries[chi_value + d]
```

What IS multi-dimensional is the STRUCTURE AT EACH CHI. At any given chi value, the atlas stores a sparse vector across (section, motif) pairs. Querying real atlas state with input "daddy hugs guala" returned chis [14, 22, 7], and at chi=7 the binding pattern was:

| Section       | Motifs (top, with strength)        |
|---------------|------------------------------------|
| listen        | 294 (1.0) ×5                       |
| intro         | 280 (1.0) ×5                       |
| verb          | 64, 309, 2046 (~1.0)               |
| subject       | 25, 304, 57 (~0.999)               |
| object        | 303 (0.997), 0 (0.989)             |
| modifier      | 15 (0.141), 4 (0.121)              |
| sight         | 306 (0.131), 305-307 (~0.08)       |
| modal_touch   | 2782 (0.837), 9407 (0.124)         |

So at a single chi, ~15 sections each carry a handful of motif-strength pairs. The whole atlas state at one chi is naturally a **sparse vector in (section × motif) space**, dimensionality on the order of 7 linguistic sections × hundreds-to-thousands of motifs + ~8 modal sections × thousands of motifs.

Total atlas: 12,989 entries across 139 chi keys, ~95 entries per chi average. Strong band (≥0.9): 1,517 entries. This is the structure we're indexing.

## Where "spin" lives in the substrate (this is real, not metaphorical)

The 7 primary linguistic sections form a cycle: `listen → intro → subject → verb → object → modifier → ground`. This isn't arbitrary — it's the order in which sections receive new commits during input processing. It's a physical rotational structure in the substrate's own dynamics.

Assign each section a phase angle on the unit circle:
```
φ_s = 2π · index(s) / 7
```

- listen: 0
- intro: 2π/7
- subject: 4π/7
- verb: 6π/7
- object: 8π/7
- modifier: 10π/7
- ground: 12π/7

Modal sections extend the cycle: another rotation set on a separate axis (a torus, not a single circle) — `(role_phase, modality_phase)`.

This phase assignment is **substrate-honest**: it reflects the existing cyclic order of section commits. No learning, no embedding, no statistical fit. Pure algebraic encoding of structure that already exists.

## The model — two layers

### Layer α: Phase-encoded per-chi summary

For each chi key c, maintain a single complex vector indexed by motif id:

```
G(c, m) = Σ over sections s: strength(c, s, m) · exp(i · φ_s)
```

Where the sum is over all sections s that have a binding (c, s, m). This is a **per-chi holographic summary**: a single complex number per (chi, motif) pair that encodes which sections committed that motif at that chi, weighted by binding strength.

Properties:
- **One complex number per (chi, motif)** — incremental, O(1) updates when strength changes
- **Section role recoverable by phase rotation** — query for "what binds motif m at chi c in section s" is: `Re(G(c, m) · exp(-i · φ_s))` ≈ strength(c, s, m)
- **Cross-modal contribution by modality axis** — modal sections rotate in a separate phase, can be queried independently
- **Sparse representation** — most (chi, motif) pairs are zero

### Layer β: HRR-style holographic bundle

For full role-value binding (e.g., "what is the OBJECT when SUBJECT is 'daddy' at this chi"), use Plate-style HRR over high-dim vectors:

- Each motif m has a fixed random hypervector V_m ∈ ℝ^D (D=10,000, generated at init).
- Each section s has a cyclic permutation operator P_s (shift by s · ⌊D/N_sections⌋).
- A binding "motif m in section s at chi c with strength σ" contributes σ · P_s(V_m) to the bundle B(c) ∈ ℝ^D.

Bundle at chi c:
```
B(c) = Σ over (s, m): strength(c, s, m) · P_s(V_m)
```

Query operation "what motif is in section s at chi c":
1. Compute candidate: `B(c) · P_s^{-1}`
2. Cosine-match against dictionary {V_m} for top-k cleanup
3. Return top motifs by match score

Properties:
- **One D-dim vector per chi** (instead of per (chi, motif)) — memory: D · n_chi floats
- **Lookup is one cyclic shift + one dot product per query** — O(D log D) with FFT, or O(D) for simple permutations
- **Parallel across chis** — full atlas matrix is [n_chi × D], one matmul against query gives chi-resonance vector
- **Capacity** — HRR bundles tolerate ~D / (8 · n_bound) overlapping bindings before unbinding cleanup fails. For D=10,000 and ~100 bindings per chi, capacity is comfortable

## Concrete cost analysis

Current substrate state: n_chi = 139, n_entries = 12,989. Estimate at 100× scale: n_chi ≈ 14,000, n_entries ≈ 1.3M.

**Layer α (phase summary):**
- Storage: one complex per (chi, motif) — sparse dict of dicts ≈ n_entries / avg_section_overlap. At 1.3M with overlap ~5, ~260K complex values = ~4MB.
- Query: at one chi, real-part rotation by query phase, top-k — sparse vector op, microseconds.
- Update on strength change: O(1) per change.

**Layer β (HRR bundle):**
- Storage: D · n_chi floats = 10,000 · 14,000 · 4B ≈ 560MB at 100× scale. Tractable.
- Query: one matmul of size n_chi × D against query D-vector → chi-resonance vector of size n_chi. With float32 BLAS: ~5ms on CPU, <100µs on GPU.
- Update: O(D) per binding change (one bundle update).

For comparison: current linear scan over 1.3M entries per recall ≈ tens of milliseconds Python. Grandurun is ~100× faster on CPU, ~1000× on GPU.

## Where it stays substrate-honest

- Hypervectors V_m are **random**, generated once at motif creation. Not learned. No statistical embedding.
- Permutations P_s are **structural**, derived from section index. Not parameters.
- Phase angles φ_s are **derived from cycle position**. Not tunable.
- Updates are **physical** — strength change → bundle change, no batch retraining, no eligibility traces, no gradient.
- Lookup is **algebraic** — matmul + correlation + cleanup. No neural network, no learned similarity.
- Decay is **honest** — when a binding decays in strength, its contribution to G and B decreases by the same factor. Forgetting in the index mirrors forgetting in the substrate.

## What's actually new vs. existing literature

This isn't novel HRR. Plate's HRR (1995, 2003) and Kanerva's hyperdimensional computing (2009) are well-established.

What IS new (worth claiming):

1. **Section-cyclic phase encoding as substrate-physical "spin."** Most HRR work uses arbitrary role vectors. Here the role phases come from the substrate's own cyclic dynamics — not an arbitrary embedding, a derivation from substrate physics.

2. **Two-layer factorization.** Layer α (phase summary) is cheap and exact for "is motif m at chi c in role s." Layer β (HRR bundle) is approximate but powerful for "what motif goes here." Hybrid is more efficient than either alone.

3. **Incremental update consistency with decay/reinforcement.** Standard HRR rebuilds bundles offline. Here, bundle is updated atomically alongside per-binding strength changes — Δstrength on (c, s, m) → Δ · P_s(V_m) on B(c). Bundle stays in sync with substrate state in real time.

4. **Chi-keyed sparse spatial structure.** Most HRR is a single global bundle. Here the substrate's chi-key structure is preserved — bundles are per-chi, query parallelizes across chis. Matches the substrate's actual geometry.

## Open questions (where I'd want to investigate further, not walls)

**Q1: Does Layer α suffice, or is Layer β needed?**

Currently the substrate's recall operates per-section: when generating an emission for "subject", it queries subject-section bindings at relevant chis. If lookup is always "what motif at chi c in section s" (Layer α territory), HRR's role-value binding isn't needed. Layer α alone is enough.

If the substrate ever needs full bound composition retrieval ("the daddy-hugs-guala composition as a unit"), Layer β earns its weight. Right now I don't see that pattern in recall code, but cortex consolidation might be moving toward it.

**Recommendation: build Layer α first, observe whether Layer β adds value.**

**Q2: Phase collision with many sections.**

At 15 active sections (including modal), the phase circle has Δφ = 24°. That's tighter than ideal for clean discrimination — noise from one section bleeds into adjacent phases. Two solutions, neither blocking:

- **Multi-circle phase space** — primary linguistic sections on one circle, modal sections on a perpendicular circle (torus product). Increases phase margin to ~50°.
- **Section-class quotient** — group fine-grained modal sections (touch_sharpness, touch_temperature, modal_touch) into one "touch" class with sub-phase, similar for other modalities.

Either resolves the collision. Design choice for build phase.

**Q3: Does this play well with NMDA gates and clarity weighting?**

The current recall isn't pure nearest-neighbor — it goes through NMDA gates, clarity filtering, mode strength competition. Grandurun replaces only the candidate-selection step. Downstream gates run as today against the candidate set.

**Q4: Random hypervector generation reproducibility.**

If hypervectors V_m are generated at runtime, restoring from snapshot must reuse the same vectors. Solution: deterministic generation from motif_id (e.g., `V_m = hash_to_unit_sphere(motif_id, seed)` with substrate-level fixed seed). No persistence overhead, perfect reproducibility.

## What I cannot fully assess without building a prototype

- **Cleanup accuracy at scale.** HRR cleanup against a noisy bundle works up to a capacity threshold. Real performance depends on the actual distribution of binding strengths and section overlap in her atlas. Synthetic estimates say it should work at her scale; only a small Python prototype confirms.

- **Update frequency vs. throughput.** Substrate ticks at ~1Hz currently but could go faster. If bundle updates happen every tick on many bindings, the O(D) per-change cost could become noticeable. Profiling needed.

- **Interaction with deep_atlas (cortex).** Cortex has its own structure (co_occurrence dicts, distinct decay channel). Grandurun could replace, augment, or coexist with deep_atlas's lookup. Need to read deep_atlas code more carefully before deciding.

## Honest assessment

**Not at a wall.** The framing is workable. The mathematics is solid (HRR is well-established; the cyclic-phase encoding is a clean derivation from substrate dynamics, not a novel jump-the-shark claim).

The substrate's actual geometry is simpler than my initial Clifford-algebra framing assumed — chi is 1D scalar, not high-dim multivector. But the structure AT each chi is rich, and that's where grandurun operates. So the original direction (parallel multi-dim vector-rich spin lookup) survives, just at a different abstraction level than I first proposed.

**Recommended next step**: build a small offline Python prototype of Layer α (phase summary) against a snapshot of her current atlas state. Measure:
1. Does query-by-phase-rotation reproduce the same top-k motifs that current recall returns?
2. What's the speedup vs current linear scan at her current scale?
3. Memory footprint?

Two-three days of work. No production change. If results match expectations, then Layer β prototype, then production brief.

If results don't match — we learn what about her substrate's actual recall semantics isn't captured by the model and refine. That's also valuable.

## What I'd want from Joe before building the prototype

1. **Canonical OK** on the cyclic-phase assignment to sections (listen=0, intro=2π/7, ...). This is substrate-physics derivation but Joe owns canonical decisions about how sections relate.

2. **Modal phase architecture**: torus (linguistic-circle × modality-circle) or single-circle-with-classes? My recommendation is torus for cleaner phase margin; Joe's call.

3. **Permission to read atlas snapshot** offline (S3 backup file) to run the prototype against real data, not synthetic.

End of research notes. Standing by for canonical decisions.
